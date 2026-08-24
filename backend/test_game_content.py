import unittest

from backend.game_content import (
    CHARACTER_CARDS,
    RELATIONSHIP_AXES,
    apply_choice,
    commit_agent_turn,
    create_snapshot,
    migrate_snapshot,
)


def valid_turn(card):
    return {
        "dialogue": "我先把这句话当作一次具体选择记住。你愿意告诉我，你希望下一步真正发生什么吗？",
        "stageDirection": "他把线索推到两人中间",
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

    def test_deepseek_delta_is_bounded_by_each_card(self):
        for card in CHARACTER_CARDS:
            snapshot = create_snapshot("INFP")
            turn = valid_turn(card)
            next_snapshot, _ = commit_agent_turn(snapshot, card["id"], "这是一次具体表达。", turn)
            for axis in RELATIONSHIP_AXES:
                self.assertLessEqual(next_snapshot["relationships"][card["id"]][axis], card["agentPolicy"]["deltaBounds"][axis][1])

    def test_event_changes_story_node(self):
        card = CHARACTER_CARDS[0]
        snapshot = create_snapshot("INFP")
        snapshot, _ = apply_choice(snapshot, "arrive-ask-rule")
        snapshot, _ = apply_choice(snapshot, "first-person")
        snapshot, receipt = commit_agent_turn(snapshot, card["id"], "我愿意尊重你的停顿，也想一起确认线索。", valid_turn(card))
        self.assertIsNotNone(receipt["eventActivation"])
        snapshot, _ = apply_choice(snapshot, "continue-event")
        self.assertEqual("event-reveal", snapshot["nodeId"])

    def test_old_snapshot_is_migrated_without_losing_scores(self):
        old = create_snapshot("ENFP")
        del old["relationships"]
        del old["eventLedger"]
        old["affection"]["shenmo"] = 4
        migrated = migrate_snapshot(old)
        self.assertEqual(4, migrated["relationships"]["shenmo"]["affection"])
        self.assertEqual([], migrated["eventLedger"])
        self.assertEqual("2.0.0", migrated["contentVersion"])


if __name__ == "__main__":
    unittest.main()
