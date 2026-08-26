#!/usr/bin/env python3
"""Run the approved R6 Seedance plan through a fail-closed budget gate.

The default mode is a local dry run. Network access is possible only with
``--run``. The immutable planning manifest must keep ``doNotSubmit=true``;
this runner derives disposable, at-most-two-shot execution manifests below
the project-local ``.work-candidates`` directory.

Secrets are read only in ``--run`` mode from ``FUMIN_API_KEY``. They are never
written to a manifest, status summary, or budget ledger. Failed or unsettled
shots are never submitted again automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
CANONICAL_MANIFEST = HERE / "manifest.r6.json"
GATE = HERE / "validate_batch_gate.py"
WORK_ROOT = HERE / ".work-candidates"
ADAPTER = (
    Path.home()
    / ".codex/skills/heart-journey-game-factory/scripts/adapters"
    / "fumin-seedance2/seedance_fumin_batch.py"
)

EXPECTED_MODEL = "seedance-2.0-mini"
HARD_CAP_CNY = Decimal("60")
QUOTA_PER_UNIT = Decimal("500000")
PRICE_CNY_PER_UNIT = Decimal("0.4")
WAVE_SIZE = 2


class GuardError(RuntimeError):
    """A condition that must stop the paid runner."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise GuardError(f"{label} not found: {path}") from error
    except json.JSONDecodeError as error:
        raise GuardError(
            f"{label} is invalid JSON at line {error.lineno}, column {error.colno}"
        ) from error


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def decimal_from(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise GuardError(f"{label} must be numeric")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise GuardError(f"{label} must be numeric") from error
    if not result.is_finite():
        raise GuardError(f"{label} must be finite")
    return result


def money_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0000001")), "f")


def quota_cost(actual_quota: int) -> Decimal:
    return Decimal(actual_quota) / QUOTA_PER_UNIT * PRICE_CNY_PER_UNIT


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_output_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    root = WORK_ROOT.resolve()
    if resolved == root or not is_within(resolved, root):
        raise GuardError(
            f"--output-dir must be an explicit child of the project work root: {root}"
        )
    return resolved


def resolve_input(value: object, manifest_dir: Path, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise GuardError(f"{label} must be a non-empty path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = manifest_dir / path
    return path.resolve()


def run_gate(approval_path: Path) -> dict[str, Any]:
    if not GATE.is_file():
        raise GuardError(f"paid gate validator is missing: {GATE}")
    result = subprocess.run(
        [sys.executable, str(GATE), str(approval_path)],
        cwd=HERE,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "gate rejected approval").strip()
        raise GuardError(detail[:1200])
    try:
        verdict = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise GuardError("paid gate returned an unreadable verdict") from error
    if verdict.get("verdict") != "R6_PAID_GATE_PASS":
        raise GuardError("paid gate did not return R6_PAID_GATE_PASS")
    return verdict


def validate_authority(
    manifest_path: Path, approval_path: Path
) -> tuple[dict[str, Any], dict[str, Any], str, str, Decimal, Decimal]:
    manifest_path = manifest_path.expanduser().resolve()
    approval_path = approval_path.expanduser().resolve()
    if manifest_path != CANONICAL_MANIFEST.resolve():
        raise GuardError(
            f"runner accepts only the canonical R6 planning manifest: {CANONICAL_MANIFEST}"
        )
    manifest = load_json(manifest_path, "planning manifest")
    approval = load_json(approval_path, "approval")
    if not isinstance(manifest, dict) or not isinstance(approval, dict):
        raise GuardError("planning manifest and approval must be JSON objects")
    if manifest.get("doNotSubmit") is not True:
        raise GuardError("planning manifest must remain doNotSubmit=true")
    run_gate(approval_path)

    hard_cap = decimal_from(
        approval.get("budget", {}).get("hardTotalMaxAmountCny"),
        "approval.budget.hardTotalMaxAmountCny",
    )
    if hard_cap != HARD_CAP_CNY:
        raise GuardError("R6 hard cap must remain exactly CNY 60")
    unit_rate = decimal_from(
        approval.get("pricing", {}).get("unitPriceCnyPerSecond"),
        "approval.pricing.unitPriceCnyPerSecond",
    )
    if unit_rate <= 0:
        raise GuardError("approved conservative unit rate must be positive")

    manifest_sha = file_sha256(manifest_path)
    approval_sha = file_sha256(approval_path)
    if approval.get("manifestSha256") != manifest_sha:
        raise GuardError("approval no longer binds the current planning manifest")
    return manifest, approval, manifest_sha, approval_sha, hard_cap, unit_rate


def selected_shots(
    manifest: dict[str, Any], start_index: int, max_shots: int | None
) -> list[tuple[int, dict[str, Any]]]:
    raw_shots = manifest.get("shots")
    if not isinstance(raw_shots, list):
        raise GuardError("planning manifest shots must be an array")
    if start_index < 1:
        raise GuardError("--start-index is one-based and must be at least 1")
    if max_shots is not None and max_shots < 1:
        raise GuardError("--max-shots must be at least 1")
    start = start_index - 1
    stop = None if max_shots is None else start + max_shots
    result: list[tuple[int, dict[str, Any]]] = []
    for offset, shot in enumerate(raw_shots[start:stop], start=start_index):
        if not isinstance(shot, dict):
            raise GuardError(f"planning shot {offset} must be an object")
        result.append((offset, shot))
    return result


def wave_chunks(
    shots: list[tuple[int, dict[str, Any]]]
) -> Iterable[list[tuple[int, dict[str, Any]]]]:
    for index in range(0, len(shots), WAVE_SIZE):
        yield shots[index : index + WAVE_SIZE]


def validate_shot_policy(
    shot: dict[str, Any], index: int, manifest_dir: Path
) -> tuple[Path, Path]:
    shot_id = shot.get("id")
    if not isinstance(shot_id, str) or not shot_id.strip():
        raise GuardError(f"shot {index} has no stable id")
    if shot.get("resolution") != "480p":
        raise GuardError(f"shot {shot_id} must remain 480p")
    if shot.get("ratio") != "9:16":
        raise GuardError(f"shot {shot_id} must remain 9:16")
    duration = shot.get("duration")
    if isinstance(duration, bool) or not isinstance(duration, int) or not 4 <= duration <= 15:
        raise GuardError(f"shot {shot_id} duration must be 4-15 seconds")
    expected_audio = shot.get("kind") != "dynamic-portrait-candidate"
    if shot.get("generate_audio") is not expected_audio:
        raise GuardError(
            f"shot {shot_id} generate_audio must remain {expected_audio!r} for its planned kind"
        )
    if shot.get("watermark") is not False:
        raise GuardError(f"shot {shot_id} must keep watermark=false")

    prompt = resolve_input(shot.get("prompt_file"), manifest_dir, f"shot {shot_id} prompt")
    reference = resolve_input(
        shot.get("reference_image"), manifest_dir, f"shot {shot_id} reference image"
    )
    if not prompt.is_file():
        raise GuardError(f"shot {shot_id} prompt is missing: {prompt}")
    if not reference.is_file():
        raise GuardError(f"shot {shot_id} reference is missing: {reference}")
    if shot.get("promptSha256") != file_sha256(prompt):
        raise GuardError(f"shot {shot_id} prompt hash no longer matches the plan")
    return prompt, reference


def build_execution_manifest(
    wave: list[tuple[int, dict[str, Any]]],
    *,
    manifest_dir: Path,
    manifest_sha: str,
    approval_sha: str,
    wave_id: str,
) -> dict[str, Any]:
    execution_shots: list[dict[str, Any]] = []
    for index, shot in wave:
        prompt, reference = validate_shot_policy(shot, index, manifest_dir)
        item: dict[str, Any] = {
            "id": shot["id"],
            "prompt_file": str(prompt),
            "reference_image": str(reference),
            "ratio": "9:16",
            "resolution": "480p",
            "duration": shot["duration"],
            "generate_audio": bool(shot["generate_audio"]),
            "watermark": False,
            "output_name": shot["output_name"],
        }
        if shot.get("reference_video"):
            item["reference_video"] = str(
                resolve_input(
                    shot["reference_video"],
                    manifest_dir,
                    f"shot {shot['id']} reference video",
                )
            )
        if shot.get("reference_video_url"):
            item["reference_video_url"] = shot["reference_video_url"]
        execution_shots.append(item)
    return {
        "schemaVersion": "heart-journey/r6-ephemeral-execution-wave-v1",
        "doNotSubmit": False,
        "executionAuthority": {
            "planningManifestSha256": manifest_sha,
            "approvalSha256": approval_sha,
            "waveId": wave_id,
            "maxConcurrency": WAVE_SIZE,
            "maxApiRetry": 0,
        },
        "shots": execution_shots,
    }


def run_adapter_validate(execution_manifest: Path) -> None:
    if not ADAPTER.is_file():
        raise GuardError(f"approved Seedance batch adapter is missing: {ADAPTER}")
    result = subprocess.run(
        [sys.executable, str(ADAPTER), str(execution_manifest), "--validate-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "adapter validation failed").strip()
        raise GuardError(detail[:1200])


def empty_ledger(
    *, manifest_sha: str, approval_sha: str, hard_cap: Decimal, unit_rate: Decimal
) -> dict[str, Any]:
    now = utc_now()
    return {
        "schemaVersion": "heart-journey/r6-sanitized-budget-ledger-v1",
        "containsCredentials": False,
        "planningManifestSha256": manifest_sha,
        "approvalSha256": approval_sha,
        "hardCapCny": money_text(hard_cap),
        "approvedConservativeRateCnyPerSecond": money_text(unit_rate),
        "quotaPerUnit": int(QUOTA_PER_UNIT),
        "priceCnyPerQuotaUnit": float(PRICE_CNY_PER_UNIT),
        "status": "active",
        "createdAt": now,
        "updatedAt": now,
        "settledActualQuota": 0,
        "settledCostCny": money_text(Decimal(0)),
        "conservativeRateCnyPerSecond": money_text(unit_rate),
        "waves": [],
        "shots": [],
        "stopReason": None,
    }


def verify_ledger(
    ledger: dict[str, Any],
    *,
    manifest_sha: str,
    approval_sha: str,
    hard_cap: Decimal,
    approved_rate: Decimal,
) -> None:
    if ledger.get("containsCredentials") is not False:
        raise GuardError("budget ledger credential boundary is invalid")
    if ledger.get("planningManifestSha256") != manifest_sha:
        raise GuardError("budget ledger belongs to a different planning manifest")
    if ledger.get("approvalSha256") != approval_sha:
        raise GuardError("budget ledger belongs to a different approval")
    if decimal_from(ledger.get("hardCapCny"), "ledger.hardCapCny") != hard_cap:
        raise GuardError("budget ledger hard cap differs from approval")
    if decimal_from(
        ledger.get("approvedConservativeRateCnyPerSecond"),
        "ledger.approvedConservativeRateCnyPerSecond",
    ) != approved_rate:
        raise GuardError("budget ledger approved rate differs from approval")
    waves = ledger.get("waves")
    shots = ledger.get("shots")
    if not isinstance(waves, list) or not isinstance(shots, list):
        raise GuardError("budget ledger waves and shots must be arrays")
    if any(wave.get("status") in {"submitting", "unsettled"} for wave in waves):
        raise GuardError(
            "budget ledger contains an unfinished wave; inspect and settle it manually before any new submission"
        )
    if ledger.get("status") == "blocked":
        raise GuardError(
            "budget ledger is blocked and requires manual review; this runner will not resume it automatically"
        )

    seen_shots: set[str] = set()
    seen_tasks: set[str] = set()
    quota_sum = 0
    for item in shots:
        if not isinstance(item, dict):
            raise GuardError("budget ledger shot entry is invalid")
        shot_id = str(item.get("shotId", ""))
        task_id = str(item.get("taskId", ""))
        if not shot_id or shot_id in seen_shots:
            raise GuardError("budget ledger contains a duplicate or empty shot id")
        if not task_id or task_id in seen_tasks:
            raise GuardError("budget ledger contains a duplicate or empty task id")
        seen_shots.add(shot_id)
        seen_tasks.add(task_id)
        quota = item.get("actualQuota")
        if isinstance(quota, bool) or not isinstance(quota, int) or quota < 0:
            raise GuardError("budget ledger actualQuota must be a non-negative integer")
        quota_sum += quota
        if decimal_from(item.get("actualCostCny"), "ledger shot cost") != quota_cost(quota):
            raise GuardError("budget ledger shot cost does not match actualQuota")
    if ledger.get("settledActualQuota") != quota_sum:
        raise GuardError("budget ledger settledActualQuota is inconsistent")
    if decimal_from(ledger.get("settledCostCny"), "ledger.settledCostCny") != quota_cost(
        quota_sum
    ):
        raise GuardError("budget ledger settledCostCny is inconsistent")


def load_or_create_ledger(
    path: Path,
    *,
    manifest_sha: str,
    approval_sha: str,
    hard_cap: Decimal,
    approved_rate: Decimal,
) -> dict[str, Any]:
    if path.exists():
        ledger = load_json(path, "budget ledger")
        if not isinstance(ledger, dict):
            raise GuardError("budget ledger must be a JSON object")
        verify_ledger(
            ledger,
            manifest_sha=manifest_sha,
            approval_sha=approval_sha,
            hard_cap=hard_cap,
            approved_rate=approved_rate,
        )
        ledger["status"] = "active"
        ledger["stopReason"] = None
        return ledger
    return empty_ledger(
        manifest_sha=manifest_sha,
        approval_sha=approval_sha,
        hard_cap=hard_cap,
        unit_rate=approved_rate,
    )


def attempted_shot_ids(ledger: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for wave in ledger.get("waves", []):
        values = wave.get("shotIds", [])
        if isinstance(values, list):
            result.update(str(value) for value in values)
    return result


def settled_cost(ledger: dict[str, Any]) -> Decimal:
    return quota_cost(int(ledger.get("settledActualQuota", 0)))


def conservative_rate(ledger: dict[str, Any], approved_rate: Decimal) -> Decimal:
    rate = approved_rate
    for item in ledger.get("shots", []):
        duration = item.get("durationSeconds")
        if isinstance(duration, int) and duration > 0:
            observed = quota_cost(item["actualQuota"]) / Decimal(duration)
            rate = max(rate, observed)
    return rate


def remaining_estimate(
    remaining: list[tuple[int, dict[str, Any]]], rate: Decimal
) -> Decimal:
    seconds = sum(int(shot["duration"]) for _, shot in remaining)
    return Decimal(seconds) * rate


def budget_projection(
    ledger: dict[str, Any],
    remaining: list[tuple[int, dict[str, Any]]],
    approved_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    actual = settled_cost(ledger)
    rate = conservative_rate(ledger, approved_rate)
    estimate = remaining_estimate(remaining, rate)
    return actual, rate, estimate, actual + estimate


def safe_process_text(value: str, api_key: str) -> str:
    text = value.replace(api_key, "<redacted-api-key>") if api_key else value
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}\b", "<redacted-api-key>", text)
    text = re.sub(
        r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,}\]]+",
        r"\1<redacted>",
        text,
    )
    return text[:10000]


def run_adapter(
    execution_manifest: Path,
    output_dir: Path,
    *,
    api_key: str,
    child_env: dict[str, str],
    poll_seconds: int,
    timeout_seconds: int,
) -> int:
    command = [
        sys.executable,
        str(ADAPTER),
        str(execution_manifest),
        "--output-dir",
        str(output_dir),
        "--concurrency",
        str(WAVE_SIZE),
        "--poll-seconds",
        str(poll_seconds),
        "--timeout-seconds",
        str(timeout_seconds),
    ]
    result = subprocess.run(
        command,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(safe_process_text(result.stdout, api_key).rstrip())
    if result.stderr:
        print(safe_process_text(result.stderr, api_key).rstrip(), file=sys.stderr)
    return result.returncode


def scalar_task_ids(value: Any, wanted: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for nested in value.values():
            found.update(scalar_task_ids(nested, wanted))
    elif isinstance(value, list):
        for nested in value:
            found.update(scalar_task_ids(nested, wanted))
    elif isinstance(value, int) and str(value) in wanted:
        found.add(str(value))
    elif isinstance(value, str):
        if value in wanted:
            found.add(value)
        else:
            # Some token-ledger entries serialize the task response or task URL
            # inside a string field. Match only the exact task-id substring and
            # never retain the surrounding provider payload.
            contained = {task_id for task_id in wanted if task_id in value}
            if len(contained) == 1:
                found.update(contained)
    return found


def quota_values(value: Any) -> list[object]:
    found: list[object] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"actual_quota", "actualQuota"}:
                found.append(nested)
            else:
                found.extend(quota_values(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(quota_values(nested))
    return found


def iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from iter_dicts(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_dicts(nested)


def integer_quota(value: object) -> int:
    if isinstance(value, bool):
        raise GuardError("settlement actual_quota is not an integer")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as error:
        raise GuardError("settlement actual_quota is not numeric") from error
    if not parsed.is_finite() or parsed < 0 or parsed != parsed.to_integral_value():
        raise GuardError("settlement actual_quota must be a non-negative integer")
    return int(parsed)


def extract_settlements(payload: Any, task_ids: set[str]) -> dict[str, int]:
    """Extract only exact task-id/actual_quota pairs from a provider response."""

    matches: dict[str, int] = {}
    for record in iter_dicts(payload):
        searchable: dict[str, Any] = record
        # Fumin's token ledger keeps settlement details as a JSON string in
        # `other`. Parse only in memory; never persist the raw account record.
        raw_other = record.get("other")
        if isinstance(raw_other, str):
            try:
                parsed_other = json.loads(raw_other)
            except json.JSONDecodeError:
                parsed_other = None
            if isinstance(parsed_other, dict):
                searchable = {**record, "_parsed_other": parsed_other}
        ids = scalar_task_ids(searchable, task_ids)
        if len(ids) != 1:
            continue
        quotas = quota_values(searchable)
        if len(quotas) != 1:
            continue
        task_id = next(iter(ids))
        quota = integer_quota(quotas[0])
        previous = matches.get(task_id)
        if previous is not None and previous != quota:
            raise GuardError(f"conflicting actual_quota settlements for task {task_id}")
        matches[task_id] = quota
    return matches


def fetch_settlements(base_url: str, api_key: str, task_ids: set[str]) -> dict[str, int]:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise GuardError("FUMIN_BASE_URL must be an http(s) origin")
    if parsed.username or parsed.password:
        raise GuardError("FUMIN_BASE_URL must not contain credentials")
    url = f"{base_url.rstrip('/')}/api/log/token"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raise GuardError(f"settlement query failed with HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise GuardError("settlement query failed; no new wave may start") from error
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as error:
        raise GuardError("settlement query returned invalid JSON") from error
    matches = extract_settlements(payload, task_ids)
    missing = sorted(task_ids - matches.keys())
    if missing:
        raise GuardError(
            "settlement actual_quota is unavailable for task(s): " + ", ".join(missing)
        )
    return matches


def status_records(
    status_path: Path, wave: list[tuple[int, dict[str, Any]]]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    status = load_json(status_path, "wave batch status")
    records = status.get("shots") if isinstance(status, dict) else None
    if not isinstance(records, dict):
        raise GuardError("wave batch status has no shots object")
    result: dict[str, dict[str, Any]] = {}
    no_task: list[str] = []
    for _, shot in wave:
        shot_id = str(shot["id"])
        record = records.get(shot_id)
        if not isinstance(record, dict):
            raise GuardError(f"wave batch status is missing shot {shot_id}")
        result[shot_id] = record
        if not record.get("task_id"):
            no_task.append(shot_id)
    return result, no_task


def recompute_ledger_totals(ledger: dict[str, Any], approved_rate: Decimal) -> None:
    total_quota = sum(int(item["actualQuota"]) for item in ledger["shots"])
    ledger["settledActualQuota"] = total_quota
    ledger["settledCostCny"] = money_text(quota_cost(total_quota))
    ledger["conservativeRateCnyPerSecond"] = money_text(
        conservative_rate(ledger, approved_rate)
    )
    ledger["updatedAt"] = utc_now()


def fail_and_write(ledger_path: Path, ledger: dict[str, Any], reason: str) -> None:
    ledger["status"] = "blocked"
    ledger["stopReason"] = reason
    ledger["updatedAt"] = utc_now()
    atomic_write_json(ledger_path, ledger)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("planning_manifest", type=Path)
    parser.add_argument("approval", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Explicit child directory below gender-rotation-r6/.work-candidates",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true", help="Permit guarded network submission")
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="Explicit local-only mode (also the default)",
    )
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--max-shots", type=int)
    parser.add_argument("--poll-seconds", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    return parser.parse_args()


def dry_run(
    *,
    shots: list[tuple[int, dict[str, Any]]],
    output_dir: Path,
    manifest_sha: str,
    approval_sha: str,
    hard_cap: Decimal,
    approved_rate: Decimal,
    manifest_dir: Path,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "budget-ledger.json"
    if ledger_path.exists():
        ledger = load_json(ledger_path, "budget ledger")
        if not isinstance(ledger, dict):
            raise GuardError("budget ledger must be a JSON object")
        verify_ledger(
            ledger,
            manifest_sha=manifest_sha,
            approval_sha=approval_sha,
            hard_cap=hard_cap,
            approved_rate=approved_rate,
        )
    else:
        ledger = empty_ledger(
            manifest_sha=manifest_sha,
            approval_sha=approval_sha,
            hard_cap=hard_cap,
            unit_rate=approved_rate,
        )
    duplicated = attempted_shot_ids(ledger) & {str(shot["id"]) for _, shot in shots}
    if duplicated:
        raise GuardError(
            "selected shots were already attempted and will not be retried: "
            + ", ".join(sorted(duplicated))
        )
    actual, rate, estimate, projected = budget_projection(ledger, shots, approved_rate)
    if projected > hard_cap:
        raise GuardError(
            f"budget projection CNY {money_text(projected)} exceeds hard cap CNY {money_text(hard_cap)}"
        )
    with tempfile.TemporaryDirectory(prefix=".validate-", dir=output_dir) as temporary:
        temp_root = Path(temporary)
        for wave in wave_chunks(shots):
            wave_id = f"wave-{wave[0][0]:03d}-{wave[-1][0]:03d}"
            execution = build_execution_manifest(
                wave,
                manifest_dir=manifest_dir,
                manifest_sha=manifest_sha,
                approval_sha=approval_sha,
                wave_id=wave_id,
            )
            path = temp_root / f"{wave_id}.json"
            atomic_write_json(path, execution)
            run_adapter_validate(path)
    print(
        json.dumps(
            {
                "verdict": "R6_GUARDED_DRY_RUN_PASS",
                "networkRequests": 0,
                "selectedShots": len(shots),
                "waves": (len(shots) + WAVE_SIZE - 1) // WAVE_SIZE,
                "settledCostCny": money_text(actual),
                "conservativeRateCnyPerSecond": money_text(rate),
                "remainingEstimateCny": money_text(estimate),
                "projectedCny": money_text(projected),
                "hardCapCny": money_text(hard_cap),
            },
            ensure_ascii=False,
        )
    )
    return 0


def paid_run(
    *,
    args: argparse.Namespace,
    shots: list[tuple[int, dict[str, Any]]],
    output_dir: Path,
    manifest_sha: str,
    approval_sha: str,
    hard_cap: Decimal,
    approved_rate: Decimal,
    manifest_dir: Path,
) -> int:
    # Secrets are consulted only after every local gate and dry validation has passed.
    api_key = os.environ.get("FUMIN_API_KEY", "")
    model = os.environ.get("FUMIN_MODEL", "")
    if not api_key:
        raise GuardError("FUMIN_API_KEY is required for --run; no request was made")
    if model != EXPECTED_MODEL:
        raise GuardError(
            f"FUMIN_MODEL must equal {EXPECTED_MODEL!r}; no request was made"
        )
    base_url = os.environ.get("FUMIN_BASE_URL", "https://fumin.ai").rstrip("/")
    parsed_base = urllib.parse.urlparse(base_url)
    if (
        parsed_base.scheme not in {"http", "https"}
        or not parsed_base.netloc
        or parsed_base.username
        or parsed_base.password
    ):
        raise GuardError("FUMIN_BASE_URL must be a credential-free http(s) origin")

    child_env = dict(os.environ)
    child_env["FUMIN_MODEL"] = EXPECTED_MODEL
    # The shared-image override would defeat per-shot identity references.
    child_env.pop("FUMIN_IMAGE_URL", None)

    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "budget-ledger.json"
    ledger = load_or_create_ledger(
        ledger_path,
        manifest_sha=manifest_sha,
        approval_sha=approval_sha,
        hard_cap=hard_cap,
        approved_rate=approved_rate,
    )
    duplicated = attempted_shot_ids(ledger) & {str(shot["id"]) for _, shot in shots}
    if duplicated:
        raise GuardError(
            "selected shots were already attempted and will not be retried: "
            + ", ".join(sorted(duplicated))
        )
    atomic_write_json(ledger_path, ledger)

    pending = list(shots)
    while pending:
        # Re-run the separate approval gate and detect any mid-run file mutation.
        run_gate(args.approval.expanduser().resolve())
        if file_sha256(args.planning_manifest.expanduser().resolve()) != manifest_sha:
            reason = "planning manifest changed after authorization"
            fail_and_write(ledger_path, ledger, reason)
            raise GuardError(reason)
        if file_sha256(args.approval.expanduser().resolve()) != approval_sha:
            reason = "approval changed after the run started"
            fail_and_write(ledger_path, ledger, reason)
            raise GuardError(reason)

        actual, rate, estimate, projected = budget_projection(
            ledger, pending, approved_rate
        )
        if projected > hard_cap:
            reason = (
                f"pre-wave projection CNY {money_text(projected)} exceeds hard cap "
                f"CNY {money_text(hard_cap)}"
            )
            fail_and_write(ledger_path, ledger, reason)
            raise GuardError(reason)
        print(
            "budget pre-wave: "
            f"settled={money_text(actual)} remaining={money_text(estimate)} "
            f"projected={money_text(projected)} cap={money_text(hard_cap)}"
        )

        wave = pending[:WAVE_SIZE]
        wave_id = f"wave-{wave[0][0]:03d}-{wave[-1][0]:03d}"
        wave_dir = output_dir / wave_id
        if wave_dir.exists():
            reason = f"wave directory already exists; refusing duplicate submission: {wave_dir}"
            fail_and_write(ledger_path, ledger, reason)
            raise GuardError(reason)
        wave_dir.mkdir(parents=True)
        execution_path = wave_dir / "execution-manifest.json"
        execution = build_execution_manifest(
            wave,
            manifest_dir=manifest_dir,
            manifest_sha=manifest_sha,
            approval_sha=approval_sha,
            wave_id=wave_id,
        )
        atomic_write_json(execution_path, execution)
        run_adapter_validate(execution_path)

        wave_record: dict[str, Any] = {
            "waveId": wave_id,
            "status": "submitting",
            "shotIndices": [index for index, _ in wave],
            "shotIds": [str(shot["id"]) for _, shot in wave],
            "executionManifest": str(execution_path.relative_to(output_dir)),
            "batchStatus": str(
                (wave_dir / "candidates/batch-status.json").relative_to(output_dir)
            ),
            "startedAt": utc_now(),
            "settledAt": None,
            "actualQuota": None,
            "actualCostCny": None,
            "noTaskShotIds": [],
        }
        ledger["waves"].append(wave_record)
        ledger["updatedAt"] = utc_now()
        atomic_write_json(ledger_path, ledger)

        candidates_dir = wave_dir / "candidates"
        adapter_code = run_adapter(
            execution_path,
            candidates_dir,
            api_key=api_key,
            child_env=child_env,
            poll_seconds=args.poll_seconds,
            timeout_seconds=args.timeout_seconds,
        )
        status_path = candidates_dir / "batch-status.json"
        try:
            records, no_task = status_records(status_path, wave)
            task_to_shot = {
                str(record["task_id"]): shot_id
                for shot_id, record in records.items()
                if record.get("task_id")
            }
            if task_to_shot:
                settlements = fetch_settlements(base_url, api_key, set(task_to_shot))
            else:
                settlements = {}
        except GuardError as error:
            wave_record["status"] = "unsettled"
            wave_record["settlementError"] = str(error)[:1200]
            fail_and_write(ledger_path, ledger, str(error))
            raise

        wave_quota = 0
        by_id = {str(shot["id"]): (index, shot) for index, shot in wave}
        for task_id, quota in settlements.items():
            shot_id = task_to_shot[task_id]
            index, shot = by_id[shot_id]
            record = records[shot_id]
            cost = quota_cost(quota)
            ledger["shots"].append(
                {
                    "shotIndex": index,
                    "shotId": shot_id,
                    "durationSeconds": int(shot["duration"]),
                    "taskId": task_id,
                    "providerStatus": str(record.get("status", "unknown")),
                    "actualQuota": quota,
                    "actualCostCny": money_text(cost),
                    "waveId": wave_id,
                    "settledAt": utc_now(),
                }
            )
            wave_quota += quota
        wave_record["actualQuota"] = wave_quota
        wave_record["actualCostCny"] = money_text(quota_cost(wave_quota))
        wave_record["settledAt"] = utc_now()
        wave_record["noTaskShotIds"] = no_task
        wave_record["status"] = "settled" if adapter_code == 0 and not no_task else "failed"
        recompute_ledger_totals(ledger, approved_rate)

        pending = pending[len(wave) :]
        actual, rate, estimate, projected = budget_projection(
            ledger, pending, approved_rate
        )
        wave_record["postWaveProjectionCny"] = money_text(projected)
        atomic_write_json(ledger_path, ledger)
        print(
            f"{wave_id} settled: actual_quota={wave_quota} "
            f"cost={money_text(quota_cost(wave_quota))}; "
            f"total={money_text(actual)}; projected={money_text(projected)}"
        )

        if adapter_code != 0 or no_task:
            reason = "wave failed; failed tasks are never retried automatically"
            fail_and_write(ledger_path, ledger, reason)
            raise GuardError(reason)
        if projected > hard_cap:
            reason = (
                f"post-wave settled spend plus remaining estimate CNY {money_text(projected)} "
                f"exceeds hard cap CNY {money_text(hard_cap)}"
            )
            fail_and_write(ledger_path, ledger, reason)
            raise GuardError(reason)

    ledger["status"] = "completed"
    ledger["stopReason"] = None
    ledger["updatedAt"] = utc_now()
    atomic_write_json(ledger_path, ledger)
    print(
        json.dumps(
            {
                "verdict": "R6_GUARDED_RUN_COMPLETE",
                "submittedShots": len(shots),
                "settledCostCny": ledger["settledCostCny"],
                "hardCapCny": ledger["hardCapCny"],
                "budgetLedger": str(ledger_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    args = parse_args()
    if args.poll_seconds < 2:
        raise GuardError("--poll-seconds must be at least 2")
    if args.timeout_seconds < 30:
        raise GuardError("--timeout-seconds must be at least 30")
    output_dir = validate_output_dir(args.output_dir)
    (
        manifest,
        _approval,
        manifest_sha,
        approval_sha,
        hard_cap,
        approved_rate,
    ) = validate_authority(args.planning_manifest, args.approval)
    shots = selected_shots(manifest, args.start_index, args.max_shots)
    if not shots:
        print(
            json.dumps(
                {
                    "verdict": "R6_GUARDED_NO_SHOTS",
                    "networkRequests": 0,
                    "startIndex": args.start_index,
                },
                ensure_ascii=False,
            )
        )
        return 0
    if len({str(shot["id"]) for _, shot in shots}) != len(shots):
        raise GuardError("selected planning shot ids must be unique")

    if not args.run:
        return dry_run(
            shots=shots,
            output_dir=output_dir,
            manifest_sha=manifest_sha,
            approval_sha=approval_sha,
            hard_cap=hard_cap,
            approved_rate=approved_rate,
            manifest_dir=args.planning_manifest.expanduser().resolve().parent,
        )
    return paid_run(
        args=args,
        shots=shots,
        output_dir=output_dir,
        manifest_sha=manifest_sha,
        approval_sha=approval_sha,
        hard_cap=hard_cap,
        approved_rate=approved_rate,
        manifest_dir=args.planning_manifest.expanduser().resolve().parent,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GuardError as error:
        print(f"R6_GUARDED_RUN_BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
