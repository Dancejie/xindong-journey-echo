#!/usr/bin/env python3
"""Fail-closed validator for an R6 paid Seedance approval record.

This validator does not submit work and never reads API keys.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXPECTED_TASKS = 81
EXPECTED_SECONDS = 416
THRESHOLD = Decimal("200")
EXPECTED_RATE = Decimal("0.1234554")
EXPECTED_INCREMENTAL = Decimal("51.3574464")
PRICING_EVIDENCE_REF = "pricing-evidence-2026-08-26.json#derived"


class GateError(RuntimeError):
    pass


def non_placeholder(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{label} is required")
    lowered = value.lower()
    if "replace" in lowered or "pending" in lowered or "placeholder" in lowered:
        raise GateError(f"{label} is still a placeholder")
    return value


def number(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GateError(f"{label} must be a verified number")
    return Decimal(str(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("approval", type=Path)
    args = parser.parse_args()

    approval = json.loads(args.approval.read_text(encoding="utf-8"))
    manifest_path = HERE / "manifest.r6.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    if approval.get("doNotSubmit") is not False:
        raise GateError("approval.doNotSubmit must be explicitly false")
    if approval.get("manifestSha256") != manifest_sha:
        raise GateError("manifestSha256 does not bind the current manifest.r6.json")
    if approval.get("approvedTaskCount") != EXPECTED_TASKS:
        raise GateError("approvedTaskCount must be 81")
    if approval.get("approvedTotalDurationSeconds") != EXPECTED_SECONDS:
        raise GateError("approvedTotalDurationSeconds must be 416")
    if manifest.get("doNotSubmit") is not True:
        raise GateError("planning manifest must remain doNotSubmit=true; the approval is the only execution authority")

    policy = approval.get("policy", {})
    expected_policy = {
        "provider": "fumin",
        "model": "seedance-2.0-mini",
        "ratio": "9:16",
        "resolution": "480p",
        "generateEventAudio": True,
        "watermark": False,
        "concurrency": 2,
        "maxApiRetry": 0,
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            raise GateError(f"policy.{key} must equal {expected!r}")
    if policy.get("durationRangeSeconds") != [4, 15]:
        raise GateError("policy.durationRangeSeconds must equal [4, 15]")

    pricing = approval.get("pricing", {})
    if pricing.get("currency") != "CNY":
        raise GateError("pricing.currency must be CNY")
    rate = number(pricing.get("unitPriceCnyPerSecond"), "pricing.unitPriceCnyPerSecond")
    if abs(rate - EXPECTED_RATE) > Decimal("0.0000000001"):
        raise GateError("price differs from the bound 480p historical sample; attach new evidence and update the plan")
    if pricing.get("pricingEvidenceRef") != PRICING_EVIDENCE_REF:
        raise GateError("pricing.pricingEvidenceRef must bind the local redacted settled-account record")
    non_placeholder(pricing.get("verifiedBy"), "pricing.verifiedBy")
    non_placeholder(pricing.get("verifiedAt"), "pricing.verifiedAt")

    budget = approval.get("budget", {})
    if number(budget.get("thresholdCny"), "budget.thresholdCny") != THRESHOLD:
        raise GateError("budget.thresholdCny must be 200")
    cumulative = number(budget.get("cumulativeSpendCnyFloor"), "budget.cumulativeSpendCnyFloor")
    if budget.get("cumulativeSpendExactKnown") is not False:
        raise GateError("budget.cumulativeSpendExactKnown must remain false; only a conservative floor is evidenced")
    non_placeholder(budget.get("cumulativeSpendEvidenceRef"), "budget.cumulativeSpendEvidenceRef")
    incremental = number(budget.get("incrementalSpendCny"), "budget.incrementalSpendCny")
    projected = number(budget.get("projectedCumulativeSpendCnyFloor"), "budget.projectedCumulativeSpendCnyFloor")
    hard_cap = number(budget.get("hardTotalMaxAmountCny"), "budget.hardTotalMaxAmountCny")
    if abs(incremental - EXPECTED_INCREMENTAL) > Decimal("0.01"):
        raise GateError("incrementalSpendCny must match 416 seconds at the conservative verified rate")
    if abs(projected - (cumulative + incremental)) > Decimal("0.01"):
        raise GateError("projectedCumulativeSpendCnyFloor must equal cumulative floor + incremental")
    if hard_cap != Decimal("60"):
        raise GateError("R6 zero-retry hardTotalMaxAmountCny must be exactly 60")
    if budget.get("retryTaskCountCap") != 0 or budget.get("retryRequiresNewApproval") is not True:
        raise GateError("paid retries are disabled and require new approval")

    # Either a batch estimate or the projected project total above CNY 200
    # requires a fresh written approval that explicitly names a maximum amount.
    if incremental > THRESHOLD or projected > THRESHOLD or cumulative > THRESHOLD:
        non_placeholder(budget.get("manualOverBudgetApprovalRef"), "budget.manualOverBudgetApprovalRef")
        manual_max = number(budget.get("manualOverBudgetMaxAmountCny"), "budget.manualOverBudgetMaxAmountCny")
        if manual_max != Decimal("60"):
            raise GateError("manualOverBudgetMaxAmountCny must explicitly approve the R6 incremental maximum CNY 60")

    user_approval = approval.get("userApproval", {})
    if user_approval.get("status") != "approved":
        raise GateError("userApproval.status must be approved")
    if user_approval.get("requiredText") != "R6新增上限¥60":
        raise GateError("userApproval.requiredText must be exactly R6新增上限¥60")
    if number(user_approval.get("maxCny"), "userApproval.maxCny") != Decimal("60"):
        raise GateError("userApproval.maxCny must explicitly be 60")
    approval_ref = non_placeholder(user_approval.get("approvalRef"), "userApproval.approvalRef")
    if approval_ref != budget.get("manualOverBudgetApprovalRef"):
        raise GateError("userApproval.approvalRef and budget.manualOverBudgetApprovalRef must identify the same written approval")
    non_placeholder(user_approval.get("approvedBy"), "userApproval.approvedBy")
    non_placeholder(user_approval.get("approvedAt"), "userApproval.approvedAt")

    rights = approval.get("rights", {})
    if rights.get("status") != "approved":
        raise GateError("rights.status must be approved")
    for field in ("likenessConsentRefIds", "voiceConsentRefIds", "referenceRightsRefIds"):
        refs = rights.get(field)
        if not isinstance(refs, list) or not refs or not all(isinstance(x, str) and x.strip() for x in refs):
            raise GateError(f"rights.{field} must contain reviewed references")
    non_placeholder(rights.get("reviewedBy"), "rights.reviewedBy")
    non_placeholder(rights.get("reviewedAt"), "rights.reviewedAt")

    for field in ("reviewedBy", "reviewedAt", "authorizedBy", "authorizedAt", "scopeRef"):
        non_placeholder(approval.get("approval", {}).get(field), f"approval.{field}")

    missing_refs = [shot["id"] for shot in manifest["shots"] if not (HERE / shot["reference_image"]).is_file()]
    if missing_refs:
        raise GateError(f"{len(missing_refs)} local reference inputs are still missing")

    print(json.dumps({"verdict": "R6_PAID_GATE_PASS", "tasks": 81, "seconds": 416, "hardCapCny": 60}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except GateError as exc:
        raise SystemExit(f"R6_PAID_GATE_BLOCKED: {exc}")
