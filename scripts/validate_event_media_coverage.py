#!/usr/bin/env python3
"""Validate the complete R4 Day 1 + StoryEvent runtime-media contract.

The coverage number is deliberately strict: a contract is covered only after
its manifest record, status, trigger, files, hashes, duration, identity anchor,
native first-play audio and full decode all pass. A generated file or a fallback
video is not coverage.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public"
CATALOG_PATH = ROOT / "content" / "story_event_catalog.v1.json"
MANIFEST_PATH = ROOT / "media" / "runtime-media-manifest.json"
AUDIO_QA_PATH = ROOT / "media" / "production" / "identity-audio-r4" / "audio-content-qa-r4.json"
AUDIO_QA_RELATIVE = "media/production/identity-audio-r4/audio-content-qa-r4.json"
VISUAL_QA_PATH = ROOT / "media" / "production" / "identity-audio-r4" / "visual-content-qa-r4.json"
VISUAL_QA_RELATIVE = "media/production/identity-audio-r4/visual-content-qa-r4.json"
MIN_EVENT_SECONDS = 9.5
PREFERRED_EVENT_SECONDS = 14.0
RUNTIME_STATUSES = {"ready", "approved-runtime"}

EXPECTED_DAY1_ASSET_IDS = {
    "arrival-context": "D1-A1-island-hotel-establish",
    "villa-arrival": "D1-A2-villa-entry",
    "introductions": "D1-A3-cast-introductions",
    "cast-first-impressions": "D1-A3B-cast-first-impressions",
    "icebreaker-choice": "D1-A4-icebreaker-selection",
    "guided-chat": "D1-A5-guided-smalltalk",
    "team-up": "D1-A6-first-dinner-team",
    "anonymous-letter": "D1-A7-heart-message",
    "callback": "D2-A1-memory-callback",
}

EXPECTED_STORY_ASSET_IDS = {
    "story.kitchen.two-person-shift": "EV-KITCHEN-two-person-shift",
    "story.house.rules-friction": "EV-RULES-house-friction",
    "story.signal.first-anonymous-message": "EV-SIGNAL-first-anonymous-message",
    "story.identity.profession-reveal": "EV-IDENTITY-profession-reveal",
    "story.date.blind-box": "EV-DATE-blind-box",
    "story.date.mutual-signal": "EV-DATE-mutual-signal",
    "story.missed-timing.empty-seat": "EV-MISSED-empty-seat",
    "story.care.breakfast-callback": "EV-CARE-breakfast-callback",
    "story.triangle.reverse-invite": "EV-TRIANGLE-reverse-invite",
    "story.challenge.water-bridge": "EV-BRIDGE-hidden-courage",
    "story.group.truth-firepit": "EV-GROUP-truth-firepit",
    "story.bombshell.ninth-card": "EV-BOMBSHELL-ninth-card",
    "story.past.consent-reveal": "EV-PAST-consent-reveal",
    "story.trip.last-two-days": "EV-TRIP-last-two-days",
    "story.final.unsent-letter": "EV-FINAL-unsent-letter",
    "story.final.confession-day": "EV-FINAL-confession-day",
}

R4_IDENTITY_SCOPES = {"single", "pair", "triple", "current-eight"}
R4_GENERATION_MODEL = "seedance-2.0-mini"
R4_AUDIO_MODE = "native-first-play"
R4_WIDTH = 480
R4_HEIGHT = 854
R4_FPS = 24.0
R4_VIDEO_CODEC = "h264"
R4_PIXEL_FORMAT = "yuv420p"
R4_AUDIO_CODEC = "aac"
R4_AUDIO_SAMPLE_RATE = 48_000
R4_AUDIO_CHANNELS = 2
R4_FRAME_COUNT = 360
R4_MIN_INTEGRATED_LUFS = -24.5
R4_MAX_INTEGRATED_LUFS = -13.0
R4_MAX_TRUE_PEAK_DBFS = -1.0


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_file(src: str) -> Path:
    return PUBLIC / src.removeprefix("/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_media(path: Path) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]]]:
    """Return duration plus video and audio stream metadata from ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-count_frames",
            "-show_entries",
            (
                "format=duration:stream=codec_type,codec_name,width,height,pix_fmt,"
                "r_frame_rate,avg_frame_rate,sample_rate,channels,nb_read_frames"
            ),
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    duration = float((payload.get("format") or {}).get("duration"))
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    video_streams = [
        stream for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "video"
    ]
    audio_streams = [
        stream for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "audio"
    ]
    return duration, video_streams, audio_streams


