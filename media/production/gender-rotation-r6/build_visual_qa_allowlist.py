#!/usr/bin/env python3
"""Build the retained R6 visual-QA allowlist and compact review report.

This is a local-only bookkeeping command. It never calls a media provider. The
review decisions below correspond to the 2026-08-26 frame review, audio-stream
probe and loudness pass. Corrective crops/trims are explicit and hash-bound.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
PLAN_PATH = HERE / "manifest.r6.json"
RUNTIME_PATH = HERE.parents[1] / "runtime-media-manifest.json"
CANDIDATE_ROOT = HERE / ".work-candidates" / "r6-paid-20260826"
REMEDIATED_ROOT = HERE / ".work-remediated-r6"
TECHNICAL_QA_PATH = HERE / "technical-qa-r6.json"
ALLOWLIST_PATH = HERE / "visual-qa-allowlist.r6.json"
REPORT_PATH = HERE / "visual-qa-report-r6.md"
EXPECTED_SOURCE_COUNTS = {"generated": 81, "local-composite": 3, "existing-runtime": 24}
MIN_AUDIBLE_PEAK_DB = -60.0

REMEDIATED = {
    "EV-SIGNAL-first-anonymous-message--F-B-luyao--r6": "Removed generated rounded app-frame border by identity-safe center crop.",
    "EV-GROUP-truth-firepit--F-B-luyao--r6": "Removed large generated top/bottom UI with a clean center frame and blurred extension.",
    "EV-IDENTITY-profession-reveal--M-A-chengye--r6": "Trimmed the first 0.3 s containing a transient pseudo-character card; held the clean tail to preserve duration.",
    "D1-A1-island-hotel-establish--M-B-hechuan--r6": "Removed four-corner pseudo-text by cropping 32 px top/bottom and reframing.",
    "EV-TRIP-last-two-days--M-B-hechuan--r6": "Removed generated 64 px white top/bottom borders with a clean center frame and blurred extension.",
}

NON_BLOCKING_NOTES = {
    "D1-A5-guided-smalltalk--F-B-luyao--r6": "An unplanned guitar remains in frame; identity and small-talk causality remain usable.",
    "EV-RULES-house-friction--F-B-luyao--r6": "The rule-board movement is subtle and relies on narration.",
    "EV-BRIDGE-hidden-courage--F-B-luyao--r6": "The rescue beat is readable through staging but benefits from narration.",
    "EV-FINAL-confession-day--F-B-luyao--r6": "A guitar enters the confession staging; identity and emotional beat remain coherent.",
    "D2-A1-memory-callback--M-A-chengye--r6": "The recalled detail is primarily conveyed by dialogue/context.",
    "EV-RULES-house-friction--M-A-chengye--r6": "The rule conflict is visually understated and benefits from narration.",
    "EV-BRIDGE-hidden-courage--M-A-chengye--r6": "Contains short, correct Chinese dramatic text; accepted as a non-blocking stylistic overlay.",
    "EV-PAST-consent-reveal--M-A-chengye--r6": "Contains short, correct Chinese dialogue text; accepted as a non-blocking stylistic overlay.",
    "EV-DATE-blind-box--M-B-hechuan--r6": "Shows about six boxes instead of three; the blind-box action remains clear.",
    "EV-BOMBSHELL-ninth-card--M-B-hechuan--r6": "Envelope carries faint prop-like pseudo-text; no identity or story error.",
    "EV-PAST-consent-reveal--M-B-hechuan--r6": "Old envelope carries faint prop-like pseudo-text; no identity or story error.",
    "EV-FINAL-confession-day--M-B-hechuan--r6": "Contains the correct subtitle '我选你'; accepted as a non-blocking dramatic overlay.",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_promotion_module():
    path = HERE / "prepare_promotion.py"
    spec = importlib.util.spec_from_file_location("r6_prepare_promotion", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import prepare_promotion.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_technical_qa(promotion, specs) -> dict[str, dict]:
    qa = promotion.load_json(TECHNICAL_QA_PATH)
    summary = qa.get("summary") if isinstance(qa.get("summary"), dict) else {}
    generated_ids = {source_id for source_id, spec in specs.items() if spec.source_type == "generated"}
    if qa.get("verdict") != "R6_TECHNICAL_QA_PASS":
        raise RuntimeError("technical QA verdict is not R6_TECHNICAL_QA_PASS")
    expected_summary = {
        "expectedJobs": len(generated_ids),
        "candidateFilesScanned": len(generated_ids),
        "presentUniqueJobs": len(generated_ids),
        "technicalPassed": len(generated_ids),
        "technicalFailed": 0,
        "pendingGeneration": 0,
        "missingJobs": 0,
        "duplicateOutputJobs": 0,
        "duplicateContentGroups": 0,
        "unexpectedCandidateFiles": 0,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise RuntimeError(f"technical QA summary mismatch for {key}: {summary.get(key)!r} != {expected!r}")
    records = qa.get("assets")
    if not isinstance(records, list):
        raise RuntimeError("technical QA assets must be an array")
    by_id: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict) or not record.get("id"):
            raise RuntimeError("technical QA contains an invalid asset record")
        source_id = str(record["id"])
        if source_id in by_id:
            raise RuntimeError(f"duplicate technical QA source: {source_id}")
        by_id[source_id] = record
    if set(by_id) != generated_ids:
        missing = sorted(generated_ids - set(by_id))
        extra = sorted(set(by_id) - generated_ids)
        raise RuntimeError(f"technical QA source set mismatch; missing={missing[:3]} extra={extra[:3]}")
    for source_id, record in by_id.items():
        if record.get("status") != "technical-passed" or record.get("errors"):
            raise RuntimeError(f"generated source did not pass technical QA: {source_id}")
        original = CANDIDATE_ROOT / str(record.get("candidatePath") or "")
        if not original.is_file():
            raise RuntimeError(f"technical QA source is missing: {original}")
        if sha256(original) != str(record.get("sha256") or ""):
            raise RuntimeError(f"technical QA source hash drifted: {source_id}")
    return by_id


def loudness_probe(path: Path) -> dict[str, float]:
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-v", "info",
        "-i", str(path), "-map", "0:a:0", "-vn", "-af", "volumedetect",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"audio loudness probe failed for {path}: {exc}") from exc
    if result.returncode != 0:
        raise RuntimeError(f"audio loudness probe failed for {path}: {result.stderr[-500:]}")
    values = {}
    for key in ("mean_volume", "max_volume"):
        match = re.search(rf"{key}:\s*(-?inf|-?\d+(?:\.\d+)?) dB", result.stderr)
        if not match or match.group(1) in {"inf", "-inf"}:
            raise RuntimeError(f"audio is silent or has no measurable {key}: {path}")
        values[key] = float(match.group(1))
    if values["max_volume"] <= MIN_AUDIBLE_PEAK_DB:
        raise RuntimeError(f"audio peak is effectively silent ({values['max_volume']} dB): {path}")
    return values


def candidate_for(source_id: str, spec) -> Path:
    remediated = REMEDIATED_ROOT / spec.expected_name
    if source_id in REMEDIATED or spec.source_type == "local-composite":
        return remediated
    if spec.source_type == "existing-runtime":
        return PROJECT_ROOT / "frontend" / "public" / "media" / "video" / spec.expected_name
    matches = list(CANDIDATE_ROOT.glob(f"wave-*/candidates/shots/{source_id}/{spec.expected_name}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one candidate for {source_id}, found {len(matches)}")
    return matches[0]


def main() -> int:
    promotion = load_promotion_module()
    plan = promotion.load_json(PLAN_PATH)
    runtime = promotion.load_json(RUNTIME_PATH)
    specs = promotion.source_specs(plan, runtime)
    source_counts = Counter(spec.source_type for spec in specs.values())
    if len(specs) != sum(EXPECTED_SOURCE_COUNTS.values()) or dict(source_counts) != EXPECTED_SOURCE_COUNTS:
        raise RuntimeError(
            f"R6 source inventory is incomplete: total={len(specs)} breakdown={dict(source_counts)}"
        )
    technical_records = validate_technical_qa(promotion, specs)
    reviewed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    approved = []
    required_audio: list[tuple[str, Path, str]] = []
    remediated_count = 0
    noted_count = 0
    for source_id, spec in specs.items():
        candidate = candidate_for(source_id, spec)
        if not candidate.is_file():
            raise RuntimeError(f"missing reviewed candidate: {candidate}")
        actual_hash = sha256(candidate)
        probe = promotion.media_probe(candidate)
        if spec.requires_audio:
            if not probe["hasAudio"]:
                raise RuntimeError(f"reviewed candidate lacks required first-play audio: {source_id}")
            if probe.get("audioCodec") != "aac":
                raise RuntimeError(f"reviewed candidate audio is not AAC: {source_id}")
            required_audio.append((source_id, candidate, spec.source_type))
        elif probe["hasAudio"]:
            raise RuntimeError(f"silent-loop candidate unexpectedly contains audio: {source_id}")
        if spec.source_type == "generated" and source_id not in REMEDIATED:
            technical_record = technical_records[source_id]
            original = (CANDIDATE_ROOT / str(technical_record["candidatePath"])).resolve()
            if candidate.resolve() != original:
                raise RuntimeError(f"candidate path differs from technical QA evidence: {source_id}")
            if actual_hash != str(technical_record["sha256"]):
                raise RuntimeError(f"candidate hash differs from technical QA evidence: {source_id}")
        notes: list[str] = []
        if source_id in REMEDIATED:
            notes.append(REMEDIATED[source_id])
            remediated_count += 1
        if source_id in NON_BLOCKING_NOTES:
            notes.append(NON_BLOCKING_NOTES[source_id])
            noted_count += 1
        item = {
            "sourceId": source_id,
            "candidatePath": str(candidate.relative_to(PROJECT_ROOT)),
            "sha256": actual_hash,
            "identityCast": list(spec.planned_cast),
            "visualQaVerdict": "passed",
            "audioQaVerdict": "passed" if spec.requires_audio else "not-applicable",
        }
        if not spec.requires_audio:
            item["requireSilent"] = True
        if notes:
            item["qaNotes"] = notes
        approved.append(item)

    if len(approved) != 108 or {item["sourceId"] for item in approved} != set(specs):
        raise RuntimeError("visual-QA allowlist does not exactly cover all 108 R6 sources")
    with ThreadPoolExecutor(max_workers=8) as pool:
        loudness_values = list(pool.map(lambda item: (item[0], item[2], loudness_probe(item[1])), required_audio))
    generated_loudness = [value for _, source_type, value in loudness_values if source_type == "generated"]
    if len(required_audio) != 100 or len(generated_loudness) != 73:
        raise RuntimeError(
            f"R6 audio inventory is incomplete: required={len(required_audio)} generated={len(generated_loudness)}"
        )
    generated_mean_min = min(value["mean_volume"] for value in generated_loudness)
    generated_mean_max = max(value["mean_volume"] for value in generated_loudness)
    generated_peak_min = min(value["max_volume"] for value in generated_loudness)
    generated_peak_max = max(value["max_volume"] for value in generated_loudness)

    allowlist = {
        "schemaVersion": "heart-journey/r6-visual-qa-allowlist-v1",
        "planningManifestSha256": sha256(PLAN_PATH),
        "reviewedBy": "Codex R6 frame QA with prior-approved F-A runtime reuse",
        "reviewedAt": reviewed_at,
        "reviewScope": {
            "generatedProviderJobs": source_counts["generated"],
            "localComposites": source_counts["local-composite"],
            "priorApprovedRuntimeReuses": source_counts["existing-runtime"],
            "technicalQa": f"{len(technical_records)}/{len(technical_records)} generated candidates passed codec, dimension, duration and stream rules",
            "audioQa": f"{len(required_audio)}/{len(required_audio)} required first-play sources have non-silent AAC; dynamic portraits are intentionally silent",
            "speechLexicalTranscription": "not-performed",
        },
        "approvedAssets": approved,
    }
    temporary_allowlist = HERE / ".visual-qa-allowlist.r6.tmp.json"
    temporary_allowlist.write_text(json.dumps(allowlist, ensure_ascii=False, indent=2) + "\n")
    try:
        promotion.prepare(PROJECT_ROOT, PLAN_PATH, RUNTIME_PATH, temporary_allowlist)
        temporary_allowlist.replace(ALLOWLIST_PATH)
    finally:
        temporary_allowlist.unlink(missing_ok=True)

    report = f"""# R6 visual and audio QA report

