import json
import unittest
from copy import deepcopy
from pathlib import Path

from backend.game_content import CHARACTER_MAP, DAY1_MEDIA_CONTRACT, NODES, create_snapshot, project_view
from backend.story_director import (
    STORY_EVENTS,
    build_story_director_messages,
    commit_story_event,
    eligible_story_events,
    resolve_story_event_media,
    resolve_story_mission,
    validate_story_director_output,
)


ROOT = Path(__file__).resolve().parent.parent


def add_memory(snapshot, character_id, index=0):
    snapshot["echoMemories"].append({
        "id": f"memory-{character_id}-{index}", "characterId": character_id, "ownerId": character_id,
        "kind": "episodic", "summary": f"{CHARACTER_MAP[character_id]['name']}与玩家完成了第{index + 1}次具体交流",
        "interpretation": "玩家愿意用行动验证判断", "salience": 70, "emotionalValence": 20,
        "callbackEligible": True,
    })


def early_snapshot():
    snapshot = create_snapshot("INFP", "jiangmi")
    snapshot["nodeId"] = "guided-chat"
    snapshot["storyArc"]["phase"] = "early"
    add_memory(snapshot, "shenmo")
    return snapshot


def valid_proposal(candidate):
    participants = candidate["participantSets"][0]
    name = CHARACTER_MAP[participants[0]]["name"]
    return {
        "decision": "activate", "proposedEventId": candidate["eventId"], "participantIds": participants,
        "bridgeTitle": "今晚的任务已经改变",
        "bridgeText": f"节目组刚把一张新的任务卡放到桌上，卡片点名了{name}，也要求你在截止时间前作出一个可以被验证的选择。",
        "sceneSetup": f"海岛酒店的公共区只亮着任务桌上方的一盏灯。{name}站在卡片旁等你确认规则，倒计时还在继续，任何人都不能替另一位嘉宾答应组队。",
        "reversalBeat": f"原本没有抢话的{name}先把任务卡翻回正面，只问谁愿意承担失败后的那一步。",
        "characterInsight": f"{name}的安静不是退缩，而是把决定留到能够真正负责的时刻。",
        "visualCue": f"{name}在暖光任务桌前翻开卡片并抬眼等待回应",
        "availableStrategies": ["先确认规则，再邀请对方共同分工", "先说明自己的边界，再决定是否接受任务"],
        "playerMissionPrompt": f"现在去找{name}，说清分工并完成一次可验证行动。",
        "publicReason": "已有互动足以触发下一步", "urgency": "medium", "memoryCallbackIds": [],
    }


