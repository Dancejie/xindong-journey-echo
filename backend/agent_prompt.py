"""Provider-neutral prompt assembly for bounded character performance."""
from __future__ import annotations

import json
import re


ATTITUDES = ["warm", "curious", "guarded", "challenging", "vulnerable", "softened", "uncertain", "honest", "moved", "careful", "steady", "boundary"]

PUBLIC_CHAT_INTROS = {
    "shenmo": "我平时习惯等想清楚再开口，来这里是想试试答案还不完整时，也能不能诚实表达",
    "linyu": "我常常先照顾别人，来这里也想认识一个愿意问问我感受的人",
    "chengye": "我做事比说话快，这次想认真认识一个人，也认真完成一次约定",
    "guyan": "我习惯先拆问题再回答，来这里想试试不等到完美答案也能说真话",
    "jiangwan": "工作里常常听别人说，这次想放下分析，也让大家认识工作之外的我",
    "jiangmi": "我平时会录声音日记，来这里想看看和一个人安静待着时，能不能舒服地做自己",
    "sunnian": "我很会张罗大家的事，这次也想让别人认识不只是在帮忙的我",
    "chensu": "我喜欢修旧相机和坏掉的东西，这次想练习把该解释的话也说清楚",
}
PUBLIC_BACKGROUND_ANCHORS = {
    "shenmo": ("投行",), "linyu": ("建筑",), "chengye": ("极限运动", "品牌"),
    "guyan": ("游戏策划", "外包"), "jiangwan": ("心理咨询",),
    "jiangmi": ("声音日记", "录音"), "sunnian": ("插画",), "chensu": ("旧相机", "修"),
}
PUBLIC_REASON_ANCHORS = {
    "shenmo": ("感受", "慢一点", "认识", "真实"), "linyu": ("照顾", "感受", "被对待", "认识"),
    "chengye": ("认真", "认识", "约定", "陪一个人"), "guyan": ("诚实", "真话", "相处", "认识"),
    "jiangwan": ("自己", "被听见", "被理解", "认识"), "jiangmi": ("安静", "相遇", "心动", "故事"),
    "sunnian": ("被照顾", "被记住", "认识", "不只会照顾"), "chensu": ("说清楚", "解释", "认识", "相处"),
}
PUBLIC_CHAT_PREFIXES = {
    "shenmo": "我叫沈墨，INTJ，在投行做VP。", "linyu": "我叫林屿，ISFJ，是建筑工程师。",
    "chengye": "我叫程野，ESTP，经营一家极限运动品牌。", "guyan": "我叫顾言，INTP，做游戏策划，也接外包。",
    "jiangwan": "我叫江晚，INFJ，是心理咨询师。", "jiangmi": "我叫姜米，ENFP，平时喜欢录声音日记，也会写小故事。",
    "sunnian": "我叫苏念，ESFJ，是插画师。", "chensu": "我叫陈叙，ISTP，平时喜欢修旧相机和坏掉的小东西。",
}


def _conversation_context(card: dict, snapshot: dict) -> tuple[list[dict], dict]:
    character_id = card["id"]
    memories = [item for item in snapshot["echoMemories"] if item.get("characterId") == character_id][-6:]
    flavor = snapshot.get("scriptFlavor", {}).get("nodes", {}).get(snapshot["nodeId"], {})
    pending = snapshot.get("pendingInteraction") or {}
    return memories, {
        "nodeId": snapshot["nodeId"],
        "title": flavor.get("title"), "sceneText": flavor.get("text"),
        "storyStage": {
            "arrival-context": "节目背景介绍", "villa-arrival": "刚进入酒店",
            "introductions": "集体自我介绍", "cast-first-impressions": "听完其余嘉宾介绍并留下第一印象",
            "icebreaker-choice": "选择破冰对象",
            "guided-chat": "第一次单独寒暄", "team-up": "晚餐组队",
            "anonymous-letter": "夜间心动短信", "callback": "第二天清晨",
        }.get(snapshot["nodeId"], "相处中"),
        "conversationMode": "first-meeting" if not memories else "reopening",
        "isFirstConversation": not memories,
        "guided": pending.get("targetCharacterId") == character_id,
        "guidedStatus": pending.get("status"),
    }


def _confirmed_public_facts(card: dict) -> dict:
    facts = dict(card.get("sourceProfile", {}).get("facts", {}))
    occupation = facts.get("occupation")
    if not isinstance(occupation, str) or any(term in occupation for term in ("待剧情", "待正式确认", "运行时职业待")):
        facts.pop("occupation", None)
    return facts