Reviewed: {reviewed_at}

## Verdict

- Approved runtime sources: **{len(approved)}** ({source_counts['generated']} generated + {source_counts['local-composite']} local composites + {source_counts['existing-runtime']} prior-approved F-A reuses).
- Generated technical QA: **{len(technical_records)}/{len(technical_records)} passed**, with zero missing, duplicate, unexpected or technically invalid candidate files.
- Required first-play audio: **{len(required_audio)}/{len(required_audio)} non-silent AAC**.
- Generated event audio: **{len(generated_loudness)}/{len(generated_loudness)} non-silent AAC**; measured mean-volume range `{generated_mean_min:.1f}` to `{generated_mean_max:.1f} dB`, peak range `{generated_peak_min:.1f}` to `{generated_peak_max:.1f} dB`.
- Dynamic portraits: **8/8 intentionally silent** and visually identity-stable.
- Paid retries: **0**. Final settled R6 spend: **CNY 41.0770200** under the approved **CNY 60** hard cap.
- Identity hard failures after original-frame review: **0**. Two apparent duplicate-person findings were contact-sheet adjacency false positives and were withdrawn after raw-frame inspection.

## Local remediation

{chr(10).join(f'- `{key}`: {value}' for key, value in REMEDIATED.items())}

## Accepted non-blocking visual deviations

{chr(10).join(f'- `{key}`: {value}' for key, value in NON_BLOCKING_NOTES.items())}

## Honest boundary

Audio QA verifies stream presence and loudness, not a word-for-word transcription of synthetic speech. Existing F-A runtime assets are reused from the project's prior approved set; this record does not create a new commercial likeness or voice-rights claim. Public/commercial clearance remains separate from local/runtime technical approval.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({
        "verdict": "R6_VISUAL_ALLOWLIST_BUILT",
        "approvedAssets": len(approved),
        "locallyRemediated": remediated_count,
        "acceptedWithNotes": noted_count,
        "allowlist": str(ALLOWLIST_PATH),
        "report": str(REPORT_PATH),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
