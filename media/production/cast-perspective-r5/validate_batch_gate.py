#!/usr/bin/env python3
"""Offline, fail-closed validation for the R5 paid media batch.

The authoritative job set is derived from runtime-variant-matrix.json entries
whose status is requiresGeneration. This program performs no HTTP requests and
never reads provider credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


EXPECTED_MODEL = "seedance-2.0-mini"
EXPECTED_PROVIDER = "fumin"
EXPECTED_RATIO = "9:16"
EXPECTED_DURATION = 15
EXPECTED_RESOLUTION = "720p"
EXPECTED_GENERATE_AUDIO = True
EXPECTED_WATERMARK = False
EXPECTED_CONCURRENCY = 2
EXPECTED_MAX_API_RETRY = 0
EXPECTED_SEMANTIC_GAP = 178
EXPECTED_TASK_COUNT = 198
EXPECTED_LOCAL_COMPOSITE_COUNT = 4
EXPECTED_TOTAL_DURATION_SECONDS = 2970
EXPECTED_RUNTIME_TOTAL = 188
EXPECTED_RUNTIME_REUSABLE = 10
EXPECTED_RUNTIME_MATRIX_SHA256 = "e7ef4b874c1d06d32526c66a59400be4cab4850538f0cbaddbaf3689f86f8a6a"
EXPECTED_INTRO_EVENT_ID = "day1.introductions"
EXPECTED_CURRENT_EIGHT_TARGET = "D1-A3B-cast-first-impressions--group-current-eight"
EXPECTED_CHARACTER_ORDER = [
    "shenmo",
    "linyu",
    "chengye",
    "guyan",
    "jiangwan",
    "jiangmi",
    "sunnian",
    "chensu",
]
EXPECTED_ROUTING_COUNTS = {
    "perspective": 58,
    "current-eight": 4,
    "participant-pov": 32,
    "unordered-pair": 81,
    "fixed-cast": 3,
}
SEMANTIC_FIELDS = [
    "targetAssetId",
    "eventId",
    "servedEventIds",
    "routingMode",
    "perspectiveCharacterId",
    "applicablePerspectiveCharacterIds",
    "participantIds",
    "identityCast",
]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER_RE = re.compile(r"(?:REPLACE|TODO|TBD|CHANGEME|PLACEHOLDER)", re.I)


class GateError(RuntimeError):
    """Raised when the paid submission contract is incomplete or inconsistent."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise GateError(f"file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise GateError(f"invalid JSON in {path}: {error}") from error


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateError(f"{label} must be an object")
    return value


def require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise GateError(f"{label} keys mismatch; missing={missing}, extra={extra}")


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateError(f"{label} must be an array")
    return value


