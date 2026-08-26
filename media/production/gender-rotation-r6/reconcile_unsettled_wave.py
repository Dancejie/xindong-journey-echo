#!/usr/bin/env python3
"""Recover an already-created R6 wave after a polling/settlement outage.

This command never creates a provider task. It only GETs the exact task IDs
already recorded in ``batch-status.json``, downloads succeeded outputs, settles
their exact quota, and unlocks the sanitized budget ledger after all checks
pass. It is intentionally narrow so a failed generation cannot be retried by
accident.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request


HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "run_approved_batch.py"
EXPECTED_MODEL = "seedance-2.0-mini"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runner = load_module("r6_guarded_runner", RUNNER_PATH)
sys.path.insert(0, str(runner.ADAPTER.parent))
adapter = load_module("r6_fumin_adapter", runner.ADAPTER)


def provider_get(base_url: str, api_key: str, task_id: str) -> dict:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/v3/contents/generations/tasks/"
        f"{urllib.parse.quote(task_id)}",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"provider task {task_id} returned a non-object payload")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("wave_id")
    parser.add_argument(
        "--confirm",
        required=True,
        choices=["GET_EXISTING_TASKS_ONLY"],
        help="Explicitly confirms that no provider POST/retry is authorized",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    ledger_path = output_dir / "budget-ledger.json"
    ledger = runner.load_json(ledger_path, "budget ledger")
    if ledger.get("status") != "blocked":
        raise RuntimeError("ledger must be blocked before manual reconciliation")
    waves = [wave for wave in ledger.get("waves", []) if wave.get("waveId") == args.wave_id]
    if len(waves) != 1 or waves[0].get("status") != "unsettled":
        raise RuntimeError("target wave must exist exactly once with status=unsettled")
    wave = waves[0]

    execution_path = output_dir / str(wave["executionManifest"])
    status_path = output_dir / str(wave["batchStatus"])
    execution = runner.load_json(execution_path, "execution manifest")
    status = runner.load_json(status_path, "batch status")
    execution_shots = execution.get("shots")
    status_shots = status.get("shots")
    if not isinstance(execution_shots, list) or not isinstance(status_shots, dict):
        raise RuntimeError("wave execution/status shape is invalid")

    api_key = os.environ.get("FUMIN_API_KEY", "")
    model = os.environ.get("FUMIN_MODEL", "")
    base_url = os.environ.get("FUMIN_BASE_URL", "https://fumin.ai").rstrip("/")
    if not api_key:
        raise RuntimeError("FUMIN_API_KEY is required for read-only task reconciliation")
    if model != EXPECTED_MODEL:
        raise RuntimeError(f"FUMIN_MODEL must equal {EXPECTED_MODEL!r}")
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
        raise RuntimeError("FUMIN_BASE_URL must be a credential-free http(s) origin")

    candidates_dir = status_path.parent
    task_to_shot: dict[str, str] = {}
    recovered: list[dict] = []
    for shot in execution_shots:
        shot_id = str(shot.get("id", ""))
        record = status_shots.get(shot_id)
        if not shot_id or not isinstance(record, dict):
            raise RuntimeError(f"missing status record for {shot_id!r}")
        task_id = str(record.get("task_id", ""))
        if not task_id:
            raise RuntimeError(f"shot {shot_id} has no existing provider task ID")
        if task_id in task_to_shot:
            raise RuntimeError(f"duplicate provider task ID {task_id}")

        result = provider_get(base_url, api_key, task_id)
        remote_status = str(result.get("status", "unknown")).lower()
        if remote_status not in adapter.SUCCESS_STATUSES:
            raise RuntimeError(
                f"existing provider task {task_id} is {remote_status}; no retry was made"
            )
        result_url = adapter.find_video_url(result)
        if not result_url:
            raise RuntimeError(f"succeeded provider task {task_id} has no video URL")

        output_name = str(shot.get("output_name", ""))
        if not output_name.endswith(".mp4"):
            raise RuntimeError(f"shot {shot_id} output name is invalid")
        shot_dir = candidates_dir / "shots" / shot_id
        shot_dir.mkdir(parents=True, exist_ok=True)
        output = shot_dir / output_name
        if output.exists():
            existing_provenance_path = shot_dir / "provenance.json"
            if not existing_provenance_path.is_file():
                raise RuntimeError(
                    f"refusing unprovenanced existing recovered output {output}"
                )
            existing_provenance = json.loads(existing_provenance_path.read_text())
            digest = adapter.file_sha256(output)
            if (
                existing_provenance.get("taskId") != task_id
                or existing_provenance.get("sha256") != digest
                or existing_provenance.get("reconciledFromExistingTask") is not True
            ):
                raise RuntimeError(
                    f"existing recovered output does not match the exact task {output}"
                )
        else:
            adapter.atomic_download(result_url, output)
            digest = adapter.file_sha256(output)
        provenance = {
            "provider": "fumin",
            "model": EXPECTED_MODEL,
            "taskId": task_id,
            "shotId": shot_id,
            "manifest": status.get("manifest"),
            "output": str(output.relative_to(candidates_dir)),
            "sha256": digest,
            "completedAt": adapter.utc_now(),
            "reconciledFromExistingTask": True,
            "providerPostRequests": 0,
        }
        adapter.atomic_write_json(shot_dir / "provenance.json", provenance)
        record.update(
            {
                "status": "succeeded",
                "output": str(output.relative_to(candidates_dir)),
                "sha256": digest,
                "error": None,
                "updated_at": adapter.utc_now(),
                "reconciledFromExistingTask": True,
            }
        )
        task_to_shot[task_id] = shot_id
        recovered.append({"shotId": shot_id, "taskId": task_id, "sha256": digest})

    settlements = runner.fetch_settlements(base_url, api_key, set(task_to_shot))
    by_id = {str(shot["id"]): shot for shot in execution_shots}
    if len(wave["shotIds"]) != len(wave["shotIndices"]):
        raise RuntimeError("wave shot IDs and indices have different lengths")
    index_by_id = dict(zip(wave["shotIds"], wave["shotIndices"]))
    already_recorded = {str(item.get("taskId")) for item in ledger.get("shots", [])}
    wave_quota = 0
    for task_id, quota in settlements.items():
        if task_id in already_recorded:
            raise RuntimeError(f"provider task {task_id} was already settled")
        shot_id = task_to_shot[task_id]
        shot = by_id[shot_id]
        cost = runner.quota_cost(quota)
        ledger["shots"].append(
            {
                "shotIndex": int(index_by_id[shot_id]),
                "shotId": shot_id,
                "durationSeconds": int(shot["duration"]),
                "taskId": task_id,
                "providerStatus": "succeeded",
                "actualQuota": quota,
                "actualCostCny": runner.money_text(cost),
                "waveId": args.wave_id,
                "settledAt": runner.utc_now(),
                "reconciledFromExistingTask": True,
            }
        )
        wave_quota += quota

    status["status"] = "completed"
    status["summary"] = {
        "total": len(execution_shots),
        "pending": 0,
        "running": 0,
        "succeeded": len(execution_shots),
        "failed": 0,
    }
    status["updated_at"] = adapter.utc_now()
    adapter.atomic_write_json(status_path, status)

    wave.update(
        {
            "status": "settled",
            "actualQuota": wave_quota,
            "actualCostCny": runner.money_text(runner.quota_cost(wave_quota)),
            "settledAt": runner.utc_now(),
            "noTaskShotIds": [],
            "reconciledFromExistingTasks": True,
        }
    )
    wave.pop("settlementError", None)
    runner.recompute_ledger_totals(
        ledger,
        runner.decimal_from(
            ledger["approvedConservativeRateCnyPerSecond"],
            "ledger.approvedConservativeRateCnyPerSecond",
        ),
    )
    ledger["status"] = "active"
    ledger["stopReason"] = None
    ledger["manualReconciliation"] = {
        "waveId": args.wave_id,
        "at": runner.utc_now(),
        "providerPostRequests": 0,
        "recoveredTaskIds": sorted(task_to_shot),
    }
    runner.atomic_write_json(ledger_path, ledger)
    print(
        json.dumps(
            {
                "verdict": "R6_EXISTING_TASKS_RECONCILED",
                "waveId": args.wave_id,
                "providerPostRequests": 0,
                "recovered": len(recovered),
                "actualQuota": wave_quota,
                "actualCostCny": runner.money_text(runner.quota_cost(wave_quota)),
                "settledTotalCny": ledger["settledCostCny"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