def parse_frame_rate(stream: dict[str, Any]) -> float:
    """Read a usable ffprobe rational, preferring average frame rate."""
    for field in ("avg_frame_rate", "r_frame_rate"):
        raw = str(stream.get(field) or "").strip()
        if not raw:
            continue
        numerator, separator, denominator = raw.partition("/")
        try:
            value = float(numerator) / float(denominator) if separator else float(raw)
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if value > 0:
            return value
    raise ValueError("no positive avg_frame_rate or r_frame_rate")


def top_level_mp4_atoms(path: Path) -> list[str]:
    """Parse MP4 top-level atoms without loading media payloads into memory."""
    atoms: list[str] = []
    total_size = path.stat().st_size
    offset = 0
    with path.open("rb") as source:
        while offset < total_size:
            if total_size - offset < 8:
                raise ValueError(f"{total_size - offset} trailing bytes after last MP4 atom")
            source.seek(offset)
            header = source.read(8)
            atom_size = int.from_bytes(header[:4], "big")
            atom_type = header[4:8].decode("latin-1")
            header_size = 8
            if atom_size == 1:
                extended_size = source.read(8)
                if len(extended_size) != 8:
                    raise ValueError(f"truncated extended-size atom {atom_type!r}")
                atom_size = int.from_bytes(extended_size, "big")
                header_size = 16
            elif atom_size == 0:
                atom_size = total_size - offset
            if atom_size < header_size:
                raise ValueError(f"invalid size {atom_size} for atom {atom_type!r}")
            if offset + atom_size > total_size:
                raise ValueError(f"atom {atom_type!r} extends beyond end of file")
            atoms.append(atom_type)
            offset += atom_size
    return atoms


def verify_r4_media_spec(
    label: str,
    asset_id: str,
    path: Path,
    video_streams: list[dict[str, Any]],
    audio_streams: list[dict[str, Any]],
    failures: list[str],
) -> None:
    """Apply the locked runtime encode gate to one strict R4 main asset."""
    if len(video_streams) != 1:
        failures.append(
            f"{label} asset {asset_id} must contain exactly one video stream; "
            f"found {len(video_streams)}"
        )
    else:
        video = video_streams[0]
        codec = str(video.get("codec_name") or "").strip()
        if codec != R4_VIDEO_CODEC:
            failures.append(
                f"{label} video codec {codec!r} must equal {R4_VIDEO_CODEC!r}"
            )
        width, height = video.get("width"), video.get("height")
        if width != R4_WIDTH or height != R4_HEIGHT:
            failures.append(
                f"{label} dimensions {width}x{height} must equal {R4_WIDTH}x{R4_HEIGHT}"
            )
        pixel_format = str(video.get("pix_fmt") or "").strip()
        if pixel_format != R4_PIXEL_FORMAT:
            failures.append(
                f"{label} pixel format {pixel_format!r} must equal {R4_PIXEL_FORMAT!r}"
            )
        try:
            fps = parse_frame_rate(video)
        except ValueError as error:
            failures.append(f"{label} cannot determine video frame rate: {error}")
        else:
            if abs(fps - R4_FPS) > 0.01:
                failures.append(f"{label} frame rate {fps:.6g}fps must equal {R4_FPS:.0f}fps")
        try:
            decoded_frames = int(video.get("nb_read_frames") or 0)
        except (TypeError, ValueError):
            decoded_frames = 0
        if decoded_frames != R4_FRAME_COUNT:
            failures.append(
                f"{label} decoded frame count {decoded_frames} must equal {R4_FRAME_COUNT}"
            )

    if len(audio_streams) != 1:
        failures.append(
            f"{label} asset {asset_id} must contain exactly one audio stream; "
            f"found {len(audio_streams)}"
        )
    else:
        audio = audio_streams[0]
        codec = str(audio.get("codec_name") or "").strip()
        if codec != R4_AUDIO_CODEC:
            failures.append(
                f"{label} audio codec {codec!r} must equal {R4_AUDIO_CODEC!r}"
            )
        sample_rate = str(audio.get("sample_rate") or "").strip()
        try:
            parsed_sample_rate = int(sample_rate)
        except (TypeError, ValueError):
            parsed_sample_rate = 0
        if parsed_sample_rate != R4_AUDIO_SAMPLE_RATE:
            failures.append(
                f"{label} audio sample rate {sample_rate!r} must equal "
                f"{R4_AUDIO_SAMPLE_RATE}Hz"
            )
        channels = audio.get("channels")
        if channels != R4_AUDIO_CHANNELS:
            failures.append(
                f"{label} audio channels {channels!r} must equal "
                f"{R4_AUDIO_CHANNELS} (stereo)"
            )

    try:
        atoms = top_level_mp4_atoms(path)
    except (OSError, ValueError) as error:
        failures.append(f"{label} cannot inspect MP4 atoms for faststart: {error}")
    else:
        if "moov" not in atoms or "mdat" not in atoms:
            failures.append(
                f"{label} MP4 must contain top-level moov and mdat atoms; found {atoms}"
            )
        elif atoms.index("moov") > atoms.index("mdat"):
            failures.append(
                f"{label} is not faststart: top-level moov occurs after mdat ({atoms})"
            )


