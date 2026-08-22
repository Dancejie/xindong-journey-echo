"""Authored content and deterministic state rules for Heart Journey episode one."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


CHARACTERS: list[dict[str, Any]] = [
    {
        "id": "shenmo", "name": "沈墨", "mbti": "INTJ", "tagline": "温柔的理想主义者",
        "accent": "#7187c9", "portrait": "/media/portraits/shenmo.jpg", "video": "/media/video/CHAR-shenmo-portrait.mp4",
        "publicMask": "礼貌、克制，习惯先观察再靠近。", "privateFear": "被热烈地选择，却从未真正被理解。",
        "memorySeed": "三年前他在一次告白中沉默太久，从此把想说的话先写在纸上。",
        "voice": "短句、留白、准确；不轻易说永远，但会记住细节。", "boundary": "不接受逼迫表态或用 MBTI 给他定罪。",
        "quickPrompts": ["你刚才为什么一直看海？", "如果只能说一句真话呢？", "我不会逼你现在回答。"]
    },
    {
        "id": "linyu", "name": "林屿", "mbti": "ISFJ", "tagline": "安静的洞察者",
        "accent": "#9d83bb", "portrait": "/media/portraits/linyu.jpg", "video": "/media/video/CHAR-linyu-portrait.mp4",
        "publicMask": "总能先发现谁需要一杯水。", "privateFear": "自己的照顾被当成理所当然。",
        "memorySeed": "他记得每个人第一次见面时喝的饮料，却很少有人问他想喝什么。",
        "voice": "温和、具体，先回应感受，再问一个小问题。", "boundary": "不会用照顾交换亲密，也拒绝道德绑架。",
        "quickPrompts": ["今天也有人照顾你吗？", "你记住了我的什么？", "这次换我听你说。"]
    },
    {
        "id": "chengye", "name": "程野", "mbti": "ESTP", "tagline": "机智的挑战者",
        "accent": "#506fb1", "portrait": "/media/portraits/chengye.jpg", "video": "/media/video/CHAR-chengye-portrait.mp4",
        "publicMask": "玩笑开得快，接住尴尬也很快。", "privateFear": "安静下来以后，没有人愿意留下。",
        "memorySeed": "他把一次失败的约会讲成笑话，只有自己知道那天等到了凌晨。",
        "voice": "轻快、直接、带一点反问；认真的话只说一遍。", "boundary": "可以被挑战，但不接受羞辱或拿真心当游戏筹码。",
        "quickPrompts": ["你是不是只会用玩笑躲开？", "敢不敢认真回答一次？", "我留下，不是因为无聊。"]
    },
    {
        "id": "guyan", "name": "顾言", "mbti": "INTP", "tagline": "天生的精准观察者",
        "accent": "#63a786", "portrait": "/media/portraits/guyan.jpg", "video": "/media/video/CHAR-guyan-portrait.mp4",
        "publicMask": "像在旁观实验，其实比谁都在意变量。", "privateFear": "表达不够及时，关系就已经被别人定义。",
        "memorySeed": "他保留着一张没有寄出的明信片，因为找不到足够准确的措辞。",
        "voice": "先拆解问题，再给笨拙但诚实的结论。", "boundary": "不会假装拥有不存在的情绪，也不接受替他解读。",
        "quickPrompts": ["别分析，先告诉我你的感觉。", "你觉得我们是什么变量？", "不准确也可以说。"]
    },
    {
        "id": "jiangwan", "name": "江晚", "mbti": "INFJ", "tagline": "安静的洞察者",
        "accent": "#9a7cca", "portrait": "/media/portraits/jiangwan.jpg", "video": "/media/video/CHAR-jiangwan-portrait.mp4",
        "publicMask": "不抢话，却常常看见没被说出口的那层。", "privateFear": "理解所有人，最后却没人看见她。",
        "memorySeed": "她曾替朋友写过很多告别信，自己的那封一直停在第一行。",
        "voice": "柔和、隐喻少而准；会追问话语背后的真正需要。", "boundary": "不做情绪读心，也不会替玩家承担所有决定。",
        "quickPrompts": ["你刚才是不是看懂我了？", "你希望谁先看见你？", "我想听你的第一行。"]
    },
    {
        "id": "jiangmi", "name": "姜米", "mbti": "ENFP", "tagline": "热烈的追梦者",
        "accent": "#e7758f", "portrait": "/media/portraits/jiangmi.jpg", "video": "/media/video/CHAR-jiangmi-portrait.mp4",
        "publicMask": "把每次相遇都当成会发光的新故事。", "privateFear": "热烈退潮后，自己只剩下吵闹。",
        "memorySeed": "她每次旅行都会给未来的自己录一段语音，唯独不敢回听上一段。",
        "voice": "有画面感、真诚、反应快；开心和失落都不藏太久。", "boundary": "不接受忽冷忽热的试探，也不会用活泼掩盖被冒犯。",
        "quickPrompts": ["你刚才的笑是真的吗？", "我们去做一件没计划的事？", "安静的时候我也想认识你。"]
    },
    {
        "id": "sunnian", "name": "苏念", "mbti": "ESFJ", "tagline": "温暖的守护者",
        "accent": "#d9904a", "portrait": "/media/portraits/sunnian.jpg", "video": "/media/video/CHAR-sunnian-portrait.mp4",
        "publicMask": "让所有人都舒服，是她进入陌生场合的本能。", "privateFear": "一旦停止有用，就失去被爱的资格。",
        "memorySeed": "她能办好所有人的生日，却连续两年假装忘了自己的。",
        "voice": "明亮、周到，会给具体回应；认真时会停止寒暄。", "boundary": "拒绝把她固定成照顾者，也不替任何人收拾情绪残局。",
        "quickPrompts": ["如果今天不用照顾任何人呢？", "你真正想收到什么？", "我记得你的需要。"]
    },
    {
        "id": "chensu", "name": "陈叙", "mbti": "ISTP", "tagline": "沉默的行动派",
        "accent": "#c98a56", "portrait": "/media/portraits/chensu.jpg", "video": "/media/video/CHAR-chensu-portrait.mp4",
        "publicMask": "话少，但总在事情失控前伸手。", "privateFear": "自己不擅长解释，最终被误会成不在乎。",
        "memorySeed": "他修好过前任留下的旧相机，却始终没有洗出最后一卷胶片。",
        "voice": "简短、朴素，不说漂亮话；用行动计划回应在意。", "boundary": "不接受逼问隐私或用沉默惩罚沉默。",
        "quickPrompts": ["你不说，但你会怎么做？", "那卷胶片为什么没洗？", "沉默也可以一起待着。"]
    },
]

CHARACTER_MAP = {character["id"]: character for character in CHARACTERS}

NODES: dict[str, dict[str, Any]] = {
    "arrival": {
        "chapter": "DAY 1 · 初见",
        "eyebrow": "心动小屋 / 18:47",
        "title": "海风替你推开了门",
        "speaker": "旁白",
        "text": "八个人已经到了。你会先让谁看见你，也会决定谁在今晚记住你。",
        "cinematic": "/media/video/E01-arrival-reveal.mp4",
        "choices": [
            {"id": "arrive-open", "label": "先走进人群", "hint": "热度上升，姜米和程野会先注意你", "next": "first-look", "patch": {"heat": 2, "affection.jiangmi": 2, "affection.chengye": 2}},
            {"id": "arrive-help", "label": "接过苏念手里的杯子", "hint": "温柔会被记住", "next": "first-look", "patch": {"clarity": 1, "affection.sunnian": 3, "affection.linyu": 1}},
            {"id": "arrive-observe", "label": "在门边看十秒", "hint": "你会读到两道没有移开的目光", "next": "first-look", "patch": {"clarity": 2, "affection.shenmo": 2, "affection.jiangwan": 2}}
        ]
    },
    "first-look": {
        "chapter": "DAY 1 · 第一印象",
        "eyebrow": "露台晚宴 / 19:12",
        "title": "有人把座位留在了身边",
        "speaker": "姜米",
        "characterId": "jiangmi",
        "text": "“我刚才猜你会坐最远的位置。”她把椅子向外拉了半步，“结果你比我想得更勇敢。”",
        "choices": [
            {"id": "answer-playful", "label": "“那你猜错的代价是什么？”", "hint": "把试探变成暧昧", "next": "private-window", "patch": {"heat": 2, "affection.jiangmi": 3}},
            {"id": "answer-honest", "label": "“其实我只是怕错过。”", "hint": "坦白会提高自我清晰度", "next": "private-window", "patch": {"clarity": 2, "affection.jiangwan": 1, "affection.linyu": 1}},
            {"id": "answer-return", "label": "“那你为什么给我留位置？”", "hint": "把镜头交回给她", "next": "private-window", "patch": {"clarity": 1, "affection.jiangmi": 2}}
        ]
    },
    "private-window": {
        "chapter": "DAY 1 · 私聊时间",
        "eyebrow": "自由交流 / 20:06",
        "title": "镜头之外，才是关系开始的地方",
        "speaker": "节目提示",
        "text": "现在可以进入任意嘉宾的 1 对 1 房间。你说过的话会进入对方的独立记忆，并在后续剧情里被重新提起。至少完成一次私聊，再继续。",
        "requiresMemory": True,
        "choices": [
            {"id": "continue-letter", "label": "写下匿名心动信", "hint": "把私聊留下的记忆带进正片", "next": "anonymous-letter", "patch": {"heat": 1}}
        ]
    },
    "anonymous-letter": {
        "chapter": "DAY 1 · 匿名信",
        "eyebrow": "心动信箱 / 22:30",
        "title": "没有署名，但每句话都有来处",
        "speaker": "旁白",
        "text": "你只能把第一封信交给一个人。今晚的私聊记忆，会改变对方读信后的回应。",
        "cinematic": "/media/video/E01-anonymous-letter.mp4",
        "characterChoice": True,
        "choices": []
    },
    "callback": {
        "chapter": "DAY 2 · 回声",
        "eyebrow": "清晨海边 / 07:18",
        "title": "有人记得你没有说完的那句话",
        "speaker": "回声",
        "text": "天亮以后，昨夜的选择没有消失。它已经变成一个人看向你的方式。",
        "isEnding": True,
        "choices": []
    }
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_snapshot(user_mbti: str = "INFP") -> dict[str, Any]:
    return {
        "runId": str(uuid4()), "contentVersion": "1.0.0", "revision": 0,
        "player": {"mbti": user_mbti, "displayName": "你"},
        "nodeId": "arrival", "flags": {"heat": 0, "clarity": 0, "publicImpression": 0},
        "affection": {character["id"]: 0 for character in CHARACTERS},
        "trust": {character["id"]: 0 for character in CHARACTERS},
        "focusCharacterId": None, "letterRecipientId": None,
        "echoMemories": [], "choiceHistory": [], "cinematicReceipt": None,
        "createdAt": utc_now(), "updatedAt": utc_now()
    }


def apply_choice(snapshot: dict[str, Any], choice_id: str, character_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    state = deepcopy(snapshot)
    node = NODES[state["nodeId"]]
    if node.get("requiresMemory") and not state["echoMemories"]:
        raise ValueError("先和一位嘉宾完成一次 1 对 1 私聊，关系才会进入正片。")
    patch: dict[str, Any] = {}
    next_node = None
    if node.get("characterChoice"):
        if character_id not in CHARACTER_MAP:
            raise ValueError("请选择一位收信人。")
        state["letterRecipientId"] = character_id
        state["focusCharacterId"] = character_id
        state["affection"][character_id] += 5
        patch = {f"affection.{character_id}": 5, "letterRecipientId": character_id}
        next_node = "callback"
        choice_id = f"letter-{character_id}"
    else:
        choice = next((item for item in node["choices"] if item["id"] == choice_id), None)
        if not choice:
            raise ValueError("这个选择已不在当前窗口。")
        next_node = choice["next"]
        patch = choice.get("patch", {})
        for key, value in patch.items():
            if key.startswith("affection."):
                state["affection"][key.split(".", 1)[1]] += value
            elif key in state["flags"]:
                state["flags"][key] += value
    receipt = {"id": str(uuid4()), "kind": "choice", "choiceId": choice_id, "patch": patch, "committedAt": utc_now()}
    state["choiceHistory"].append(receipt)
    state["nodeId"] = next_node
    state["revision"] += 1
    state["updatedAt"] = utc_now()
    state["cinematicReceipt"] = {"src": NODES[next_node].get("cinematic"), "afterRevision": state["revision"]} if NODES[next_node].get("cinematic") else None
    return state, receipt


def classify_agent_intent(message: str) -> tuple[str, int, int]:
    text = message.strip()
    if any(word in text for word in ["滚", "闭嘴", "废物", "必须喜欢", "逼你", "操控"]):
        return "companion.boundary", 0, 0
    if any(word in text for word in ["喜欢", "心动", "留下", "想你", "约会", "靠近"]):
        return "companion.flirt", 2, 1
    if any(word in text for word in ["为什么", "告诉我", "想听", "怎么想", "感觉", "秘密"]):
        return "companion.listen", 1, 2
    if any(word in text for word in ["敢不敢", "挑战", "认真", "别躲", "真话"]):
        return "companion.challenge", 1, 1
    return "companion.presence", 1, 1


def commit_agent_memory(snapshot: dict[str, Any], character_id: str, player_text: str, reply: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if character_id not in CHARACTER_MAP:
        raise ValueError("这位嘉宾不在心动小屋。")
    state = deepcopy(snapshot)
    intent, affection_delta, trust_delta = classify_agent_intent(player_text)
    if intent != "companion.boundary":
        state["affection"][character_id] += affection_delta
        state["trust"][character_id] += trust_delta
    memory = {
        "id": str(uuid4()), "characterId": character_id, "playerText": player_text[:240],
        "agentReply": reply[:480], "intentId": intent, "affectionDelta": affection_delta,
        "trustDelta": trust_delta, "createdAt": utc_now(), "callbackEligible": True
    }
    state["echoMemories"].append(memory)
    state["focusCharacterId"] = character_id
    state["revision"] += 1
    state["updatedAt"] = utc_now()
    receipt = {"id": memory["id"], "kind": "agent-memory", "intentId": intent, "patch": {f"affection.{character_id}": affection_delta, f"trust.{character_id}": trust_delta}, "committedAt": memory["createdAt"]}
    return state, receipt


def project_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    node = deepcopy(NODES[snapshot["nodeId"]])
    if node.get("characterChoice"):
        node["choices"] = [
            {"id": f"letter-{c['id']}", "characterId": c["id"], "label": f"写给 {c['name']}", "hint": f"{c['mbti']} · {c['tagline']}"}
            for c in CHARACTERS
        ]
    if node.get("isEnding"):
        character_id = snapshot.get("letterRecipientId") or snapshot.get("focusCharacterId")
        character = CHARACTER_MAP.get(character_id or "")
        memories = [m for m in snapshot["echoMemories"] if m["characterId"] == character_id]
        if character:
            node["speaker"] = character["name"]
            node["characterId"] = character_id
            if memories:
                echo = memories[-1]["playerText"][:32]
                node["text"] = f"“昨晚你说『{echo}』的时候，我其实记住了。” {character['name']}没有替你定义答案，只把并肩的位置留了出来。"
            else:
                node["text"] = f"{character['name']}在晨光里拆开信，抬头时没有躲开你的目光。关系没有被一次选择决定，但它已经开始。"
    return {"snapshot": snapshot, "node": node, "characters": CHARACTERS}
