import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.game_content import (
    CHARACTER_CARDS,
    CHARACTER_CARD_MAP,
    CARD_PACKAGE,
    CHARACTER_MAP,
    CONTENT_VERSION,
    DAY1_MEDIA_CONTRACT,
    NODES,
    RELATIONSHIP_AXES,
    apply_choice,
    build_fallback_script_flavor,
    commit_agent_turn,
    create_snapshot,
    migrate_snapshot,
    project_view,
    validate_agent_turn,
)
from backend.agent_prompt import build_agent_messages, extract_json, fallback_chat_opening, validate_chat_opening
from backend.day1_script import (
    build_day1_node_messages,
    install_cached_day1_script,
    install_day1_node_script,
    install_day1_script,
    validate_day1_node_script,
    validate_day1_script,
)


def valid_turn(card):
    background = {
        "shenmo": "我在投行工作", "linyu": "我是建筑工程师", "chengye": "我在经营极限运动品牌",
        "guyan": "我做游戏策划", "jiangwan": "我是心理咨询师", "jiangmi": "我喜欢录声音日记",
        "sunnian": "我是插画师", "chensu": "我平时喜欢修旧相机",
    }[card["id"]]
    return {
        "dialogue": f"你好，我是{card['names']['primary']}，MBTI是{card['mbti']}，{background}。这次来这里，是想从一件具体的小事开始认识一个人。你呢？",
        "stageDirection": "对方把身体转向你，认真等你回答",
        "attitude": "curious",
        "intentId": card["agentPolicy"]["allowedIntentIds"][0],
        "publicReason": "具体表达让关系判断发生变化",
        "relationshipDelta": {axis: 3 for axis in RELATIONSHIP_AXES},
        "memory": {"kind": "episodic", "summary": "玩家作出一次具体表达", "interpretation": "对方愿意承担下一步", "salience": 70, "emotionalValence": 25},
        "proposedEventId": card["eventPolicy"]["eventId"],
    }