def decode_video(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        check=True,
        capture_output=True,
        text=True,
    )


def measure_loudness(path: Path) -> dict[str, float]:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-af", "loudnorm=I=-16:TP=-2:LRA=7:print_format=json",
            "-f", "null", "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    start = result.stderr.rfind("{")
    end = result.stderr.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("loudness analysis did not return JSON")
    payload = json.loads(result.stderr[start:end + 1])
    return {
        "integratedLufs": float(payload["input_i"]),
        "truePeakDbfs": float(payload["input_tp"]),
        "loudnessRangeLu": float(payload["input_lra"]),
    }


def verify_r4_loudness(label: str, path: Path, failures: list[str]) -> None:
    try:
        loudness = measure_loudness(path)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError, json.JSONDecodeError) as error:
        failures.append(f"{label} cannot measure runtime loudness: {error}")
        return
    integrated = loudness["integratedLufs"]
    peak = loudness["truePeakDbfs"]
    if not R4_MIN_INTEGRATED_LUFS <= integrated <= R4_MAX_INTEGRATED_LUFS:
        failures.append(
            f"{label} integrated loudness {integrated:.1f} LUFS must be within "
            f"[{R4_MIN_INTEGRATED_LUFS}, {R4_MAX_INTEGRATED_LUFS}]"
        )
    if peak > R4_MAX_TRUE_PEAK_DBFS:
        failures.append(
            f"{label} true peak {peak:.1f} dBFS must not exceed {R4_MAX_TRUE_PEAK_DBFS:.1f} dBFS"
        )


