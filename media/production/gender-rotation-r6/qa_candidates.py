#!/usr/bin/env python3
"""Offline technical QA for R6 generated media candidates.

The tool is intentionally read-only with respect to the planning manifest,
approval record, and candidate media.  It only invokes the local ``ffprobe``
binary, then writes compact JSON/Markdown evidence reports.

``--allow-partial`` is intended for a batch that is still being generated:
missing jobs remain ``pending-generation`` and do not fail the command.  A
candidate that already exists but violates a technical contract still fails.
Without ``--allow-partial``, missing jobs are a complete-batch failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = "heart-journey/r6-technical-media-qa-v1"
VIDEO_CODEC = "h264"
EVENT_AUDIO_CODEC = "aac"
DEFAULT_DURATION_TOLERANCE_SECONDS = 0.5
RATIO_TOLERANCE = 0.035
RESOLUTION_PROFILES = {
    # Seedance's observed 480p vertical output is 496x864.  Treat "480p" as a
    # bounded profile, not a promise of exactly 480 pixels on the short edge.
    "480p": {"shortMin": 480, "shortMax": 512, "longMin": 848, "longMax": 896},
}


class CandidateQaError(RuntimeError):
    """Invalid input or unavailable local QA dependency."""


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    kind: str
    output_name: str
    duration: float
    ratio: str
    resolution: str
    requires_audio: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CandidateQaError(f"missing planning manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CandidateQaError(f"invalid planning manifest JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CandidateQaError("planning manifest root must be an object")
    return payload


def parse_ratio(raw: str) -> float:
    try:
        left, right = raw.split(":", 1)
        numerator = float(left)
        denominator = float(right)
        if numerator <= 0 or denominator <= 0:
            raise ValueError
        return numerator / denominator
    except (AttributeError, ValueError, ZeroDivisionError) as exc:
        raise CandidateQaError(f"unsupported ratio in planning manifest: {raw!r}") from exc


def manifest_jobs(manifest: dict[str, Any]) -> tuple[list[JobSpec], set[str]]:
    shots = manifest.get("shots")
    if not isinstance(shots, list) or not shots:
        raise CandidateQaError("planning manifest shots must be a non-empty array")

    jobs: list[JobSpec] = []
    ids: set[str] = set()
    output_names: set[str] = set()
    for index, raw in enumerate(shots):
        if not isinstance(raw, dict):
            raise CandidateQaError(f"shots[{index}] must be an object")
        job_id = str(raw.get("id") or "")
        kind = str(raw.get("kind") or "")
        output_name = str(raw.get("output_name") or "")
        if not job_id or job_id in ids:
            raise CandidateQaError(f"missing or duplicate job id: {job_id!r}")
        if not output_name or Path(output_name).name != output_name or output_name in output_names:
            raise CandidateQaError(f"missing, nested, or duplicate output_name: {output_name!r}")
        if kind not in {"event-rotation-candidate", "dynamic-portrait-candidate"}:
            raise CandidateQaError(f"unsupported job kind for {job_id}: {kind!r}")
        try:
            duration = float(raw["duration"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CandidateQaError(f"invalid duration for {job_id}") from exc
        if duration <= 0:
            raise CandidateQaError(f"duration must be positive for {job_id}")
        ratio = str(raw.get("ratio") or manifest.get("defaults", {}).get("ratio") or "")
        parse_ratio(ratio)
        resolution = str(raw.get("resolution") or manifest.get("defaults", {}).get("resolution") or "")
        if resolution not in RESOLUTION_PROFILES:
            raise CandidateQaError(f"unsupported resolution profile for {job_id}: {resolution!r}")

        declared_audio = raw.get("generate_audio")
        expected_audio = kind == "event-rotation-candidate"
        if declared_audio is not expected_audio:
            raise CandidateQaError(
                f"audio contract mismatch in manifest for {job_id}: "
                f"{kind} requires generate_audio={str(expected_audio).lower()}"
            )
        ids.add(job_id)
        output_names.add(output_name)
        jobs.append(
            JobSpec(
                job_id=job_id,
                kind=kind,
                output_name=output_name,
                duration=duration,
                ratio=ratio,
                resolution=resolution,
                requires_audio=expected_audio,
            )
        )

    known_non_job_outputs = {
        str(item.get("output_name"))
        for item in manifest.get("localComposites", [])
        if isinstance(item, dict) and item.get("output_name")
    }
    return jobs, known_non_job_outputs


def ffprobe_media(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        (
            "format=format_name,duration,size:"
            "stream=index,codec_type,codec_name,width,height,pix_fmt,"
            "avg_frame_rate,r_frame_rate,sample_rate,channels"
        ),
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CandidateQaError("ffprobe is required but was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise CandidateQaError(f"ffprobe failed: {detail}") from exc
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CandidateQaError(f"ffprobe returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CandidateQaError("ffprobe result must be an object")
    return payload


def relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def inspect_candidate(
    spec: JobSpec,
    path: Path,
    candidate_root: Path,
    duration_tolerance: float,
    prober: Callable[[Path], dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        probe = prober(path)
    except CandidateQaError as exc:
        return {
            "id": spec.job_id,
            "kind": spec.kind,
            "status": "technical-failed",
            "candidatePath": relative_or_absolute(path, candidate_root),
            "errors": [str(exc)],
        }

    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1:
        errors.append(f"expected exactly 1 video stream, found {len(video_streams)}")
    video = video_streams[0] if video_streams else {}
    if video.get("codec_name") != VIDEO_CODEC:
        errors.append(f"video codec {video.get('codec_name')!r} != {VIDEO_CODEC!r}")

    width = video.get("width")
    height = video.get("height")
    try:
        width = int(width)
        height = int(height)
    except (TypeError, ValueError):
        width = height = 0
        errors.append("video dimensions are missing or invalid")
    if width > 0 and height > 0:
        profile = RESOLUTION_PROFILES[spec.resolution]
        short_edge, long_edge = sorted((width, height))
        if not (profile["shortMin"] <= short_edge <= profile["shortMax"]):
            errors.append(
                f"short edge {short_edge}px outside {spec.resolution} profile "
                f"{profile['shortMin']}-{profile['shortMax']}px"
            )
        if not (profile["longMin"] <= long_edge <= profile["longMax"]):
            errors.append(
                f"long edge {long_edge}px outside {spec.resolution} profile "
                f"{profile['longMin']}-{profile['longMax']}px"
            )
        expected_ratio = parse_ratio(spec.ratio)
        actual_ratio = width / height
        if abs(actual_ratio - expected_ratio) > RATIO_TOLERANCE:
            errors.append(
                f"display ratio {actual_ratio:.4f} differs from {spec.ratio} "
                f"by more than {RATIO_TOLERANCE:.3f}"
            )

    format_data = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    try:
        duration = float(format_data.get("duration"))
    except (TypeError, ValueError):
        duration = 0.0
        errors.append("container duration is missing or invalid")
    delta = abs(duration - spec.duration)
    if duration > 0 and delta > duration_tolerance:
        errors.append(
            f"duration {duration:.3f}s differs from planned {spec.duration:.3f}s "
            f"by {delta:.3f}s (tolerance {duration_tolerance:.3f}s)"
        )

    if spec.requires_audio:
        if len(audio_streams) != 1:
            errors.append(f"event requires exactly 1 audio stream, found {len(audio_streams)}")
        elif audio_streams[0].get("codec_name") != EVENT_AUDIO_CODEC:
            errors.append(
                f"event audio codec {audio_streams[0].get('codec_name')!r} "
                f"!= {EVENT_AUDIO_CODEC!r}"
            )
    elif audio_streams:
        errors.append(f"dynamic portrait must be silent, found {len(audio_streams)} audio stream(s)")

    digest = sha256_file(path)
    return {
        "id": spec.job_id,
        "kind": spec.kind,
        "status": "technical-passed" if not errors else "technical-failed",
        "candidatePath": relative_or_absolute(path, candidate_root),
        "sha256": digest,
        "sizeBytes": path.stat().st_size,
        "plannedDurationSeconds": spec.duration,
        "durationSeconds": round(duration, 6),
        "durationDeltaSeconds": round(delta, 6),
        "video": {
            "codec": video.get("codec_name"),
            "width": width,
            "height": height,
            "pixelFormat": video.get("pix_fmt"),
            "averageFrameRate": video.get("avg_frame_rate") or video.get("r_frame_rate"),
        },
        "audio": {
            "expected": spec.requires_audio,
            "streamCount": len(audio_streams),
            "codec": audio_streams[0].get("codec_name") if audio_streams else None,
            "sampleRate": audio_streams[0].get("sample_rate") if audio_streams else None,
            "channels": audio_streams[0].get("channels") if audio_streams else None,
        },
        "errors": errors,
    }


def run_qa(
    manifest_path: Path,
    candidate_root: Path,
    *,
    allow_partial: bool,
    duration_tolerance: float = DEFAULT_DURATION_TOLERANCE_SECONDS,
    prober: Callable[[Path], dict[str, Any]] = ffprobe_media,
) -> dict[str, Any]:
    if duration_tolerance < 0:
        raise CandidateQaError("duration tolerance must be non-negative")
    manifest_path = manifest_path.expanduser().resolve()
    candidate_root = candidate_root.expanduser().resolve()
    if not candidate_root.is_dir():
        raise CandidateQaError(f"candidate output root is not a directory: {candidate_root}")
    manifest = load_json(manifest_path)
    jobs, known_non_job_outputs = manifest_jobs(manifest)

    all_candidate_files = sorted(
        path for path in candidate_root.rglob("*-candidate.mp4") if path.is_file()
    )
    by_name: dict[str, list[Path]] = defaultdict(list)
    for path in all_candidate_files:
        by_name[path.name].append(path)

    expected_names = {job.output_name for job in jobs}
    unexpected = [
        relative_or_absolute(path, candidate_root)
        for path in all_candidate_files
        if path.name not in expected_names and path.name not in known_non_job_outputs
    ]

    assets: list[dict[str, Any]] = []
    missing: list[str] = []
    duplicate_outputs: list[dict[str, Any]] = []
    for spec in jobs:
        matches = by_name.get(spec.output_name, [])
        if not matches:
            missing.append(spec.job_id)
            assets.append(
                {
                    "id": spec.job_id,
                    "kind": spec.kind,
                    "status": "pending-generation" if allow_partial else "missing-candidate",
                    "candidatePath": None,
                    "errors": [] if allow_partial else ["expected candidate is missing"],
                }
            )
            continue
        if len(matches) > 1:
            paths = [relative_or_absolute(path, candidate_root) for path in matches]
            duplicate_outputs.append({"id": spec.job_id, "paths": paths})
            assets.append(
                {
                    "id": spec.job_id,
                    "kind": spec.kind,
                    "status": "technical-failed",
                    "candidatePath": None,
                    "errors": [f"expected output exists {len(matches)} times"],
                    "duplicatePaths": paths,
                }
            )
            continue
        assets.append(
            inspect_candidate(
                spec,
                matches[0],
                candidate_root,
                duration_tolerance,
                prober,
            )
        )

    digest_groups: dict[str, list[str]] = defaultdict(list)
    for asset in assets:
        if asset.get("sha256"):
            digest_groups[str(asset["sha256"])].append(str(asset["id"]))
    duplicate_content = [
        {"sha256": digest, "jobIds": ids}
        for digest, ids in sorted(digest_groups.items())
        if len(ids) > 1
    ]
    duplicate_content_ids = {
        job_id for group in duplicate_content for job_id in group["jobIds"]
    }
    if duplicate_content_ids:
        for asset in assets:
            if asset["id"] in duplicate_content_ids:
                asset["status"] = "technical-failed"
                asset.setdefault("errors", []).append("candidate bytes duplicate another job output")

    passed = sum(asset["status"] == "technical-passed" for asset in assets)
    failed = sum(asset["status"] == "technical-failed" for asset in assets)
    pending = sum(asset["status"] == "pending-generation" for asset in assets)
    missing_failures = sum(asset["status"] == "missing-candidate" for asset in assets)
    global_failures = len(unexpected)
    all_present = not missing
    technical_failure = bool(failed or missing_failures or duplicate_outputs or duplicate_content or global_failures)
    if technical_failure:
        verdict = "R6_TECHNICAL_QA_FAILED"
    elif all_present:
        verdict = "R6_TECHNICAL_QA_PASS"
    else:
        verdict = "R6_PARTIAL_QA_PASS_PRESENT_CANDIDATES"

    summary = {
        "expectedJobs": len(jobs),
        "candidateFilesScanned": len(all_candidate_files),
        "presentUniqueJobs": passed + failed,
        "technicalPassed": passed,
        "technicalFailed": failed + missing_failures + global_failures,
        "pendingGeneration": pending,
        "missingJobs": len(missing),
        "duplicateOutputJobs": len(duplicate_outputs),
        "duplicateContentGroups": len(duplicate_content),
        "unexpectedCandidateFiles": len(unexpected),
        "progressPercent": round((passed + failed) / len(jobs) * 100, 1),
        "creativeApproved": 0,
        "runtimeIntegrated": 0,
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": "allow-partial" if allow_partial else "complete",
        "verdict": verdict,
        "exitCode": 1 if technical_failure else 0,
        "claimBoundary": (
            "ffprobe technical evidence only; identity, motion, dialogue/audio content, "
            "creative, rights, mobile crop, and runtime integration remain unverified"
        ),
        "source": {
            "planningManifest": str(manifest_path),
            "planningManifestSha256": sha256_file(manifest_path),
            "candidateRoot": str(candidate_root),
        },
        "constraints": {
            "videoCodec": VIDEO_CODEC,
            "eventAudioCodec": EVENT_AUDIO_CODEC,
            "durationToleranceSeconds": duration_tolerance,
            "ratioTolerance": RATIO_TOLERANCE,
            "resolutionProfiles": RESOLUTION_PROFILES,
        },
        "summary": summary,
        "missingJobIds": missing,
        "duplicateOutputs": duplicate_outputs,
        "duplicateContent": duplicate_content,
        "unexpectedCandidatePaths": unexpected,
        "assets": assets,
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# R6 candidate technical QA",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Mode: `{report['mode']}`",
        f"- Planning manifest SHA-256: `{report['source']['planningManifestSha256']}`",
        (
            f"- Progress: {summary['presentUniqueJobs']}/{summary['expectedJobs']} "
            f"({summary['progressPercent']}%)"
        ),
        (
            f"- Present technical pass/fail: {summary['technicalPassed']}/"
            f"{summary['technicalFailed']}"
        ),
        f"- Pending generation: {summary['pendingGeneration']}",
        (
            f"- Duplicate outputs/content groups/unexpected: "
            f"{summary['duplicateOutputJobs']}/{summary['duplicateContentGroups']}/"
            f"{summary['unexpectedCandidateFiles']}"
        ),
        "- Boundary: technical metadata only; no creative, identity, audio-content, rights, crop, or runtime approval.",
        "",
    ]
    failures = [asset for asset in report["assets"] if asset["status"] == "technical-failed"]
    missing_failures = [asset for asset in report["assets"] if asset["status"] == "missing-candidate"]
    pending = [asset for asset in report["assets"] if asset["status"] == "pending-generation"]
    # A live partial run can have dozens of future jobs. Keep Markdown readable;
    # the JSON report retains the complete per-job list.
    noteworthy = failures + missing_failures + pending[:10]
    if noteworthy:
        lines.extend(["## Pending or failed jobs", "", "| Job | State | Detail |", "|---|---|---|"])
        for asset in noteworthy:
            detail = "; ".join(asset.get("errors") or []) or "generation not complete"
            detail = detail.replace("|", "\\|")
            lines.append(f"| `{asset['id']}` | `{asset['status']}` | {detail} |")
        if len(pending) > 10:
            lines.append(
                f"| ... | `pending-generation` | {len(pending) - 10} more pending jobs; see JSON for the full list |"
            )
        lines.append("")
    else:
        lines.extend(["All planned provider jobs have one technically conforming candidate.", ""])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="immutable R6 planning manifest")
    parser.add_argument("candidate_root", type=Path, help="root containing wave candidate outputs")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="treat jobs not generated yet as pending rather than failed",
    )
    parser.add_argument(
        "--duration-tolerance-seconds",
        type=float,
        default=DEFAULT_DURATION_TOLERANCE_SECONDS,
    )
    parser.add_argument("--json-output", type=Path, help="JSON report path")
    parser.add_argument("--markdown-output", type=Path, help="Markdown report path")
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="do not write report files; print compact summary only",
    )
    return parser.parse_args(argv)


def write_report(path: Path, payload: str) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if shutil.which("ffprobe") is None:
            raise CandidateQaError("ffprobe is required but was not found on PATH")
        report = run_qa(
            args.manifest,
            args.candidate_root,
            allow_partial=args.allow_partial,
            duration_tolerance=args.duration_tolerance_seconds,
        )
        if not args.stdout_only:
            manifest_dir = args.manifest.expanduser().resolve().parent
            json_output = args.json_output or manifest_dir / "technical-qa-r6.json"
            markdown_output = args.markdown_output or manifest_dir / "technical-qa-r6.md"
            write_report(json_output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            write_report(markdown_output, markdown_report(report))
        print(json.dumps({"verdict": report["verdict"], **report["summary"]}, ensure_ascii=False))
        return int(report["exitCode"])
    except CandidateQaError as exc:
        print(json.dumps({"verdict": "R6_TECHNICAL_QA_INPUT_ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
