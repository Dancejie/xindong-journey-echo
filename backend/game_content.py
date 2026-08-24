"""EchoCore-compatible story state and validated DeepSeek Agent commits."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
RELATIONSHIP_AXES = ("trust", "affection", "respect", "fear", "debt", "attraction", "resentment")
ATTITUDES = {"warm", "curious", "guarded", "challenging", "vulnerable", "softened", "uncertain", "honest", "moved", "careful", "steady", "boundary"}


def _load_json(name: str) -> dict[str, Any]:
    with (ROOT / "content" / name).open(encoding="utf-8") as source:
        return json.load(source)


CARD_PACKAGE = _load_json("character_cards.v2.json")
PLAYER_GROUPS: dict[str, list[str]] = CARD_PACKAGE["playerGroups"]
CHARACTER_CARDS: list[dict[str, Any]] = CARD_PACKAGE["cards"]
CHARACTER_CARD_MAP = {card["id"]: card for card in CHARACTER_CARDS}


def _public_character(card: dict[str, Any]) -> dict[str, Any]:
    psychology, voice = card["psychology"], card["voice"]
    return {
        "id": card["id"], "name": card["names"]["primary"], "mbti": card["mbti"],
        "tagline": card["tagline"], "accent": card["accent"], "portrait": card["portrait"],
        "video": card["video"], "publicMask": "、".join(psychology["publicMask"]),
        "privateFear": psychology["fears"][0], "memorySeed": card["drives"]["stakes"],
        "voice": f"{voice['register']}；{voice['sentenceShape']}",
        "boundary": "；".join(psychology["boundaries"]),
        "quickPrompts": [shot["player"] for shot in card["fewShots"]],
        "independentInterest": card["drives"]["independentInterest"],
        "eventLabel": card["eventPolicy"]["label"],
    }


CHARACTERS = [_public_character(card) for card in CHARACTER_CARDS]
CHARACTER_MAP = {character["id"]: character for character in CHARACTERS}

NODES: dict[str, dict[str, Any]] = {
    "arrival": {
        "chapter": "DAY 1 · 入住任务", "eyebrow": "心动小屋 / 18:47",
        "title": "八个人，四张双人任务卡", "speaker": "节目组",
        "text": "21:00 前，你必须和一位嘉宾找到藏在小屋里的第二把钥匙。第一把钥匙就在桌上，但拿起它的人会失去优先选人权。",
        "cinematic": "/media/video/E01-arrival-reveal.mp4",
        "choices": [
            {"id": "arrive-take-key", "label": "直接拿起第一把钥匙", "hint": "获得线索，但把优先选人权让给别人", "next": "first-look", "patch": {"flags.courage": 2, "flags.priorityChoice": -1}},
            {"id": "arrive-ask-rule", "label": "先问：第二把钥匙为什么存在？", "hint": "保留选择权，公开质疑任务前提", "next": "first-look", "patch": {"flags.clarity": 2}},
            {"id": "arrive-watch-hands", "label": "不看表情，只看谁先碰线索", "hint": "获得一条观察优势", "next": "first-look", "patch": {"flags.observation": 2}}
        ]
    },
    "first-look": {
        "chapter": "DAY 1 · 第一轮结盟", "eyebrow": "露台晚宴 / 19:12",
        "title": "姜米拉开椅子，桌下压着半张地图", "speaker": "姜米", "characterId": "jiangmi",
        "text": "“地图只剩一半，另一半在某个人的随身物里。”她没有把椅子推到底，“你想赢任务，还是想借任务看清一个人？”",
        "choices": [
            {"id": "first-win", "label": "“先赢。答案可以在路上变。”", "hint": "确立行动目标：拿到第二把钥匙", "next": "private-window", "patch": {"flags.taskFocus": 2}},
            {"id": "first-person", "label": "“先看清人，输一次也可以。”", "hint": "确立关系目标：完成一次真实交换", "next": "private-window", "patch": {"flags.relationshipFocus": 2}},
            {"id": "first-both", "label": "“我要知道谁愿意和我一起承担输。”", "hint": "确立共同责任目标", "next": "private-window", "patch": {"flags.reciprocity": 2}}
        ]
    },
    "private-window": {
        "chapter": "DAY 1 · 线索私聊", "eyebrow": "钥匙倒计时 / 20:06",
        "title": "第二把钥匙藏在一个人的真实选择里", "speaker": "节目提示",
        "text": "进入任意嘉宾的 1 对 1 房间。每个人掌握不同物证，也有不愿被节目利用的底线。只有当对方主动提出专属事件，线索才会进入正片。",
        "requiresMemory": True, "requiresEvent": True,
        "choices": [{"id": "continue-event", "label": "带着被激活的事件返回正片", "hint": "专属事件将决定第二把钥匙如何出现", "next": "event-reveal", "patch": {"flags.eventLinked": 1}}]
    },
    "event-reveal": {
        "chapter": "DAY 1 · 专属事件", "eyebrow": "钥匙倒计时 / 20:41",
        "title": "你们的对话改变了任务现场", "speaker": "回声",
        "text": "这不是好感提示。对方刚才作出的判断，已经让一个物件、一条线索或一次邀约进入现实。",
        "choices": [
            {"id": "carry-event", "label": "接受线索，也接受它的边界", "hint": "把事件物证带到匿名信环节", "next": "anonymous-letter", "patch": {"flags.acceptedEvent": 1}},
            {"id": "question-event", "label": "保留线索，不替对方定义意义", "hint": "不抢夺解释权", "next": "anonymous-letter", "patch": {"flags.clarity": 1}}
        ]
    },
    "anonymous-letter": {
        "chapter": "DAY 1 · 匿名信", "eyebrow": "心动信箱 / 22:30",
        "title": "第二把钥匙打开的，不只是信箱", "speaker": "旁白",
        "text": "你只能把第一封信交给一个人。被激活的专属事件和那个人记住的事实，会改变明早发生的事。",
        "cinematic": "/media/video/E01-anonymous-letter.mp4", "characterChoice": True, "choices": []
    },
    "callback": {
        "chapter": "DAY 2 · 事件回声", "eyebrow": "清晨海边 / 07:18",
        "title": "昨夜的判断，变成了今天的行动", "speaker": "回声",
        "text": "关系没有被一次选择决定，但一条被记住的事实已经改变了今天的安排。",
        "isEnding": True, "choices": []
    }
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def player_group(mbti: str) -> str:
    return next((group for group, types in PLAYER_GROUPS.items() if mbti in types), "diplomats")


def _empty_axes() -> dict[str, int]:
    return {axis: 0 for axis in RELATIONSHIP_AXES}


def create_snapshot(user_mbti: str = "INFP") -> dict[str, Any]:
    relationships = {character["id"]: _empty_axes() for character in CHARACTERS}
    flags = {key: 0 for key in ("heat", "clarity", "publicImpression", "courage", "priorityChoice", "observation", "taskFocus", "relationshipFocus", "reciprocity", "eventLinked", "acceptedEvent")}
    return {
        "runId": str(uuid4()), "contentVersion": "2.0.0", "revision": 0,
        "player": {"mbti": user_mbti, "group": player_group(user_mbti), "displayName": "你"},
        "nodeId": "arrival", "flags": flags, "relationships": relationships,
        "affection": {cid: 0 for cid in relationships}, "trust": {cid: 0 for cid in relationships},
        "attitudes": {cid: "curious" for cid in relationships}, "beliefs": [],
        "echoMemories": [], "eventLedger": [], "choiceHistory": [],
        "focusCharacterId": None, "activeEventId": None, "letterRecipientId": None,
        "cinematicReceipt": None, "createdAt": utc_now(), "updatedAt": utc_now()
    }


def migrate_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not snapshot:
        return None
    state = deepcopy(snapshot)
    state.setdefault("relationships", {})
    for character in CHARACTERS:
        cid = character["id"]
        state["relationships"].setdefault(cid, _empty_axes())
        for axis in RELATIONSHIP_AXES:
            state["relationships"][cid].setdefault(axis, 0)
        state["relationships"][cid]["affection"] = int(state.get("affection", {}).get(cid, state["relationships"][cid]["affection"]))
        state["relationships"][cid]["trust"] = int(state.get("trust", {}).get(cid, state["relationships"][cid]["trust"]))
    state["affection"] = {cid: axes["affection"] for cid, axes in state["relationships"].items()}
    state["trust"] = {cid: axes["trust"] for cid, axes in state["relationships"].items()}
    state.setdefault("attitudes", {character["id"]: "curious" for character in CHARACTERS})
    state.setdefault("beliefs", []); state.setdefault("eventLedger", []); state.setdefault("activeEventId", None)
    state.setdefault("flags", {})
    defaults = create_snapshot(state.get("player", {}).get("mbti", "INFP"))
    for key in defaults["flags"]:
        state["flags"].setdefault(key, 0)
    state.setdefault("player", {}).setdefault("group", player_group(state.get("player", {}).get("mbti", "INFP")))
    state["contentVersion"] = "2.0.0"
    return state


def apply_choice(snapshot: dict[str, Any], choice_id: str, character_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    state = migrate_snapshot(snapshot); assert state is not None
    node = NODES[state["nodeId"]]
    if node.get("requiresMemory") and not state["echoMemories"]:
        raise ValueError("先和一位嘉宾完成一次 1 对 1 交流。")
    if node.get("requiresEvent") and not state.get("activeEventId"):
        raise ValueError("对话还没有激活具体事件。继续交流，让对方作出一个会改变现场的决定。")
    if node.get("characterChoice"):
        if character_id not in CHARACTER_MAP:
            raise ValueError("请选择一位收信人。")
        state["letterRecipientId"] = character_id; state["focusCharacterId"] = character_id
        patch: dict[str, Any] = {"letterRecipientId": character_id}; next_node = "callback"; choice_id = f"letter-{character_id}"
    else:
        choice = next((item for item in node["choices"] if item["id"] == choice_id), None)
        if not choice:
            raise ValueError("这个选择已不在当前窗口。")
        patch = choice.get("patch", {}); next_node = choice["next"]
        for path, value in patch.items():
            if path.startswith("flags."):
                key = path.split(".", 1)[1]; state["flags"][key] = int(state["flags"].get(key, 0)) + int(value)
    receipt = {"id": str(uuid4()), "kind": "choice", "choiceId": choice_id, "patch": patch, "committedAt": utc_now()}
    state["choiceHistory"].append(receipt); state["nodeId"] = next_node; state["revision"] += 1; state["updatedAt"] = utc_now()
    state["cinematicReceipt"] = {"src": NODES[next_node].get("cinematic"), "afterRevision": state["revision"]} if NODES[next_node].get("cinematic") else None
    return state, receipt


def validate_agent_turn(card: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    dialogue = str(payload.get("dialogue") or "").strip()
    if not 8 <= len(dialogue) <= 240:
        raise ValueError("DeepSeek 角色台词长度不符合合同")
    attitude = str(payload.get("attitude") or "").strip()
    if attitude not in ATTITUDES:
        raise ValueError("DeepSeek 返回了未允许的角色态度")
    intent_id = str(payload.get("intentId") or "").strip()
    if intent_id not in card["agentPolicy"]["allowedIntentIds"]:
        raise ValueError("DeepSeek 返回了未允许的角色意图")
    raw_delta, bounds, delta = payload.get("relationshipDelta") or {}, card["agentPolicy"]["deltaBounds"], {}
    for axis in RELATIONSHIP_AXES:
        try: value = int(raw_delta.get(axis, 0))
        except (TypeError, ValueError): value = 0
        low, high = bounds[axis]; delta[axis] = max(int(low), min(int(high), value))
    if intent_id == "boundary":
        delta["affection"] = min(0, delta["affection"]); delta["attraction"] = min(0, delta["attraction"])
    event_id = payload.get("proposedEventId")
    if event_id not in [None, "", *card["agentPolicy"]["allowedEventIds"]]: event_id = None
    memory = payload.get("memory") or {}; kind = str(memory.get("kind") or "episodic")
    if kind not in {"episodic", "promise", "preference", "semantic"}: kind = "episodic"
    try: salience = int(memory.get("salience", 50) or 50)
    except (TypeError, ValueError): salience = 50
    try: valence = int(memory.get("emotionalValence", 0) or 0)
    except (TypeError, ValueError): valence = 0
    return {
        "dialogue": dialogue, "stageDirection": str(payload.get("stageDirection") or "").strip()[:100],
        "attitude": attitude, "intentId": intent_id,
        "publicReason": str(payload.get("publicReason") or "关系判断已更新").strip()[:100],
        "relationshipDelta": delta,
        "memory": {"kind": kind, "summary": str(memory.get("summary") or "这次交流被记住了").strip()[:120], "interpretation": str(memory.get("interpretation") or "仍需后续验证").strip()[:160], "salience": max(0, min(100, salience)), "emotionalValence": max(-100, min(100, valence))},
        "proposedEventId": event_id or None,
    }


def commit_agent_turn(snapshot: dict[str, Any], character_id: str, player_text: str, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if character_id not in CHARACTER_CARD_MAP: raise ValueError("这位嘉宾不在心动小屋。")
    state = migrate_snapshot(snapshot); assert state is not None
    card, turn, axes = CHARACTER_CARD_MAP[character_id], validate_agent_turn(CHARACTER_CARD_MAP[character_id], payload), state["relationships"][character_id]
    committed_delta: dict[str, int] = {}
    for axis, delta in turn["relationshipDelta"].items():
        before = int(axes[axis]); axes[axis] = max(-100, min(100, before + delta)); committed_delta[axis] = axes[axis] - before
    state["affection"][character_id] = axes["affection"]; state["trust"][character_id] = axes["trust"]; state["attitudes"][character_id] = turn["attitude"]
    turn_count = 1 + sum(1 for item in state["echoMemories"] if item.get("characterId") == character_id)
    policy = card["eventPolicy"]; existing = {item["eventId"] for item in state["eventLedger"]}; activated_event = None
    meets_axes = all(axes.get(axis, 0) >= threshold for axis, threshold in policy["minAxes"].items())
    if turn["proposedEventId"] == policy["eventId"] and turn_count >= policy["minTurns"] and meets_axes and policy["eventId"] not in existing:
        activated_event = {"id": str(uuid4()), "eventId": policy["eventId"], "characterId": character_id, "label": policy["label"], "text": policy["activationText"], "sourceIntentId": turn["intentId"], "activatedAt": utc_now()}
        state["eventLedger"].append(activated_event); state["activeEventId"] = policy["eventId"]
    memory_id = str(uuid4())
    memory = {
        "id": memory_id, "ownerId": character_id, "characterId": character_id, "branchId": "main", "scope": "relationship",
        "kind": turn["memory"]["kind"], "rawQuote": player_text[:240], "playerText": player_text[:240],
        "summary": turn["memory"]["summary"], "interpretation": turn["memory"]["interpretation"], "salience": turn["memory"]["salience"], "emotionalValence": turn["memory"]["emotionalValence"],
        "agentReply": turn["dialogue"], "stageDirection": turn["stageDirection"], "attitude": turn["attitude"], "intentId": turn["intentId"],
        "relationshipDelta": committed_delta, "affectionDelta": committed_delta["affection"], "trustDelta": committed_delta["trust"],
        "createdAt": utc_now(), "callbackEligible": True, "callbackAfterEventIds": [policy["eventId"]] if activated_event else []
    }
    state["echoMemories"].append(memory); state["focusCharacterId"] = character_id; state["revision"] += 1; state["updatedAt"] = utc_now()
    receipt = {"id": memory_id, "kind": "agent-turn", "intentId": turn["intentId"], "attitude": turn["attitude"], "publicReason": turn["publicReason"], "patch": {f"relationships.{character_id}.{axis}": delta for axis, delta in committed_delta.items() if delta}, "eventActivation": activated_event, "committedAt": memory["createdAt"]}
    return state, receipt


def project_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    state = migrate_snapshot(snapshot); assert state is not None
    node = deepcopy(NODES[state["nodeId"]])
    active_event = next((item for item in reversed(state["eventLedger"]) if item["eventId"] == state.get("activeEventId")), None)
    if state["nodeId"] == "private-window" and active_event:
        node["title"], node["text"] = f"已激活：{active_event['label']}", active_event["text"]
    if state["nodeId"] == "event-reveal" and active_event:
        character = CHARACTER_MAP[active_event["characterId"]]; node.update({"speaker": character["name"], "characterId": character["id"], "title": active_event["label"], "text": active_event["text"]})
    if node.get("characterChoice"):
        node["choices"] = [{"id": f"letter-{c['id']}", "characterId": c["id"], "label": f"写给 {c['name']}", "hint": f"{c['mbti']} · 当前态度：{state['attitudes'].get(c['id'], 'curious')}"} for c in CHARACTERS]
    if node.get("isEnding"):
        cid = state.get("letterRecipientId") or state.get("focusCharacterId"); character = CHARACTER_MAP.get(cid or "")
        memories = [item for item in state["echoMemories"] if item.get("characterId") == cid]
        event = next((item for item in reversed(state["eventLedger"]) if item.get("characterId") == cid), active_event)
        if character:
            node.update({"speaker": character["name"], "characterId": cid})
            if memories and event:
                node["title"] = f"{event['label']}没有停在昨夜"; node["text"] = f"{character['name']}按昨夜记住的“{memories[-1]['summary']}”作出了今天的行动。{event['text']}"
            elif memories: node["text"] = f"{character['name']}没有复述你的原话，只按记忆中的判断为你留出了一个新的选择。"
    return {"snapshot": state, "node": node, "characters": CHARACTERS}