class CharacterCardContractTests(unittest.TestCase):
    def test_all_eight_cards_have_interop_contract(self):
        self.assertEqual(8, len(CHARACTER_CARDS))
        for card in CHARACTER_CARDS:
            self.assertEqual(set(RELATIONSHIP_AXES), set(card["agentPolicy"]["deltaBounds"]))
            self.assertEqual({"analysts", "diplomats", "sentinels", "explorers"}, set(card["interactionStrategies"]) & {"analysts", "diplomats", "sentinels", "explorers"})
            self.assertGreaterEqual(len(card["fewShots"]), 2)
            self.assertIn(card["eventPolicy"]["eventId"], card["agentPolicy"]["allowedEventIds"])
            self.assertIn(card["sourceProfile"]["alignment"], {"exact", "name-adapted", "runtime-original", "type-adapted", "name-and-type-adapted"})
            self.assertTrue(card["cognitiveStyle"]["decisionRule"])
            self.assertTrue(card["knowledge"]["doesNotKnow"])
            self.assertEqual({"supportive", "probing", "challenging", "boundaryViolation"}, set(card["reactionMatrix"]))
            self.assertIn("新事实", card["dialoguePolicy"]["mustAdvanceBy"])

    def test_deepseek_delta_is_bounded_by_each_card(self):
        for card in CHARACTER_CARDS:
            perspective_id = "jiangmi" if card["id"] != "jiangmi" else "shenmo"
            snapshot = create_snapshot("INFP", perspective_id)
            turn = valid_turn(card)
            next_snapshot, _ = commit_agent_turn(snapshot, card["id"], "这是一次具体表达。", turn)
            for axis in RELATIONSHIP_AXES:
                self.assertLessEqual(next_snapshot["relationships"][card["id"]][axis], card["agentPolicy"]["deltaBounds"][axis][1])

    def test_day_one_is_a_guided_plain_language_flow(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        self.assertEqual("arrival-context", snapshot["nodeId"])
        for choice_id, expected in (
            ("context-meet", "villa-arrival"),
            ("arrival-help-luggage", "introductions"),
            ("intro-clear", "cast-first-impressions"),
        ):
            snapshot, _ = apply_choice(snapshot, choice_id)
            self.assertEqual(expected, snapshot["nodeId"])
        transition = project_view(snapshot)["node"]
        self.assertGreaterEqual(len(transition["textBeats"]), 3)
        self.assertIn("其余七", transition["text"])
        self.assertEqual(3, len(transition["choices"]))
        for choice in transition["choices"]:
            self.assertIn(CHARACTER_MAP[choice["targetCharacterId"]]["name"], choice["label"])
        snapshot, impression_receipt = apply_choice(snapshot, transition["choices"][0]["id"])
        self.assertEqual("icebreaker-choice", snapshot["nodeId"])
        self.assertEqual(impression_receipt["targetCharacterId"], snapshot["firstImpressionSeed"]["characterId"])
        self.assertEqual(["team-up", "anonymous-letter", "callback"], snapshot["firstImpressionSeed"]["plannedCallbackNodeIds"])
        projected = project_view(snapshot)
        self.assertEqual(3, len(projected["node"]["choices"]))
        target_ids = [choice["targetCharacterId"] for choice in projected["node"]["choices"]]
        self.assertEqual(3, len(set(target_ids)))
        self.assertNotIn("jiangmi", target_ids)
        snapshot, receipt = apply_choice(snapshot, projected["node"]["choices"][0]["id"])
        target_id = receipt["targetCharacterId"]
        self.assertEqual("guided-chat", snapshot["nodeId"])
        self.assertEqual(target_id, snapshot["guidedTargetCharacterId"])
        self.assertEqual("required", snapshot["pendingInteraction"]["status"])
        with self.assertRaisesRegex(ValueError, "完成一次"):
            apply_choice(snapshot, "chat-team-direct")
        other_id = next(character_id for character_id in CHARACTER_MAP if character_id not in {target_id, "jiangmi"})
        with self.assertRaisesRegex(ValueError, "这一段先去"):
            commit_agent_turn(snapshot, other_id, "你好。", valid_turn(next(card for card in CHARACTER_CARDS if card["id"] == other_id)))
        target_card = next(card for card in CHARACTER_CARDS if card["id"] == target_id)
        snapshot, receipt = commit_agent_turn(snapshot, target_id, "你好，我也第一次参加这样的节目。", valid_turn(target_card))
        self.assertTrue(receipt["guidedInteractionCompleted"])
        self.assertEqual("completed", snapshot["pendingInteraction"]["status"])
        snapshot, _ = apply_choice(snapshot, "chat-team-together")
        self.assertEqual("team-up", snapshot["nodeId"])
        callback = project_view(snapshot)["node"]["firstImpressionCallback"]
        self.assertEqual(snapshot["firstImpressionSeed"]["characterId"], callback["characterId"])
        self.assertTrue(callback["matchesCurrentFocus"])
        snapshot, _ = apply_choice(snapshot, "team-cooperate")
        self.assertEqual("anonymous-letter", snapshot["nodeId"])
        recipients = project_view(snapshot)["node"]["choices"]
        self.assertEqual(3, len(recipients))
        self.assertNotIn("jiangmi", {choice["characterId"] for choice in recipients})
        snapshot, _ = apply_choice(snapshot, recipients[0]["id"], recipients[0]["characterId"])
        self.assertEqual("callback", snapshot["nodeId"])

    def test_every_active_day_one_story_node_has_three_engine_owned_choices(self):
        for node_id in ("arrival-context", "villa-arrival", "introductions", "cast-first-impressions", "icebreaker-choice", "guided-chat", "team-up"):
            self.assertEqual(3, len(NODES[node_id]["choices"]), node_id)
            self.assertEqual(3, len({choice["id"] for choice in NODES[node_id]["choices"]}))
            for choice in NODES[node_id]["choices"]:
                self.assertTrue(choice["intentId"])
                self.assertIn(choice["next"], NODES)

    def test_all_day_one_nodes_project_engine_owned_media_contract(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        for node_id in NODES:
            snapshot["nodeId"] = node_id
            view = project_view(snapshot)
            media = view["mediaContext"]
            contract = DAY1_MEDIA_CONTRACT[node_id]
            self.assertEqual(contract["eventId"], media["eventId"])
            allowed_asset_ids = {
                contract["assetId"],
                *contract.get("variantAssetIds", {}).values(),
            }
            self.assertIn(media["assetId"], allowed_asset_ids)
            if media["available"]:
                self.assertTrue(media["src"].startswith("/media/video/"))
                self.assertEqual(media["src"], view["node"]["cinematic"])
            else:
                self.assertEqual("", media["src"])
                self.assertEqual("", media["poster"])
                self.assertIsNone(view["node"]["cinematic"])
                self.assertTrue(media["plannedSrc"].startswith("/media/video/"))
                self.assertTrue(media["plannedPoster"].startswith("/media/posters/"))
            self.assertIn("fallback", media)
            self.assertEqual(media, view["node"]["media"])

    def test_character_specific_media_variants_only_route_when_identity_matches(self):
        assets = {
            "D1-A6-first-dinner-team": {"path": "/media/video/D1-A6-first-dinner-team.mp4", "status": "ready"},
            "D1-A6-first-dinner-team--shenmo": {"path": "/media/video/D1-A6-first-dinner-team--shenmo.mp4", "status": "ready"},
            "D1-A7-heart-message": {"path": "/media/video/D1-A7-heart-message.mp4", "status": "ready"},
            "D1-A7-heart-message--jiangmi": {"path": "/media/video/D1-A7-heart-message--jiangmi.mp4", "status": "ready"},
        }
        snapshot = create_snapshot("ENFP", "jiangmi")
        with patch("backend.game_content._runtime_asset_map", return_value=assets):
            snapshot["nodeId"] = "team-up"
            snapshot["guidedTargetCharacterId"] = "shenmo"
            team_media = project_view(snapshot)["mediaContext"]
            self.assertEqual("D1-A6-first-dinner-team--shenmo", team_media["assetId"])
            self.assertEqual("shenmo", team_media["variantForCharacterId"])
            snapshot["nodeId"] = "anonymous-letter"
            letter_media = project_view(snapshot)["mediaContext"]
            self.assertEqual("D1-A7-heart-message--jiangmi", letter_media["assetId"])
            self.assertEqual("jiangmi", letter_media["variantForCharacterId"])

    def test_unapproved_media_never_routes_as_runtime_cinematic(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "arrival-context"
        assets = {
            "D1-A1-island-hotel-establish": {
                "path": "/media/video/D1-A1-island-hotel-establish.mp4",
                "poster": "/media/posters/D1-A1-island-hotel-establish.jpg",
                "status": "provisional-approved",
            }
        }
        with patch("backend.game_content._runtime_asset_map", return_value=assets):
            view = project_view(snapshot)
        self.assertFalse(view["mediaContext"]["available"])
        self.assertEqual("", view["mediaContext"]["src"])
        self.assertIsNone(view["node"]["cinematic"])

    def test_fallback_introductions_are_direct_character_specific_speech(self):
        for card in CHARACTER_CARDS:
            flavor = build_fallback_script_flavor(card["id"])
            introductions = flavor["nodes"]["introductions"]["choices"]
            self.assertEqual(3, len(introductions))
            for choice in introductions:
                self.assertIn(card["names"]["primary"], choice["label"])
                self.assertIn(card["mbti"], choice["label"])
                self.assertTrue(any(marker in choice["label"] for marker in ("来这里", "这七天", "这次", "想看看", "想试试", "参加")))
                self.assertIn("introductionMode", choice)
            validate_day1_script(create_snapshot(card["mbti"], card["id"]), flavor)

    def test_intro_validator_rejects_riddle_and_contextual_node_keeps_engine_ids(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        fallback = build_fallback_script_flavor("jiangmi")
        fallback["nodes"]["introductions"]["choices"][0]["label"] = "我叫姜米，ENFP，其他的先留个秘密，你猜我为什么来。"
        with self.assertRaisesRegex(ValueError, "工作或日常背景|谜语"):
            validate_day1_script(snapshot, fallback)
        valid_node = {"node": build_fallback_script_flavor("jiangmi")["nodes"]["team-up"]}
        normalized = validate_day1_node_script(snapshot, "team-up", valid_node)
        self.assertEqual([item["id"] for item in NODES["team-up"]["choices"]], [item["id"] for item in normalized["choices"]])
        installed = install_day1_node_script(snapshot, "team-up", valid_node, {"provider": "deepseek", "model": "test"})
        self.assertEqual("deepseek-contextual", installed["scriptFlavor"]["contextualNodes"]["team-up"]["source"])

    def test_contextual_node_prompt_contains_protagonist_memory_and_not_media_contract(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "team-up"
        snapshot["guidedTargetCharacterId"] = "shenmo"
        snapshot["echoMemories"].append({"id": "m1", "characterId": "shenmo", "summary": "沈墨记得姜米愿意先说清分工", "interpretation": "她的邀请很具体"})
        prompt = build_day1_node_messages(snapshot, "team-up")[1]["content"]
        self.assertIn('"primary": "姜米"', prompt)
        self.assertIn("沈墨记得姜米愿意先说清分工", prompt)
        self.assertNotIn("/media/video/", prompt)

    def test_perspective_character_cannot_chat_or_receive_own_letter(self):
        snapshot = create_snapshot("ESFJ", "sunnian")
        with self.assertRaisesRegex(ValueError, "不能和自己私聊"):
            commit_agent_turn(snapshot, "sunnian", "你好。", valid_turn(next(card for card in CHARACTER_CARDS if card["id"] == "sunnian")))
        snapshot["nodeId"] = "anonymous-letter"
        with self.assertRaisesRegex(ValueError, "不能把心动短信发给自己"):
            apply_choice(snapshot, "letter-sunnian", "sunnian")

    def test_cold_start_delta_is_clamped_to_one(self):
        for card in CHARACTER_CARDS:
            perspective_id = "jiangmi" if card["id"] != "jiangmi" else "shenmo"
            snapshot = create_snapshot("INFP", perspective_id)
            next_snapshot, _ = commit_agent_turn(snapshot, card["id"], "第一次具体表达。", valid_turn(card))
            for value in next_snapshot["relationships"][card["id"]].values():
                self.assertLessEqual(abs(value), 1)

    def test_old_snapshot_is_migrated_without_losing_scores(self):
        old = create_snapshot("ENFP")
        del old["relationships"]
        del old["eventLedger"]
        old["affection"]["shenmo"] = 4
        migrated = migrate_snapshot(old)
        self.assertEqual(4, migrated["relationships"]["shenmo"]["affection"])
        self.assertEqual([], migrated["eventLedger"])
        self.assertEqual(CONTENT_VERSION, migrated["contentVersion"])

    def test_selected_perspective_is_persisted_and_projected(self):
        snapshot = create_snapshot("ISTP", "chensu")
        self.assertEqual("chensu", snapshot["player"]["perspectiveCharacterId"])
        self.assertEqual("chensu", project_view(snapshot)["node"]["characterId"])

    def test_per_run_script_validator_preserves_ids_and_forbids_self_target(self):
        snapshot = create_snapshot("ESFJ", "jiangmi")
        fallback = build_fallback_script_flavor("jiangmi")
        validated = validate_day1_script(snapshot, fallback)
        self.assertEqual("deepseek", validated["source"])
        self.assertEqual(
            [choice["id"] for choice in NODES["icebreaker-choice"]["choices"]],
            [choice["id"] for choice in validated["nodes"]["icebreaker-choice"]["choices"]],
        )
        injected = build_fallback_script_flavor("jiangmi")
        injected["nodes"]["icebreaker-choice"]["choices"][0]["targetCharacterId"] = "jiangmi"
        with self.assertRaisesRegex(ValueError, "非主角"):
            validate_day1_script(snapshot, injected)
        installed = install_day1_script(snapshot, injected)
        self.assertEqual("fallback", installed["scriptFlavor"]["source"])
        self.assertNotIn("jiangmi", {choice["targetCharacterId"] for choice in installed["scriptFlavor"]["nodes"]["icebreaker-choice"]["choices"]})

    def test_script_validator_rejects_third_person_player_and_mechanical_key_copy(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        third_person = build_fallback_script_flavor("jiangmi")
        third_person["nodes"]["villa-arrival"]["action"] = "姜米拉开椅子，等你决定。"
        with self.assertRaisesRegex(ValueError, "第三人称"):
            validate_day1_script(snapshot, third_person)
        old_task = build_fallback_script_flavor("jiangmi")
        old_task["nodes"]["icebreaker-choice"]["choices"][0]["label"] = "先问第二把钥匙在哪里"
        with self.assertRaisesRegex(ValueError, "旧钥匙任务"):
            validate_day1_script(snapshot, old_task)

    def test_extract_json_accepts_one_object_before_provider_epilogue(self):
        self.assertEqual({"ok": True}, extract_json('{"ok": true}\n以上是完整 JSON。'))

    def test_first_chat_rejects_invented_elapsed_days_and_program_clues(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "guided-chat"
        card = next(card for card in CHARACTER_CARDS if card["id"] == "shenmo")
        turn = valid_turn(card)
        turn["dialogue"] = "我已经数了三天桌签，节目组说里面藏着一条线索。"
        with self.assertRaisesRegex(ValueError, "尚未发生"):
            validate_agent_turn(card, turn, snapshot)

    def test_first_chat_requires_direct_public_introduction(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "guided-chat"
        card = CHARACTER_CARD_MAP["jiangwan"]
        turn = valid_turn(card)
        turn["dialogue"] = "我更习惯听别人说。你先告诉我，最近最想留下什么声音？"
        with self.assertRaisesRegex(ValueError, "角色姓名"):
            validate_agent_turn(card, turn, snapshot, "你好。")

    def test_first_opener_cannot_invent_unknown_player_job(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        target = next(card for card in CHARACTER_CARDS if card["id"] == "shenmo")
        player = next(card for card in CHARACTER_CARDS if card["id"] == "jiangmi")
        payload = {
            "opening": "你好，我是沈墨。刚进小屋，我们先从简单的问题开始吧。",
            "stageDirection": "他朝你点了点头",
            "suggestions": ["你好，我叫姜米。", "我是做市场相关工作的。", "你为什么会来这里？"],
        }
        with self.assertRaisesRegex(ValueError, "编造了职业"):
            validate_chat_opening(target, snapshot, payload, player)

    def test_first_opener_stays_in_small_talk_instead_of_clue_hunting(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        target = next(card for card in CHARACTER_CARDS if card["id"] == "shenmo")
        player = next(card for card in CHARACTER_CARDS if card["id"] == "jiangmi")
        payload = {
            "opening": "你好，我是沈墨。刚进小屋，我们先从简单的问题开始吧。",
            "stageDirection": "他朝你点了点头",
            "suggestions": ["你好，我是姜米。", "你现在还紧张吗？", "你刚才是在找什么线索？"],
        }
        with self.assertRaisesRegex(ValueError, "任务或秘密"):
            validate_chat_opening(target, snapshot, payload, player)

    def test_validated_deepseek_cache_installs_without_runtime_generation(self):
        snapshot = create_snapshot("ESFJ", "jiangmi")
        fallback = build_fallback_script_flavor("jiangmi")
        package = {
            "schemaVersion": 1,
            "characterCardContentVersion": CARD_PACKAGE["contentVersion"],
            "generator": {"provider": "deepseek", "model": "test-model"},
            "generatedAt": "2026-08-24T10:00:00+08:00",
            "flavors": {"jiangmi": {"generatedAt": "2026-08-24T10:01:00+08:00", "payload": {"nodes": fallback["nodes"]}}},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "day1-script.json"
            path.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
            installed = install_cached_day1_script(snapshot, path)
        self.assertIsNotNone(installed)
        self.assertEqual("deepseek-cached", installed["scriptFlavor"]["source"])
        self.assertEqual("test-model", installed["scriptFlavor"]["generator"]["model"])
        self.assertEqual(CARD_PACKAGE["contentVersion"], installed["scriptFlavor"]["characterCardContentVersion"])

    def test_runtime_cache_contains_eight_valid_deepseek_flavors(self):
        package = json.loads((Path(__file__).resolve().parent.parent / "content" / "day1_script_flavors.v1.json").read_text(encoding="utf-8"))
        self.assertEqual({card["id"] for card in CHARACTER_CARDS}, set(package["flavors"]))
        for card in CHARACTER_CARDS:
            snapshot = create_snapshot(card["mbti"], card["id"])
            installed = install_cached_day1_script(snapshot)
            self.assertIsNotNone(installed)
            self.assertEqual("deepseek-cached", installed["scriptFlavor"]["source"])
            for choice in installed["scriptFlavor"]["nodes"]["introductions"]["choices"]:
                self.assertIn(card["names"]["primary"], choice["label"])
                self.assertIn(card["mbti"], choice["label"])
                self.assertNotIn("你猜", choice["label"])

    def test_all_live_fallback_introductions_are_spoken_character_lines(self):
        background_anchors = {
            "shenmo": ("投行",), "linyu": ("建筑",), "chengye": ("极限运动",),
            "guyan": ("游戏",), "jiangwan": ("心理咨询",), "jiangmi": ("声音", "录音", "故事"),
            "sunnian": ("插画",), "chensu": ("相机", "修"),
        }
        strategy_summaries = ("认真介绍姓名", "介绍完自己", "承认有点紧张", "选择一种方式")
        for card in CHARACTER_CARDS:
            snapshot = create_snapshot(card["mbti"], card["id"])
            snapshot["nodeId"] = "introductions"
            choices = project_view(snapshot)["node"]["choices"]
            self.assertEqual(3, len(choices))
            for choice in choices:
                label = choice["label"]
                self.assertIn(card["names"]["primary"], label)
                self.assertIn(card["mbti"], label)
                self.assertTrue(any(anchor in label for anchor in background_anchors[card["id"]]))
                self.assertTrue(any(marker in label for marker in ("来这里", "来参加", "这次来", "这七天", "我来参加")))
                self.assertFalse(any(summary in label for summary in strategy_summaries))

    def test_all_installed_cached_nodes_pass_contextual_surface_contract(self):
        package = json.loads((Path(__file__).resolve().parent.parent / "content" / "day1_script_flavors.v1.json").read_text(encoding="utf-8"))
        for card in CHARACTER_CARDS:
            snapshot = create_snapshot(card["mbti"], card["id"])
            installed = install_cached_day1_script(snapshot)
            self.assertIsNotNone(installed)
            self.assertEqual(
                {"cast-first-impressions", "icebreaker-choice"},
                set(installed["scriptFlavor"]["nodeSources"]),
            )
            for node_id, node in installed["scriptFlavor"]["nodes"].items():
                snapshot["nodeId"] = node_id
                validate_day1_node_script(snapshot, node_id, {"node": node})

    def test_contextual_transition_requires_ensemble_summary_and_future_hook(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "cast-first-impressions"
        fallback = build_fallback_script_flavor("jiangmi")["nodes"]["cast-first-impressions"]
        valid = validate_day1_node_script(snapshot, "cast-first-impressions", {"node": fallback})
        self.assertEqual(4, len(valid["textBeats"]))
        broken = json.loads(json.dumps(fallback, ensure_ascii=False))
        broken["title"] = "客厅重新安静下来"
        broken["text"] = "客厅里重新安静下来。你记住了几个人刚才说话的样子，准备选择一个人继续留意。"
        broken["textBeats"] = ["客厅里重新安静下来。", "你记住了几个人刚才说话的样子。", "现在准备选择一个人继续留意。"]
        broken["action"] = "镜头回到你停在膝上的手。"
        with self.assertRaisesRegex(ValueError, "其余七位"):
            validate_day1_node_script(snapshot, "cast-first-impressions", {"node": broken})

    def test_transition_surface_cannot_redirect_engine_route_or_patch(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "cast-first-impressions"
        payload = build_fallback_script_flavor("jiangmi")["nodes"]["cast-first-impressions"]
        payload = json.loads(json.dumps(payload, ensure_ascii=False))
        payload["choices"][0]["next"] = "callback"
        payload["choices"][0]["patch"] = {"flags.heat": 99}
        installed = install_day1_node_script(snapshot, "cast-first-impressions", {"node": payload})
        next_snapshot, receipt = apply_choice(installed, "impression-listener")
        self.assertEqual("icebreaker-choice", next_snapshot["nodeId"])
        self.assertEqual(0, next_snapshot["flags"]["heat"])
        self.assertEqual("impression.remember-listener", receipt["effectIntentId"])

    def test_contextual_icebreaker_requires_plain_completion_rules(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "icebreaker-choice"
        fallback = build_fallback_script_flavor("jiangmi")["nodes"]["icebreaker-choice"]
        self.assertEqual(4, len(validate_day1_node_script(snapshot, "icebreaker-choice", {"node": fallback})["textBeats"]))
        broken = json.loads(json.dumps(fallback, ensure_ascii=False))
        broken["text"] = "三张卡放在桌上。你选一张，再去找对应的人聊一会儿。"
        broken["textBeats"] = ["三张卡放在桌上。", "你选一张，再去找对应的人聊一会儿。"]
        with self.assertRaisesRegex(ValueError, "完成条件"):
            validate_day1_node_script(snapshot, "icebreaker-choice", {"node": broken})

    def test_transition_prompt_has_full_protagonist_and_ensemble_context(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "cast-first-impressions"
        prompt = build_day1_node_messages(snapshot, "cast-first-impressions")[1]["content"]
        self.assertIn('"protagonistCard"', prompt)
        self.assertIn('"otherCastCount": 7', prompt)
        self.assertIn('"primary": "姜米"', prompt)
        self.assertIn("其余七位嘉宾继续并完成自我介绍", prompt)
        self.assertNotIn("/media/video/", prompt)

    def test_introduction_rejects_invented_unknown_job(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        flavor = build_fallback_script_flavor("jiangmi")
        flavor["nodes"]["introductions"]["choices"][0]["label"] = (
            "大家好，我叫姜米，ENFP，平时喜欢录声音日记和写故事，我是声音设计师。"
            "这次来参加，是想看看安静时会不会也有人愿意留下。"
        )
        with self.assertRaisesRegex(ValueError, "未确认职业"):
            validate_day1_script(snapshot, {"nodes": flavor["nodes"]})

    def test_agent_first_chat_rejects_task_only_participation_reason(self):
        snapshot = create_snapshot("ESFJ", "sunnian")
        snapshot["nodeId"] = "guided-chat"
        card = CHARACTER_CARD_MAP["chensu"]
        turn = valid_turn(card)
        turn["dialogue"] = (
            "你好，我叫陈叙，ISTP，平时喜欢修旧相机。"
            "这次来这里主要想修好一台旧相机，顺便认识大家。你刚才说有点生疏，我也一样。"
        )
        with self.assertRaisesRegex(ValueError, "人物任务"):
            validate_agent_turn(card, turn, snapshot, "你好，我是苏念。")

    def test_agent_mainline_accepts_clear_action_with_natural_word_order(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "guided-chat"
        card = CHARACTER_CARD_MAP["sunnian"]
        turn = valid_turn(card)
        turn["suggestions"] = [
            {"type": "followup", "text": "你刚才说整理房间会放松，这个习惯是一直都有的吗？"},
            {"type": "mainline", "text": "要不要一起去厨房看看，今晚我们能准备什么？"},
            {"type": "deeper", "text": "别人第一次见你时，最容易误会你的哪一点？"},
        ]
        validated = validate_agent_turn(card, turn, snapshot, "刚进客厅还有点生疏。")
        self.assertEqual("mainline-gradient", validated["suggestions"][1]["style"])

    def test_agent_suggestion_cannot_turn_future_interest_into_present_fact(self):
        snapshot = create_snapshot("ESFJ", "sunnian")
        snapshot["nodeId"] = "guided-chat"
        card = CHARACTER_CARD_MAP["chensu"]
        turn = valid_turn(card)
        turn["suggestions"] = [
            {"type": "followup", "text": "你刚才说修东西会放松，是一直都有的习惯吗？"},
            {"type": "mainline", "text": "要不要一起去厨房准备晚餐，我们先商量分工？"},
            {"type": "deeper", "text": "你带的那台旧相机，最想拍下谁？"},
        ]
        with self.assertRaisesRegex(ValueError, "已发生事实"):
            validate_agent_turn(card, turn, snapshot, "你好，我是苏念。")

    def test_agent_prompt_knows_first_meeting_and_reopening(self):
        snapshot = create_snapshot("INFP", "jiangmi")
        card = next(card for card in CHARACTER_CARDS if card["id"] == "shenmo")
        first_prompt = build_agent_messages(card, snapshot, "你好")[1]["content"]
        self.assertIn('"isFirstConversation": true', first_prompt)
        self.assertIn('"requiredOpeningPrefix": "我叫沈墨，INTJ，在投行做VP。"', first_prompt)
        opening = fallback_chat_opening(card, snapshot)
        self.assertIn("沈墨", opening["opening"])
        self.assertEqual("first-meeting", validate_chat_opening(card, snapshot, opening)["mode"])
        snapshot, _ = commit_agent_turn(snapshot, "shenmo", "你好，我叫姜米。", valid_turn(card))
        reopened = fallback_chat_opening(card, snapshot)
        self.assertEqual("reopening", reopened["mode"])
        self.assertIn("上次", reopened["opening"])

    def test_agent_turn_returns_typed_suggestions_and_legacy_projection(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "guided-chat"
        card = CHARACTER_CARD_MAP["shenmo"]
        turn = valid_turn(card)
        turn["suggestions"] = [
            {"type": "followup", "text": "你刚才说会先想清楚，哪一步最难开口？"},
            {"type": "mainline", "text": "沈墨，要不要和我一起准备晚餐？我们先商量分工。"},
            {"type": "deeper", "text": "如果没有镜头，你通常怎样让一个人知道你在意？"},
        ]
        validated = validate_agent_turn(card, turn, snapshot, "我也会先想清楚。")
        self.assertEqual(["followup", "mainline", "deeper"], [item["type"] for item in validated["suggestions"]])
        self.assertEqual("mainline-gradient", validated["suggestions"][1]["style"])
        self.assertEqual([item["text"] for item in validated["suggestions"]], validated["suggestedPrompts"])
        prompt = build_agent_messages(card, snapshot, "我也会先想清楚。", CHARACTER_CARD_MAP["jiangmi"])[1]["content"]
        self.assertIn('"playerVoiceForSuggestions"', prompt)
        self.assertIn('"type": "mainline"', prompt)

    def test_agent_mainline_suggestion_must_return_to_current_goal(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "guided-chat"
        card = CHARACTER_CARD_MAP["shenmo"]
        turn = valid_turn(card)
        turn["suggestions"] = [
            {"type": "followup", "text": "你刚才停了一下，是哪句话还没说完？"},
            {"type": "mainline", "text": "我们以后慢慢聊。"},
            {"type": "deeper", "text": "你平时怎样确认自己真的在意一个人？"},
        ]
        with self.assertRaisesRegex(ValueError, "当前剧情目标"):
            validate_agent_turn(card, turn, snapshot, "你好。")

    def test_agent_followup_must_connect_to_last_exchange(self):
        snapshot = create_snapshot("ENFP", "jiangmi")
        snapshot["nodeId"] = "guided-chat"
        card = CHARACTER_CARD_MAP["shenmo"]
        turn = valid_turn(card)
        turn["suggestions"] = [
            {"type": "followup", "text": "你平时喜欢什么颜色？"},
            {"type": "mainline", "text": "要不要和我一起准备晚餐？我们可以先商量分工。"},
            {"type": "deeper", "text": "你遇到分歧时通常会先做什么？"},
        ]
        with self.assertRaisesRegex(ValueError, "没有承接"):
            validate_agent_turn(card, turn, snapshot, "我会先把分工写下来。")

    def test_female_fallback_opening_uses_card_pronoun_and_hides_unknown_job(self):
        snapshot = create_snapshot("INTJ", "shenmo")
        card = next(card for card in CHARACTER_CARDS if card["id"] == "jiangmi")
        opening = fallback_chat_opening(card, snapshot)
        self.assertTrue(opening["stageDirection"].startswith("她"))
        self.assertNotIn("待剧情", opening["opening"])


if __name__ == "__main__":
    unittest.main()