def verify_asset(
    label: str,
    asset_id: str,
    expected_src: str,
    expected_poster: str,
    expected_trigger: str,
    assets: dict[str, dict[str, Any]],
    audio_qa_items: dict[str, dict[str, Any]],
    visual_qa_items: dict[str, dict[str, Any]],
    duplicate_asset_ids: set[str],
    failures: list[str],
    warnings: list[str],
    *,
    strict_r4: bool,
) -> bool:
    """Append all failures for one asset and return its real pass state."""
    start_failure_count = len(failures)
    asset = assets.get(asset_id)
    if not asset:
        failures.append(f"{label} references unknown assetId {asset_id}")
        return False
    if asset_id in duplicate_asset_ids:
        failures.append(f"{label} assetId {asset_id} is duplicated in the manifest")
    if asset.get("kind") == "dynamic-portrait":
        failures.append(f"{label} incorrectly uses character portrait {asset_id} as event footage")

    approval = str(asset.get("status") or "")
    if approval not in RUNTIME_STATUSES:
        allowed = ", ".join(sorted(RUNTIME_STATUSES))
        failures.append(f"{label} asset {asset_id} status {approval!r} is not one of: {allowed}")

    actual_trigger = str(asset.get("trigger") or "").strip()
    if actual_trigger != expected_trigger:
        failures.append(f"{label} trigger {actual_trigger!r} must equal {expected_trigger!r}")

    actual_src = str(asset.get("path") or "").strip()
    if actual_src != expected_src:
        failures.append(f"{label} path {actual_src!r} must equal {expected_src!r}")
    actual_poster_src = str(asset.get("poster") or "").strip()
    if actual_poster_src != expected_poster:
        failures.append(f"{label} poster {actual_poster_src!r} must equal {expected_poster!r}")

    if strict_r4:
        identity_reference = str(asset.get("identityReference") or "").strip()
        if not identity_reference:
            failures.append(f"{label} asset {asset_id} has no identityReference")
        else:
            identity_path = (ROOT / identity_reference).resolve()
            if ROOT not in identity_path.parents or not identity_path.is_file():
                failures.append(
                    f"{label} asset {asset_id} identityReference is missing or outside workspace"
                )
        identity_cast = asset.get("identityCast")
        if not isinstance(identity_cast, list) or not identity_cast or not all(
            isinstance(member, str) and member.strip() for member in identity_cast
        ):
            failures.append(
                f"{label} asset {asset_id} identityCast must be a non-empty string array"
            )
        identity_scope = str(asset.get("identityScope") or "").strip()
        if identity_scope not in R4_IDENTITY_SCOPES:
            failures.append(
                f"{label} asset {asset_id} identityScope {identity_scope!r} must be one of "
                f"{', '.join(sorted(R4_IDENTITY_SCOPES))}"
            )
        prompt_file = str(asset.get("generationPromptFile") or "").strip()
        if not prompt_file:
            failures.append(f"{label} asset {asset_id} has no generationPromptFile")
        else:
            prompt_path = (ROOT / prompt_file).resolve()
            if ROOT not in prompt_path.parents or not prompt_path.is_file():
                failures.append(
                    f"{label} asset {asset_id} generationPromptFile is missing or outside workspace"
                )
        generation_model = str(asset.get("generationModel") or "").strip()
        if generation_model != R4_GENERATION_MODEL:
            failures.append(
                f"{label} asset {asset_id} generationModel {generation_model!r} "
                f"must equal {R4_GENERATION_MODEL!r}"
            )
        audio = asset.get("audio") if isinstance(asset.get("audio"), dict) else {}
        if audio.get("hasAudio") is not True:
            failures.append(f"{label} asset {asset_id} audio.hasAudio must equal true")
        if str(audio.get("mode") or "").strip() != R4_AUDIO_MODE:
            failures.append(
                f"{label} asset {asset_id} audio.mode must equal {R4_AUDIO_MODE!r}"
            )
        if str(audio.get("qaVerdict") or "").strip() != "passed":
            failures.append(f"{label} asset {asset_id} audio.qaVerdict must equal 'passed'")
        if str(asset.get("qaVerdict") or "").strip() != "passed":
            failures.append(f"{label} asset {asset_id} qaVerdict must equal 'passed'")
        if str(asset.get("qaEvidence") or "").strip() != AUDIO_QA_RELATIVE:
            failures.append(
                f"{label} asset {asset_id} qaEvidence must equal {AUDIO_QA_RELATIVE!r}"
            )
        audio_qa = audio_qa_items.get(asset_id)
        if not audio_qa:
            failures.append(f"{label} asset {asset_id} has no matching audio QA item")
        else:
            verdicts = (
                audio_qa.get("verdict"),
                audio_qa.get("contentVerdict"),
                audio_qa.get("technicalVerdict"),
            )
            if verdicts != ("passed", "passed", "passed"):
                failures.append(f"{label} asset {asset_id} audio QA is not fully passed: {verdicts}")
            if str(audio_qa.get("sha256") or "").strip() != str(asset.get("sha256") or "").strip():
                failures.append(f"{label} asset {asset_id} audio QA SHA disagrees with manifest")
        if str(asset.get("visualQaEvidence") or "").strip() != VISUAL_QA_RELATIVE:
            failures.append(
                f"{label} asset {asset_id} visualQaEvidence must equal {VISUAL_QA_RELATIVE!r}"
            )
        visual_qa = visual_qa_items.get(asset_id)
        if not visual_qa:
            failures.append(f"{label} asset {asset_id} has no matching visual QA item")
        else:
            verdicts = (
                visual_qa.get("verdict"),
                visual_qa.get("identityVerdict"),
                visual_qa.get("frameVerdict"),
            )
            if verdicts != ("passed", "passed", "passed"):
                failures.append(f"{label} asset {asset_id} visual QA is not fully passed: {verdicts}")
            if str(visual_qa.get("sha256") or "").strip() != str(asset.get("sha256") or "").strip():
                failures.append(f"{label} asset {asset_id} visual QA SHA disagrees with manifest")

    path = runtime_file(expected_src)
    if not path.is_file():
        failures.append(f"{label} points to missing video {expected_src}")
    else:
        expected_hash = str(asset.get("sha256") or "").strip()
        if not expected_hash:
            failures.append(f"{label} asset {asset_id} has no sha256")
        elif sha256_file(path) != expected_hash:
            failures.append(f"{label} video hash disagrees with manifest for {asset_id}")
        try:
            actual_duration, video_streams, audio_streams = probe_media(path)
            decode_video(path)
        except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as error:
            failures.append(f"{label} cannot be fully decoded as video: {error}")
        else:
            declared_duration = asset.get("duration")
            if not isinstance(declared_duration, (int, float)):
                failures.append(f"{label} asset {asset_id} has no numeric duration")
            elif abs(float(declared_duration) - actual_duration) > 0.25:
                failures.append(
                    f"{label} duration {actual_duration:.3f}s disagrees with manifest {declared_duration}s"
                )
            if actual_duration < MIN_EVENT_SECONDS:
                failures.append(
                    f"{label} is only {actual_duration:.3f}s; event films must be at least {MIN_EVENT_SECONDS:.1f}s"
                )
            elif actual_duration < PREFERRED_EVENT_SECONDS:
                warnings.append(f"{label} is {actual_duration:.3f}s rather than the preferred ~15s")
            if strict_r4:
                verify_r4_media_spec(
                    label, asset_id, path, video_streams, audio_streams, failures
                )
                verify_r4_loudness(label, path, failures)

    poster_path = runtime_file(expected_poster)
    if not poster_path.is_file():
        failures.append(f"{label} points to missing poster {expected_poster}")
    else:
        poster_hash = str(asset.get("posterSha256") or "").strip()
        if not poster_hash:
            failures.append(f"{label} asset {asset_id} has no posterSha256")
        elif sha256_file(poster_path) != poster_hash:
            failures.append(f"{label} poster hash disagrees with manifest for {asset_id}")

    return len(failures) == start_failure_count


