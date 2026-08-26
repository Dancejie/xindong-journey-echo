#!/usr/bin/env python3
"""Validate R5 local Seedance inputs for exact 178/178 completeness.

This validator is network-free.  It verifies semantic coverage, local file and
hash bindings, the five-window 15-second director plan, reference-image shape,
identity names, state contracts and the hard doNotSubmit gate.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parent
MATRIX = ROOT / "runtime-variant-matrix.json"
MANIFEST = ROOT / "manifest.r5.json"
PROMPTS = ROOT / "prompts-r5"
REFS = ROOT / "refs-r5"

DISPLAY = {
    "shenmo": "沈墨",
    "linyu": "林屿",
    "chengye": "程野",
    "guyan": "顾言",
    "jiangwan": "江晚",
    "jiangmi": "姜米",
    "sunnian": "苏念",
    "chensu": "陈叙",
}

TIMECODES = ["0-3s", "3-6s", "6-9s", "9-12s", "12-15s"]


class ValidationError(RuntimeError):
    pass


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot load {path}: {error}") from error


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text_sha(body)


def resolve(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        raise ValidationError(f"absolute path is forbidden in manifest: {relative}")
    result = (ROOT / path).resolve()
    project = ROOT.parents[2].resolve()
    if not result.is_relative_to(project):
        raise ValidationError(f"path escapes project: {relative}")
    if not result.is_file():
        raise ValidationError(f"local input is missing: {relative}")
    return result


def check() -> dict[str, Any]:
    matrix = load(MATRIX)
    manifest = load(MANIFEST)
    required = {
        item["targetAssetId"]: item
        for item in matrix["masters"]
        if item["status"] == "requiresGeneration"
    }
    if len(required) != 178:
        raise ValidationError(f"runtime matrix requiresGeneration count is {len(required)}, expected 178")
    if matrix["summary"] != {
        **matrix["summary"],
        "generationGap": 178,
    }:
        raise ValidationError("runtime matrix summary generationGap changed")
    if manifest.get("doNotSubmit") is not True or manifest.get("defaults", {}).get("doNotSubmit") is not True:
        raise ValidationError("manifest and defaults must both keep doNotSubmit=true")
    policy = manifest.get("policy", {})
    if policy.get("expectedSemanticMasterGap") != 178:
        raise ValidationError("manifest expectedSemanticMasterGap must be 178")
    if policy.get("expectedTaskCount") != 198:
        raise ValidationError("manifest expectedTaskCount must be 198 provider jobs")
    if policy.get("expectedLocalCompositeOutputs") != 4:
        raise ValidationError("manifest expectedLocalCompositeOutputs must be 4")
    if manifest.get("sourceBindings", {}).get("runtimeVariantMatrix", {}).get("sha256") != sha(MATRIX):
        raise ValidationError("runtime matrix hash binding is stale")

    shots = manifest.get("shots")
    if not isinstance(shots, list) or len(shots) != 198:
        raise ValidationError(f"manifest shot count is {len(shots) if isinstance(shots, list) else 'not-array'}, expected 198")
    provider_job_ids = [shot.get("id") for shot in shots]
    if len(provider_job_ids) != len(set(provider_job_ids)):
        raise ValidationError("manifest contains duplicate provider job ids")
    provider_job_id_set = set(provider_job_ids)
    current_eight_targets = {
        target for target, semantic in required.items() if semantic["routingMode"] == "current-eight"
    }
    d1a3b_target = "D1-A3B-cast-first-impressions--group-current-eight"
    if len(current_eight_targets) != 4 or d1a3b_target not in current_eight_targets:
        raise ValidationError("runtime matrix current-eight target contract changed")

    expected_prompt_names: set[str] = set()
    expected_composite_paths: set[Path] = set()
    semantic_route_counts: Counter[str] = Counter(item["routingMode"] for item in required.values())
    provider_role_counts: Counter[str] = Counter()
    audio_counts: Counter[str] = Counter()
    intro_count = 0
    prompt_bytes = 0
    reference_paths: set[Path] = set()
    direct_semantic_targets: set[str] = set()
    atom_characters_by_target: dict[str, set[str]] = {target: set() for target in current_eight_targets - {d1a3b_target}}

    for index, shot in enumerate(shots):
        target = shot["semanticTargetAssetId"]
        semantic = required[target]
        if shot.get("targetAssetId") != target or shot.get("targetRuntimeAssetId") != target:
            raise ValidationError(f"shot[{index}] {shot.get('id')} semantic target binding mismatch")
        provider_role = shot.get("providerJobRole")
        provider_role_counts[provider_role] += 1
        for key in (
            "eventId",
            "servedEventIds",
            "routingMode",
            "perspectiveCharacterId",
            "applicablePerspectiveCharacterIds",
            "participantIds",
        ):
            if shot.get(key) != semantic.get(key):
                raise ValidationError(f"shot[{index}] {target} semantic field {key} is stale")
        if shot.get("semanticIdentityCast") != semantic.get("identityCast"):
            raise ValidationError(f"shot[{index}] {target} semanticIdentityCast is stale")
        if provider_role == "direct-semantic-master-candidate":
            if target in current_eight_targets:
                raise ValidationError(f"shot[{index}] {target} illegally attempts direct eight-face generation")
            expected_job_id = f"{target}--r5"
            if shot.get("identityCast") != semantic.get("identityCast"):
                raise ValidationError(f"shot[{index}] {target} direct identityCast mismatch")
            if shot.get("atomCharacterId") is not None:
                raise ValidationError(f"shot[{index}] {target} direct shot has atomCharacterId")
            direct_semantic_targets.add(target)
        elif provider_role == "single-identity-current-eight-atom":
            if target == d1a3b_target or target not in current_eight_targets:
                raise ValidationError(f"shot[{index}] {target} is not an atomized current-eight target")
            character_id = shot.get("atomCharacterId")
            if character_id not in DISPLAY or shot.get("identityCast") != [character_id]:
                raise ValidationError(f"shot[{index}] {target} atom must have one exact identity")
            if character_id in atom_characters_by_target[target]:
                raise ValidationError(f"shot[{index}] {target} duplicate atom for {character_id}")
            atom_characters_by_target[target].add(character_id)
            expected_job_id = f"{target}--atom-{character_id}--r5"
        else:
            raise ValidationError(f"shot[{index}] {target} unsupported providerJobRole {provider_role!r}")
        if shot.get("id") != expected_job_id or shot.get("output_name") != f"{expected_job_id}-candidate.mp4":
            raise ValidationError(f"shot[{index}] {target} deterministic provider naming mismatch")
        if shot.get("rightsStatus") != "pending":
            raise ValidationError(f"shot[{index}] {target} planning rightsStatus must be pending")
        for rights_field in ("rightsRefIds", "likenessConsentRefIds", "voiceConsentRefIds"):
            if shot.get(rights_field) != []:
                raise ValidationError(f"shot[{index}] {target} must not invent {rights_field} before approval")
        prompt_path = resolve(shot["prompt_file"])
        expected_prompt_names.add(prompt_path.name)
        prompt_bytes += prompt_path.stat().st_size
        prompt = prompt_path.read_text(encoding="utf-8")
        if sha(prompt_path) != shot.get("promptSha256"):
            raise ValidationError(f"shot[{index}] {target} prompt hash mismatch")
        if any(code not in prompt for code in TIMECODES):
            raise ValidationError(f"shot[{index}] {target} is missing one or more per-second timeline windows")
        for contract_marker in ("【State In】", "【State Out】", "9:16", "15秒", "720p", "原生有声"):
            if contract_marker not in prompt:
                raise ValidationError(f"shot[{index}] {target} prompt missing {contract_marker}")
        for character_id in shot["identityCast"]:
            if DISPLAY[character_id] not in prompt:
                raise ValidationError(f"shot[{index}] {target} prompt does not name {DISPLAY[character_id]}")

        if text_sha(shot["stateIn"]) != shot.get("stateInSha256"):
            raise ValidationError(f"shot[{index}] {target} stateIn hash mismatch")
        if text_sha(shot["stateOut"]) != shot.get("stateOutSha256"):
            raise ValidationError(f"shot[{index}] {target} stateOut hash mismatch")
        if canonical_hash(shot["identityCast"]) != shot.get("identityCastSha256"):
            raise ValidationError(f"shot[{index}] {target} identityCast hash mismatch")
        state_contract = {
            "stateIn": shot["stateIn"],
            "stateOut": shot["stateOut"],
            "providerIdentityCast": shot["identityCast"],
            "semanticIdentityCast": shot["semanticIdentityCast"],
            "eventId": shot["eventId"],
            "servedEventIds": shot["servedEventIds"],
        }
        if canonical_hash(state_contract) != shot.get("stateContractSha256"):
            raise ValidationError(f"shot[{index}] {target} state contract hash mismatch")

        reference = resolve(shot["reference_image"])
        reference_paths.add(reference)
        if sha(reference) != shot.get("referenceImageSha256"):
            raise ValidationError(f"shot[{index}] {target} reference image hash mismatch")
        with Image.open(reference) as image:
            image.verify()
        cast_count = len(shot["identityCast"])
        expected_role = "single-identity-anchor" if cast_count == 1 else "composite-identity-board"
        if shot.get("referenceImageRole") != expected_role:
            raise ValidationError(f"shot[{index}] {target} reference role mismatch")
        if cast_count == 1:
            expected_suffix = f"frontend/public/media/portraits/{shot['identityCast'][0]}.jpg"
            if not reference.as_posix().endswith(expected_suffix):
                raise ValidationError(f"shot[{index}] {target} does not reuse the approved single portrait")
        else:
            if not reference.is_relative_to(REFS.resolve()):
                raise ValidationError(f"shot[{index}] {target} composite is outside refs-r5")
            expected_composite_paths.add(reference)

        audio_mode = shot.get("audioMode")
        audio_counts[audio_mode] += 1
        if shot.get("eventId") == "day1.introductions":
            intro_count += 1
            if shot.get("kind") != "self-introduction" or audio_mode != "character-speech":
                raise ValidationError(f"shot[{index}] {target} introduction is not voiced")
            if "完整说" not in prompt or "自然年轻中文原声" not in prompt:
                raise ValidationError(f"shot[{index}] {target} introduction lacks exact natural voice instruction")
        elif provider_role == "single-identity-current-eight-atom":
            if shot.get("kind") != "current-eight-atom" or audio_mode != "ambient-only":
                raise ValidationError(f"shot[{index}] {target} group atom kind/audio mismatch")
        elif shot.get("kind") != "runtime-variant":
            raise ValidationError(f"shot[{index}] {target} non-introduction kind mismatch")

    if intro_count != 8:
        raise ValidationError(f"voiced introduction count is {intro_count}, expected 8")
    actual_prompt_names = {path.name for path in PROMPTS.glob("*.txt")}
    if actual_prompt_names != expected_prompt_names:
        missing = sorted(expected_prompt_names - actual_prompt_names)
        extra = sorted(actual_prompt_names - expected_prompt_names)
        raise ValidationError(f"prompt directory mismatch; missing={missing[:5]}, extra={extra[:5]}")
    actual_refs = {path.resolve() for path in REFS.glob("*.jpg")}
    if actual_refs != expected_composite_paths:
        missing = sorted(path.name for path in expected_composite_paths - actual_refs)
        extra = sorted(path.name for path in actual_refs - expected_composite_paths)
        raise ValidationError(f"composite reference directory mismatch; missing={missing[:5]}, extra={extra[:5]}")

    expected_routes = {
        "perspective": 58,
        "current-eight": 4,
        "participant-pov": 32,
        "unordered-pair": 81,
        "fixed-cast": 3,
    }
    if dict(semantic_route_counts) != expected_routes:
        raise ValidationError(f"semantic routing counts changed: {dict(semantic_route_counts)}")
    if direct_semantic_targets != set(required) - current_eight_targets:
        missing = sorted((set(required) - current_eight_targets) - direct_semantic_targets)
        raise ValidationError(f"direct semantic-master coverage mismatch; missing={missing[:5]}")
    for target, characters in atom_characters_by_target.items():
        if characters != set(DISPLAY):
            raise ValidationError(f"{target} atom identity coverage is {sorted(characters)}, expected all eight")

    composites = manifest.get("localCompositeOutputs")
    if not isinstance(composites, list) or len(composites) != 4:
        raise ValidationError("manifest must contain exactly four localCompositeOutputs")
    composite_targets: set[str] = set()
    for index, composite in enumerate(composites):
        target = composite.get("targetRuntimeAssetId")
        if target not in current_eight_targets or target in composite_targets:
            raise ValidationError(f"localCompositeOutputs[{index}] invalid/duplicate target {target!r}")
        composite_targets.add(target)
        semantic = required[target]
        if composite.get("eventId") != semantic["eventId"] or composite.get("servedEventIds") != semantic["servedEventIds"]:
            raise ValidationError(f"localCompositeOutputs[{index}] {target} semantic binding mismatch")
        if composite.get("identityCast") != list(DISPLAY) or composite.get("routingMode") != "current-eight":
            raise ValidationError(f"localCompositeOutputs[{index}] {target} exact eight-person cast mismatch")
        if composite.get("doNotSubmit") is not True or composite.get("status") != "planned-awaiting-approved-source-candidates":
            raise ValidationError(f"localCompositeOutputs[{index}] {target} must remain planned and local-only")
        if text_sha(composite["stateIn"]) != composite.get("stateInSha256") or text_sha(composite["stateOut"]) != composite.get("stateOutSha256"):
            raise ValidationError(f"localCompositeOutputs[{index}] {target} state hash mismatch")
        if canonical_hash(composite["identityCast"]) != composite.get("identityCastSha256"):
            raise ValidationError(f"localCompositeOutputs[{index}] {target} identity hash mismatch")
        assembly = composite.get("assembly")
        if canonical_hash(assembly) != composite.get("assemblyContractSha256"):
            raise ValidationError(f"localCompositeOutputs[{index}] {target} assembly hash mismatch")
        if assembly.get("durationSeconds") != 15.0 or len(assembly.get("segments", [])) != 8:
            raise ValidationError(f"localCompositeOutputs[{index}] {target} must be a 15s/8-segment edit")
        source_ids = composite.get("sourceProviderJobIds")
        if source_ids != assembly.get("sourceProviderJobIds") or len(source_ids) != 8:
            raise ValidationError(f"localCompositeOutputs[{index}] {target} source list mismatch")
        if not set(source_ids) <= provider_job_id_set:
            raise ValidationError(f"localCompositeOutputs[{index}] {target} references missing provider jobs")
        expected_sources = (
            [f"D1-A3-cast-introductions--p-{character_id}--r5" for character_id in DISPLAY]
            if target == d1a3b_target
            else [f"{target}--atom-{character_id}--r5" for character_id in DISPLAY]
        )
        if source_ids != expected_sources:
            raise ValidationError(f"localCompositeOutputs[{index}] {target} source ordering mismatch")
        segment_characters = [segment.get("characterId") for segment in assembly["segments"]]
        if segment_characters != list(DISPLAY):
            raise ValidationError(f"localCompositeOutputs[{index}] {target} segment order must cover each face once")
    if composite_targets != current_eight_targets:
        raise ValidationError("local composite semantic coverage is incomplete")
    semantic_coverage = direct_semantic_targets | composite_targets
    if semantic_coverage != set(required):
        raise ValidationError("178 semantic gaps are not fully covered by direct jobs plus local composites")

    expected_provider_roles = {
        "direct-semantic-master-candidate": 174,
        "single-identity-current-eight-atom": 24,
    }
    if dict(provider_role_counts) != expected_provider_roles:
        raise ValidationError(f"provider role counts changed: {dict(provider_role_counts)}")
    total_bytes = MANIFEST.stat().st_size + prompt_bytes + sum(path.stat().st_size for path in actual_refs)
    return {
        "status": "PASS",
        "networkRequests": 0,
        "doNotSubmit": True,
        "semanticMasterCoverage": "178/178",
        "providerJobCoverage": "198/198",
        "providerJobs": 198,
        "localCompositeOutputs": "4/4",
        "voicedIntroductions": intro_count,
        "promptFiles": len(actual_prompt_names),
        "compositeBoards": len(actual_refs),
        "uniqueReferenceFiles": len(reference_paths),
        "semanticRoutingCounts": dict(semantic_route_counts),
        "providerJobRoleCounts": dict(provider_role_counts),
        "audioModeCounts": dict(audio_counts),
        "totalInputBytes": total_bytes,
        "manifestSha256": sha(MANIFEST),
        "runtimeMatrixSha256": sha(MATRIX),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(check(), ensure_ascii=False, indent=2))
    except ValidationError as error:
        print(f"R5 PRODUCTION INPUTS INVALID: {error}", file=sys.stderr)
        raise SystemExit(2)