class StoryDirectorContractTests(unittest.TestCase):
    def test_catalog_ids_and_sources_are_valid(self):
        source_package = json.loads((ROOT / "content" / "story_event_sources.v1.json").read_text(encoding="utf-8"))
        source_ids = {item["id"] for item in source_package["sources"]}
        event_ids = [event["id"] for event in STORY_EVENTS]
        self.assertEqual(len(event_ids), len(set(event_ids)))
        self.assertGreaterEqual(len(event_ids), 12)
        for event in STORY_EVENTS:
            self.assertTrue(set(event["sourceRefIds"]).issubset(source_ids))
            self.assertTrue(event["playerMission"]["objective"])
            self.assertTrue(event["playerMission"]["exit"])
            self.assertTrue(event["safety"])
            runtime_media = event.get("mediaPlan", {}).get("runtimeAsset")
            if runtime_media:
                self.assertTrue((ROOT / "frontend" / "public" / runtime_media["src"].removeprefix("/")).is_file())
                self.assertGreater(float(runtime_media["durationSeconds"]), 0)

    def test_all_sixteen_story_events_have_stable_media_or_fallback(self):
        self.assertEqual(16, len(STORY_EVENTS))
        for event in STORY_EVENTS:
            plan = event["mediaPlan"]
            for field in ("assetId", "src", "poster", "fallback", "status"):
                self.assertTrue(plan.get(field), f"{event['id']} missing {field}")
            media = resolve_story_event_media(event)
            self.assertEqual(event["id"], media["eventId"])
            self.assertEqual(plan["assetId"], media["assetId"])
            self.assertTrue(media["intent"].startswith("story-event:"))
            self.assertIn(media["status"], {"ready", "planned"})
            self.assertTrue(media["fallback"]["kind"])

    def test_all_day_and_catalog_events_have_deterministic_media_identity(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        day_media = []
        for node_id in NODES:
            snapshot["nodeId"] = node_id
            day_media.append(project_view(snapshot)["mediaContext"])
        catalog_media = [resolve_story_event_media(event) for event in STORY_EVENTS]
        self.assertEqual(len(NODES) + len(STORY_EVENTS), len(day_media) + len(catalog_media))
        self.assertEqual(25, len(day_media) + len(catalog_media))
        for media in [*day_media, *catalog_media]:
            self.assertTrue(media["eventId"])
            self.assertTrue(media["intent"])
            if media["available"]:
                self.assertEqual(f"/media/video/{media['assetId']}.mp4", media["src"])
            else:
                self.assertEqual("", media["src"])
                self.assertEqual("", media["poster"])
                self.assertEqual(f"/media/video/{media['assetId']}.mp4", media["plannedSrc"])
                self.assertEqual(f"/media/posters/{media['assetId']}.jpg", media["plannedPoster"])
            self.assertTrue(media["fallback"]["kind"])

    def test_named_character_event_films_are_cast_constrained(self):
        expected_cast = {
            "story.house.rules-friction": ["shenmo"],
            "story.triangle.reverse-invite": ["shenmo", "chengye"],
            "story.challenge.water-bridge": ["chensu", "jiangmi"],
            "story.trip.last-two-days": ["jiangwan"],
        }
        by_id = {event["id"]: event for event in STORY_EVENTS}
        for event_id, character_ids in expected_cast.items():
            self.assertEqual(character_ids, by_id[event_id]["eligibility"].get("characterIds"))

    def test_planned_story_event_never_projects_a_playable_src(self):
        event = deepcopy(STORY_EVENTS[0])
        event["mediaPlan"]["status"] = "planned"
        event["mediaPlan"].pop("runtimeAsset", None)
        media = resolve_story_event_media(event)
        self.assertFalse(media["available"])
        self.assertEqual("", media["src"])
        self.assertEqual("", media["poster"])
        self.assertTrue(media["plannedSrc"])

    def test_story_director_sees_media_intent_and_cue_but_not_allowlisted_paths(self):
        snapshot = early_snapshot()
        candidates = eligible_story_events(snapshot)
        prompt = build_story_director_messages(snapshot, candidates)[1]["content"]
        self.assertIn("mediaIntent", prompt)
        self.assertIn("mediaCue", prompt)
        self.assertNotIn("/media/video/", prompt)
        self.assertNotIn("/media/posters/", prompt)

    def test_first_day_key_task_is_removed_but_researched_events_remain(self):
        snapshot = early_snapshot()
        event_ids = {item["eventId"] for item in eligible_story_events(snapshot, limit=20)}
        self.assertIn("story.kitchen.two-person-shift", event_ids)
        self.assertFalse(any("key-partner" in event_id for event_id in event_ids))
        self.assertNotIn("story.bombshell.ninth-card", event_ids)
        self.assertNotIn("story.past.consent-reveal", event_ids)

    def test_triangle_requires_two_observed_attractions(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "team-up"
        snapshot["storyArc"]["phase"] = "middle"
        for index in range(2):
            add_memory(snapshot, "shenmo", index)
            add_memory(snapshot, "chengye", index)
        snapshot["relationships"]["shenmo"]["attraction"] = 2
        snapshot["relationships"]["chengye"]["attraction"] = 2
        candidates = eligible_story_events(snapshot, limit=20)
        triangle = next(item for item in candidates if item["eventId"] == "story.triangle.reverse-invite")
        self.assertIn(["chengye", "shenmo"], [sorted(group) for group in triangle["participantSets"]])

    def test_injected_event_and_participant_are_rejected(self):
        snapshot = early_snapshot()
        candidates = eligible_story_events(snapshot)
        proposal = valid_proposal(candidates[0])
        proposal["proposedEventId"] = "story.injected.unwritten-ending"
        with self.assertRaises(ValueError):
            validate_story_director_output(snapshot, candidates, proposal)
        proposal = valid_proposal(candidates[0])
        proposal["participantIds"] = ["not-a-cast-member"]
        with self.assertRaises(ValueError):
            validate_story_director_output(snapshot, candidates, proposal)

    def test_state_patch_from_model_is_ignored(self):
        snapshot = early_snapshot()
        candidates = eligible_story_events(snapshot)
        proposal = valid_proposal(candidates[0])
        proposal["statePatch"] = {"relationships.shenmo.trust": 100, "nodeId": "finale"}
        next_snapshot, _ = commit_story_event(snapshot, candidates, proposal)
        self.assertEqual(0, next_snapshot["relationships"]["shenmo"]["trust"])
        self.assertEqual("guided-chat", next_snapshot["nodeId"])

    def test_only_one_active_mission_and_resolution_is_deterministic(self):
        snapshot = early_snapshot()
        candidates = eligible_story_events(snapshot)
        next_snapshot, receipt = commit_story_event(snapshot, candidates, valid_proposal(candidates[0]))
        self.assertEqual("active", next_snapshot["storyMission"]["status"])
        self.assertEqual([], eligible_story_events(next_snapshot))
        resolved, resolution = resolve_story_mission(next_snapshot, receipt["mission"]["id"], "completed", "完成了具体分工")
        self.assertIsNone(resolved["storyMission"])
        self.assertEqual("completed", resolved["storyEventLedger"][-1]["status"])
        self.assertEqual("completed", resolution["outcome"])

    def test_generated_event_media_is_attached_only_after_commit(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "team-up"
        snapshot["storyArc"]["phase"] = "middle"
        for index in range(2):
            add_memory(snapshot, "shenmo", index)
            add_memory(snapshot, "chengye", index)
        snapshot["relationships"]["shenmo"]["attraction"] = 2
        snapshot["relationships"]["chengye"]["attraction"] = 2
        candidates = eligible_story_events(snapshot, limit=20)
        triangle = next(item for item in candidates if item["eventId"] == "story.triangle.reverse-invite")
        next_snapshot, receipt = commit_story_event(snapshot, candidates, valid_proposal(triangle))
        self.assertEqual("EV-TRIANGLE-reverse-invite", receipt["mission"]["media"]["assetId"])
        self.assertEqual("/media/video/EV-TRIANGLE-reverse-invite.mp4", next_snapshot["storyMission"]["media"]["src"])

    def test_memory_callbacks_are_limited_to_selected_participants(self):
        snapshot = create_snapshot("INFP", "jiangmi")
        snapshot["nodeId"] = "guided-chat"
        snapshot["storyArc"]["phase"] = "early"
        add_memory(snapshot, "shenmo")
        add_memory(snapshot, "linyu")
        candidates = eligible_story_events(snapshot, limit=20)
        kitchen = next(item for item in candidates if item["eventId"] == "story.kitchen.two-person-shift")
        proposal = valid_proposal(kitchen)
        selected = proposal["participantIds"][0]
        other = "linyu" if selected == "shenmo" else "shenmo"
        proposal["memoryCallbackIds"] = [f"memory-{selected}-0", f"memory-{other}-0", "invented-memory"]
        validated = validate_story_director_output(snapshot, candidates, proposal)
        self.assertEqual([f"memory-{selected}-0"], validated["memoryCallbackIds"])

    def test_water_bridge_requires_both_authored_characters(self):
        snapshot = create_snapshot("ISTP", "shenmo")
        snapshot["nodeId"] = "team-up"; snapshot["storyArc"]["phase"] = "middle"
        add_memory(snapshot, "chensu"); add_memory(snapshot, "jiangmi")
        candidates = eligible_story_events(snapshot, limit=30)
        bridge = next(item for item in candidates if item["eventId"] == "story.challenge.water-bridge")
        self.assertEqual([["chensu", "jiangmi"]], [sorted(group) for group in bridge["participantSets"]])

    def test_director_cannot_invent_trauma_for_a_reversal(self):
        snapshot = create_snapshot("ISTP", "shenmo")
        snapshot["nodeId"] = "team-up"; snapshot["storyArc"]["phase"] = "middle"
        add_memory(snapshot, "chensu"); add_memory(snapshot, "jiangmi")
        candidates = eligible_story_events(snapshot, limit=30)
        bridge = next(item for item in candidates if item["eventId"] == "story.challenge.water-bridge")
        proposal = valid_proposal(bridge)
        proposal["reversalBeat"] = "姜米因为童年创伤突然无法靠近水面，陈叙决定替她完成挑战。"
        with self.assertRaises(ValueError):
            validate_story_director_output(snapshot, candidates, proposal)

    def test_bridge_cannot_reference_an_uncommitted_story_artifact(self):
        snapshot = create_snapshot("INFJ")
        snapshot["nodeId"] = "callback"
        snapshot["storyArc"]["phase"] = "late"
        for index in range(4):
            add_memory(snapshot, "jiangwan", index)
        for index in range(3):
            add_memory(snapshot, "linyu", index)
        snapshot["relationships"]["jiangwan"].update({"trust": 5, "affection": 4, "attraction": 3})
        snapshot["trust"]["jiangwan"] = 5; snapshot["affection"]["jiangwan"] = 4
        snapshot["relationships"]["linyu"].update({"trust": 3, "affection": 2, "attraction": 1})
        snapshot["trust"]["linyu"] = 3; snapshot["affection"]["linyu"] = 2
        candidates = eligible_story_events(snapshot, limit=20)
        trip = next(item for item in candidates if item["eventId"] == "story.trip.last-two-days")
        proposal = valid_proposal(trip)
        name = CHARACTER_MAP[proposal["participantIds"][0]]["name"]
        proposal["bridgeText"] = f"{name}把一封尚未在剧情中发生的告别信放到桌上，要求你根据这封信决定是否接受最后两日一夜的同行邀请。"
        with self.assertRaises(ValueError):
            validate_story_director_output(snapshot, candidates, proposal)


if __name__ == "__main__":
    unittest.main()