def validate_unique_master_contracts(
    contract_asset_ids: set[str],
    assets: dict[str, dict[str, Any]],
    failures: list[str],
) -> set[str]:
    """Require every one of the 25 R4 main contracts to own a unique master."""
    failed_asset_ids: set[str] = set()
    by_hash: dict[str, list[str]] = defaultdict(list)
    for asset_id in sorted(contract_asset_ids):
        asset = assets.get(asset_id) or {}
        digest = str(asset.get("sha256") or "").strip()
        if digest:
            by_hash[digest].append(asset_id)

    for digest, asset_ids in sorted(by_hash.items()):
        if len(asset_ids) > 1:
            failures.append(
                "R4 main event assets must not reuse a physical master: "
                f"{', '.join(sorted(asset_ids))} ({digest[:12]}...)"
            )
            failed_asset_ids.update(asset_ids)

    for asset_id in sorted(contract_asset_ids):
        if str((assets.get(asset_id) or {}).get("reuseOfAssetId") or "").strip():
            failures.append(f"R4 main event asset {asset_id} must not declare reuseOfAssetId")
            failed_asset_ids.add(asset_id)

    present_assets = [assets.get(asset_id) for asset_id in contract_asset_ids]
    if len(contract_asset_ids) == 25 and all(present_assets):
        digests = [str(asset.get("sha256") or "").strip() for asset in present_assets if asset]
        if all(digests) and len(set(digests)) != 25:
            failures.append(
                "25 R4 main event contracts must resolve to exactly 25 unique master SHAs; "
                f"found {len(set(digests))}"
            )
            failed_asset_ids.update(contract_asset_ids)
    return failed_asset_ids


