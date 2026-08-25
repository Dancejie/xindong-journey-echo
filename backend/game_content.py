"""EchoCore-compatible story state and validated DeepSeek Agent commits."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
RELATIONSHIP_AXES = ("trust", "affection", "respect", "fear", "debt", "attraction", "resentment")
ATTITUDES = {"warm", "curious", "guarded", "challenging", "vulnerable", "softened", "uncertain", "honest", "moved", "careful", "steady", "boundary"}
CONTENT_VERSION = "3.5.0-cast-impression-transition"
INTRODUCTION_MODES = {
    "intro-clear": "camera-full",
    "intro-question": "living-room-keepsake",
    "intro-honest": "contrast-full",
}
SUGGESTION_PRESENTATION = {
    "followup": {"style": "followup", "action": "send-message"},
    "mainline": {"style": "mainline-gradient", "action": "send-message"},
    "deeper": {"style": "deeper", "action": "prefill-message"},
}
MECHANICAL_COPY_TERMS = (
    "看清一个人", "赢任务", "观察还是相信", "先决定相信", "先决定观察", "说出自己的需要",
    "真正看见一个人", "行动目标", "关系目标", "共同信任目标", "建立信任", "确立关系",
    "推进剧情", "完成主线", "最具体的是哪一部分", "如果先不考虑节目镜头",
)

INTRODUCTION_FALLBACKS: dict[str, dict[str, tuple[str, str]]] = {
    "shenmo": {
        "intro-clear": ("大家好，我叫沈墨，29岁，在投行做VP，MBTI是INTJ。平时习惯先把问题想清楚；这次来参加，是想练习在答案还没出来时，也把真实感受说出来。", "镜头前把姓名、工作、性格和来意一次说清"),
        "intro-question": ("我是沈墨，投行VP，INTJ。我来这里想慢一点认识人，不急着给答案。你们第一天最怕别人误会自己哪一点？", "简短介绍后，问一个每个人都能回答的问题"),
        "intro-honest": ("我叫沈墨，29岁，在投行做VP，MBTI是INTJ。看起来可能有点难接近；其实我来参加，是想遇到一个不催我给答案、但愿意等我把话说完的人。", "说清公开信息，也承认冷静外表后的真实期待"),
    },
    "linyu": {
        "intro-clear": ("大家好，我叫林屿，27岁，是建筑工程师，MBTI是ISFJ。我来这里，是想少一点照顾所有人，也认识一个会问问我感受的人。", "姓名、工作和参加原因都说得清楚"),
        "intro-question": ("我是林屿，建筑工程师，ISFJ。我来参加，是想少替别人拿主意，也先问问自己想做什么。你们刚进门时，最希望别人帮你哪件小事？", "用一个生活化的问题让客厅自然接话"),
        "intro-honest": ("我叫林屿，27岁，做建筑，MBTI是ISFJ。大家常觉得我很会照顾人；但这次来这里，我也想知道，不主动递水时，会不会有人先问我渴不渴。", "不把体贴当完美人设，坦白自己也想被照顾"),
    },
    "chengye": {
        "intro-clear": ("大家好，我叫程野，26岁，经营一家极限运动品牌，MBTI是ESTP。我来参加，是想认真认识一个人，也认真完成一次说出口的约定。", "直接交代姓名、工作、性格和这次来意"),
        "intro-question": ("我是程野，做极限运动品牌，ESTP。我来这里想把这七天过得痛快，也把答应的事做完。你们最想和大家一起试哪件事？", "轻快开场，再抛出一个能聊到行动的问题"),
        "intro-honest": ("我叫程野，26岁，做极限运动品牌，MBTI是ESTP。看着像什么都敢冲；其实这次来参加，我更想试试遇到状况时不绕开，认真陪一个人把话说完。", "保留爽快，也说出不逃开的反差来意"),
    },
    "guyan": {
        "intro-clear": ("大家好，我叫顾言，25岁，做游戏策划，也接外包，MBTI是INTP。我来参加，是想试试不等到答案完美，也能和人诚实相处。", "信息说全，不把自我介绍讲成一道题"),
        "intro-question": ("我是顾言，做游戏策划和外包，INTP。我来这里想少分析一会儿，先认识真实的人。你们更怕第一天冷场，还是被问得太快？", "用一个好回答的二选一，让大家自然接话"),
        "intro-honest": ("我叫顾言，25岁，游戏策划，MBTI是INTP。我确实不太会寒暄；但我来参加，不是为了研究别人，是想练习答案不够漂亮时也把真话说出来。", "承认笨拙，但不把人当成待验证的问题"),
    },
    "jiangwan": {
        "intro-clear": ("大家好，我叫江晚，26岁，是心理咨询师，MBTI是INFJ。工作里常听别人说；这次来参加，我想少分析一点，也让大家认识工作之外的我。", "把姓名、职业、性格和参加原因温和地说清"),
        "intro-question": ("我是江晚，心理咨询师，INFJ。我来这里想多说一点自己的事。你们刚进客厅时，最想先找谁聊一句什么？", "短介绍后把选择还给大家，问题容易回答"),
        "intro-honest": ("我叫江晚，26岁，做心理咨询，MBTI是INFJ。大家可能先觉得我很会倾听；其实这次来这里，我也希望有人先问问我想要什么。", "不分析别人，先坦白自己也希望被询问"),
    },
    "jiangmi": {
        "intro-clear": ("大家好，我叫姜米，ENFP。平时喜欢录声音日记，也会把偶遇写成小故事。我来参加，是想知道两个人不说漂亮话，只一起吹吹海风，也会不会心动。", "轻快说清姓名、日常背景、性格和来意"),
        "intro-question": ("嗨，我是姜米，ENFP，爱录声音日记，也爱写小故事。我来这里想遇见一些值得记住的声音。你们刚进门先记住的是海浪、行李轮，还是谁的一声你好？", "用眼前的声音开场，让每个人都有话可接"),
        "intro-honest": ("我叫姜米，ENFP，平时会录声音日记、写小故事。我看起来很能热场；其实来参加，是想试试安静下来时，也有人愿意继续坐在我旁边。", "承认热闹外表后的期待，但不故作神秘"),
    },
    "sunnian": {
        "intro-clear": ("大家好，我叫苏念，25岁，是插画师，MBTI是ESFJ。我来参加，是想认真过好这七天，也让大家认识不只会照顾人的我。", "明亮、完整地交代自己和这次来意"),
        "intro-question": ("我是苏念，插画师，ESFJ。我来这里想少忙着照顾所有人，也试试被别人记住。你们第一天最想吃到哪道家常菜？", "从晚餐前最容易接住的小问题开始聊天"),
        "intro-honest": ("我叫苏念，25岁，画插画，MBTI是ESFJ。看起来我很会张罗；但这次来参加，我不想只做收尾的人，也想体验一次被人认真照顾。", "承认自己也有需要，不再只维持气氛"),
    },
    "chensu": {
        "intro-clear": ("大家好，我叫陈叙，27岁，平时喜欢修旧相机和坏掉的小东西，MBTI是ISTP。我来参加，是想练习把该说的话也说清楚。", "不虚构职业，只说确认过的兴趣与来意"),
        "intro-question": ("我是陈叙，ISTP，平时喜欢修旧相机。我来这里，想和人一起做点具体的事。你们这七天最想一起完成什么？", "话不多，但给大家一个具体好答的问题"),
        "intro-honest": ("我叫陈叙，27岁，MBTI是ISTP，平时会修旧相机。看着话少，不代表不想认识人；这次来参加，我想试试先把原因说出来，再低头做事。", "保留行动派的简短，也把沉默解释清楚"),
    },
}
INTRO_BACKGROUND_ANCHORS = {
    "shenmo": ("投行",), "linyu": ("建筑",), "chengye": ("极限运动", "品牌"),
    "guyan": ("游戏", "外包"), "jiangwan": ("心理咨询",),
    "jiangmi": ("声音", "录音", "故事"), "sunnian": ("插画",), "chensu": ("相机", "修"),
}
INTRO_REASON_ANCHORS = {
    "shenmo": ("感受", "慢一点", "认识", "真实"),
    "linyu": ("照顾", "感受", "被对待", "认识"),
    "chengye": ("认真", "认识", "约定", "陪一个人"),
    "guyan": ("诚实", "真话", "相处", "认识"),
    "jiangwan": ("自己", "被听见", "被理解", "认识"),
    "jiangmi": ("安静", "相遇", "心动", "故事"),
    "sunnian": ("被照顾", "被记住", "认识", "不只会照顾"),
    "chensu": ("说清楚", "解释", "认识", "相处"),
}

CAST_FIRST_IMPRESSION_FALLBACKS: dict[str, tuple[str, str]] = {
    "shenmo": (
        "我先记住沈墨。他介绍得很简洁，听别人说话时也没有抢着接话。",
        "晚餐分工时，我想看看他的克制会不会变成可靠的行动。",
    ),
    "linyu": (
        "我对林屿有点好奇。他把照顾别人说得自然，也承认自己不想总做收尾的人。",
        "之后一起做事时，我想看看有没有人会先顾到他的感受。",
    ),
    "chengye": (
        "我记住了程野。他接话很快，说到认真认识一个人时反而慢了下来。",
        "如果晚餐需要临时搭档，我想知道他会不会把玩笑后的话做到。",
    ),
    "guyan": (
        "我想再认识顾言。他承认自己不擅长寒暄，却没有拿分析代替真话。",
        "三分钟单聊时，我想听听他不准备标准答案会怎么说。",
    ),
    "jiangwan": (
        "我先记住江晚。她没有替任何人下结论，也清楚说了自己想被认识。",
        "今晚再聊时，我想把问题留给她，而不是只让她听别人说。",
    ),
    "jiangmi": (
        "我对姜米有点好奇。她把客厅带热了，也坦白自己安静下来时会更敏感。",
        "之后场面安静时，我想看看她会留下，还是先把气氛重新点亮。",
    ),
    "sunnian": (
        "我记住了苏念。她很会接住大家，也直接说不想只做照顾人的那一个。",
        "晚餐准备时，我想看看谁会主动把一件事从她手里接过去。",
    ),
    "chensu": (
        "我想再认识陈叙。他话不多，却把想练习说清楚这件事讲得很实在。",
        "三分钟单聊时，我想问一个具体问题，看看他会不会认真回答。",
    ),
}

STORY_OBJECTIVES = {
    "arrival-context": "选定你想怎样进入这段七天六夜的旅程",
    "villa-arrival": "走进酒店，用一个自然动作和八位嘉宾见面",
    "introductions": "在客厅完成一次姓名、公开背景、性格和来意都清楚的自我介绍",
    "cast-first-impressions": "听完其余七位嘉宾的介绍，留下一个以后可以被行动验证的第一印象",
    "icebreaker-choice": "选一位非主角嘉宾完成三分钟破冰，记住对方一件真实小事",
    "guided-chat": "先完成一次自然寒暄，再用一句可回答的话邀请对方一起准备晚餐",
    "team-up": "和破冰对象商量第一顿晚餐的具体分工",
    "anonymous-letter": "从三位非主角嘉宾中选择今晚最想继续认识的人发送匿名短信",
    "callback": "回收昨晚的选择，进入第二天",
}

DAY1_MEDIA_CONTRACT: dict[str, dict[str, Any]] = {
    "arrival-context": {"eventId": "day1.arrival-context", "assetId": "D1-A1-island-hotel-establish", "intent": "establish-island-journey"},
    "villa-arrival": {"eventId": "day1.villa-arrival", "assetId": "D1-A2-villa-entry", "intent": "enter-villa-and-meet-cast"},
    "introductions": {"eventId": "day1.introductions", "assetId": "D1-A3-cast-introductions", "intent": "camera-ready-self-introduction"},
    "cast-first-impressions": {
        "eventId": "day1.cast-first-impressions",
        "assetId": "D1-A3B-cast-first-impressions",
        "intent": "hear-full-cast-and-seed-first-impression",
    },
    "icebreaker-choice": {"eventId": "day1.icebreaker-choice", "assetId": "D1-A4-icebreaker-selection", "intent": "choose-first-small-talk"},
    "guided-chat": {"eventId": "day1.guided-chat", "assetId": "D1-A5-guided-smalltalk", "intent": "guided-one-to-one-smalltalk"},
    "team-up": {
        "eventId": "day1.team-up", "assetId": "D1-A6-first-dinner-team", "intent": "first-dinner-cooperation",
        "variantRouting": "participants", "variantAssetIds": {"shenmo": "D1-A6-first-dinner-team--shenmo"},
    },
    "anonymous-letter": {
        "eventId": "day1.anonymous-letter", "assetId": "D1-A7-heart-message", "intent": "send-anonymous-heart-message",
        "variantRouting": "perspective", "variantAssetIds": {"jiangmi": "D1-A7-heart-message--jiangmi"},
    },
    "callback": {"eventId": "day2.morning-callback", "assetId": "D2-A1-memory-callback", "intent": "recall-choice-next-morning"},
}


def _load_json(name: str) -> dict[str, Any]:
    with (ROOT / "content" / name).open(encoding="utf-8") as source:
        return json.load(source)


CARD_PACKAGE = _load_json("character_cards.v3.json")
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
    "arrival-context": {
        "chapter": "DAY 1 · 旅程开始", "eyebrow": "心动之旅 / 序章",
        "title": "七天六夜，从一句你好开始", "speaker": "节目旁白",
        "text": "八位嘉宾将在海岛酒店共同生活七天六夜。一起吃饭、出行、做游戏，也一起面对心动、犹豫和误会。靠近别人，也是在重新认识自己。",
        "action": "海面掠过傍晚的光，镜头缓缓靠近亮灯的海岛酒店。",
        "cinematic": "/media/video/D1-A1-island-hotel-establish.mp4",
        "mediaCue": "海岛酒店远景、车辆驶近，八位嘉宾尚未见面的旅程序章",
        "choices": [
            {"id": "context-meet", "intentId": "context.meet-people", "label": "先认真认识眼前的每一个人", "hint": "不急着贴标签，让相处给出答案", "next": "villa-arrival", "patch": {"flags.relationshipFocus": 1}},
            {"id": "context-live", "intentId": "context.share-life", "label": "从一起生活的小事慢慢靠近", "hint": "把衣食住行当成了解彼此的开始", "next": "villa-arrival", "patch": {"flags.reciprocity": 1}},
            {"id": "context-self", "intentId": "context.know-self", "label": "也想借这趟旅程重新认识自己", "hint": "允许心动，也允许改变原来的判断", "next": "villa-arrival", "patch": {"flags.clarity": 1}},
        ],
    },
    "villa-arrival": {
        "chapter": "DAY 1 · 抵达海岛", "eyebrow": "心动酒店 / 17:30",
        "title": "欢迎来到《心动之旅》", "speaker": "节目旁白",
        "text": "八位嘉宾将在海岛酒店共同生活七天六夜。从今天起，做饭、出行、游戏和每一次相处，都可能碰撞出意想不到的火花。",
        "action": "车辆停在酒店门前，八只行李箱陆续被搬下车。",
        "cinematic": "/media/video/E01-arrival-reveal.mp4",
        "mediaCue": "八位嘉宾先后抵达海岛酒店、搬运行李并第一次看见彼此",
        "gameBrief": {
            "name": "七天六夜，从一句你好开始",
            "format": "白天一起生活并完成节目组安排，晚上可以把一条心动短信发给当天最想继续认识的人。",
            "winCondition": "这里没有积分榜。旅程结束时，你可以走向一位还想继续了解的人，也可以带着更清楚的自己离开。",
            "strategyPrompt": "刚走进酒店，你准备先做什么？",
            "strategyOptions": ["先帮身边的人拿行李", "先向客厅里的大家打招呼", "先记住每个人的名字和位置"],
        },
        "choices": [
            {"id": "arrival-help-luggage", "intentId": "arrival.offer-help", "label": "接过身边的一只行李箱", "hint": "用一个自然的小动作打开第一句话", "next": "introductions", "patch": {"flags.courage": 1, "flags.publicImpression": 1}},
            {"id": "arrival-greet-room", "intentId": "arrival.greet-group", "label": "先走进客厅向大家问好", "hint": "让所有人先记住你的名字", "next": "introductions", "patch": {"flags.courage": 2}},
            {"id": "arrival-observe-names", "intentId": "arrival.observe", "label": "慢一步，先记住谁在做什么", "hint": "你会带着更多生活细节进入破冰", "next": "introductions", "patch": {"flags.observation": 2}},
        ],
    },
    "introductions": {
        "chapter": "DAY 1 · 初次见面", "eyebrow": "酒店客厅 / 18:05",
        "title": "八个名字，第一次被彼此叫出来", "speaker": "节目旁白",
        "text": "大家围着客厅坐下。节目组请每个人说说自己是谁、做什么工作，以及为什么愿意把七天时间交给一群陌生人。现在轮到你了。",
        "action": "镜头掠过围坐的嘉宾，最后停在你的座位前。",
        "mediaCue": "海岛别墅客厅内八位嘉宾围坐、轮流自然自我介绍",
        "choices": [
            {"id": "intro-clear", "intentId": "introduction.clear", "introductionMode": "camera-full", "label": "认真介绍姓名、工作和来意", "hint": "信息清楚，给别人一个容易接住的话题", "next": "cast-first-impressions", "patch": {"flags.clarity": 2}},
            {"id": "intro-question", "intentId": "introduction.invite", "introductionMode": "living-room-keepsake", "label": "介绍完自己，再把问题抛给大家", "hint": "主动制造一次轻松的来回", "next": "cast-first-impressions", "patch": {"flags.reciprocity": 2}},
            {"id": "intro-honest", "intentId": "introduction.honest", "introductionMode": "contrast-full", "label": "承认有点紧张，也说一句真心话", "hint": "不追求完美，先让人看见真实的一面", "next": "cast-first-impressions", "patch": {"flags.relationshipFocus": 2}},
        ],
    },
    "cast-first-impressions": {
        "chapter": "DAY 1 · 初见回声", "eyebrow": "酒店客厅 / 18:18",
        "title": "最后一个名字说完，客厅才真的安静下来", "speaker": "节目旁白",
        "text": "你说完后没有立刻起身。其余七位嘉宾继续介绍：有人把工作和来意讲得干脆，有人承认面对镜头会紧张，也有人把问题抛回给大家。最后一个名字落下时，你已经悄悄记住了一个人。这个第一印象，会在晚餐分工和今晚的短信里被重新验证。",
        "textBeats": [
            "你说完后没有立刻起身，其余七位嘉宾继续介绍自己。",
            "有人讲得干脆，有人承认紧张，也有人把问题重新抛回给大家。",
            "最后一个名字落下时，你已经悄悄记住了一个人。",
            "这个第一印象，会在晚餐分工和今晚的短信里被重新验证。",
        ],
        "action": "镜头依次切过其余七人的表情，最后回到你停在膝上的手。",
        "mediaCue": "主角听完其余七位嘉宾的自然自我介绍，目光在几位嘉宾之间停留并形成第一印象",
        "choices": [
            {
                "id": "impression-listener", "intentId": "impression.remember-listener",
                "impressionKind": "listening", "label": "先记住那个认真听完所有人介绍的人",
                "hint": "这份安静是真诚还是谨慎，要等下一次相处验证",
                "next": "icebreaker-choice", "patch": {"flags.observation": 1},
            },
            {
                "id": "impression-care", "intentId": "impression.notice-care",
                "impressionKind": "care", "label": "留意那个一直替别人把话接住的人",
                "hint": "照顾场面的人，也可能希望有人先问问他自己",
                "next": "icebreaker-choice", "patch": {"flags.reciprocity": 1},
            },
            {
                "id": "impression-contrast", "intentId": "impression.follow-contrast",
                "impressionKind": "contrast", "label": "记住那个第一眼和自我介绍最不一样的人",
                "hint": "先把反差留在心里，之后用行动而不是标签确认",
                "next": "icebreaker-choice", "patch": {"flags.relationshipFocus": 1},
            },
        ],
    },
    "icebreaker-choice": {
        "chapter": "DAY 1 · 破冰时刻", "eyebrow": "酒店公共区 / 18:25",
        "title": "三张场景卡，选一个人聊三分钟", "speaker": "节目组",
        "text": "桌上有三张卡，分别写着客厅、露台和行李区。每张卡都对应一位你还没单独聊过的嘉宾。选一张，就去那个地方找到卡片上的人，从刚才的自我介绍或眼前的小事聊起。三分钟后回到客厅，准确说出对方亲口告诉你的一件小事，对方点头或补充，就算完成。",
        "textBeats": [
            "桌上有三张卡：客厅、露台和行李区，每张都对应一位嘉宾。",
            "选一张，就去那个地方找到卡片上的人，聊够三分钟。",
            "可以从刚才的自我介绍问起，也可以从眼前正在做的小事开口。",
            "回来后说出对方亲口告诉你的一件小事；对方点头或补充，就算完成。",
        ],
        "action": "三张写着地点和嘉宾姓名的生活场景卡被翻到桌面中央。",
        "mediaCue": "嘉宾在客厅抽取生活场景卡并分散到厨房、露台和行李区破冰",
        "gameBrief": {
            "name": "三分钟，记住一件小事",
            "format": "三张卡分别写着一个地点和一位嘉宾。选卡后去对应地点，和那位嘉宾单独聊三分钟；卡片不是配对结果，也没有隐藏谜题。",
            "winCondition": "回到客厅后，说出对方亲口告诉你的一件真实小事。对方点头确认或主动补充，就算你认真听见了。",
            "strategyPrompt": "看清每张卡上的人和开场方式，再选你愿意真的聊三分钟的那一张。",
            "strategyOptions": ["问刚才自我介绍里没展开的一句", "从对方眼前正在做的小事开口", "先交换为什么来参加节目的真实原因"],
        },
        "choices": [
            {"id": "break-help", "intentId": "icebreaker.offer-help", "label": "去帮一位嘉宾整理手边的东西", "hint": "从共同做一件小事开始认识", "next": "guided-chat", "patch": {"flags.publicImpression": 1}},
            {"id": "break-introduce", "intentId": "icebreaker.exchange-names", "label": "走向一位嘉宾，先交换姓名", "hint": "从最普通的一声你好开始", "next": "guided-chat", "patch": {"flags.courage": 1}},
            {"id": "break-notice", "intentId": "icebreaker.notice-detail", "label": "问问一位嘉宾刚才在忙什么", "hint": "用你真正看到的细节打开话题", "next": "guided-chat", "patch": {"flags.observation": 1}},
        ],
    },
    "guided-chat": {
        "chapter": "DAY 1 · 第一次单独说话", "eyebrow": "破冰倒计时 / 18:31",
        "title": "先认识对方，再谈要不要同行", "speaker": "节目提示",
        "text": "你已经选好了这次破冰的对象。先从姓名、来到节目的原因或眼前的小事聊起；完成一次真实来回后，再决定怎样提出今晚的组队邀请。",
        "action": "对应嘉宾的头像亮起，正在等你开口。",
        "requiresGuidedInteraction": True,
        "mediaCue": "指定嘉宾在生活场景中停下动作，转身和玩家开始第一次单独交谈",
        "choices": [
            {"id": "chat-team-direct", "intentId": "team.invite-direct", "label": "直接邀请对方和你组队", "hint": "态度清楚，也给对方拒绝的空间", "next": "team-up", "patch": {"flags.taskFocus": 1}},
            {"id": "chat-team-together", "intentId": "team.decide-together", "label": "先问对方想做什么，再一起决定", "hint": "把分工变成一次共同选择", "next": "team-up", "patch": {"flags.reciprocity": 2}},
            {"id": "chat-team-light", "intentId": "team.keep-light", "label": "只约定完成今晚这一件事", "hint": "降低压力，给关系留下继续了解的空间", "next": "team-up", "patch": {"flags.clarity": 1}},
        ],
    },
    "team-up": {
        "chapter": "DAY 1 · 第一次组队", "eyebrow": "晚餐准备 / 19:10",
        "title": "第一顿晚餐，是第一次一起做事", "speaker": "节目旁白",
        "text": "今晚不比输赢。你和刚认识的搭档要在晚餐前完成一项生活分工。一起做事时的照顾、坚持和小摩擦，往往比自我介绍更接近真实。",
        "action": "厨房、采购桌和露台布置区同时亮起任务灯。",
        "mediaCue": "双人搭档在厨房备菜、整理餐桌或核对采购清单，其他嘉宾从旁经过互动",
        "gameBrief": {
            "name": "第一顿晚餐搭档",
            "format": "你和破冰对象从备菜、布置餐桌、核对饮品中选一项，在晚餐开始前共同完成。",
            "winCondition": "两个人都完成自己答应的部分，并在结束时说清下一次希望怎样合作，就算完成。",
            "strategyPrompt": "你准备怎样和搭档配合？",
            "strategyOptions": ["先分工，各自做好一半", "边做边商量，随时交换任务", "先承担麻烦的部分，再请对方补位"],
        },
        "choices": [
            {"id": "team-split", "intentId": "team.split-work", "label": "先把任务拆开，各自负责一半", "hint": "效率更高，也能看见彼此是否守约", "next": "anonymous-letter", "patch": {"flags.clarity": 1, "flags.taskFocus": 1}},
            {"id": "team-cooperate", "intentId": "team.work-together", "label": "留在同一区域，边做边商量", "hint": "有更多相处时间，也可能暴露小摩擦", "next": "anonymous-letter", "patch": {"flags.relationshipFocus": 1, "flags.reciprocity": 1}},
            {"id": "team-volunteer", "intentId": "team.take-hard-part", "label": "先接下更麻烦的那一部分", "hint": "用行动表达诚意，但不替对方包办", "next": "anonymous-letter", "patch": {"flags.courage": 1, "flags.publicImpression": 1}},
        ],
    },
    "anonymous-letter": {
        "chapter": "DAY 1 · 心动短信", "eyebrow": "心动信箱 / 22:30",
        "title": "今晚，你还想继续认识谁？", "speaker": "节目旁白",
        "text": "睡前，每个人可以把一条不署名的心动短信发给今天最想继续了解的人。节目只公布每个人收到几条，不公布发送者。你的一条短信，不等于承诺，只代表今天的真实选择。",
        "action": "八部手机同时亮起，只留下一个收信人的位置。",
        "cinematic": "/media/video/E01-anonymous-letter.mp4", "characterChoice": True, "choices": [],
        "mediaCue": "夜晚卧室与走廊交叉剪辑，嘉宾独自编辑匿名心动短信并等待提示音",
    },
    "callback": {
        "chapter": "DAY 2 · 清晨回声", "eyebrow": "海边早餐 / 07:18",
        "title": "昨晚的一句话，留到了今天", "speaker": "节目旁白",
        "text": "短信没有替任何人决定关系，却让今天的座位、目光和下一次邀请有了新的方向。七天六夜才刚刚开始。",
        "action": "清晨餐桌旁，有人把相邻的椅子轻轻拉开。",
        "mediaCue": "清晨海边早餐桌、手机短信提示与昨晚收信对象的自然回望",
        "isEnding": True, "choices": [],
    },
}

DAY1_SCRIPT_NODE_IDS = tuple(NODES)
LEGACY_NODE_MAP = {
    "first-look": "introductions",
    "private-window": "guided-chat",
    "event-reveal": "team-up",
    "arrival": "arrival-context",
    "heart-message": "anonymous-letter",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def player_group(mbti: str) -> str:
    return next((group for group, types in PLAYER_GROUPS.items() if mbti in types), "diplomats")


def _empty_axes() -> dict[str, int]:
    return {axis: 0 for axis in RELATIONSHIP_AXES}


def split_story_beats(text: str) -> list[str]:
    """Split visible prose into a small manual-reading sequence without changing its meaning."""
    parts = [part.strip() for part in re.findall(r"[^。！？!?；;]+[。！？!?；;]?", str(text or "")) if part.strip()]
    if not parts:
        return []
    beats: list[str] = []
    for part in parts:
        if beats and (len(part) < 18 or len(beats[-1]) < 18) and len(beats[-1]) + len(part) <= 60:
            beats[-1] += part
        else:
            beats.append(part)
    while len(beats) > 4:
        beats[-2] += beats.pop()
    return beats


def _fallback_target_ids(perspective_character_id: str) -> list[str]:
    """Return three deterministic non-self people for the first guided exchange."""
    cast_order = [character["id"] for character in CHARACTERS]
    first_four, second_four = cast_order[:4], cast_order[4:]
    preferred = second_four if perspective_character_id in first_four else first_four
    ordered = [*preferred, *(character_id for character_id in cast_order if character_id not in preferred)]
    return [character_id for character_id in ordered if character_id != perspective_character_id][:3]


def _runtime_asset_map() -> dict[str, dict[str, Any]]:
    try:
        package = json.loads((ROOT / "media" / "runtime-media-manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {str(item.get("id")): item for item in package.get("assets", []) if isinstance(item, dict) and item.get("id")}


def day1_media_context(state: dict[str, Any], node: dict[str, Any] | None = None) -> dict[str, Any]:
    """Project an engine-owned media cue; model-written copy cannot alter asset routing."""
    node_id = state["nodeId"]
    blueprint = NODES[node_id]
    contract = DAY1_MEDIA_CONTRACT[node_id]
    asset_map = _runtime_asset_map()
    selected_asset_id = contract["assetId"]
    guided_id = state.get("guidedTargetCharacterId")
    perspective_id = state["player"]["perspectiveCharacterId"]
    variant_character_id = None
    variant_ids = contract.get("variantAssetIds", {})
    if contract.get("variantRouting") == "perspective":
        candidate_ids = [perspective_id]
    elif contract.get("variantRouting") == "participants":
        candidate_ids = [perspective_id, guided_id]
    else:
        candidate_ids = []
    for character_id in candidate_ids:
        candidate_asset_id = variant_ids.get(character_id)
        candidate_asset = asset_map.get(candidate_asset_id, {}) if candidate_asset_id else {}
        if (
            candidate_asset_id
            and candidate_asset.get("path")
            and candidate_asset.get("status") in {"ready", "approved-runtime"}
        ):
            selected_asset_id = candidate_asset_id
            variant_character_id = character_id
            break
    asset = asset_map.get(selected_asset_id, {})
    expected_src = f"/media/video/{selected_asset_id}.mp4"
    expected_poster = f"/media/posters/{selected_asset_id}.jpg"
    available = bool(asset.get("path")) and asset.get("status") in {"ready", "approved-runtime"}
    return {
        "eventId": contract["eventId"],
        "assetId": selected_asset_id,
        "baseAssetId": contract["assetId"],
        "variantForCharacterId": variant_character_id,
        "intent": contract["intent"],
        "cue": blueprint.get("mediaCue") or "恋综现场的自然过场",
        "src": asset.get("path") if available else "",
        "poster": asset.get("poster") or "" if available else "",
        "plannedSrc": expected_src,
        "plannedPoster": expected_poster,
        "available": available,
        "status": "ready" if available else "planned",
        "fallback": {
            "kind": "scene-card",
            "characterId": None,
            "src": None,
            "poster": asset.get("poster") if available else None,
        },
        "allowedChoiceIntentIds": [choice["intentId"] for choice in blueprint.get("choices", [])],
    }


def build_fallback_script_flavor(perspective_character_id: str) -> dict[str, Any]:
    """Natural authored fallback; IDs and patches always come from ``NODES``."""
    nodes: dict[str, Any] = {}
    for node_id, blueprint in NODES.items():
        nodes[node_id] = {
            "title": blueprint["title"], "text": blueprint["text"],
            "textBeats": deepcopy(blueprint.get("textBeats") or split_story_beats(blueprint["text"])),
            "speakerId": "program" if blueprint["speaker"] == "节目组" else "narrator",
            "action": blueprint.get("action", ""),
            "choices": [
                {"id": choice["id"], "label": choice["label"], "hint": choice["hint"], "targetCharacterId": None}
                for choice in blueprint.get("choices", [])
            ],
        }
    targets = _fallback_target_ids(perspective_character_id)
    icebreaker_copy = [
        (f"选客厅卡，去问{CHARACTER_MAP[targets[0]]['name']}刚才没展开的参加原因", "姓名写在卡上；从自我介绍里没说完的一句接着聊"),
        (f"选露台卡，和{CHARACTER_MAP[targets[1]]['name']}交换这七天最想体验的事", "问题容易回答，也能听见对方真实的期待"),
        (f"选行李区卡，先问{CHARACTER_MAP[targets[2]]['name']}要不要搭把手放行李", "从眼前能一起完成的小事开口，不必硬找话题"),
    ]
    for choice, target_id, copy in zip(nodes["icebreaker-choice"]["choices"], targets, icebreaker_copy):
        choice.update({"label": copy[0], "hint": copy[1], "targetCharacterId": target_id})
    for choice, target_id in zip(nodes["cast-first-impressions"]["choices"], targets):
        label, hint = CAST_FIRST_IMPRESSION_FALLBACKS[target_id]
        choice.update({"label": label, "hint": hint, "targetCharacterId": target_id})
    intro_copy = INTRODUCTION_FALLBACKS[perspective_character_id]
    for choice in nodes["introductions"]["choices"]:
        label, hint = intro_copy[choice["id"]]
        choice.update({"label": label, "hint": hint, "introductionMode": INTRODUCTION_MODES[choice["id"]]})
    nodes["introductions"]["text"] = (
        "大家围着客厅坐下，轮流说出姓名、公开背景和来到这里的原因。现在镜头来到你："
        "不用准备漂亮答案，让陌生人先认识一个真实、具体的你。"
    )
    return {
        "schemaVersion": 1, "source": "fallback", "perspectiveCharacterId": perspective_character_id,
        "generatedAt": utc_now(), "nodes": nodes,
    }


def create_snapshot(user_mbti: str = "INFP", perspective_character_id: str | None = None) -> dict[str, Any]:
    if perspective_character_id not in CHARACTER_MAP:
        perspective_character_id = CHARACTER_CARDS[0]["id"]
    relationships = {character["id"]: _empty_axes() for character in CHARACTERS}
    flags = {key: 0 for key in ("heat", "clarity", "publicImpression", "courage", "priorityChoice", "observation", "taskFocus", "relationshipFocus", "reciprocity", "eventLinked", "acceptedEvent")}
    return {
        "runId": str(uuid4()), "contentVersion": CONTENT_VERSION, "revision": 0,
        "player": {"mbti": user_mbti, "group": player_group(user_mbti), "displayName": CHARACTER_MAP[perspective_character_id]["name"], "perspectiveCharacterId": perspective_character_id},
        "nodeId": "arrival-context", "flags": flags, "relationships": relationships,
        "affection": {cid: 0 for cid in relationships}, "trust": {cid: 0 for cid in relationships},
        "attitudes": {cid: "curious" for cid in relationships}, "beliefs": [],
        "echoMemories": [], "eventLedger": [], "choiceHistory": [],
        "focusCharacterId": None, "activeEventId": None, "letterRecipientId": None,
        "guidedTargetCharacterId": None, "pendingInteraction": None, "agentConversations": {},
        "firstImpressionSeed": None,
        "storyArc": {"phase": "early", "beatCount": 0, "activeMissionId": None, "tension": 0, "reciprocity": 0, "uncertainty": 0},
        "storyEventLedger": [], "storyMission": None, "storyCooldowns": {}, "castTags": [],
        "scriptFlavor": build_fallback_script_flavor(perspective_character_id),
        "cinematicReceipt": None, "createdAt": utc_now(), "updatedAt": utc_now()
    }


def migrate_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not snapshot:
        return None
    state = deepcopy(snapshot)
    state["nodeId"] = LEGACY_NODE_MAP.get(state.get("nodeId"), state.get("nodeId", "arrival-context"))
    if state["nodeId"] not in NODES:
        state["nodeId"] = "arrival-context"
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
    default_phase = {"arrival-context": "early", "villa-arrival": "early", "introductions": "early", "cast-first-impressions": "early", "icebreaker-choice": "early", "guided-chat": "early", "team-up": "middle", "anonymous-letter": "middle", "callback": "late"}.get(state.get("nodeId"), "early")
    story_arc = state.setdefault("storyArc", {})
    story_arc.setdefault("phase", default_phase); story_arc.setdefault("beatCount", 0); story_arc.setdefault("activeMissionId", None)
    for axis in ("tension", "reciprocity", "uncertainty"): story_arc.setdefault(axis, 0)
    state.setdefault("storyEventLedger", []); state.setdefault("storyMission", None); state.setdefault("storyCooldowns", {}); state.setdefault("castTags", [])
    state.setdefault("flags", {})
    defaults = create_snapshot(state.get("player", {}).get("mbti", "INFP"))
    for key in defaults["flags"]:
        state["flags"].setdefault(key, 0)
    state.setdefault("player", {}).setdefault("group", player_group(state.get("player", {}).get("mbti", "INFP")))
    state["player"].setdefault("perspectiveCharacterId", CHARACTER_CARDS[0]["id"])
    perspective_id = state["player"]["perspectiveCharacterId"]
    if perspective_id not in CHARACTER_MAP:
        perspective_id = CHARACTER_CARDS[0]["id"]
        state["player"]["perspectiveCharacterId"] = perspective_id
    state["player"]["displayName"] = CHARACTER_MAP[perspective_id]["name"]
    state.setdefault("guidedTargetCharacterId", None)
    state.setdefault("pendingInteraction", None)
    state.setdefault("agentConversations", {})
    state.setdefault("firstImpressionSeed", None)
    if state["nodeId"] == "guided-chat" and state.get("guidedTargetCharacterId") not in CHARACTER_MAP:
        focus_id = state.get("focusCharacterId")
        target_id = focus_id if focus_id in CHARACTER_MAP and focus_id != perspective_id else _fallback_target_ids(perspective_id)[0]
        state["guidedTargetCharacterId"] = target_id
        completed = any(item.get("characterId") == target_id for item in state.get("echoMemories", []))
        state["pendingInteraction"] = {
            "type": "guided-first-chat", "targetCharacterId": target_id,
            "status": "completed" if completed else "required", "requiredTurnCount": 1,
            "completedTurnCount": 1 if completed else 0,
        }
    flavor = state.get("scriptFlavor")
    if not isinstance(flavor, dict) or flavor.get("perspectiveCharacterId") != perspective_id:
        state["scriptFlavor"] = build_fallback_script_flavor(perspective_id)
    else:
        fallback = build_fallback_script_flavor(perspective_id)
        flavor.setdefault("schemaVersion", 1); flavor.setdefault("source", "fallback"); flavor.setdefault("nodes", {})
        for node_id, node_flavor in fallback["nodes"].items():
            flavor["nodes"].setdefault(node_id, node_flavor)
    state["contentVersion"] = CONTENT_VERSION
    return state


def _flavored_choice(state: dict[str, Any], node_id: str, choice_id: str) -> dict[str, Any] | None:
    node = state.get("scriptFlavor", {}).get("nodes", {}).get(node_id, {})
    return next((choice for choice in node.get("choices", []) if choice.get("id") == choice_id), None)


def _letter_recipient_ids(state: dict[str, Any]) -> list[str]:
    perspective_id = state["player"]["perspectiveCharacterId"]
    eligible = [character_id for character_id in CHARACTER_MAP if character_id != perspective_id]
    guided_id = state.get("guidedTargetCharacterId")
    ranked = sorted(
        eligible,
        key=lambda character_id: (
            0 if character_id == guided_id else 1,
            -int(state["relationships"][character_id].get("attraction", 0)),
            -int(state["relationships"][character_id].get("trust", 0)),
            character_id,
        ),
    )
    return ranked[:3]


def apply_choice(snapshot: dict[str, Any], choice_id: str, character_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    state = migrate_snapshot(snapshot); assert state is not None
    node = NODES[state["nodeId"]]
    selected_target_id: str | None = None
    if node.get("requiresGuidedInteraction"):
        pending = state.get("pendingInteraction") or {}
        if pending.get("status") != "completed":
            target = CHARACTER_MAP.get(state.get("guidedTargetCharacterId") or "")
            target_name = target["name"] if target else "亮起头像的嘉宾"
            raise ValueError(f"先和{target_name}完成一次从自我介绍开始的 1 对 1 交流。")
    if node.get("characterChoice"):
        perspective_id = state["player"]["perspectiveCharacterId"]
        if character_id == perspective_id:
            raise ValueError("不能把心动短信发给自己。")
        if character_id not in _letter_recipient_ids(state):
            raise ValueError("请选择本轮给出的三位收信人之一。")
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
        if state["nodeId"] == "cast-first-impressions":
            flavored = _flavored_choice(state, "cast-first-impressions", choice_id) or {}
            selected_target_id = flavored.get("targetCharacterId")
            if selected_target_id not in CHARACTER_MAP or selected_target_id == state["player"]["perspectiveCharacterId"]:
                selected_target_id = _fallback_target_ids(state["player"]["perspectiveCharacterId"])[0]
            impression_copy = str(flavored.get("label") or CAST_FIRST_IMPRESSION_FALLBACKS[selected_target_id][0]).strip()
            seed = {
                "choiceId": choice_id,
                "effectIntentId": choice["intentId"],
                "kind": choice["impressionKind"],
                "characterId": selected_target_id,
                "summary": impression_copy[:120],
                "plannedCallbackNodeIds": ["team-up", "anonymous-letter", "callback"],
                "status": "seeded",
                "createdAt": utc_now(),
            }
            state["firstImpressionSeed"] = seed
            state["focusCharacterId"] = selected_target_id
            patch = {**patch, "firstImpressionSeed": seed}
        if state["nodeId"] == "icebreaker-choice":
            flavored = _flavored_choice(state, "icebreaker-choice", choice_id) or {}
            target_id = flavored.get("targetCharacterId")
            if target_id not in CHARACTER_MAP or target_id == state["player"]["perspectiveCharacterId"]:
                target_id = _fallback_target_ids(state["player"]["perspectiveCharacterId"])[0]
            state["guidedTargetCharacterId"] = target_id
            state["focusCharacterId"] = target_id
            state["pendingInteraction"] = {
                "type": "guided-first-chat", "targetCharacterId": target_id, "status": "required",
                "requiredTurnCount": 1, "completedTurnCount": 0, "sourceChoiceId": choice_id,
                "reason": f"完成与{CHARACTER_MAP[target_id]['name']}的三分钟破冰交流",
            }
            patch = {**patch, "guidedTargetCharacterId": target_id, "pendingInteraction.status": "required"}
            selected_target_id = target_id
    committed_node_id = state["nodeId"]
    if node.get("characterChoice"):
        effect_intent_id = "heart-message.send"
    else:
        effect_intent_id = choice["intentId"]
    receipt = {
        "id": str(uuid4()), "kind": "choice", "choiceId": choice_id, "patch": patch,
        "effectIntentId": effect_intent_id,
        "targetCharacterId": selected_target_id or character_id,
        "committedAt": utc_now(),
    }
    state["choiceHistory"].append(receipt); state["nodeId"] = next_node
    state["storyArc"]["phase"] = {"arrival-context": "early", "villa-arrival": "early", "introductions": "early", "cast-first-impressions": "early", "icebreaker-choice": "early", "guided-chat": "early", "team-up": "middle", "anonymous-letter": "middle", "callback": "late"}.get(next_node, state["storyArc"]["phase"])
    state["revision"] += 1; state["updatedAt"] = utc_now()
    next_media = day1_media_context(state)
    state["cinematicReceipt"] = (
        {"src": next_media["src"], "assetId": next_media["assetId"], "afterRevision": state["revision"]}
        if next_media["available"] else None
    )
    receipt["fromEventId"] = DAY1_MEDIA_CONTRACT[committed_node_id]["eventId"]
    receipt["nextMedia"] = next_media
    return state, receipt


def _fallback_typed_suggestions(
    snapshot: dict[str, Any], card: dict[str, Any], dialogue: str, player_text: str = "",
) -> list[dict[str, str]]:
    player_id = snapshot["player"]["perspectiveCharacterId"]
    player_name = CHARACTER_MAP[player_id]["name"]
    node_id = snapshot["nodeId"]
    target_name = card["names"]["primary"]
    stage_copy = {
        "guided-chat": f"{target_name}，要不要和我一起准备今晚的晚餐？我们可以先商量分工。",
        "team-up": "今晚的晚餐我们一起做吧，你更想负责哪一部分？",
        "anonymous-letter": "如果今晚还能发一条短信，我会写：想继续认识你。",
    }.get(node_id, f"我叫{player_name}。回到现在这件事，你愿意告诉我你的想法吗？")
    voice_copy = {
        "shenmo": ("你刚才提到这个习惯，它每次都有效，还是今天刚好有效？", f"先说清一件事：{target_name}，要不要和我一起准备晚餐，再商量分工？", "如果答案还没想好，你通常会先做哪一件小事？"),
        "linyu": ("你刚才说这样会放松，那我现在做什么会让你更自在一点？", f"{target_name}，要不要一起去厨房准备晚餐？你先挑顺手的，我来补另一边。", "别人照顾你时，什么样的分寸最舒服？"),
        "chengye": ("你刚才说的那个办法，光说不算——现在最想先试哪一步？", f"{target_name}，别站着聊了，要不要一起去厨房准备晚餐，分工边做边定？", "别人第一次误会你时，你会解释还是直接做给对方看？"),
        "guyan": ("你刚才提到这个习惯，我确认一下：它是在躲开人，还是帮你回到人群？", f"如果目标是继续聊，{target_name}，要不要一起准备晚餐？分工可以边做边调整。", "有没有哪次你原本的判断，后来被一个人改掉了？"),
        "jiangwan": ("你刚才说到这件事，我这样理解对吗：你需要的不是热闹，而是有人不催你？", f"如果你愿意，我们今晚一起准备晚餐，先从你顺手的部分商量分工。", "什么样的一句追问，会让你觉得自己真的被听见？"),
        "jiangmi": ("你刚才那句话有个画面——如果把它录成声音，最先听见的会是什么？", f"{target_name}，走，一起去厨房准备晚餐吧；你挑一件想做的，我跟上。", "安静下来以后，你最希望身边的人做什么？"),
        "sunnian": ("你刚才说这样会安心，那有没有一件事也想让别人替你做？", f"{target_name}，今晚一起准备晚餐吧。你告诉我需要哪一部分，我来搭手。", "如果今天不用照顾任何人，你最想把时间留给什么？"),
        "chensu": ("你刚才说的我听见了；如果现在就做一步，你会先从哪儿下手？", f"{target_name}，一起准备晚餐吧。你选备菜还是摆桌，剩下的我来。", "有什么事你宁愿先做，也一直不太会开口解释？"),
    }
    followup, voiced_mainline, deeper = voice_copy[player_id]
    if node_id == "guided-chat":
        stage_copy = voiced_mainline
    return [
        {"type": "followup", "text": followup},
        {"type": "mainline", "text": stage_copy},
        {"type": "deeper", "text": deeper},
    ]


def _normalize_agent_suggestions(
    card: dict[str, Any], payload: dict[str, Any], snapshot: dict[str, Any] | None, dialogue: str, player_text: str,
) -> list[dict[str, str]]:
    if snapshot is None:
        return []
    raw = payload.get("suggestions")
    expected_types = ("followup", "mainline", "deeper")
    if raw is None:
        items = _fallback_typed_suggestions(snapshot, card, dialogue, player_text)
    elif isinstance(raw, list) and len(raw) == 3 and all(isinstance(item, str) for item in raw):
        items = [{"type": suggestion_type, "text": str(text)} for suggestion_type, text in zip(expected_types, raw)]
    elif isinstance(raw, list) and len(raw) == 3 and all(isinstance(item, dict) for item in raw):
        by_type = {str(item.get("type") or "").strip(): item for item in raw}
        if set(by_type) != set(expected_types):
            raise ValueError("DeepSeek 建议语必须包含 followup、mainline、deeper 三类")
        items = [{"type": suggestion_type, "text": str(by_type[suggestion_type].get("text") or "")} for suggestion_type in expected_types]
    else:
        raise ValueError("DeepSeek 建议语必须正好三条")
    normalized, seen = [], set()
    player_name = CHARACTER_MAP[snapshot["player"]["perspectiveCharacterId"]]["name"]
    player_card = CHARACTER_CARD_MAP[snapshot["player"]["perspectiveCharacterId"]]
    player_occupation = player_card.get("sourceProfile", {}).get("facts", {}).get("occupation")
    unknown_player_job = not isinstance(player_occupation, str) or any(
        term in player_occupation for term in ("待剧情", "待正式确认", "运行时职业待")
    )
    for item in items:
        suggestion_type = item["type"]
        text = item["text"].strip()
        if not 4 <= len(text) <= 72 or text in seen:
            raise ValueError("DeepSeek 建议语重复或长度不符合合同")
        if any(term in text for term in (*MECHANICAL_COPY_TERMS, "关系数值", "写入记忆", "触发事件", "DeepSeek", "Agent", "API")):
            raise ValueError("DeepSeek 建议语暴露后台或使用机械表达")
        if any(term in text for term in ("带的那台旧相机", "节目组秘密", "桌签", "线索", "地图", "钥匙")):
            raise ValueError("DeepSeek 建议语把未来兴趣或隐藏信息写成了已发生事实")
        for claimed_name in re.findall(r"我叫([\u4e00-\u9fff·]{2,8})", text):
            if claimed_name != player_name:
                raise ValueError("DeepSeek 建议语替主角编造了错误姓名")
        if unknown_player_job and re.search(r"我(?:是|在|做).{0,12}(?:工作|职业|行业|相关)", text):
            raise ValueError("DeepSeek 建议语替主角编造了职业")
        if suggestion_type == "followup":
            link_markers = ("刚才", "你说", "你问", "这句话", "你提到", "你刚刚", "你说的")
            if not any(marker in text for marker in link_markers):
                raise ValueError("followup 建议语没有承接玩家上一句与角色回复")
        if suggestion_type == "mainline":
            node_id = snapshot["nodeId"]
            if node_id == "guided-chat":
                actionable = any(anchor in text for anchor in ("晚餐", "晚饭", "厨房", "备菜")) and any(
                    anchor in text for anchor in ("准备", "分工", "搭档", "一起", "负责")
                )
            elif node_id == "team-up":
                actionable = any(anchor in text for anchor in ("备菜", "餐桌", "饮品", "厨房")) and any(
                    anchor in text for anchor in ("负责", "分工", "一起", "我来", "你来")
                )
            elif node_id == "anonymous-letter":
                actionable = any(anchor in text for anchor in ("短信", "今晚", "继续认识"))
            else:
                actionable = True
            if not actionable:
                raise ValueError("mainline 建议语没有回到当前剧情目标")
        seen.add(text)
        normalized.append({"type": suggestion_type, "text": text, **SUGGESTION_PRESENTATION[suggestion_type]})
    return normalized


def validate_agent_turn(
    card: dict[str, Any], payload: dict[str, Any], snapshot: dict[str, Any] | None = None, player_text: str = "",
) -> dict[str, Any]:
    dialogue = str(payload.get("dialogue") or "").strip()
    if not 8 <= len(dialogue) <= 240:
        raise ValueError("DeepSeek 角色台词长度不符合合同")
    if any(term in dialogue for term in MECHANICAL_COPY_TERMS):
        raise ValueError("DeepSeek 角色台词使用了通用机械表达")
    if snapshot:
        character_id = card["id"]
        first_conversation = not any(item.get("characterId") == character_id for item in snapshot.get("echoMemories", []))
        if first_conversation and snapshot.get("nodeId") == "guided-chat":
            stage_direction = str(payload.get("stageDirection") or "")
            impossible_first_meeting = (
                "昨天", "前几天", "这几天", "桌签", "节目组秘密", "节目组说", "线索", "地图", "钥匙", "共同经历", "天台",
            )
            if any(term in dialogue for term in impossible_first_meeting) or re.search(r"(?:已经|连续|数了).{0,6}[一二三四五六七八九十\d]+天", dialogue):
                raise ValueError("DeepSeek 首聊台词编造了尚未发生的时间或节目事实")
            if card["names"]["primary"] not in dialogue:
                raise ValueError("DeepSeek 首聊没有直接介绍角色姓名")
            if card["mbti"] not in dialogue:
                raise ValueError("DeepSeek 首聊没有清楚介绍 MBTI 或性格")
            if not any(anchor in dialogue for anchor in INTRO_BACKGROUND_ANCHORS[character_id]):
                raise ValueError("DeepSeek 首聊没有介绍人物卡允许公开的工作或日常背景")
            if not any(marker in dialogue for marker in ("来这里", "参加", "这次", "这七天")):
                raise ValueError("DeepSeek 首聊没有说清参加节目的来意")
            if re.search(r"(?:来这里|来参加|这次来|这七天).{0,32}(?:想|主要).{0,16}(?:修|破解|赢|找出)", dialogue):
                raise ValueError("DeepSeek 首聊把人物任务写成了参加恋综的主要原因")
            if any(term in stage_direction for term in ("录音笔", "旧相机", "插画本", "工具箱")):
                raise ValueError("DeepSeek 首聊动作新增了当前现场没有的随身道具")
            if any(term in dialogue for term in ("你猜", "猜我", "秘密", "以后会知道", "先看你怎么回答", "试探")):
                raise ValueError("DeepSeek 首聊使用了谜语或抽象试探")
            if character_id == "jiangmi" and any(
                term in dialogue for term in ("做一组录音", "收集七天", "听大家的故事", "还没被播放", "像一段录音")
            ):
                raise ValueError("DeepSeek 首聊把姜米写成了录音任务或谜语")
            occupation = card.get("sourceProfile", {}).get("facts", {}).get("occupation")
            unknown_job = not isinstance(occupation, str) or any(
                term in occupation for term in ("待剧情", "待正式确认", "运行时职业待")
            )
            if unknown_job and re.search(r"(?:我是|职业是|工作是|从事).{0,12}(?:师|员|经理|博主|策划|工程|设计|工作|行业)", dialogue):
                raise ValueError("DeepSeek 首聊替角色编造了未确认职业")
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
    suggestions = _normalize_agent_suggestions(card, payload, snapshot, dialogue, player_text)
    return {
        "dialogue": dialogue, "stageDirection": str(payload.get("stageDirection") or "").strip()[:100],
        "attitude": attitude, "intentId": intent_id,
        "publicReason": str(payload.get("publicReason") or "关系判断已更新").strip()[:100],
        "relationshipDelta": delta,
        "memory": {"kind": kind, "summary": str(memory.get("summary") or "这次交流被记住了").strip()[:120], "interpretation": str(memory.get("interpretation") or "仍需后续验证").strip()[:160], "salience": max(0, min(100, salience)), "emotionalValence": max(-100, min(100, valence))},
        "proposedEventId": event_id or None,
        "suggestions": suggestions,
        "suggestedPrompts": [item["text"] for item in suggestions],
        "suggestionsSource": "deepseek" if payload.get("suggestions") is not None else "engine-fallback",
    }


def commit_agent_turn(snapshot: dict[str, Any], character_id: str, player_text: str, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if character_id not in CHARACTER_CARD_MAP: raise ValueError("这位嘉宾不在心动小屋。")
    state = migrate_snapshot(snapshot); assert state is not None
    perspective_id = state["player"]["perspectiveCharacterId"]
    if character_id == perspective_id:
        raise ValueError("你正在从这位嘉宾的视角体验，不能和自己私聊。")
    pending = state.get("pendingInteraction") or {}
    if state["nodeId"] == "guided-chat" and pending.get("status") == "required" and character_id != pending.get("targetCharacterId"):
        target_name = CHARACTER_MAP[pending["targetCharacterId"]]["name"]
        raise ValueError(f"这一段先去和{target_name}完成节目组安排的破冰交流。")
    card = CHARACTER_CARD_MAP[character_id]
    turn, axes = validate_agent_turn(card, payload, state, player_text), state["relationships"][character_id]
    cold_start = not any(axes.values()) and not any(item.get("characterId") == character_id for item in state["echoMemories"])
    if cold_start:
        turn["relationshipDelta"] = {axis: max(-1, min(1, delta)) for axis, delta in turn["relationshipDelta"].items()}
        turn["proposedEventId"] = None
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
        "suggestions": turn["suggestions"], "suggestedPrompts": turn["suggestedPrompts"], "suggestionsSource": turn["suggestionsSource"],
        "relationshipDelta": committed_delta, "affectionDelta": committed_delta["affection"], "trustDelta": committed_delta["trust"],
        "createdAt": utc_now(), "callbackEligible": True, "callbackAfterEventIds": [policy["eventId"]] if activated_event else []
    }
    state["echoMemories"].append(memory); state["focusCharacterId"] = character_id
    conversations = state.setdefault("agentConversations", {})
    conversation = conversations.setdefault(character_id, {"turnCount": 0, "firstMetAtNodeId": state["nodeId"]})
    conversation["turnCount"] = int(conversation.get("turnCount", 0)) + 1
    conversation["lastMemoryId"] = memory_id; conversation["lastSpokeAt"] = memory["createdAt"]
    guided_completed = False
    if pending.get("targetCharacterId") == character_id and pending.get("status") == "required":
        pending["completedTurnCount"] = int(pending.get("completedTurnCount", 0)) + 1
        if pending["completedTurnCount"] >= int(pending.get("requiredTurnCount", 1)):
            pending["status"] = "completed"; pending["completedAt"] = memory["createdAt"]; pending["memoryId"] = memory_id
            guided_completed = True
        state["pendingInteraction"] = pending
    state["revision"] += 1; state["updatedAt"] = utc_now()
    receipt = {"id": memory_id, "kind": "agent-turn", "intentId": turn["intentId"], "attitude": turn["attitude"], "publicReason": turn["publicReason"], "patch": {f"relationships.{character_id}.{axis}": delta for axis, delta in committed_delta.items() if delta}, "eventActivation": activated_event, "suggestions": turn["suggestions"], "suggestedPrompts": turn["suggestedPrompts"], "suggestionsSource": turn["suggestionsSource"], "committedAt": memory["createdAt"]}
    receipt["guidedInteractionCompleted"] = guided_completed
    return state, receipt


def _project_script_flavor(state: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    flavor = state.get("scriptFlavor", {}).get("nodes", {}).get(state["nodeId"], {})
    for field in ("title", "text", "action"):
        value = flavor.get(field)
        if isinstance(value, str) and value.strip():
            node[field] = value.strip()
    raw_beats = flavor.get("textBeats")
    if isinstance(raw_beats, list) and raw_beats and all(isinstance(beat, str) and beat.strip() for beat in raw_beats):
        node["textBeats"] = [beat.strip() for beat in raw_beats]
    else:
        node["textBeats"] = deepcopy(node.get("textBeats") or split_story_beats(node.get("text", "")))
    speaker_id = flavor.get("speakerId")
    if speaker_id == "program":
        node["speaker"] = "节目组"
    elif speaker_id == "narrator":
        node["speaker"] = "节目旁白"
    elif speaker_id in CHARACTER_MAP and speaker_id != state["player"]["perspectiveCharacterId"]:
        node["speaker"] = CHARACTER_MAP[speaker_id]["name"]
        node["speakerCharacterId"] = speaker_id
    flavored_choices = {choice.get("id"): choice for choice in flavor.get("choices", []) if isinstance(choice, dict)}
    for choice in node.get("choices", []):
        surface = flavored_choices.get(choice["id"], {})
        for field in ("label", "hint"):
            value = surface.get(field)
            if isinstance(value, str) and value.strip():
                choice[field] = value.strip()
        target_id = surface.get("targetCharacterId")
        if target_id in CHARACTER_MAP and target_id != state["player"]["perspectiveCharacterId"]:
            choice["targetCharacterId"] = target_id
            if state["nodeId"] in {"cast-first-impressions", "icebreaker-choice"}:
                choice["characterId"] = target_id
    return node


def project_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    state = migrate_snapshot(snapshot); assert state is not None
    node = _project_script_flavor(state, deepcopy(NODES[state["nodeId"]]))
    perspective_id = state["player"]["perspectiveCharacterId"]
    guided_id = state.get("guidedTargetCharacterId")
    if state["nodeId"] in {"arrival-context", "villa-arrival", "introductions", "cast-first-impressions", "icebreaker-choice"}:
        node["characterId"] = perspective_id
    elif state["nodeId"] in {"guided-chat", "team-up"} and guided_id in CHARACTER_MAP:
        target = CHARACTER_MAP[guided_id]
        node["characterId"] = guided_id
        flavor_node = state.get("scriptFlavor", {}).get("nodes", {}).get(state["nodeId"], {})
        if state["nodeId"] == "guided-chat" and not (flavor_node.get("title") and flavor_node.get("text")):
            node["title"] = f"先和{target['name']}从一句你好开始"
            node["text"] = f"{target['name']}正在等你开口。先交换姓名和来到节目的原因；完成一次自然寒暄后，再决定要不要一起准备今晚的晚餐。"
    pending = deepcopy(state.get("pendingInteraction"))
    if pending and pending.get("targetCharacterId") in CHARACTER_MAP:
        target = CHARACTER_MAP[pending["targetCharacterId"]]
        pending.update({"targetName": target["name"], "targetMbti": target["mbti"], "targetPortrait": target["portrait"], "targetVideo": target["video"]})
        node["guidedInteraction"] = pending
        node["guidedTargetCharacterId"] = target["id"]
    impression_seed = deepcopy(state.get("firstImpressionSeed"))
    if (
        isinstance(impression_seed, dict)
        and state["nodeId"] in impression_seed.get("plannedCallbackNodeIds", [])
        and impression_seed.get("characterId") in CHARACTER_MAP
    ):
        impression_character = CHARACTER_MAP[impression_seed["characterId"]]
        node["firstImpressionCallback"] = {
            "characterId": impression_character["id"],
            "characterName": impression_character["name"],
            "kind": impression_seed.get("kind"),
            "summary": impression_seed.get("summary"),
            "matchesCurrentFocus": impression_character["id"] in {
                state.get("guidedTargetCharacterId"), state.get("letterRecipientId"), state.get("focusCharacterId"),
            },
        }
    active_event = next((item for item in reversed(state["eventLedger"]) if item["eventId"] == state.get("activeEventId")), None)
    if node.get("characterChoice"):
        node["choices"] = [
            {
                "id": f"letter-{character_id}", "characterId": character_id,
                "label": f"把今晚的短信发给 {CHARACTER_MAP[character_id]['name']}",
                "hint": f"{CHARACTER_MAP[character_id]['mbti']} · 今天的态度：{state['attitudes'].get(character_id, 'curious')}",
            }
            for character_id in _letter_recipient_ids(state)
        ]
    if node.get("isEnding"):
        cid = state.get("letterRecipientId") or state.get("focusCharacterId"); character = CHARACTER_MAP.get(cid or "")
        memories = [item for item in state["echoMemories"] if item.get("characterId") == cid]
        event = next((item for item in reversed(state["eventLedger"]) if item.get("characterId") == cid), active_event)
        if character:
            node.update({"characterId": cid})
            if memories and event:
                node["title"] = f"{event['label']}没有停在昨夜"; node["text"] = f"{character['name']}按昨夜记住的“{memories[-1]['summary']}”作出了今天的行动。{event['text']}"
            elif memories:
                node["text"] = f"昨晚的短信没有署名，但{character['name']}仍记得你们聊过的那件小事。今天，彼此有了继续认识的机会。"
    media_context = day1_media_context(state, node)
    node["media"] = media_context
    # The approved media contract is authoritative. Old blueprint cinematics
    # are authoring placeholders and must never override an event-owned master.
    node["cinematic"] = media_context["src"] if media_context["available"] else None
    node["eventId"] = media_context["eventId"]
    node["eventIntent"] = media_context["intent"]
    projected_characters = deepcopy(CHARACTERS)
    for character in projected_characters:
        character["isPlayerPerspective"] = character["id"] == perspective_id
        character["chatEnabled"] = character["id"] != perspective_id
        character["isGuidedTarget"] = character["id"] == guided_id and (state.get("pendingInteraction") or {}).get("status") == "required"
    return {"snapshot": state, "node": node, "characters": projected_characters, "mediaContext": media_context}