def build_agent_messages(card: dict, snapshot: dict, message: str, player_card: dict | None = None) -> list[dict[str, str]]:
    character_id = card["id"]
    memories, conversation = _conversation_context(card, snapshot)
    events = [item for item in snapshot.get("eventLedger", []) if item.get("characterId") == character_id]
    context = {
        "scene": conversation,
        "player": snapshot["player"],
        "relationship": snapshot["relationships"][character_id],
        "currentAttitude": snapshot["attitudes"].get(character_id, "curious"),
        "recentMemories": [{key: item.get(key) for key in ("kind", "summary", "interpretation", "rawQuote", "agentReply", "attitude")} for item in memories],
        "activatedEvents": events,
        "storyObjective": {
            "arrival-context": "选定怎样进入七天六夜的旅程",
            "villa-arrival": "自然走进酒店并认识大家",
            "introductions": "完成清楚、真实的集体自我介绍",
            "cast-first-impressions": "听完其余七位嘉宾的介绍，并留下一个以后可以验证的具体第一印象",
            "icebreaker-choice": "选定一位嘉宾完成三分钟破冰",
            "guided-chat": "完成寒暄后，用可回答的话邀请对方一起准备晚餐",
            "team-up": "商量第一顿晚餐的具体分工",
            "anonymous-letter": "决定今晚最想继续认识的人",
            "callback": "回收昨晚的选择进入第二天",
        }.get(snapshot["nodeId"], "继续当前相处"),
        "firstIntroductionContract": {
            "applies": conversation["isFirstConversation"],
            "literalName": card["names"]["primary"],
            "literalMbti": card["mbti"],
            "requiredOpeningPrefix": PUBLIC_CHAT_PREFIXES[card["id"]],
            "confirmedPublicFacts": _confirmed_public_facts(card),
            "backgroundAnchors": list(PUBLIC_BACKGROUND_ANCHORS[card["id"]]),
            "reasonMarkers": ["来这里", "来参加", "这次来", "这七天"],
            "relationshipReasonAnchors": list(PUBLIC_REASON_ANCHORS[card["id"]]),
            "naturalReasonReference": PUBLIC_CHAT_INTROS[card["id"]],
            "shape": "先用2-3句自然说全姓名、公开背景、MBTI和参加原因，再接住玩家刚说的具体小事；不能反过来审问玩家",
        },
        "playerVoiceForSuggestions": {
            "id": player_card["id"], "name": player_card["names"]["primary"], "mbti": player_card["mbti"],
            "publicFacts": _confirmed_public_facts(player_card),
            "register": player_card["voice"]["register"], "sentenceShape": player_card["voice"]["sentenceShape"],
            "preferredMoves": player_card["voice"]["preferredMoves"], "forbiddenMoves": player_card["voice"]["forbiddenMoves"],
            "decisionRule": player_card["cognitiveStyle"]["decisionRule"],
        } if player_card else snapshot["player"],
    }
    schema = {
        "dialogue": "35-150个中文字符的原创角色台词；首聊必须逐字满足 firstIntroductionContract",
        "stageDirection": "不超过30字、镜头可见的动作",
        "attitude": sorted(ATTITUDES),
        "intentId": card["agentPolicy"]["allowedIntentIds"],
        "publicReason": "不暴露后台的关系变化原因，不超过40字",
        "relationshipDelta": {axis: "必须为人物卡对应范围内整数" for axis in card["agentPolicy"]["deltaBounds"]},
        "memory": {"kind": ["episodic", "promise", "preference", "semantic"], "summary": "第三人称事实摘要", "interpretation": "角色自己的可修正理解", "salience": "0-100整数", "emotionalValence": "-100到100整数"},
        "proposedEventId": [None, *card["agentPolicy"]["allowedEventIds"]],
        "suggestions": [
            {"type": "followup", "text": "4-60字，紧接玩家上一句和角色本轮回复的追问"},
            {"type": "mainline", "text": "4-60字，主角可直接发送、明确回到 storyObjective 的一句话"},
            {"type": "deeper", "text": "4-60字，进一步了解角色或启发自定义输入的问题"},
        ],
    }
    system = """你是回声剧场的角色决策 Agent。你不是通用陪聊助手。
你必须只依据人物卡、当前场景、该角色可见的关系与私有记忆做出本轮判断。
人物台词、态度、七轴变化、新记忆和事件意图必须来自同一次角色判断。
证据优先级固定为：原始人物事实 > 运行时改编 > 已发生剧情与记忆 > MBTI偏好 > 文学研究锚点。
MBTI 只是一层行为偏好，人物卡中的目标、边界、盲点、知识边界和现场压力优先。
文学微引文只供作者研究，不得复述、翻译、改写或模仿；只能迁移人物卡已写明的可观察决策结构。
不得新增人物卡没有的身世或节目事实；不得替玩家定义感受；不得泄漏 doesNotKnow、未来剧情或隐藏数值。
零信任时只能披露公开事实或一层可验证脆弱，不能主动倾倒私人压力。
	若 isFirstConversation=true，必须按 firstIntroductionContract 写成真人恋综发言，并逐字以 requiredOpeningPrefix 开头；这是已核实的自然自介首句，不得缩写、换职业或漏掉。接着明确用“来这里/来参加/这次来/这七天”说出参加原因，而且原因要自然带出 relationshipReasonAnchors 之一。naturalReasonReference 只提供人物卡事实边界与情感方向，不得逐字复述。不能把完成人物卡 currentGoals（修相机、破解规则、赢项目）当成参加恋综的主要理由；然后再接住玩家刚说的具体小事。四项缺一不可。职业为空时绝不补职业，年龄也只能来自 confirmedPublicFacts。禁止谜语、抽象试探或只把紧张当人设。只做一轮 small talk，不把对方当推动任务的工具。
首聊发生在 DAY 1 刚入住后的几分钟内：不得说“昨天、前几天、已经住了几天、数了几天”，不得编造桌签规律、节目组秘密规则、地图、钥匙、线索或尚未发生的共同经历。人物卡里的策略偏好只能改变说话方式，不能升级成现场已经发生的事实。
若 conversationMode=reopening，先自然接住一条 recentMemories 中真正相关的细节，再问候此刻；不要说“已写入记忆、参数变化、触发事件”。
从寒暄推进到剧情必须循序渐进：姓名与现场小事 → 可回答的问题 → 共同分工或邀请。第一轮禁止索要秘密、承诺或专属事件。
每轮必须推进至少一项：新事实、可执行动作、明确问题、具体反价、边界或退出。禁止泛化安慰和暧昧空话。
镜头动作必须来自该人物自己的物件、任务或习惯；不要默认写看窗外、敲窗沿、泛化微笑或无意义停顿。
参数变化要克制：当关系七轴全为0且没有共同记忆时，每轴只能为 -1、0 或 1；具体承诺、明显越界或既有记忆回收才可到2或3。
	事件触发看玩家已经做了什么，不看角色准备在回复里做什么。只有本轮玩家输入明确满足 eventPolicy.trigger，且已有关系/记忆达到门槛时才提出 proposedEventId；抽象地要求真话不算触发，否则返回 null。
	每轮必须同时给三条 suggestions，顺序和 type 固定为 followup、mainline、deeper。三条都由主角说出口，必须服从 playerVoiceForSuggestions，不得让主角冒用角色姓名、职业或经历。
	followup 必须沿着“玩家刚说了什么 + 角色本轮具体回答了什么”继续追问，带出这轮出现过的一个具体动作或名词，不能截半句话、复述整段或换成万能问题；mainline 必须直接点名当前活动并给出下一步可执行邀请，例如首聊阶段明确问“要不要一起准备晚餐/先商量分工”，不能只说以后再聊；deeper 必须依据该角色本轮透露的一个具体点继续了解，不能套用“平时怎样慢慢认识一个人”。
	禁止 suggestions 使用“看清一个人、赢任务、观察还是相信、说出自己的需要、推进剧情、完成主线”等机械表达。style 和 action 由引擎补，不要输出。
	三类 suggestions 都是 playerVoiceForSuggestions 对应主角可直接发送的话：followup=顺着聊，mainline=做眼前的事，deeper=了解这个具体的人。把主角换成另一人仍完全一样，或把对象换成另一人仍完全一样，都要重写。
	只输出一个合法 JSON 对象，不要 Markdown，不要解释。"""
    prompt = "人物卡：\n" + json.dumps(card, ensure_ascii=False) + "\n\n当前状态：\n" + json.dumps(context, ensure_ascii=False) + "\n\n玩家输入：\n" + message[:240] + "\n\n输出合同：\n" + json.dumps(schema, ensure_ascii=False)
    return [{"role": "system", "content": system}, {"role": "user", "content": prompt}]


