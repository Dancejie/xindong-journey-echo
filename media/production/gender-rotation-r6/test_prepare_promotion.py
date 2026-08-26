import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("prepare_promotion.py")
SPEC = importlib.util.spec_from_file_location("r6_prepare_promotion", SCRIPT)
promotion = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = promotion
SPEC.loader.exec_module(promotion)


class PromotionPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "media").mkdir()
        (self.root / "frontend/public/media/video").mkdir(parents=True)
        self.plan_path = self.root / "media/manifest.r6.json"
        self.runtime_path = self.root / "media/runtime-media-manifest.json"
        self.allowlist_path = self.root / "media/visual-qa.json"
        self.probe = {"duration": 4.0, "videoCodec": "h264", "width": 496, "height": 864, "hasAudio": True}

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def candidate(self, name="candidate.mp4", payload=b"reviewed-video"):
        path = self.root / "media" / name
        path.write_bytes(payload)
        return path, hashlib.sha256(payload).hexdigest()

    def base_plan(self):
        return {
            "doNotSubmit": True,
            "schemes": [
                {"id": "F-A-jiangmi", "gender": "female", "leadId": "jiangmi", "supportId": "chensu"},
                {"id": "F-B-luyao", "gender": "female", "leadId": "luyao", "supportId": "chensu"},
            ],
            "shots": [],
            "localComposites": [],
        }

    def write_allowlist(self, plan, items):
        self.write_json(self.plan_path, plan)
        self.write_json(self.allowlist_path, {
            "schemaVersion": "heart-journey/r6-visual-qa-allowlist-v1",
            "planningManifestSha256": promotion.sha256_file(self.plan_path),
            "approvedAssets": items,
        })

    def prepare(self):
        with patch.object(promotion, "media_probe", return_value=self.probe):
            return promotion.prepare(self.root, self.plan_path, self.runtime_path, self.allowlist_path)

    def test_generated_event_maps_to_runtime_rotation_alias_without_copying(self):
        plan = self.base_plan()
        plan["shots"] = [{
            "id": "D1-A1--F-B-luyao--r6", "kind": "event-rotation-candidate",
            "eventAssetId": "D1-A1", "schemeId": "F-B-luyao",
            "leadCharacterId": "luyao", "supportCharacterIds": ["chensu"],
            "generate_audio": True, "output_name": "candidate.mp4",
        }]
        self.write_json(self.runtime_path, {"assets": []})
        candidate, digest = self.candidate()
        self.write_allowlist(plan, [{
            "sourceId": "D1-A1--F-B-luyao--r6", "candidatePath": str(candidate.relative_to(self.root)),
            "sha256": digest, "identityCast": ["luyao"],
            "visualQaVerdict": "passed", "audioQaVerdict": "passed",
        }])
        result = self.prepare()
        asset = result["assets"][0]["runtimeAsset"]
        self.assertEqual("D1-A1--rotation-F-B-luyao", asset["id"])
        self.assertEqual("女性", asset["leadGender"])
        self.assertEqual(["luyao"], asset["identityCast"])
        self.assertFalse((self.root / result["assets"][0]["destination"]).exists())

    def test_existing_fa_reuse_preserves_original_identity_cast(self):
        plan = self.base_plan()
        source, digest = self.candidate("D1-A1.mp4", b"existing-runtime")
        self.write_json(self.runtime_path, {"assets": [{
            "id": "D1-A1", "path": "/media/video/D1-A1.mp4", "status": "approved-runtime",
            "identityCast": ["jiangmi", "chensu"], "sha256": digest,
            "audio": {"hasAudio": True},
        }]})
        self.write_allowlist(plan, [{
            "sourceId": "reuse:D1-A1:F-A-jiangmi", "candidatePath": str(source.relative_to(self.root)),
            "sha256": digest, "identityCast": ["jiangmi", "chensu"],
            "visualQaVerdict": "passed", "audioQaVerdict": "passed",
        }])
        asset = self.prepare()["assets"][0]["runtimeAsset"]
        self.assertEqual("D1-A1--rotation-F-A-jiangmi", asset["id"])
        self.assertEqual(["jiangmi", "chensu"], asset["identityCast"])

    def test_fa_reuse_rejects_blanket_support_rewrite(self):
        plan = self.base_plan()
        source, digest = self.candidate("D1-A1.mp4")
        self.write_json(self.runtime_path, {"assets": [{
            "id": "D1-A1", "path": "/media/video/D1-A1.mp4", "status": "approved-runtime",
            "identityCast": ["jiangmi", "shenmo"], "audio": {"hasAudio": True},
        }]})
        self.write_allowlist(plan, [{
            "sourceId": "reuse:D1-A1:F-A-jiangmi", "candidatePath": str(source.relative_to(self.root)),
            "sha256": digest, "identityCast": ["jiangmi", "chensu"],
            "visualQaVerdict": "passed", "audioQaVerdict": "passed",
        }])
        with self.assertRaisesRegex(promotion.PromotionError, "preserve original identityCast"):
            self.prepare()

    def test_generated_event_rejects_identity_overclaim(self):
        plan = self.base_plan()
        # Keep shenmo a known roster identity without adding another promotable
        # source; this fixture is specifically about cast overclaim, not
        # incomplete allowlist coverage.
        plan["schemes"].append({
            "id": "M-A-shenmo", "gender": "male", "leadId": "shenmo", "supportId": "luyao",
        })
        plan["shots"] = [{
            "id": "D1-A1--F-B-luyao--r6", "kind": "event-rotation-candidate",
            "eventAssetId": "D1-A1", "schemeId": "F-B-luyao",
            "leadCharacterId": "luyao", "supportCharacterIds": ["chensu"],
            "generate_audio": True, "output_name": "candidate.mp4",
        }]
        self.write_json(self.runtime_path, {"assets": []})
        candidate, digest = self.candidate()
        self.write_allowlist(plan, [{
            "sourceId": "D1-A1--F-B-luyao--r6", "candidatePath": str(candidate.relative_to(self.root)),
            "sha256": digest, "identityCast": ["luyao", "shenmo"],
            "visualQaVerdict": "passed", "audioQaVerdict": "passed",
        }])
        with self.assertRaisesRegex(promotion.PromotionError, "overclaims"):
            self.prepare()

    def test_local_composite_requires_both_reviewed_people(self):
        plan = self.base_plan()
        plan["localComposites"] = [{
            "id": "D1-A3B--F-B-luyao--r6", "eventAssetId": "D1-A3B",
            "schemeId": "F-B-luyao", "output_name": "composite.mp4",
        }]
        self.write_json(self.runtime_path, {"assets": []})
        candidate, digest = self.candidate("composite.mp4")
        self.write_allowlist(plan, [{
            "sourceId": "D1-A3B--F-B-luyao--r6", "candidatePath": str(candidate.relative_to(self.root)),
            "sha256": digest, "identityCast": ["luyao"],
            "visualQaVerdict": "passed", "audioQaVerdict": "passed",
        }])
        with self.assertRaisesRegex(promotion.PromotionError, "both planned inputs"):
            self.prepare()

    def test_hash_mismatch_blocks_before_promotion(self):
        plan = self.base_plan()
        plan["shots"] = [{
            "id": "CHAR-luyao-portrait--r6", "kind": "dynamic-portrait-candidate",
            "leadCharacterId": "luyao", "supportCharacterIds": [], "generate_audio": False,
            "output_name": "portrait.mp4",
        }]
        self.write_json(self.runtime_path, {"assets": []})
        candidate, _ = self.candidate("portrait.mp4")
        self.write_allowlist(plan, [{
            "sourceId": "CHAR-luyao-portrait--r6", "candidatePath": str(candidate.relative_to(self.root)),
            "sha256": "0" * 64, "identityCast": ["luyao"],
            "visualQaVerdict": "passed", "requireSilent": True,
        }])
        with self.assertRaisesRegex(promotion.PromotionError, "sha256 mismatch"):
            self.prepare()

    def test_existing_runtime_target_is_never_overwritten(self):
        plan = self.base_plan()
        plan["shots"] = [{
            "id": "D1-A1--F-B-luyao--r6", "kind": "event-rotation-candidate",
            "eventAssetId": "D1-A1", "schemeId": "F-B-luyao",
            "leadCharacterId": "luyao", "supportCharacterIds": [],
            "generate_audio": True, "output_name": "candidate.mp4",
        }]
        self.write_json(self.runtime_path, {"assets": [{
            "id": "D1-A1--rotation-F-B-luyao", "path": "/media/video/already.mp4",
            "status": "approved-runtime", "identityCast": ["luyao"],
        }]})
        candidate, digest = self.candidate()
        self.write_allowlist(plan, [{
            "sourceId": "D1-A1--F-B-luyao--r6", "candidatePath": str(candidate.relative_to(self.root)),
            "sha256": digest, "identityCast": ["luyao"],
            "visualQaVerdict": "passed", "audioQaVerdict": "passed",
        }])
        with self.assertRaisesRegex(promotion.PromotionError, "overwrite refused"):
            self.prepare()

    def test_incomplete_allowlist_is_rejected(self):
        plan = self.base_plan()
        plan["shots"] = [{
            "id": "CHAR-luyao-portrait--r6", "kind": "dynamic-portrait-candidate",
            "leadCharacterId": "luyao", "supportCharacterIds": [], "generate_audio": False,
            "output_name": "portrait.mp4",
        }, {
            "id": "CHAR-shenmo-portrait--r6", "kind": "dynamic-portrait-candidate",
            "leadCharacterId": "shenmo", "supportCharacterIds": [], "generate_audio": False,
            "output_name": "other.mp4",
        }]
        self.write_json(self.runtime_path, {"assets": []})
        candidate, digest = self.candidate("portrait.mp4")
        self.write_allowlist(plan, [{
            "sourceId": "CHAR-luyao-portrait--r6", "candidatePath": str(candidate.relative_to(self.root)),
            "sha256": digest, "identityCast": ["luyao"],
            "visualQaVerdict": "passed", "requireSilent": True,
        }])
        with self.assertRaisesRegex(promotion.PromotionError, "complete source set"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