def require_exact(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise GateError(f"{label} must be {expected!r}; got {value!r}")


def require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise GateError(f"{label} must be a boolean")
    return value


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GateError(f"{label} must be an integer")
    return value


def require_text(value: Any, label: str, *, allow_placeholder: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{label} must be a non-empty string")
    text = value.strip()
    if not allow_placeholder and PLACEHOLDER_RE.search(text):
        raise GateError(f"{label} still contains a placeholder")
    return text


def require_text_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    raw = require_list(value, label)
    if not allow_empty and not raw:
        raise GateError(f"{label} must not be empty")
    items = [require_text(item, f"{label}[{index}]") for index, item in enumerate(raw)]
    if len(items) != len(set(items)):
        raise GateError(f"{label} must not contain duplicates")
    return items


def require_sha(value: Any, label: str, *, allow_zero: bool = False) -> str:
    text = require_text(value, label, allow_placeholder=True)
    if not SHA256_RE.fullmatch(text):
        raise GateError(f"{label} must be a lowercase SHA-256 hex digest")
    if not allow_zero and text == "0" * 64:
        raise GateError(f"{label} is still the zero placeholder")
    return text


def require_ref_ids(value: Any, label: str, *, allow_empty: bool = False) -> set[str]:
    return set(require_text_list(value, label, allow_empty=allow_empty))


def require_timestamp(value: Any, label: str) -> datetime:
    text = require_text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise GateError(f"{label} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise GateError(f"{label} must include a timezone")
    parsed_utc = parsed.astimezone(timezone.utc)
    if parsed_utc.year < 2025:
        raise GateError(f"{label} is a template/expired timestamp")
    if parsed_utc > datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=5):
        raise GateError(f"{label} cannot be in the future")
    return parsed_utc


def require_decimal(value: Any, label: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GateError(f"{label} must be a decimal amount")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise GateError(f"{label} is not a valid decimal amount") from error
    if not amount.is_finite():
        raise GateError(f"{label} must be finite")
    if positive and amount <= 0:
        raise GateError(f"{label} must be greater than zero")
    if not positive and amount < 0:
        raise GateError(f"{label} must be zero or greater")
    return amount


def resolve_relative_file(base_file: Path, raw: Any, label: str) -> Path:
    value = require_text(raw, label)
    candidate = Path(value)
    if candidate.is_absolute():
        raise GateError(f"{label} must be a relative, reviewable path")
    resolved = (base_file.parent / candidate).resolve()
    if not resolved.is_file():
        raise GateError(f"{label} does not exist: {resolved}")
    return resolved


def validate_runtime_matrix(
    runtime: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    require_exact(
        runtime.get("schemaVersion"),
        "heart-journey/runtime-variant-matrix-v1",
        "runtimeMatrix.schemaVersion",
    )
    authority = require_object(runtime.get("authority"), "runtimeMatrix.authority")
    require_exact(
        authority.get("characterOrder"),
        EXPECTED_CHARACTER_ORDER,
        "runtimeMatrix.authority.characterOrder",
    )
    summary = require_object(runtime.get("summary"), "runtimeMatrix.summary")
    require_exact(summary.get("totalUniqueMasters"), EXPECTED_RUNTIME_TOTAL, "runtimeMatrix.summary.totalUniqueMasters")
    require_exact(summary.get("currentReusable"), EXPECTED_RUNTIME_REUSABLE, "runtimeMatrix.summary.currentReusable")
    require_exact(summary.get("generationGap"), EXPECTED_SEMANTIC_GAP, "runtimeMatrix.summary.generationGap")
    require_exact(
        summary.get("contentContractRejectedTargetAssetIds"),
        ["D1-A3-cast-introductions--p-jiangmi"],
        "runtimeMatrix.summary.contentContractRejectedTargetAssetIds",
    )

    masters = require_list(runtime.get("masters"), "runtimeMatrix.masters")
    require_exact(len(masters), EXPECTED_RUNTIME_TOTAL, "runtimeMatrix.masters length")
    seen: set[str] = set()
    required: dict[str, dict[str, Any]] = {}
    status_counts: Counter[str] = Counter()
    routing_counts: Counter[str] = Counter()
    for index, raw in enumerate(masters):
        master = require_object(raw, f"runtimeMatrix.masters[{index}]")
        for field in SEMANTIC_FIELDS + ["status"]:
            if field not in master:
                raise GateError(f"runtimeMatrix.masters[{index}] is missing {field}")
        target_id = require_text(master.get("targetAssetId"), f"runtimeMatrix.masters[{index}].targetAssetId")
        if target_id in seen:
            raise GateError(f"runtimeMatrix has duplicate targetAssetId: {target_id}")
        seen.add(target_id)
        status = require_text(master.get("status"), f"runtimeMatrix.masters[{index}].status")
        if status not in {"requiresGeneration", "existingApprovedReusable"}:
            raise GateError(f"runtimeMatrix master {target_id} has unsupported status {status!r}")
        status_counts[status] += 1
        identity_cast = require_text_list(master.get("identityCast"), f"runtimeMatrix master {target_id}.identityCast", allow_empty=False)
        unknown = set(identity_cast) - set(EXPECTED_CHARACTER_ORDER)
        if unknown:
            raise GateError(f"runtimeMatrix master {target_id} has unknown identityCast ids: {sorted(unknown)}")
        require_text_list(master.get("servedEventIds"), f"runtimeMatrix master {target_id}.servedEventIds", allow_empty=False)
        require_text_list(master.get("applicablePerspectiveCharacterIds"), f"runtimeMatrix master {target_id}.applicablePerspectiveCharacterIds", allow_empty=False)
        require_text_list(master.get("participantIds"), f"runtimeMatrix master {target_id}.participantIds")
        if status == "requiresGeneration":
            required[target_id] = master
            routing_counts[require_text(master.get("routingMode"), f"runtimeMatrix master {target_id}.routingMode")] += 1

    require_exact(status_counts["requiresGeneration"], EXPECTED_SEMANTIC_GAP, "runtimeMatrix requiresGeneration count")
    require_exact(status_counts["existingApprovedReusable"], EXPECTED_RUNTIME_REUSABLE, "runtimeMatrix reusable count")
    require_exact(dict(routing_counts), EXPECTED_ROUTING_COUNTS, "runtimeMatrix requiresGeneration routing counts")
    return required


def validate_task_matrix(
    matrix: dict[str, Any], matrix_path: Path
) -> tuple[dict[str, dict[str, Any]], dict[str, str], Path, str]:
    require_exact_keys(
        matrix,
        {
            "schemaVersion",
            "sourceRuntimeVariantMatrix",
            "derivation",
            "generationContract",
            "requiredVoicedIntroductions",
            "characters",
            "requiredCurrentEightMaster",
            "claimBoundary",
            "currentEightAssembly",
        },
        "taskMatrix",
    )
    require_exact(matrix.get("schemaVersion"), "cast-perspective-r5/task-matrix-v3", "taskMatrix.schemaVersion")
    source = require_object(matrix.get("sourceRuntimeVariantMatrix"), "taskMatrix.sourceRuntimeVariantMatrix")
    require_exact_keys(
        source,
        {
            "path",
            "sha256",
            "schemaVersion",
            "expectedTotalUniqueMasters",
            "expectedCurrentReusable",
            "expectedGenerationGap",
        },
        "taskMatrix.sourceRuntimeVariantMatrix",
    )
    require_exact(source.get("path"), "runtime-variant-matrix.json", "taskMatrix source path")
    require_exact(source.get("sha256"), EXPECTED_RUNTIME_MATRIX_SHA256, "taskMatrix source sha256")
    require_exact(source.get("schemaVersion"), "heart-journey/runtime-variant-matrix-v1", "taskMatrix source schemaVersion")
    require_exact(source.get("expectedTotalUniqueMasters"), EXPECTED_RUNTIME_TOTAL, "taskMatrix source total")
    require_exact(source.get("expectedCurrentReusable"), EXPECTED_RUNTIME_REUSABLE, "taskMatrix source reusable")
    require_exact(source.get("expectedGenerationGap"), EXPECTED_SEMANTIC_GAP, "taskMatrix source gap")
    runtime_path = resolve_relative_file(matrix_path, source.get("path"), "taskMatrix source path")
    runtime_hash = file_sha256(runtime_path)
    require_exact(runtime_hash, EXPECTED_RUNTIME_MATRIX_SHA256, "runtime variant matrix file sha256")
    runtime = require_object(load_json(runtime_path), "runtime variant matrix")
    required = validate_runtime_matrix(runtime)

    derivation = require_object(matrix.get("derivation"), "taskMatrix.derivation")
    require_exact(
        derivation,
        {
            "statusField": "status",
            "requiredStatus": "requiresGeneration",
            "uniqueKey": "targetAssetId",
            "semanticFields": SEMANTIC_FIELDS,
        },
        "taskMatrix.derivation",
    )
    contract = require_object(matrix.get("generationContract"), "taskMatrix.generationContract")
    require_exact(contract.get("expectedSemanticMasterGap"), EXPECTED_SEMANTIC_GAP, "taskMatrix semantic gap")
    require_exact(contract.get("expectedProviderJobCount"), EXPECTED_TASK_COUNT, "taskMatrix provider job count")
    require_exact(contract.get("expectedLocalCompositeOutputs"), EXPECTED_LOCAL_COMPOSITE_COUNT, "taskMatrix local composite count")
    require_exact(contract.get("durationSecondsPerProviderJob"), EXPECTED_DURATION, "taskMatrix provider duration")
    require_exact(contract.get("expectedTotalProviderDurationSeconds"), EXPECTED_TOTAL_DURATION_SECONDS, "taskMatrix total provider duration")
    require_exact(contract.get("requiredSemanticRoutingModeCounts"), EXPECTED_ROUTING_COUNTS, "taskMatrix semantic routing counts")

    assembly = require_object(matrix.get("currentEightAssembly"), "taskMatrix.currentEightAssembly")
    require_exact(
        assembly,
        {
            "policy": "never-submit-a-direct-eight-face-provider-job",
            "semanticTargetCount": 4,
            "d1a3bTargetAssetId": EXPECTED_CURRENT_EIGHT_TARGET,
            "d1a3bSource": "reuse-the-eight-required-voiced-introduction-provider-jobs",
            "otherCurrentEightTargetCount": 3,
            "atomsPerTarget": 8,
            "providerAtomJobCount": 24,
            "localCompositeOutputCount": 4,
        },
        "taskMatrix.currentEightAssembly",
    )

    characters_raw = require_object(matrix.get("characters"), "taskMatrix.characters")
    characters: dict[str, str] = {}
    for character_id, raw in characters_raw.items():
        character = require_object(raw, f"taskMatrix.characters.{character_id}")
        require_exact_keys(character, {"displayName"}, f"taskMatrix.characters.{character_id}")
        characters[character_id] = require_text(character.get("displayName"), f"taskMatrix.characters.{character_id}.displayName")
    require_exact(list(characters), EXPECTED_CHARACTER_ORDER, "taskMatrix character order")

    intros = require_object(matrix.get("requiredVoicedIntroductions"), "taskMatrix.requiredVoicedIntroductions")
    require_exact(intros.get("eventId"), EXPECTED_INTRO_EVENT_ID, "taskMatrix intro eventId")
    require_exact(intros.get("audioMode"), "character-speech", "taskMatrix intro audioMode")
    require_exact(intros.get("expectedTaskCount"), 8, "taskMatrix intro count")
    intro_targets = require_text_list(intros.get("targetAssetIds"), "taskMatrix intro targetAssetIds", allow_empty=False)
    derived_intro_targets = [
        target_id for target_id, master in required.items() if master.get("eventId") == EXPECTED_INTRO_EVENT_ID
    ]
    require_exact(intro_targets, derived_intro_targets, "taskMatrix voiced introduction targets")
    require_exact(len(intro_targets), 8, "derived voiced introduction count")

    require_exact(
        matrix.get("requiredCurrentEightMaster"),
        EXPECTED_CURRENT_EIGHT_TARGET,
        "taskMatrix required current-eight master",
    )
    current_eight = required.get(EXPECTED_CURRENT_EIGHT_TARGET)
    if current_eight is None:
        raise GateError("D1-A3B current-eight master is not in the requiresGeneration set")
    require_exact(current_eight.get("routingMode"), "current-eight", "D1-A3B routingMode")
    require_exact(current_eight.get("identityCast"), EXPECTED_CHARACTER_ORDER, "D1-A3B identityCast")
    require_text(matrix.get("claimBoundary"), "taskMatrix.claimBoundary")
    return required, characters, runtime_path, runtime_hash


def validate_manifest_constants(manifest: dict[str, Any], *, template: bool) -> None:
    require_exact(manifest.get("schemaVersion"), "cast-perspective-r5/provider-manifest-v2", "manifest.schemaVersion")
    require_bool(manifest.get("doNotSubmit"), "manifest.doNotSubmit")
    require_text(manifest.get("planId"), "manifest.planId", allow_placeholder=template)
    require_exact(manifest.get("taskMatrix"), "task-matrix.json", "manifest.taskMatrix")
    defaults = require_object(manifest.get("defaults"), "manifest.defaults")
    require_exact(defaults.get("doNotSubmit"), manifest.get("doNotSubmit"), "manifest.defaults.doNotSubmit")
    require_exact(defaults.get("ratio"), EXPECTED_RATIO, "manifest.defaults.ratio")
    require_exact(defaults.get("duration"), EXPECTED_DURATION, "manifest.defaults.duration")
    require_exact(defaults.get("resolution"), EXPECTED_RESOLUTION, "manifest.defaults.resolution")
    require_exact(defaults.get("generate_audio"), EXPECTED_GENERATE_AUDIO, "manifest.defaults.generate_audio")
    require_exact(defaults.get("watermark"), EXPECTED_WATERMARK, "manifest.defaults.watermark")
    policy = require_object(manifest.get("policy"), "manifest.policy")
    require_exact(policy.get("provider"), EXPECTED_PROVIDER, "manifest.policy.provider")
    require_exact(policy.get("model"), EXPECTED_MODEL, "manifest.policy.model")
    require_exact(policy.get("expectedTaskCount"), EXPECTED_TASK_COUNT, "manifest.policy.expectedTaskCount")
    require_exact(policy.get("concurrency"), EXPECTED_CONCURRENCY, "manifest.policy.concurrency")
    require_exact(policy.get("maxApiRetry"), EXPECTED_MAX_API_RETRY, "manifest.policy.maxApiRetry")


def validate_approval_constants(approval: dict[str, Any], *, template: bool) -> None:
    require_exact_keys(
        approval,
        {
            "schemaVersion",
            "batchId",
            "doNotSubmit",
            "manifestSha256",
            "taskMatrixSha256",
            "runtimeVariantMatrixSha256",
            "approvedTaskCount",
            "approvedTotalDurationSeconds",
            "policy",
            "pricing",
            "budget",
            "rights",
            "approval",
        },
        "approval",
    )
    require_exact(approval.get("schemaVersion"), "cast-perspective-r5/approval-v1", "approval.schemaVersion")
    require_text(approval.get("batchId"), "approval.batchId", allow_placeholder=template)
    require_bool(approval.get("doNotSubmit"), "approval.doNotSubmit")
    require_sha(approval.get("manifestSha256"), "approval.manifestSha256", allow_zero=template)
    require_sha(approval.get("taskMatrixSha256"), "approval.taskMatrixSha256", allow_zero=template)
    require_exact(
        require_sha(approval.get("runtimeVariantMatrixSha256"), "approval.runtimeVariantMatrixSha256"),
        EXPECTED_RUNTIME_MATRIX_SHA256,
        "approval.runtimeVariantMatrixSha256",
    )
    require_exact(approval.get("approvedTaskCount"), EXPECTED_TASK_COUNT, "approval.approvedTaskCount")
    require_exact(approval.get("approvedTotalDurationSeconds"), EXPECTED_TOTAL_DURATION_SECONDS, "approval.approvedTotalDurationSeconds")
    policy = require_object(approval.get("policy"), "approval.policy")
    require_exact_keys(
        policy,
        {
            "provider",
            "model",
            "ratio",
            "durationSeconds",
            "resolution",
            "generateAudio",
            "watermark",
            "concurrency",
            "maxApiRetry",
        },
        "approval.policy",
    )
    expected = {
        "provider": EXPECTED_PROVIDER,
        "model": EXPECTED_MODEL,
        "ratio": EXPECTED_RATIO,
        "durationSeconds": EXPECTED_DURATION,
        "resolution": EXPECTED_RESOLUTION,
        "generateAudio": EXPECTED_GENERATE_AUDIO,
        "watermark": EXPECTED_WATERMARK,
        "concurrency": EXPECTED_CONCURRENCY,
        "maxApiRetry": EXPECTED_MAX_API_RETRY,
    }
    for key, value in expected.items():
        require_exact(policy.get(key), value, f"approval.policy.{key}")


def validate_shot(
    shot: dict[str, Any],
    semantic: dict[str, Any],
    index: int,
    manifest_path: Path,
    defaults: dict[str, Any],
    characters: dict[str, str],
    global_rights: dict[str, set[str]],
) -> tuple[str, int, str]:
    label = f"manifest.shots[{index}]"
    merged = {**defaults, **shot}
    target_id = require_text(shot.get("semanticTargetAssetId"), f"{label}.semanticTargetAssetId")
    require_exact(shot.get("targetAssetId"), target_id, f"{label}.targetAssetId")
    require_exact(shot.get("targetRuntimeAssetId"), target_id, f"{label}.targetRuntimeAssetId")
    role = require_text(shot.get("providerJobRole"), f"{label}.providerJobRole")
    actual_identity_cast = require_text_list(shot.get("identityCast"), f"{label}.identityCast", allow_empty=False)
    require_exact(shot.get("semanticIdentityCast"), semantic.get("identityCast"), f"{label}.semanticIdentityCast")
    if role == "direct-semantic-master-candidate":
        if semantic.get("routingMode") == "current-eight":
            raise GateError(f"{label} cannot submit a direct current-eight provider job")
        require_exact(actual_identity_cast, semantic.get("identityCast"), f"{label}.identityCast")
        require_exact(shot.get("atomCharacterId"), None, f"{label}.atomCharacterId")
        expected_shot_id = f"{target_id}--r5"
        expected_kind = "self-introduction" if semantic.get("eventId") == EXPECTED_INTRO_EVENT_ID else "runtime-variant"
    elif role == "single-identity-current-eight-atom":
        if semantic.get("routingMode") != "current-eight" or target_id == EXPECTED_CURRENT_EIGHT_TARGET:
            raise GateError(f"{label} atom role is not legal for {target_id}")
        atom_id = require_text(shot.get("atomCharacterId"), f"{label}.atomCharacterId")
        if atom_id not in EXPECTED_CHARACTER_ORDER:
            raise GateError(f"{label}.atomCharacterId is not in the fixed cast")
        require_exact(actual_identity_cast, [atom_id], f"{label}.identityCast")
        expected_shot_id = f"{target_id}--atom-{atom_id}--r5"
        expected_kind = "current-eight-atom"
    else:
        raise GateError(f"{label}.providerJobRole is unsupported: {role!r}")
    shot_id = require_text(shot.get("id"), f"{label}.id")
    require_exact(shot_id, expected_shot_id, f"{label}.id semantic naming")
    for field in [item for item in SEMANTIC_FIELDS if item != "identityCast"]:
        if field not in shot:
            raise GateError(f"{label} is missing semantic field {field}")
        require_exact(shot.get(field), semantic.get(field), f"{label}.{field}")

    kind = require_text(shot.get("kind"), f"{label}.kind")
    require_exact(kind, expected_kind, f"{label}.kind")
    require_exact(merged.get("doNotSubmit"), defaults.get("doNotSubmit"), f"{label}.doNotSubmit")
    require_exact(merged.get("ratio"), EXPECTED_RATIO, f"{label}.ratio")
    require_exact(merged.get("duration"), EXPECTED_DURATION, f"{label}.duration")
    require_exact(merged.get("resolution"), EXPECTED_RESOLUTION, f"{label}.resolution")
    require_exact(merged.get("generate_audio"), EXPECTED_GENERATE_AUDIO, f"{label}.generate_audio")
    require_exact(merged.get("watermark"), EXPECTED_WATERMARK, f"{label}.watermark")
    require_exact(shot.get("generationModel"), EXPECTED_MODEL, f"{label}.generationModel")

    prompt_path = resolve_relative_file(manifest_path, shot.get("prompt_file"), f"{label}.prompt_file")
    expected_prompt_hash = require_sha(shot.get("promptSha256"), f"{label}.promptSha256")
    actual_prompt_hash = file_sha256(prompt_path)
    require_exact(actual_prompt_hash, expected_prompt_hash, f"{label}.promptSha256")
    prompt = prompt_path.read_text(encoding="utf-8")

    identity_cast = actual_identity_cast
    for character_id in actual_identity_cast:
        display_name = characters.get(character_id)
        if display_name is None:
            raise GateError(f"{label}.identityCast contains unknown id {character_id!r}")
        if display_name not in prompt:
            raise GateError(f"{label} prompt must explicitly anchor {character_id} using name {display_name!r}")
    if kind == "self-introduction":
        perspective = semantic.get("perspectiveCharacterId")
        require_exact(actual_identity_cast, [perspective], f"{label}.identityCast for introduction")

    image_path = resolve_relative_file(manifest_path, shot.get("reference_image"), f"{label}.reference_image")
    expected_image_hash = require_sha(shot.get("referenceImageSha256"), f"{label}.referenceImageSha256")
    require_exact(file_sha256(image_path), expected_image_hash, f"{label}.referenceImageSha256")
    expected_image_role = "single-identity-anchor" if len(identity_cast) == 1 else "composite-identity-board"
    require_exact(shot.get("referenceImageRole"), expected_image_role, f"{label}.referenceImageRole")

    if "reference_video_url" in shot:
        raise GateError(f"{label}.reference_video_url is forbidden; use a local hashed reference_video")
    has_reference_video = "reference_video" in shot
    if has_reference_video:
        video_path = resolve_relative_file(manifest_path, shot.get("reference_video"), f"{label}.reference_video")
        expected_video_hash = require_sha(shot.get("referenceVideoSha256"), f"{label}.referenceVideoSha256")
        require_exact(file_sha256(video_path), expected_video_hash, f"{label}.referenceVideoSha256")
        require_exact(shot.get("referenceVideoRole"), "motion-only", f"{label}.referenceVideoRole")

    planning_only = defaults.get("doNotSubmit") is True
    rights_status = require_text(shot.get("rightsStatus"), f"{label}.rightsStatus")
    rights_refs = require_ref_ids(shot.get("rightsRefIds"), f"{label}.rightsRefIds", allow_empty=planning_only)
    likeness_refs = require_ref_ids(shot.get("likenessConsentRefIds"), f"{label}.likenessConsentRefIds", allow_empty=planning_only)
    if planning_only:
        require_exact(rights_status, "pending", f"{label}.rightsStatus")
        if rights_refs or likeness_refs:
            raise GateError(f"{label} planning manifest must not invent rights or likeness consent refs")
    else:
        require_exact(rights_status, "approved", f"{label}.rightsStatus")
        if not likeness_refs <= global_rights["likeness"]:
            raise GateError(f"{label}.likenessConsentRefIds are not covered by batch approval")
    audio_mode = require_text(shot.get("audioMode"), f"{label}.audioMode")
    if audio_mode not in {"character-speech", "ambient-only"}:
        raise GateError(f"{label}.audioMode must be character-speech or ambient-only")
    voice_refs = require_ref_ids(
        shot.get("voiceConsentRefIds"),
        f"{label}.voiceConsentRefIds",
        allow_empty=planning_only or audio_mode == "ambient-only",
    )
    if planning_only and voice_refs:
        raise GateError(f"{label} planning manifest must not invent voice consent refs")
    if not planning_only and audio_mode == "character-speech" and not voice_refs <= global_rights["voice"]:
        raise GateError(f"{label}.voiceConsentRefIds are not covered by batch approval")
    if audio_mode == "ambient-only" and voice_refs:
        raise GateError(f"{label}.voiceConsentRefIds must be empty for ambient-only audio")
    if kind == "self-introduction" and audio_mode != "character-speech":
        raise GateError(f"{label} self-introduction must contain approved character speech")
    if kind == "current-eight-atom" and audio_mode != "ambient-only":
        raise GateError(f"{label} current-eight atom must use ambient-only audio")
    if has_reference_video:
        motion_refs = require_ref_ids(shot.get("referenceVideoRightsRefIds"), f"{label}.referenceVideoRightsRefIds")
        if not motion_refs <= global_rights["referenceVideo"]:
            raise GateError(f"{label}.referenceVideoRightsRefIds are not covered by batch approval")

    require_text(shot.get("stateIn"), f"{label}.stateIn")
    require_text(shot.get("stateOut"), f"{label}.stateOut")
    require_text(shot.get("identityNotes"), f"{label}.identityNotes")
    output_name = require_text(shot.get("output_name"), f"{label}.output_name")
    require_exact(output_name, f"{shot_id}-candidate.mp4", f"{label}.output_name semantic naming")
    return shot_id, EXPECTED_DURATION, target_id


def validate_production(
    manifest_path: Path,
    approval_path: Path,
    matrix_path: Path,
    *,
    require_executable: bool,
) -> None:
    manifest = require_object(load_json(manifest_path), "manifest")
    approval = require_object(load_json(approval_path), "approval")
    matrix = require_object(load_json(matrix_path), "task matrix")
    validate_manifest_constants(manifest, template=False)
    validate_approval_constants(approval, template=False)
    expected_jobs, characters, _runtime_path, runtime_hash = validate_task_matrix(matrix, matrix_path)

    require_exact(approval.get("batchId"), manifest.get("planId"), "approval.batchId")
    require_exact(approval.get("manifestSha256"), file_sha256(manifest_path), "approval.manifestSha256")
    require_exact(approval.get("taskMatrixSha256"), file_sha256(matrix_path), "approval.taskMatrixSha256")
    require_exact(approval.get("runtimeVariantMatrixSha256"), runtime_hash, "approval.runtimeVariantMatrixSha256")

    pricing = require_object(approval.get("pricing"), "approval.pricing")
    require_exact_keys(pricing, {"currency", "unitPriceAmount", "unitPriceBasis", "pricingEvidenceRef", "verifiedBy", "verifiedAt"}, "approval.pricing")
    currency = require_text(pricing.get("currency"), "approval.pricing.currency")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise GateError("approval.pricing.currency must be a three-letter uppercase currency code")
    unit_price = require_decimal(pricing.get("unitPriceAmount"), "approval.pricing.unitPriceAmount", positive=True)
    basis = require_text(pricing.get("unitPriceBasis"), "approval.pricing.unitPriceBasis")
    if basis not in {"per-task", "per-second"}:
        raise GateError("approval.pricing.unitPriceBasis must be per-task or per-second")
    require_text(pricing.get("pricingEvidenceRef"), "approval.pricing.pricingEvidenceRef")
    require_text(pricing.get("verifiedBy"), "approval.pricing.verifiedBy")
    require_timestamp(pricing.get("verifiedAt"), "approval.pricing.verifiedAt")

    rights = require_object(approval.get("rights"), "approval.rights")
    require_exact_keys(
        rights,
        {"status", "commercialUseApproved", "publicReleaseApproved", "likenessConsentRefIds", "voiceConsentRefIds", "referenceVideoRightsRefIds", "reviewedBy", "reviewedAt"},
        "approval.rights",
    )
    require_exact(rights.get("status"), "approved", "approval.rights.status")
    require_exact(rights.get("commercialUseApproved"), True, "approval.rights.commercialUseApproved")
    require_exact(rights.get("publicReleaseApproved"), True, "approval.rights.publicReleaseApproved")
    global_rights = {
        "likeness": require_ref_ids(rights.get("likenessConsentRefIds"), "approval.rights.likenessConsentRefIds"),
        "voice": require_ref_ids(rights.get("voiceConsentRefIds"), "approval.rights.voiceConsentRefIds"),
        "referenceVideo": require_ref_ids(rights.get("referenceVideoRightsRefIds"), "approval.rights.referenceVideoRightsRefIds", allow_empty=True),
    }
    require_text(rights.get("reviewedBy"), "approval.rights.reviewedBy")
    require_timestamp(rights.get("reviewedAt"), "approval.rights.reviewedAt")

    approval_block = require_object(approval.get("approval"), "approval.approval")
    require_exact_keys(approval_block, {"reviewedBy", "reviewedAt", "authorizedBy", "authorizedAt", "scopeRef"}, "approval.approval")
    require_text(approval_block.get("reviewedBy"), "approval.approval.reviewedBy")
    require_timestamp(approval_block.get("reviewedAt"), "approval.approval.reviewedAt")
    require_text(approval_block.get("authorizedBy"), "approval.approval.authorizedBy")
    require_timestamp(approval_block.get("authorizedAt"), "approval.approval.authorizedAt")
    require_text(approval_block.get("scopeRef"), "approval.approval.scopeRef")

    shots = require_list(manifest.get("shots"), "manifest.shots")
    require_exact(len(shots), EXPECTED_TASK_COUNT, "manifest.shots length")
    defaults = require_object(manifest.get("defaults"), "manifest.defaults")
    actual_jobs: set[str] = set()
    shot_ids: set[str] = set()
    total_duration = 0
    for index, raw in enumerate(shots):
        shot = require_object(raw, f"manifest.shots[{index}]")
        target_id = require_text(shot.get("targetAssetId"), f"manifest.shots[{index}].targetAssetId")
        semantic = expected_jobs.get(target_id)
        if semantic is None:
            raise GateError(f"manifest.shots[{index}] targetAssetId is not a requiresGeneration semantic master: {target_id}")
        job_key, duration, shot_id = validate_shot(
            shot, semantic, index, manifest_path, defaults, characters, global_rights
        )
        if job_key in actual_jobs:
            raise GateError(f"duplicate targetAssetId job: {job_key}")
        actual_jobs.add(job_key)
        if shot_id in shot_ids:
            raise GateError(f"duplicate shot id: {shot_id}")
        shot_ids.add(shot_id)
        total_duration += duration
    expected_ids = set(expected_jobs)
    if actual_jobs != expected_ids:
        missing = sorted(expected_ids - actual_jobs)[:10]
        extra = sorted(actual_jobs - expected_ids)[:10]
        raise GateError(f"semantic job matrix mismatch; missing={missing}, extra={extra}")
    require_exact(total_duration, EXPECTED_TOTAL_DURATION_SECONDS, "computed total duration")

    budget = require_object(approval.get("budget"), "approval.budget")
    require_exact_keys(
        budget,
        {"baseGenerationMaxAmount", "retryTaskCountCap", "retryGenerationMaxAmount", "hardTotalMaxAmount", "retryRequiresNewApproval", "budgetApprovalRef"},
        "approval.budget",
    )
    base_cap = require_decimal(budget.get("baseGenerationMaxAmount"), "approval.budget.baseGenerationMaxAmount", positive=True)
    retry_count = require_int(budget.get("retryTaskCountCap"), "approval.budget.retryTaskCountCap")
    if not 0 <= retry_count <= EXPECTED_TASK_COUNT:
        raise GateError(f"approval.budget.retryTaskCountCap must be between 0 and {EXPECTED_TASK_COUNT}")
    retry_cap = require_decimal(budget.get("retryGenerationMaxAmount"), "approval.budget.retryGenerationMaxAmount")
    hard_total = require_decimal(budget.get("hardTotalMaxAmount"), "approval.budget.hardTotalMaxAmount", positive=True)
    require_exact(budget.get("retryRequiresNewApproval"), True, "approval.budget.retryRequiresNewApproval")
    require_text(budget.get("budgetApprovalRef"), "approval.budget.budgetApprovalRef")
    cost_per_task = unit_price if basis == "per-task" else unit_price * Decimal(EXPECTED_DURATION)
    estimated_base = cost_per_task * Decimal(EXPECTED_TASK_COUNT)
    estimated_retry = cost_per_task * Decimal(retry_count)
    if base_cap < estimated_base:
        raise GateError(f"baseGenerationMaxAmount {base_cap} {currency} is below estimated base {estimated_base} {currency}")
    if retry_cap < estimated_retry:
        raise GateError(f"retryGenerationMaxAmount {retry_cap} {currency} is below retry reserve {estimated_retry} {currency}")
    if retry_count == 0 and retry_cap != 0:
        raise GateError("retryGenerationMaxAmount must be 0 when retryTaskCountCap is 0")
    if hard_total < base_cap + retry_cap:
        raise GateError("hardTotalMaxAmount must cover baseGenerationMaxAmount plus retryGenerationMaxAmount")

    manifest_blocked = require_bool(manifest.get("doNotSubmit"), "manifest.doNotSubmit")
    approval_blocked = require_bool(approval.get("doNotSubmit"), "approval.doNotSubmit")
    require_exact(manifest_blocked, approval_blocked, "approval.doNotSubmit")
    if require_executable and manifest_blocked:
        raise GateError("paid execution is blocked: both reviewed files must explicitly set doNotSubmit=false")

    print(f"R5 GATE VALID: semanticGap={len(shots)}, duration={total_duration}s, runtimeMatrix={runtime_hash}")
    print(f"model={EXPECTED_MODEL}, spec={EXPECTED_RATIO}/{EXPECTED_DURATION}s/{EXPECTED_RESOLUTION}/audio=true/watermark=false, concurrency=2, apiRetry=0")
    print(f"estimatedBase={estimated_base} {currency}, baseCap={base_cap} {currency}, retryCap={retry_cap} {currency}, hardCap={hard_total} {currency}")
    if manifest_blocked:
        print("SUBMISSION BLOCKED: doNotSubmit=true. Validation made no network request.")
    else:
        print("EXECUTABLE APPROVAL VALIDATED. This validator still made no network request.")


def validate_templates(manifest_path: Path, approval_path: Path, matrix_path: Path, schema_path: Path) -> None:
    manifest = require_object(load_json(manifest_path), "manifest template")
    approval = require_object(load_json(approval_path), "approval template")
    matrix = require_object(load_json(matrix_path), "task matrix")
    schema = require_object(load_json(schema_path), "approval schema")
    validate_manifest_constants(manifest, template=True)
    validate_approval_constants(approval, template=True)
    expected_jobs, _characters, _runtime_path, runtime_hash = validate_task_matrix(matrix, matrix_path)
    require_exact(len(expected_jobs), EXPECTED_SEMANTIC_GAP, "derived template semantic-gap count")
    require_exact(approval.get("runtimeVariantMatrixSha256"), runtime_hash, "approval template runtime matrix hash")
    require_exact(manifest.get("doNotSubmit"), True, "manifest template doNotSubmit")
    require_exact(manifest.get("defaults", {}).get("doNotSubmit"), True, "manifest template defaults.doNotSubmit")
    require_exact(approval.get("doNotSubmit"), True, "approval template doNotSubmit")
    require_exact(len(require_list(manifest.get("shots"), "manifest template shots")), 0, "manifest template shots length")
    require_exact(schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema", "approval schema draft")
    missing = set(require_list(schema.get("required"), "approval schema required")) - set(approval)
    if missing:
        raise GateError(f"approval template is missing schema-required fields: {sorted(missing)}")
    print("R5 TEMPLATE CHECK VALID: runtime matrix 188 total / 10 reusable / 178 requiresGeneration.")
    print("Production contract: 198 provider jobs / 2970s plus 4 local current-eight composites; D1-A3B reuses the 8 voiced introductions.")
    print("SUBMISSION BLOCKED: templates contain placeholders and doNotSubmit=true. No network request was made.")


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=here / "manifest.template.json")
    parser.add_argument("--approval", type=Path, default=here / "batch-approval.template.json")
    parser.add_argument("--matrix", type=Path, default=here / "task-matrix.json")
    parser.add_argument("--schema", type=Path, default=here / "batch-approval.schema.json")
    parser.add_argument("--template-check", action="store_true", help="Check the intentionally blocked templates and bound runtime matrix")
    parser.add_argument("--require-executable-approval", action="store_true", help="Also require both doNotSubmit flags to be false")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    approval_path = args.approval.expanduser().resolve()
    matrix_path = args.matrix.expanduser().resolve()
    schema_path = args.schema.expanduser().resolve()
    if args.template_check:
        validate_templates(manifest_path, approval_path, matrix_path, schema_path)
    else:
        validate_production(
            manifest_path,
            approval_path,
            matrix_path,
            require_executable=args.require_executable_approval,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as error:
        print(f"R5 GATE BLOCKED: {error}", file=sys.stderr)
        print("No network request was made.", file=sys.stderr)
        raise SystemExit(3)