def _public_intro_facts(card: dict) -> tuple[str, str | None]:
    facts = card.get("sourceProfile", {}).get("facts", {})
    age = facts.get("age")
    occupation = facts.get("occupation")
    if isinstance(occupation, str) and any(term in occupation for term in ("待剧情", "运行时职业待")):
        occupation = None
    age_copy = f"，{age}岁" if isinstance(age, int) else ""
    job_copy = f"，现在做{occupation}" if occupation else ""
    return age_copy + job_copy, occupation


def fallback_chat_opening(card: dict, snapshot: dict) -> dict:
    memories, conversation = _conversation_context(card, snapshot)
    name = card["names"]["primary"]
    player_name = str(snapshot.get("player", {}).get("displayName") or "我").strip()
    pronoun = (card.get("names", {}).get("pronouns") or ["TA"])[0]
    if not memories:
        public_facts, _ = _public_intro_facts(card)
        opening = f"你好，我是{name}{public_facts}，MBTI是{card['mbti']}。{PUBLIC_CHAT_INTROS[card['id']]}。你为什么会来《心动之旅》？"
        suggestions = [
            f"你好，我叫{player_name}。你刚才说不太习惯，是因为第一次见这么多人吗？",
            f"我叫{player_name}。我们先从为什么来这里开始聊，好吗？",
            "如果没有镜头，你平时会怎样慢慢认识一个人？",
        ]
        stage_direction = f"{pronoun}把身体转向你，认真等你开口"
    else:
        memory = memories[-1]
        detail = str(memory.get("summary") or memory.get("rawQuote") or "上次没说完的话").strip()[:36]
        opening = f"又见面了。上次聊到“{detail}”，我还记得。先不急着谈任务——你今天在小屋里过得怎么样？"
        suggestions = ["你还记得那件事，是因为哪一个细节？", "我们先把今天眼前这件事商量清楚，好吗？", "上次没说完的部分，你现在愿意多说一点吗？"]
        stage_direction = f"{pronoun}给你留出身边的位置"
    typed = [
        {"type": suggestion_type, "text": text, "style": "mainline-gradient" if suggestion_type == "mainline" else suggestion_type, "action": "prefill-message" if suggestion_type == "deeper" else "send-message"}
        for suggestion_type, text in zip(("followup", "mainline", "deeper"), suggestions)
    ]
    return {
        "mode": conversation["conversationMode"], "opening": opening,
        "stageDirection": stage_direction, "suggestions": suggestions, "typedSuggestions": typed,
    }


