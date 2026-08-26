#!/usr/bin/env python3
"""Self-tests for the offline R6 candidate technical QA tool."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_candidates


def probe(*, audio: bool, duration: float = 4.04, width: int = 496, height: int = 864) -> dict:
    streams = [
        {
            "index": 0,
            "codec_type": "video",
            "codec_name": "h264",
            "width": width,
            "height": height,
            "pix_fmt": "yuv420p",
            "avg_frame_rate": "24/1",
        }
    ]
    if audio:
        streams.append(
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "32000",
                "channels": 2,
            }
        )
    return {"format": {"format_name": "mov,mp4", "duration": str(duration), "size": "12"}, "streams": streams}


class CandidateQaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.candidates = self.root / "candidates"
        self.candidates.mkdir()
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "defaults": {"ratio": "9:16", "resolution": "480p"},
                    "shots": [
                        {
                            "id": "event-a",
                            "kind": "event-rotation-candidate",
                            "output_name": "event-a-candidate.mp4",
                            "duration": 4,
                            "ratio": "9:16",
                            "resolution": "480p",
                            "generate_audio": True,
                        },
                        {
                            "id": "portrait-a",
                            "kind": "dynamic-portrait-candidate",
                            "output_name": "portrait-a-candidate.mp4",
                            "duration": 4,
                            "ratio": "9:16",
                            "resolution": "480p",
                            "generate_audio": False,
                        },
                    ],
                    "localComposites": [
                        {"output_name": "local-composite-candidate.mp4"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def touch(self, relative: str, payload: bytes) -> Path:
        path = self.candidates / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def test_allow_partial_keeps_missing_pending_and_passes(self) -> None:
        self.touch("wave-1/event-a-candidate.mp4", b"event")

        def fake(path: Path) -> dict:
            return probe(audio=path.name.startswith("event"))

        report = qa_candidates.run_qa(
            self.manifest, self.candidates, allow_partial=True, prober=fake
        )
        self.assertEqual(report["verdict"], "R6_PARTIAL_QA_PASS_PRESENT_CANDIDATES")
        self.assertEqual(report["exitCode"], 0)
        self.assertEqual(report["summary"]["technicalPassed"], 1)
        self.assertEqual(report["summary"]["pendingGeneration"], 1)
        self.assertEqual(report["assets"][1]["status"], "pending-generation")

    def test_complete_mode_fails_missing(self) -> None:
        self.touch("wave-1/event-a-candidate.mp4", b"event")
        report = qa_candidates.run_qa(
            self.manifest,
            self.candidates,
            allow_partial=False,
            prober=lambda _path: probe(audio=True),
        )
        self.assertEqual(report["verdict"], "R6_TECHNICAL_QA_FAILED")
        self.assertEqual(report["exitCode"], 1)
        self.assertEqual(report["assets"][1]["status"], "missing-candidate")

    def test_audio_contract_and_duplicates_fail_even_in_partial_mode(self) -> None:
        self.touch("wave-1/event-a-candidate.mp4", b"event")
        self.touch("wave-2/event-a-candidate.mp4", b"event-copy")
        self.touch("wave-2/portrait-a-candidate.mp4", b"portrait")

        def fake(path: Path) -> dict:
            # The dynamic portrait intentionally has an audio stream.
            return probe(audio=True)

        report = qa_candidates.run_qa(
            self.manifest, self.candidates, allow_partial=True, prober=fake
        )
        self.assertEqual(report["verdict"], "R6_TECHNICAL_QA_FAILED")
        self.assertEqual(report["summary"]["duplicateOutputJobs"], 1)
        portrait = next(item for item in report["assets"] if item["id"] == "portrait-a")
        self.assertIn("dynamic portrait must be silent", portrait["errors"][0])

    def test_duplicate_content_and_unexpected_candidate_are_detected(self) -> None:
        self.touch("wave-1/event-a-candidate.mp4", b"same")
        self.touch("wave-2/portrait-a-candidate.mp4", b"same")
        self.touch("wave-3/unknown-candidate.mp4", b"unknown")
        # A planned local composite is known but is not counted as a provider job.
        self.touch("local/local-composite-candidate.mp4", b"composite")

        def fake(path: Path) -> dict:
            return probe(audio=path.name.startswith("event"))

        report = qa_candidates.run_qa(
            self.manifest, self.candidates, allow_partial=True, prober=fake
        )
        self.assertEqual(report["summary"]["duplicateContentGroups"], 1)
        self.assertEqual(report["summary"]["unexpectedCandidateFiles"], 1)
        self.assertEqual(report["summary"]["candidateFilesScanned"], 4)
        self.assertEqual(report["exitCode"], 1)

    def test_duration_and_resolution_tolerance(self) -> None:
        self.touch("wave-1/event-a-candidate.mp4", b"event")
        self.touch("wave-2/portrait-a-candidate.mp4", b"portrait")

        def fake(path: Path) -> dict:
            if path.name.startswith("event"):
                return probe(audio=True, duration=4.51)
            return probe(audio=False, width=720, height=1280)

        report = qa_candidates.run_qa(
            self.manifest, self.candidates, allow_partial=True, prober=fake
        )
        self.assertEqual(report["summary"]["technicalFailed"], 2)
        details = " ".join(error for item in report["assets"] for error in item["errors"])
        self.assertIn("duration", details)
        self.assertIn("short edge", details)


if __name__ == "__main__":
    unittest.main()
