#!/usr/bin/env python3
"""Validate R6 local production coverage without making a network call."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.r6.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["doNotSubmit"] is True
    assert data["scope"]["eventSlotCount"] == 25
    assert data["scope"]["rotationSchemeCount"] == 4
    assert data["scope"]["requiredRuntimeEventOutputs"] == 100
    assert data["scope"]["existingRuntimeReuseEventOutputs"] == 25
    assert data["scope"]["existingQaApprovedReusableEventOutputs"] == 24
    assert data["scope"]["existingHeldEventOutputs"] == 1
    assert data["scope"]["providerEventJobs"] == 73
    assert data["scope"]["providerDynamicPortraitJobs"] == 8
    assert data["scope"]["providerJobCount"] == 81
    assert data["scope"]["providerDurationSeconds"] == 416
    assert data["scope"]["localCompositeCount"] == 3

    shots = data["shots"]
    assert len(shots) == 81
    assert sum(item["duration"] for item in shots) == 416
    assert all(item["resolution"] == "480p" for item in shots)
    assert all(4 <= item["duration"] <= 12 for item in shots)
    assert len({item["id"] for item in shots}) == 81
    assert sum(item["kind"] == "dynamic-portrait-candidate" for item in shots) == 8
    assert sum(item["kind"] == "event-rotation-candidate" for item in shots) == 73

    for item in shots:
        prompt = HERE / item["prompt_file"]
        assert prompt.is_file(), prompt
        assert sha(prompt) == item["promptSha256"], prompt
        text = prompt.read_text(encoding="utf-8")
        assert "9:16" in text and "480p" in text
        assert "无水印" in text or "无Logo" in text
        if item["kind"] == "event-rotation-candidate":
            assert "【State In】" in text and "【State Out】" in text
            assert "【精确时间线】" in text and "【声音】" in text
            assert item["generate_audio"] is True

    # Four schemes cover all 25 event slots: 24 reviewed reuses + 73 provider
    # outputs + 3 local composites = 100 real runtime files after QA.
    assert 24 + 73 + len(data["localComposites"]) == 100
    assert {s["gender"] for s in data["schemes"]} == {"female", "male"}
    assert sum(s["gender"] == "female" for s in data["schemes"]) == 2
    assert sum(s["gender"] == "male" for s in data["schemes"]) == 2

    missing_refs = [item["id"] for item in shots if item["referenceStatus"] != "present"]
    missing_ref_files = {item["reference_image"] for item in shots if item["referenceStatus"] != "present"}
    print(
        json.dumps(
            {
                "verdict": "LOCAL_PLAN_VALID_SEPARATE_PAID_GATE_REQUIRED",
                "providerJobs": 81,
                "providerDurationSeconds": 416,
                "eventCoverageAfterQa": "100/100",
                "missingReferenceShotCount": len(missing_refs),
                "missingReferenceFileCount": len(missing_ref_files),
                "rightsStatus": data["rights"]["status"],
                "doNotSubmit": data["doNotSubmit"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
