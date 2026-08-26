from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, patch

from backend.app import _agent_turn
from backend.game_content import CHARACTER_CARD_MAP, CHARACTER_MAP, active_cast_ids, create_snapshot


def _runtime_turn(card: dict, dialogue: str, topic: str) -> dict:
    return {
        "dialogue": dialogue,
        "stageDirection": "他把手里的杯子放到一边，认真接住这句话",
        "attitude": "warm",
        "intentId": card["agentPolicy"]["allowedIntentIds"][0],
        "publicReason": "回应了当下的具体细节",
        "relationshipDelta": {axis: 0 for axis in card["agentPolicy"]["deltaBounds"]},
        "memory": {
            "kind": "episodic", "summary": topic, "interpretation": "这件事以后还可以继续了解",
            "salience": 55, "emotionalValence": 12,
        },
        "topicSummary": topic,
        "proposedEventId": None,
    }


class AgentRuntimeRewriteTests(unittest.IsolatedAsyncioTestCase):
    async def test_repeat_is_rewritten_locally_without_real_deepseek_call(self) -> None:
        snapshot = create_snapshot("ENFP", "jiangmi")
        target_id = next(
            character_id for character_id in active_cast_ids(snapshot)
            if character_id != "jiangmi" and CHARACTER_MAP[character_id]["gender"] == "男性"
        )
        card = CHARACTER_CARD_MAP[target_id]
        repeated = "刚才你说有点紧张，我也会紧张。要不要喝点什么？"
        snapshot["echoMemories"] = [
            {"characterId": target_id, "agentReply": repeated},
            {"characterId": target_id, "agentReply": "我把晚餐分工记下来了，不用再从头问一次。"},
        ]
        snapshot["agentConversations"][target_id] = {
            "turnCount": 2, "topicLedger": [{"topic": "刚进小屋为什么紧张"}],
        }
        first = _runtime_turn(card, repeated, "重复紧张话题")
        second = _runtime_turn(
            card,
            "我刚才也认错了两个人的名字，幸好你先笑了，不然我还得装镇定。晚餐分工我负责收尾，你挑想做的那一段。",
            "用认错名字化解紧张",
        )
        fake_llm = AsyncMock(side_effect=[
            json.dumps(first, ensure_ascii=False), json.dumps(second, ensure_ascii=False),
        ])
        with patch("backend.app._llm_text", fake_llm):
            result = await _agent_turn(CHARACTER_MAP[target_id], snapshot, "其实我现在还是有点紧张。")

        self.assertEqual(second["dialogue"], result["dialogue"])
        self.assertEqual(2, fake_llm.await_count)


if __name__ == "__main__":
    unittest.main()