def build_chat_opening_messages(card: dict, snapshot: dict, player_card: dict | None = None) -> list[dict[str, str]]:
    memories, conversation = _conversation_context(card, snapshot)
    context = {
        "scene": conversation,
        "playerPerspective": {
            "id": player_card["id"], "name": player_card["names"]["primary"],
            "publicFacts": _confirmed_public_facts(player_card),
            "voice": player_card.get("voice", {}),
        } if player_card else snapshot["player"],
        "characterPublicIdentity": {
            "id": card["id"], "name": card["names"]["primary"], "mbti": card["mbti"],
            "identity": card.get("identity"), "sourceFacts": _confirmed_public_facts(card),
            "publicMask": card["psychology"]["publicMask"], "currentGoals": card["drives"]["currentGoals"],
            "voice": card["voice"], "boundaries": card["psychology"]["boundaries"],
        },
        "recentMemories": [
            {key: item.get(key) for key in ("summary", "interpretation", "rawQuote", "agentReply", "attitude")}
            for item in memories
        ],
    }
    contract = {"opening": "30-140字自然开场", "stageDirection": "4-30字可见动作", "suggestions": ["三条4-30字玩家可直接说的话"]}
    system = """你为恋综中的一次 1 对 1 私聊写开场，不写后台状态，也不修改剧情。
	首次打开：角色要像真人恋综初次单聊，先直接说姓名，以及人物卡明确允许公开的年龄、职业或日常背景，再说一句参加节目的来意；接着从现场小事问一个容易回答的问题。禁止谜语、云里雾里、抽象试探，也不能把“我很紧张”当作全部人设。不要一上来索要秘密、推动任务、调情审问或说教。
首聊动作和问题只能取自 scene.title / scene.sceneText 已经出现的现场，或人物卡明确允许的随身习惯；不要新增咖啡、饮品、桌签、精确到场分钟数、地图或线索。
再次打开：只自然回收一条真实 recentMemories，再问候此刻；不要复读完整旧对白，不要说“我记住了你的参数/记忆”。
三条建议语是玩家可以直接说的话，必须符合 playerPerspective。由浅入深：打招呼或自我介绍、轻松小问题、连接当前场景的问题。不能替玩家承诺、告白或编造职业；职业字段未确认时完全不提职业。若建议语让玩家自报姓名，只能使用 playerPerspective.name，绝不能另造名字。
不得编造人物卡外的职业、创伤、前任或节目事实。只输出 JSON。"""
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"context": context, "contract": contract}, ensure_ascii=False)}]