def load_audio_qa_items(failures: list[str]) -> dict[str, dict[str, Any]]:
    if not AUDIO_QA_PATH.is_file():
        failures.append(f"required audio QA report is missing: {AUDIO_QA_RELATIVE}")
        return {}
    try:
        report = load_json(AUDIO_QA_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        failures.append(f"cannot parse audio QA report: {error}")
        return {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    if summary.get("total") != 25 or summary.get("passed") != 25 or summary.get("p1") != 0 or summary.get("p0") != 0:
        failures.append(f"audio QA summary is not a clean 25/25 pass: {summary}")
    rows = [row for row in report.get("items", []) if isinstance(row, dict)]
    ids = [str(row.get("id") or "").strip() for row in rows]
    duplicates = {asset_id for asset_id, count in Counter(ids).items() if asset_id and count > 1}
    expected_ids = set(EXPECTED_DAY1_ASSET_IDS.values()) | set(EXPECTED_STORY_ASSET_IDS.values())
    if len(rows) != 25 or set(ids) != expected_ids:
        failures.append("audio QA report must contain exactly the 25 expected asset IDs")
    if duplicates:
        failures.append(f"audio QA report contains duplicate IDs: {', '.join(sorted(duplicates))}")
    return {asset_id: row for asset_id, row in zip(ids, rows) if asset_id and asset_id not in duplicates}


def load_visual_qa_items(failures: list[str]) -> dict[str, dict[str, Any]]:
    if not VISUAL_QA_PATH.is_file():
        failures.append(f"required visual QA report is missing: {VISUAL_QA_RELATIVE}")
        return {}
    try:
        report = load_json(VISUAL_QA_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        failures.append(f"cannot parse visual QA report: {error}")
        return {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    if summary.get("total") != 25 or summary.get("passed") != 25 or summary.get("p1") != 0 or summary.get("p0") != 0:
        failures.append(f"visual QA summary is not a clean 25/25 pass: {summary}")
    rows = [row for row in report.get("items", []) if isinstance(row, dict)]
    ids = [str(row.get("id") or "").strip() for row in rows]
    duplicates = {asset_id for asset_id, count in Counter(ids).items() if asset_id and count > 1}
    expected_ids = set(EXPECTED_DAY1_ASSET_IDS.values()) | set(EXPECTED_STORY_ASSET_IDS.values())
    if len(rows) != 25 or set(ids) != expected_ids:
        failures.append("visual QA report must contain exactly the 25 expected asset IDs")
    if duplicates:
        failures.append(f"visual QA report contains duplicate IDs: {', '.join(sorted(duplicates))}")
    return {asset_id: row for asset_id, row in zip(ids, rows) if asset_id and asset_id not in duplicates}


def main() -> int:
    sys.path.insert(0, str(ROOT))
    # Imported after the workspace is on sys.path. The media contract—not an old
    # blueprint cinematic—is the authoritative route for every Day 1 node.
    from backend.game_content import DAY1_MEDIA_CONTRACT, NODES

    catalog = load_json(CATALOG_PATH)
    manifest = load_json(MANIFEST_PATH)
    failures: list[str] = []
    warnings: list[str] = []
    rows: list[tuple[str, str, str, str]] = []
    audio_qa_items = load_audio_qa_items(failures)
    visual_qa_items = load_visual_qa_items(failures)

    manifest_items = [item for item in manifest.get("assets", []) if isinstance(item, dict)]
    manifest_ids = [str(item.get("id") or "").strip() for item in manifest_items]
    for index, asset_id in enumerate(manifest_ids):
        if not asset_id:
            failures.append(f"manifest asset at index {index} has no id")
    duplicate_asset_ids = {
        asset_id for asset_id, count in Counter(manifest_ids).items() if asset_id and count > 1
    }
    for asset_id in sorted(duplicate_asset_ids):
        failures.append(f"manifest contains duplicate asset id {asset_id}")
    assets: dict[str, dict[str, Any]] = {}
    for item, asset_id in zip(manifest_items, manifest_ids):
        if asset_id:
            assets.setdefault(asset_id, item)

    node_ids = list(NODES)
    expected_day1_ids = set(EXPECTED_DAY1_ASSET_IDS)
    if len(node_ids) != 9 or set(node_ids) != expected_day1_ids:
        failures.append(
            "Day1 must contain exactly the expected 9 nodes; "
            f"missing={sorted(expected_day1_ids - set(node_ids))}, "
            f"extra={sorted(set(node_ids) - expected_day1_ids)}"
        )
    contract_node_ids = set(DAY1_MEDIA_CONTRACT)
    if contract_node_ids != expected_day1_ids:
        failures.append(
            "DAY1_MEDIA_CONTRACT must cover exactly the expected 9 nodes; "
            f"missing={sorted(expected_day1_ids - contract_node_ids)}, "
            f"extra={sorted(contract_node_ids - expected_day1_ids)}"
        )

    events = [event for event in catalog.get("events", []) if isinstance(event, dict)]
    event_ids = [str(event.get("id") or "").strip() for event in events]
    duplicate_event_ids = {
        event_id for event_id, count in Counter(event_ids).items() if event_id and count > 1
    }
    for event_id in sorted(duplicate_event_ids):
        failures.append(f"story catalog contains duplicate event id {event_id}")
    expected_story_ids = set(EXPECTED_STORY_ASSET_IDS)
    if len(event_ids) != 16 or set(event_ids) != expected_story_ids:
        failures.append(
            "StoryEvent catalog must contain exactly the expected 16 events; "
            f"missing={sorted(expected_story_ids - set(event_ids))}, "
            f"extra={sorted(set(event_ids) - expected_story_ids)}"
        )

    contract_asset_ids: set[str] = set()
    variant_asset_ids: set[str] = set()

    for node_id in EXPECTED_DAY1_ASSET_IDS:
        label = f"Day1 node {node_id!r}"
        contract_failures: list[str] = []
        contract = DAY1_MEDIA_CONTRACT.get(node_id) or {}
        expected_asset_id = EXPECTED_DAY1_ASSET_IDS[node_id]
        asset_id = str(contract.get("assetId") or "").strip()
        if asset_id != expected_asset_id:
            contract_failures.append(
                f"{label} assetId {asset_id!r} must equal {expected_asset_id!r}"
            )
        contract_asset_ids.add(expected_asset_id)
        expected_src = f"/media/video/{expected_asset_id}.mp4"
        expected_poster = f"/media/posters/{expected_asset_id}.jpg"
        expected_trigger = f"node.{node_id}.committed"
        verify_asset(
            label,
            expected_asset_id,
            expected_src,
            expected_poster,
            expected_trigger,
            assets,
            audio_qa_items,
            visual_qa_items,
            duplicate_asset_ids,
            contract_failures,
            warnings,
            strict_r4=True,
        )
        failures.extend(contract_failures)
        rows.append(
            (f"day1:{node_id}", "covered" if not contract_failures else "failed", expected_src, expected_asset_id)
        )

        variants = contract.get("variantAssetIds")
        if not isinstance(variants, dict):
            continue
        for character_id, raw_variant_id in variants.items():
            variant_id = str(raw_variant_id or "").strip()
            if not variant_id or variant_id not in assets:
                continue
            # Historical character variants remain useful local extras, but are
            # not part of the 25-main-asset R4 gate. Validate only variants that
            # are both declared by this contract and actually present in the
            # manifest, and retain the legacy file/hash/full-decode checks. In
            # particular, a silent old variant must not block the current Jiangmi
            # mainline's native-first-play audio acceptance.
            variant_asset_ids.add(variant_id)
            variant_label = f"Day1 node {node_id!r} variant {character_id!r}"
            variant_failures: list[str] = []
            verify_asset(
                variant_label,
                variant_id,
                f"/media/video/{variant_id}.mp4",
                f"/media/posters/{variant_id}.jpg",
                expected_trigger,
                assets,
                audio_qa_items,
                visual_qa_items,
                duplicate_asset_ids,
                variant_failures,
                warnings,
                strict_r4=False,
            )
            failures.extend(variant_failures)
            rows.append(
                (
                    f"variant:{node_id}:{character_id}",
                    "covered" if not variant_failures else "failed",
                    f"/media/video/{variant_id}.mp4",
                    variant_id,
                )
            )

    event_by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        event_id = str(event.get("id") or "").strip()
        if event_id:
            event_by_id.setdefault(event_id, event)

    for event_id in EXPECTED_STORY_ASSET_IDS:
        label = f"Story event {event_id!r}"
        contract_failures: list[str] = []
        if event_id in duplicate_event_ids:
            contract_failures.append(f"{label} is duplicated in the story catalog")
        event = event_by_id.get(event_id) or {}
        plan = event.get("mediaPlan") if isinstance(event.get("mediaPlan"), dict) else {}
        runtime = plan.get("runtimeAsset") if isinstance(plan.get("runtimeAsset"), dict) else {}
        expected_asset_id = EXPECTED_STORY_ASSET_IDS[event_id]
        contract_asset_ids.add(expected_asset_id)

        plan_asset_id = str(plan.get("assetId") or "").strip()
        runtime_asset_id = str(runtime.get("assetId") or "").strip()
        if plan_asset_id != expected_asset_id:
            contract_failures.append(
                f"{label} mediaPlan.assetId {plan_asset_id!r} must equal {expected_asset_id!r}"
            )
        if runtime_asset_id != expected_asset_id:
            contract_failures.append(
                f"{label} runtimeAsset.assetId {runtime_asset_id!r} must equal {expected_asset_id!r}"
            )
        if str(plan.get("status") or "") != "ready":
            contract_failures.append(f"{label} mediaPlan.status must equal 'ready'")

        expected_src = f"/media/video/{expected_asset_id}.mp4"
        expected_poster = f"/media/posters/{expected_asset_id}.jpg"
        plan_src = str(plan.get("src") or "").strip()
        runtime_src = str(runtime.get("src") or "").strip()
        plan_poster = str(plan.get("poster") or "").strip()
        runtime_poster = str(runtime.get("poster") or "").strip()
        if plan_src != expected_src:
            contract_failures.append(f"{label} mediaPlan.src {plan_src!r} must equal {expected_src!r}")
        if runtime_src != expected_src:
            contract_failures.append(
                f"{label} runtimeAsset.src {runtime_src!r} must equal {expected_src!r}"
            )
        if plan_poster != expected_poster:
            contract_failures.append(
                f"{label} mediaPlan.poster {plan_poster!r} must equal {expected_poster!r}"
            )
        if runtime_poster != expected_poster:
            contract_failures.append(
                f"{label} runtimeAsset.poster {runtime_poster!r} must equal {expected_poster!r}"
            )

        asset = assets.get(expected_asset_id) or {}
        runtime_duration = runtime.get("durationSeconds")
        manifest_duration = asset.get("duration")
        if not isinstance(runtime_duration, (int, float)):
            contract_failures.append(f"{label} runtimeAsset has no numeric durationSeconds")
        elif not isinstance(manifest_duration, (int, float)):
            contract_failures.append(f"{label} manifest asset has no numeric duration")
        elif abs(float(runtime_duration) - float(manifest_duration)) > 0.25:
            contract_failures.append(
                f"{label} runtimeAsset duration {runtime_duration}s disagrees with manifest {manifest_duration}s"
            )

        verify_asset(
            label,
            expected_asset_id,
            expected_src,
            expected_poster,
            f"{event_id}.committed",
            assets,
            audio_qa_items,
            visual_qa_items,
            duplicate_asset_ids,
            contract_failures,
            warnings,
            strict_r4=True,
        )
        failures.extend(contract_failures)
        rows.append(
            (f"event:{event_id}", "covered" if not contract_failures else "failed", expected_src, expected_asset_id)
        )

    reuse_failed_asset_ids = validate_unique_master_contracts(
        contract_asset_ids, assets, failures
    )
    rows = [
        (item_id, "failed" if asset_id in reuse_failed_asset_ids else status, src, asset_id)
        for item_id, status, src, asset_id in rows
    ]

    for item_id, status, src, _asset_id in rows:
        print(f"{status:7}  {item_id:54}  {src}")
    base_rows = [row for row in rows if not row[0].startswith("variant:")]
    covered_count = sum(status == "covered" for _, status, _, _ in base_rows)
    print(f"\ncoverage={covered_count}/25")
    if variant_asset_ids:
        variant_rows = [row for row in rows if row[0].startswith("variant:")]
        variant_passed = sum(status == "covered" for _, status, _, _ in variant_rows)
        print(f"variants={variant_passed}/{len(variant_rows)} present manifest variants")
    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"- {warning}")
    if failures:
        sys.stdout.flush()
        print("\nFAILURES:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("All 9 Day1 and 16 StoryEvent contracts have verified R4 runtime media.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
