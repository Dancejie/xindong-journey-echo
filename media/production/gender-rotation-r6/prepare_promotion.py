#!/usr/bin/env python3
"""Prepare or apply an identity-safe R6 runtime-media promotion.

The default mode is a read-only dry run.  The script accepts only assets named
in a human visual-QA allowlist, verifies their bytes, derives runtime aliases,
and emits a reviewable plan.  ``--apply`` is deliberately guarded and performs
an atomic, no-overwrite copy plus manifest merge only after the same preflight
has passed for every asset.

This script never calls a media provider and never changes the R6 planning
manifest or budget approval files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


APPLY_CONFIRMATION = "PROMOTE_R6_VISUALLY_APPROVED_ASSETS"
PASSED = {"passed", "approved", "human-reviewed-passed"}
GENDER_ZH = {"female": "女性", "male": "男性"}


class PromotionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromotionError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromotionError(f"invalid JSON file: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"JSON root must be an object: {path}")
    return value


def resolve_inside(project_root: Path, raw_path: str, label: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    if candidate.is_symlink():
        raise PromotionError(f"{label} may not be a symlink: {raw_path}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise PromotionError(f"{label} escapes project root: {raw_path}") from exc
    return resolved


def media_probe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise PromotionError(f"ffprobe failed for {path}: {detail.strip()}") from exc
    probe = json.loads(result.stdout)
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not video:
        raise PromotionError(f"candidate has no video stream: {path}")
    return {
        "duration": round(float(probe.get("format", {}).get("duration") or 0), 6),
        "videoCodec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "hasAudio": audio is not None,
        "audioCodec": audio.get("codec_name") if audio else None,
    }


@dataclass(frozen=True)
class SourceSpec:
    source_type: str
    source_id: str
    event_asset_id: str | None
    scheme_id: str | None
    expected_name: str
    planned_cast: tuple[str, ...]
    lead_id: str | None
    requires_audio: bool


def source_specs(plan: dict[str, Any], runtime: dict[str, Any]) -> dict[str, SourceSpec]:
    schemes = {item["id"]: item for item in plan.get("schemes", []) if isinstance(item, dict) and item.get("id")}
    specs: dict[str, SourceSpec] = {}
    for shot in plan.get("shots", []):
        if not isinstance(shot, dict) or not shot.get("id"):
            continue
        kind = str(shot.get("kind") or "")
        lead = str(shot.get("leadCharacterId") or "") or None
        support = tuple(str(item) for item in shot.get("supportCharacterIds", []) if str(item))
        planned_cast = tuple(dict.fromkeys(([lead] if lead else []) + list(support)))
        specs[shot["id"]] = SourceSpec(
            source_type="generated",
            source_id=shot["id"],
            event_asset_id=shot.get("eventAssetId"),
            scheme_id=shot.get("schemeId"),
            expected_name=str(shot.get("output_name") or ""),
            planned_cast=planned_cast,
            lead_id=lead,
            requires_audio=bool(shot.get("generate_audio")) if kind == "event-rotation-candidate" else False,
        )
    for composite in plan.get("localComposites", []):
        if not isinstance(composite, dict) or not composite.get("id"):
            continue
        scheme = schemes.get(composite.get("schemeId"), {})
        lead = str(scheme.get("leadId") or "") or None
        support = str(scheme.get("supportId") or "") or None
        specs[composite["id"]] = SourceSpec(
            source_type="local-composite",
            source_id=composite["id"],
            event_asset_id=composite.get("eventAssetId"),
            scheme_id=composite.get("schemeId"),
            expected_name=str(composite.get("output_name") or ""),
            planned_cast=tuple(item for item in (lead, support) if item),
            lead_id=lead,
            requires_audio=True,
        )

    runtime_assets = {item.get("id"): item for item in runtime.get("assets", []) if isinstance(item, dict) and item.get("id")}
    # F-A reuses each approved base asset except its held introduction.  Its
    # original identityCast is authoritative and is intentionally not replaced
    # by the scheme support person.
    for asset_id, asset in runtime_assets.items():
        if not isinstance(asset_id, str) or asset_id.startswith("CHAR-") or "--" in asset_id:
            continue
        if asset.get("status") not in {"ready", "approved-runtime"}:
            continue
        cast = tuple(str(item) for item in asset.get("identityCast", []) if str(item))
        if "jiangmi" not in cast:
            continue
        source_id = f"reuse:{asset_id}:F-A-jiangmi"
        specs[source_id] = SourceSpec(
            source_type="existing-runtime",
            source_id=source_id,
            event_asset_id=asset_id,
            scheme_id="F-A-jiangmi",
            expected_name=Path(str(asset.get("path") or "")).name,
            planned_cast=cast,
            lead_id="jiangmi",
            requires_audio=bool(asset.get("audio", {}).get("hasAudio", True)),
        )
    return specs


def runtime_id_for(spec: SourceSpec) -> str:
    if spec.source_type == "generated" and not spec.event_asset_id:
        if not spec.lead_id:
            raise PromotionError(f"portrait source has no character: {spec.source_id}")
        return f"CHAR-{spec.lead_id}-portrait"
    if not spec.event_asset_id or not spec.scheme_id:
        raise PromotionError(f"event source lacks event/scheme: {spec.source_id}")
    return f"{spec.event_asset_id}--rotation-{spec.scheme_id}"


def prepare(project_root: Path, plan_path: Path, runtime_path: Path, allowlist_path: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    plan_path = plan_path.resolve()
    runtime_path = runtime_path.resolve()
    allowlist_path = allowlist_path.resolve()
    plan = load_json(plan_path)
    runtime = load_json(runtime_path)
    allowlist = load_json(allowlist_path)
    if allowlist.get("schemaVersion") != "heart-journey/r6-visual-qa-allowlist-v1":
        raise PromotionError("unsupported visual-QA allowlist schema")
    plan_hash = sha256_file(plan_path)
    if allowlist.get("planningManifestSha256") != plan_hash:
        raise PromotionError("allowlist planningManifestSha256 does not match the immutable R6 plan")
    if plan.get("doNotSubmit") is not True:
        raise PromotionError("R6 planning manifest must remain doNotSubmit=true")

    specs = source_specs(plan, runtime)
    known_character_ids = {
        str(item.get("leadCharacterId")) for item in plan.get("shots", []) if isinstance(item, dict) and item.get("leadCharacterId")
    }
    known_character_ids.update(
        str(character_id)
        for spec in specs.values()
        for character_id in spec.planned_cast
    )
    known_character_ids.update(
        str(character_id)
        for scheme in plan.get("schemes", []) if isinstance(scheme, dict)
        for character_id in (scheme.get("leadId"), scheme.get("supportId"))
        if character_id
    )
    runtime_ids = {str(item.get("id")) for item in runtime.get("assets", []) if isinstance(item, dict) and item.get("id")}
    items = allowlist.get("approvedAssets")
    if not isinstance(items, list) or not items:
        raise PromotionError("allowlist approvedAssets must be a non-empty array")
    if len(items) != len(specs):
        raise PromotionError(
            f"allowlist must cover the complete source set: {len(items)} != {len(specs)}"
        )

    planned: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    seen_runtime: set[str] = set()
    for index, approval in enumerate(items):
        if not isinstance(approval, dict):
            raise PromotionError(f"allowlist item {index} must be an object")
        source_id = str(approval.get("sourceId") or "")
        if source_id in seen_sources:
            raise PromotionError(f"duplicate allowlist sourceId: {source_id}")
        seen_sources.add(source_id)
        spec = specs.get(source_id)
        if not spec:
            raise PromotionError(f"allowlist sourceId is not in the immutable R6 plan/runtime reuse set: {source_id}")
        if str(approval.get("visualQaVerdict") or "").lower() not in PASSED:
            raise PromotionError(f"visual QA has not passed: {source_id}")
        identity_cast = tuple(str(item) for item in approval.get("identityCast", []) if str(item))
        if not identity_cast or len(set(identity_cast)) != len(identity_cast):
            raise PromotionError(f"identityCast must be non-empty and unique: {source_id}")
        if any(item not in known_character_ids for item in identity_cast):
            raise PromotionError(f"identityCast contains unknown character: {source_id}")
        if spec.source_type == "existing-runtime":
            if identity_cast != spec.planned_cast:
                raise PromotionError(f"reuse must preserve original identityCast exactly: {source_id}")
        else:
            if spec.lead_id not in identity_cast:
                raise PromotionError(f"reviewed clip does not contain its rotation lead: {source_id}")
            if not set(identity_cast).issubset(set(spec.planned_cast)):
                raise PromotionError(f"identityCast overclaims an unplanned/unreviewed person: {source_id}")
            if spec.source_type == "local-composite" and set(identity_cast) != set(spec.planned_cast):
                raise PromotionError(f"local composite must visibly verify both planned inputs: {source_id}")
        if spec.requires_audio and str(approval.get("audioQaVerdict") or "").lower() not in PASSED:
            raise PromotionError(f"required first-play audio QA has not passed: {source_id}")

        candidate = resolve_inside(project_root, str(approval.get("candidatePath") or ""), f"candidatePath for {source_id}")
        if not candidate.is_file():
            raise PromotionError(f"candidate does not exist: {candidate}")
        if candidate.name != spec.expected_name:
            raise PromotionError(f"candidate filename mismatch for {source_id}: {candidate.name} != {spec.expected_name}")
        actual_hash = sha256_file(candidate)
        if str(approval.get("sha256") or "").lower() != actual_hash:
            raise PromotionError(f"candidate sha256 mismatch: {source_id}")
        probe = media_probe(candidate)
        if spec.requires_audio and not probe["hasAudio"]:
            raise PromotionError(f"required audio stream is absent: {source_id}")
        if not spec.requires_audio and approval.get("requireSilent") is True and probe["hasAudio"]:
            raise PromotionError(f"silent-loop candidate unexpectedly contains audio: {source_id}")

        runtime_id = runtime_id_for(spec)
        if runtime_id in seen_runtime:
            raise PromotionError(f"two sources map to one runtime id: {runtime_id}")
        seen_runtime.add(runtime_id)
        if runtime_id in runtime_ids:
            raise PromotionError(f"runtime manifest already contains target id; overwrite refused: {runtime_id}")
        destination = project_root / "frontend" / "public" / "media" / "video" / f"{runtime_id}.mp4"
        if destination.exists():
            raise PromotionError(f"runtime destination already exists; overwrite refused: {destination}")

        scheme = next((item for item in plan.get("schemes", []) if item.get("id") == spec.scheme_id), None)
        lead_gender = GENDER_ZH.get(str((scheme or {}).get("gender") or "")) if spec.scheme_id else None
        manifest_asset = {
            "id": runtime_id,
            "kind": "dynamic-portrait" if not spec.event_asset_id else "r6-gender-rotation-event",
            "path": f"/media/video/{runtime_id}.mp4",
            "sha256": actual_hash,
            "duration": probe["duration"],
            "status": "approved-runtime",
            "qaVerdict": "passed",
            "visualQa": "human-reviewed-r6-allowlist",
            "visualQaEvidence": str(allowlist_path.relative_to(project_root)),
            "identityCast": list(identity_cast),
            "identityScope": "single" if len(identity_cast) == 1 else "group",
            "sourceType": spec.source_type,
            "sourceId": source_id,
        }
        if spec.scheme_id:
            manifest_asset.update({
                "baseAssetId": spec.event_asset_id,
                "rotationSlot": spec.scheme_id,
                "leadGender": lead_gender,
                "leadCharacterId": spec.lead_id,
            })
        if probe["hasAudio"]:
            manifest_asset["audio"] = {"hasAudio": True, "mode": "native-first-play", "qaVerdict": "passed"}
        planned.append({
            "source": str(candidate.relative_to(project_root)),
            "destination": str(destination.relative_to(project_root)),
            "runtimeAsset": manifest_asset,
            "probe": probe,
        })

    missing_sources = sorted(set(specs) - seen_sources)
    if missing_sources:
        preview = ", ".join(missing_sources[:5])
        raise PromotionError(f"allowlist is missing planned sources: {preview}")

    return {
        "schemaVersion": "heart-journey/r6-promotion-plan-v1",
        "mode": "dry-run",
        "planningManifest": str(plan_path.relative_to(project_root)),
        "planningManifestSha256": plan_hash,
        "runtimeManifest": str(runtime_path.relative_to(project_root)),
        "runtimeManifestSha256Before": sha256_file(runtime_path),
        "visualQaAllowlist": str(allowlist_path.relative_to(project_root)),
        "assetCount": len(planned),
        "assets": planned,
    }


def apply(project_root: Path, runtime_path: Path, promotion: dict[str, Any]) -> None:
    if sha256_file(runtime_path) != promotion["runtimeManifestSha256Before"]:
        raise PromotionError("runtime manifest changed after preflight")
    runtime = load_json(runtime_path)
    destinations = [project_root / item["destination"] for item in promotion["assets"]]
    if any(path.exists() for path in destinations):
        raise PromotionError("a runtime destination appeared after preflight; overwrite refused")
    copied: list[Path] = []
    try:
        for item, destination in zip(promotion["assets"], destinations):
            source = project_root / item["source"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as src, destination.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            shutil.copystat(source, destination)
            if sha256_file(destination) != item["runtimeAsset"]["sha256"]:
                raise PromotionError(f"post-copy hash mismatch: {destination}")
            copied.append(destination)
        runtime.setdefault("assets", []).extend(item["runtimeAsset"] for item in promotion["assets"])
        runtime["generationRound"] = "seedance-r6-gender-rotation-reviewed"
        runtime["qaVerdict"] = "r6-assets-promoted-from-explicit-visual-qa-allowlist"
        fd, raw_tmp = tempfile.mkstemp(prefix=runtime_path.name + ".", suffix=".tmp", dir=runtime_path.parent)
        tmp_path = Path(raw_tmp)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(runtime, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, runtime_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception:
        for path in copied:
            path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    project_default = here.parents[2]
    parser.add_argument("allowlist", type=Path)
    parser.add_argument("--project-root", type=Path, default=project_default)
    parser.add_argument("--plan", type=Path, default=here / "manifest.r6.json")
    parser.add_argument("--runtime-manifest", type=Path, default=here.parents[1] / "runtime-media-manifest.json")
    parser.add_argument("--output", type=Path, help="optional dry-run plan JSON")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args(argv)
    project_root = args.project_root.resolve()
    try:
        promotion = prepare(
            project_root,
            args.plan.resolve(),
            args.runtime_manifest.resolve(),
            args.allowlist.resolve(),
        )
        if args.apply:
            if args.confirm != APPLY_CONFIRMATION:
                raise PromotionError(f"--apply requires --confirm {APPLY_CONFIRMATION}")
            apply(project_root, args.runtime_manifest.resolve(), promotion)
            promotion["mode"] = "applied"
        rendered = json.dumps(promotion, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        sys.stdout.write(rendered)
        return 0
    except PromotionError as exc:
        sys.stderr.write(f"R6_PROMOTION_BLOCKED: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