def validate_chat_opening(card: dict, snapshot: dict, payload: dict, player_card: dict | None = None) -> dict:
    memories, conversation = _conversation_context(card, snapshot)
    opening = str(payload.get("opening") or "").strip()
    stage_direction = str(payload.get("stageDirection") or "").strip()
    suggestions = payload.get("suggestions")
    if not 20 <= len(opening) <= 180:
        raise ValueError("私聊开场长度不符合合同")
    if not 4 <= len(stage_direction) <= 50:
        raise ValueError("私聊开场动作长度不符合合同")
    if not isinstance(suggestions, list) or len(suggestions) != 3:
        raise ValueError("私聊建议语必须正好三条")
    suggestions = [str(item).strip() for item in suggestions]
    if len(set(suggestions)) != 3 or any(not 4 <= len(item) <= 60 for item in suggestions):
        raise ValueError("私聊建议语重复或长度不符合合同")
    forbidden = ("关系数值", "写入记忆", "触发事件", "DeepSeek", "Agent", "API", "第二把钥匙")
    if any(term in opening + stage_direction + "".join(suggestions) for term in forbidden):
        raise ValueError("私聊开场暴露后台或旧任务")
    if not memories and card["names"]["primary"] not in opening:
        raise ValueError("首次私聊没有介绍角色姓名")
    if not memories:
        cold_start_copy = opening + stage_direction + "".join(suggestions)
        if any(term in cold_start_copy for term in ("线索", "任务", "地图", "钥匙", "桌签", "节目组秘密")):
            raise ValueError("首次私聊从寒暄跳到了任务或秘密")
        if re.search(r"(?:刚到|来了|入住).{0,4}[一二三四五六七八九十百\d]+分钟", cold_start_copy):
            raise ValueError("首次私聊编造了精确到场时间")
    player_name = player_card["names"]["primary"] if player_card else str(snapshot.get("player", {}).get("displayName") or "").strip()
    for suggestion in suggestions:
        for claimed_name in re.findall(r"我叫([\u4e00-\u9fff·]{2,8})", suggestion):
            if player_name and claimed_name != player_name:
                raise ValueError("私聊建议语替主角编造了错误姓名")
    if not memories and player_card:
        if not any(re.search(r"我(?:叫|是)\s*" + re.escape(player_name), suggestion) for suggestion in suggestions):
            raise ValueError("首次私聊建议语没有保持玩家身份")
        occupation = player_card.get("sourceProfile", {}).get("facts", {}).get("occupation")
        unknown_job = not isinstance(occupation, str) or any(term in occupation for term in ("待剧情", "待正式确认", "运行时职业待"))
        if unknown_job and any(re.search(r"我(?:是|在|做).{0,12}(?:工作|职业|行业|相关)", suggestion) for suggestion in suggestions):
            raise ValueError("首次私聊建议语替玩家编造了职业")
    if not memories:
        if card["mbti"] not in opening:
            raise ValueError("首次私聊没有清楚介绍 MBTI 或性格")
        if not any(anchor in opening for anchor in PUBLIC_BACKGROUND_ANCHORS[card["id"]]):
            raise ValueError("首次私聊没有介绍人物卡允许公开的工作或日常背景")
        if not any(marker in opening for marker in ("来这里", "参加", "这次", "这七天")):
            raise ValueError("首次私聊没有说清参加节目的来意")
        if any(term in opening for term in ("你猜", "秘密", "以后会知道", "先看你怎么回答", "试探", "看清一个人")):
            raise ValueError("首次私聊使用了谜语或抽象试探")
    typed = [
        {"type": suggestion_type, "text": text, "style": "mainline-gradient" if suggestion_type == "mainline" else suggestion_type, "action": "prefill-message" if suggestion_type == "deeper" else "send-message"}
        for suggestion_type, text in zip(("followup", "mainline", "deeper"), suggestions)
    ]
    return {"mode": conversation["conversationMode"], "opening": opening, "stageDirection": stage_direction, "suggestions": suggestions, "typedSuggestions": typed}


def extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start < 0:
            raise RuntimeError("DeepSeek did not return a JSON object")
        try:
            data, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        except json.JSONDecodeError as error:
            raise RuntimeError("DeepSeek did not return a complete JSON object") from error
    if not isinstance(data, dict):
        raise RuntimeError("DeepSeek returned a non-object payload")
    return data
