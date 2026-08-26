#!/usr/bin/env python3
"""Build the local-only Heart Journey R6 Seedance production plan.

This script never contacts a provider. It inventories the reviewed runtime media,
creates exact 480p director prompts, and writes a fail-closed paid-batch manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNTIME_MANIFEST = ROOT / "media/runtime-media-manifest.json"
CHARACTER_CARDS = ROOT / "content/character_cards.v3.json"
PRICING_EVIDENCE = HERE / "pricing-evidence-2026-08-26.json"
PROMPT_DIR = HERE / "prompts-r6"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


NEW_CAST = [
    {
        "id": "luyao",
        "displayName": "陆遥",
        "mbti": "INTJ",
        "gender": "female",
        "counterpartOf": "shenmo",
        "occupationDraft": "智能硬件产品负责人",
        "mediaDirection": "冷静利落、主动决策，用极轻的冷幽默缓解紧张",
    },
    {
        "id": "yecheng",
        "displayName": "叶澄",
        "mbti": "ISFJ",
        "gender": "female",
        "counterpartOf": "linyu",
        "occupationDraft": "古籍修复师",
        "mediaDirection": "安静有礼、重视物件和承诺留下的痕迹，原则处坚定",
    },
    {
        "id": "tangli",
        "displayName": "唐梨",
        "mbti": "ESTP",
        "gender": "female",
        "counterpartOf": "chengye",
        "occupationDraft": "户外纪录片现场制片人",
        "mediaDirection": "明快直接、反应快，行动力来自现场责任感而非炫技",
    },
    {
        "id": "wenxu",
        "displayName": "温序",
        "mbti": "INTP",
        "gender": "female",
        "counterpartOf": "guyan",
        "occupationDraft": "城市气候数据研究员",
        "mediaDirection": "联想跳跃、有轻微黑色幽默，像在验证一个有趣假设",
    },
    {
        "id": "hechuan",
        "displayName": "贺川",
        "mbti": "INFJ",
        "gender": "male",
        "counterpartOf": "jiangwan",
        "occupationDraft": "纪录片剪辑师",
        "mediaDirection": "温和沉静，擅长把被忽略的人重新带回对话",
    },
    {
        "id": "peiran",
        "displayName": "裴然",
        "mbti": "ENFP",
        "gender": "male",
        "counterpartOf": "jiangmi",
        "occupationDraft": "儿童博物馆体验策展人",
        "mediaDirection": "松弛好奇、反应快，能让陌生人自然参与同一个游戏",
    },
    {
        "id": "lichuan",
        "displayName": "黎川",
        "mbti": "ESFJ",
        "gender": "male",
        "counterpartOf": "sunnian",
        "occupationDraft": "精品酒店餐饮运营经理",
        "mediaDirection": "大方可靠、现场统筹力强，亲切但有自己的秩序",
    },
    {
        "id": "qiaolan",
        "displayName": "乔岚",
        "mbti": "ISTP",
        "gender": "female",
        "counterpartOf": "chensu",
        "occupationDraft": "舞台机械工程师",
        "mediaDirection": "话少、稳、手上有办法，幽默干脆但不冷漠",
    },
]


SCHEMES = [
    {
        "id": "F-A-jiangmi",
        "gender": "female",
        "leadId": "jiangmi",
        "leadName": "姜米",
        "leadMbti": "ENFP",
        "leadOccupation": "内容策划（待人物卡最终确认）",
        "supportId": "chensu",
        "supportName": "陈叙",
        "status": "existing-approved-set-with-one-held-introduction-replacement",
        "selectionBucket": ["ENFP", "ESFJ", "ISFJ", "ESTP"],
    },
    {
        "id": "F-B-luyao",
        "gender": "female",
        "leadId": "luyao",
        "leadName": "陆遥",
        "leadMbti": "INTJ",
        "leadOccupation": "智能硬件产品负责人",
        "supportId": "chensu",
        "supportName": "陈叙",
        "status": "planned-new",
        "selectionBucket": ["INTJ", "INFJ", "INTP", "ISTP"],
    },
    {
        "id": "M-A-chengye",
        "gender": "male",
        "leadId": "chengye",
        "leadName": "程野",
        "leadMbti": "ESTP",
        "leadOccupation": "极限运动品牌创始人",
        "supportId": "jiangmi",
        "supportName": "姜米",
        "status": "planned-new",
        "selectionBucket": ["ESTP", "ISTP", "ESFJ", "ISFJ"],
    },
    {
        "id": "M-B-hechuan",
        "gender": "male",
        "leadId": "hechuan",
        "leadName": "贺川",
        "leadMbti": "INFJ",
        "leadOccupation": "纪录片剪辑师",
        "supportId": "jiangwan",
        "supportName": "江晚",
        "status": "planned-new",
        "selectionBucket": ["ENFP", "INFJ", "INTJ", "INTP"],
    },
]


# 25 runtime event slots. D1-A3B is a local montage built from reviewed Seedance
# sources, so the new three schemes still have a real file but no redundant job.
EVENTS = [
    ("D1-A1-island-hotel-establish", "day1.arrival-context", "海岛酒店初见", 6, "solo", "接驳车停在海岛酒店门前；主角下车，海风吹动衣角，抬头看见亮灯的小屋", "海风、远处浪声、行李轮落地声"),
    ("D1-A2-villa-entry", "day1.villa-arrival", "走进心动小屋", 6, "solo", "主角推门、放稳行李，与客厅里的人自然点头问好；其他人只用背影或强虚焦", "开门声、室内寒暄、自然轻笑"),
    ("D1-A3-cast-introductions", "day1.introductions", "第一次说出自己是谁", 12, "solo-speech", "主角坐在客厅围谈区，用真人口语完成一次清楚自我介绍，眼神会自然扫过在场的人", "character-speech"),
    ("D1-A3B-cast-first-impressions", "day1.cast-first-impressions", "初见印象混剪", 8, "local-composite", "从主角自我介绍和搭档动态肖像剪出两次自然反应，作为进入破冰前的小结", "延续室内声床；不新增生成"),
    ("D1-A4-icebreaker-selection", "day1.icebreaker-choice", "抽取破冰搭档", 4, "pair", "桌面摆放无字生活场景卡；主角先选卡，再与搭档确认视线，动作因果清楚", "卡片摩擦、椅子轻响、低声讨论"),
    ("D1-A5-guided-smalltalk", "day1.guided-chat", "三分钟认识一个人", 4, "pair", "主角和搭档在露台并肩聊天；先从姓名与来意开始，再自然问一个具体生活问题", "海风、近距离寒暄、一声自然轻笑"),
    ("D1-A6-first-dinner-team", "day1.team-up", "第一次餐桌分工", 6, "pair", "两人在厨房分洗切摆盘；一次递碗与接碗形成自然停顿，动作生活化", "洗菜水声、碗碟轻碰、短句协作"),
    ("D1-A7-heart-message", "day1.anonymous-letter", "睡前第一条心动短信", 4, "solo", "夜里主角坐在床边拿起节目组旧手机，犹豫后输入并发送，屏幕不可读", "夜间海风、床单摩擦、发送提示音"),
    ("D2-A1-memory-callback", "day2.morning-callback", "第二天的记忆回声", 4, "pair", "早餐桌边，搭档用一个昨晚发生的具体小动作回扣主角，主角先意外再笑", "杯勺轻响、早餐室内声、自然对话碎片"),
    ("EV-KITCHEN-two-person-shift", "story.kitchen.two-person-shift", "只够两个人站下的厨房", 6, "pair", "狭窄厨房里两人交错取物、让路、合作把食材装盘；避免摆拍式对视", "切菜、油锅、衣料摩擦、短句配合"),
    ("EV-RULES-house-friction", "story.house.rules-friction", "被改掉的值日表", 4, "pair", "主角发现无字值日板被挪动，与搭档对照现场物品，克制地交换意见", "白板笔、纸张、远处室内声"),
    ("EV-SIGNAL-first-anonymous-message", "story.signal.first-anonymous-message", "第一封匿名心动短信", 4, "solo", "主角独自读到一条不可见文字的短信，表情从好奇到确认；不展示可读屏幕", "手机轻震、夜间房间声、呼吸"),
    ("EV-IDENTITY-profession-reveal", "story.identity.profession-reveal", "职业卡翻面", 4, "solo", "主角把无字职业卡翻面放回桌上，抬眼观察其他人的反应，保持自然克制", "卡片、杯子、多人低声反应"),
    ("EV-DATE-blind-box", "story.date.blind-box", "没有名字的约会盲盒", 4, "solo", "主角从三个无字盒子中选一个，打开后只看见象征地点的小物件，不出现文字", "纸盒、海风、短促惊喜声"),
    ("EV-DATE-mutual-signal", "story.date.mutual-signal", "双向信号后的二十分钟", 6, "pair", "两人在海边步道散步，谈话中自然放慢脚步并交换一次明确邀请，不拥吻", "浪声、脚步、远处单车铃、自然短句"),
    ("EV-MISSED-empty-seat", "story.missed-timing.empty-seat", "被留空的座位", 4, "solo", "主角来到约定地点，看见对面空椅；坐下后把另一杯水推回桌心，留下克制遗憾", "椅脚、海风、远处人声"),
    ("EV-CARE-breakfast-callback", "story.care.breakfast-callback", "没有署名的早餐", 4, "pair", "主角发现一份按自己偏好准备的早餐，循着动作看向正在收拾台面的搭档", "咖啡、餐具、清晨鸟声、轻声问候"),
    ("EV-TRIANGLE-reverse-invite", "story.triangle.reverse-invite", "同一时刻的两张邀约卡", 6, "pair", "主角同时收到两只无字信封，搭档在远处看见；镜头在手、目光和停顿间建立张力", "信封、脚步停住、聚会环境声"),
    ("EV-BRIDGE-hidden-courage", "story.challenge.water-bridge", "水面上的最后一块踏板", 6, "pair", "浅水挑战中主角在缺失踏板前犹豫，搭档先下水站稳再伸手，主角确认后借力通过", "水声、队友呼喊、急促呼吸；无煽情配乐"),
    ("EV-GROUP-truth-firepit", "story.group.truth-firepit", "围炉真心话", 6, "pair", "篝火旁主角抽到无字问题卡，停顿后说出一句具体真话；搭档给出安静回应", "篝火、海风、围坐人群的自然反应"),
    ("EV-BOMBSHELL-ninth-card", "story.bombshell.ninth-card", "第九张人物卡", 4, "pair", "工作人员把第九只无字信封放到桌心；主角和搭档先后意识到有新嘉宾", "门铃、信封落桌、真实吸气与议论"),
    ("EV-PAST-consent-reveal", "story.past.consent-reveal", "由本人决定是否翻开的旧信", 4, "pair", "主角把旧信放在桌上，先询问搭档是否愿意听；得到点头后才翻开，不显示内容", "纸张、雨声或海风、低声确认"),
    ("EV-TRIP-last-two-days", "story.trip.last-two-days", "告白前的两日一夜", 6, "pair", "两人收拾轻便行李、上车、抵达海边旅店，用三个连贯镜头表现共同旅行", "拉链、车门、路声、海风、松弛笑声"),
    ("EV-FINAL-unsent-letter", "story.final.unsent-letter", "可以不寄出的信", 4, "solo", "告白前夜主角写完一封不可读的信，折好后在寄出与留在桌上之间停顿", "笔尖、纸张、窗外海浪、呼吸"),
    ("EV-FINAL-confession-day", "story.final.confession-day", "最终告白日", 6, "pair", "主角走向等待的人，停在一步距离清楚表达选择；对方先确认再伸手，不强制牵手成功", "海风、脚步、清楚但简短的现场话语"),
]


SELF_INTRO = {
    "F-A-jiangmi": "大家好，我是姜米，做内容策划。平时挺爱热闹，也很容易被新鲜的人和事吸引。希望这七天能和大家慢慢熟起来。",
    "F-B-luyao": "大家好，我是陆遥，做智能硬件产品。平时习惯先把事情想清楚，不过今天想允许自己少做一点计划。很高兴认识大家。",
    "M-A-chengye": "大家好，我是程野，做户外运动品牌。平时闲不住，也喜欢和不同的人打交道。希望这七天大家别客气，有事一起上。",
    "M-B-hechuan": "大家好，我是贺川，做纪录片剪辑。平时话不算多，但很喜欢听人把一件事慢慢讲完。希望这七天能真正认识几个人。",
}


def timeline(duration: int, scene: str) -> list[str]:
    if duration == 4:
        bounds = [(0, 1), (1, 3), (3, 4)]
    elif duration == 6:
        bounds = [(0, 2), (2, 4), (4, 6)]
    elif duration == 8:
        bounds = [(0, 2), (2, 6), (6, 8)]
    elif duration == 10:
        bounds = [(0, 3), (3, 8), (8, 10)]
    else:
        bounds = [(0, 3), (3, 9), (9, 12)]
    return [
        f"{bounds[0][0]}-{bounds[0][1]}s【推镜环境中景】先交代空间与动作起因：{scene}。",
        f"{bounds[1][0]}-{bounds[1][1]}s【平稳横移中近景】完成核心动作与人物反应，动作先后关系清楚，表演生活化。",
        f"{bounds[2][0]}-{bounds[2][1]}s【轻推近后停稳】落在一个可继续剧情的目光、手部动作或明确停顿；末帧稳定至少0.6秒。",
    ]


def portrait_prompt(card: dict) -> str:
    return f"""4秒竖屏写实电影动态肖像，9:16，480p，24fps。参考图唯一人物是{card['displayName']}，{card['mbti']}，{card['occupationDraft']}；严格保持参考图的脸型、五官、发型、年龄感和{('女性' if card['gender']=='female' else '男性')}性别表达。海岛酒店落日露台，柔和粉金侧光、真实皮肤与衣料、浅景深。0-1s人物在做一件自然小事；1-3s听见镜头外有人叫名字，抬眼看向镜头；3-4s出现符合人物的轻微表情并停稳。人物气质：{card['mediaDirection']}。主体位于中央60%安全区，顶部和底部留干净画面供运行时身份牌与对话叠加。无台词、无可读文字、无Logo、无水印、无陌生正脸、无坏手、无夸张变脸、无手机界面。generate_audio=false。"""


def event_prompt(event: tuple, scheme: dict) -> str:
    asset_id, _, title, duration, cast_mode, scene, audio = event
    ref_note = (
        f"参考板只包含主角{scheme['leadName']}和搭档{scheme['supportName']}；两张脸不得融合或互换。"
        if cast_mode == "pair"
        else f"参考图唯一人物是主角{scheme['leadName']}；其他人只能是背影、裁切肩部或强虚焦轮廓。"
    )
    speech = ""
    if cast_mode == "solo-speech":
        speech = f"\n【唯一清楚台词】{scheme['leadName']}用自然真人口语说：‘{SELF_INTRO[scheme['id']]}’ 禁止旁白替读，口型、音色与说话者一致。"
    timeline_text = "\n".join(timeline(duration, scene))
    return f"""{duration}秒竖屏写实电影恋爱观察综艺短片，9:16，480p，24fps，原生有声，无水印。事件：{title}。{ref_note}

【State In】{scene}的动作尚未开始，人物关系只保留此前已发生的熟悉度，不提前告白或重置关系。
【State Out】本事件的核心动作已经完成，画面停在可由正文旁白承接的结果上；不得擅自生成后续选择、告白结果或新人物。

【精确时间线】
{timeline_text}{speech}

【声音】首次播放保留原生声：{audio}。禁止画外旁白、罐头笑声、平台提示音和抢对白的配乐；循环播放由运行时默认静音，不烘焙第二套音轨。

【画面与身份】9:16竖屏、480p、稳定电影运镜、低对比柔和胶片色、真实皮肤与布料、动作有先因后果。主角{scheme['leadName']}始终是最清楚、最主要的可辨人物，且主角性别为{('女性' if scheme['gender']=='female' else '男性')}。主体位于中央60%安全区，顶部和底部留干净画面供运行时身份牌、旁白与选项覆盖。禁止生成任何可读文字、姓名牌、MBTI、字幕、Logo、手机UI、进度条、伪字、陌生清晰正脸、脸融合、换脸、坏手、多余手指、重复物体、跳切式瞬移和机械摆拍。身份牌由前端叠加3秒后渐隐，不烘焙进视频。"""


def main() -> None:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    for stale_prompt in PROMPT_DIR.glob("*.txt"):
        stale_prompt.unlink()
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    runtime_assets = {item["id"]: item for item in runtime["assets"]}

    # Character expansion is a proposal only. The full cards and identity anchors
    # must be approved separately before any paid Seedance call.
    expansion = {
        "schemaVersion": "heart-journey/gender-doubled-cast-proposal-v1",
        "status": "proposal-not-canonical",
        "rule": "Each represented MBTI has one male and one female playable character.",
        "currentCardSource": {
            "path": "../../../content/character_cards.v3.json",
            "sha256": digest(CHARACTER_CARDS),
            "currentCount": 8,
        },
        "newCharacters": NEW_CAST,
        "resultingRoster": {"count": 16, "male": 8, "female": 8, "mbtiPairs": 8},
        "blockingPrerequisites": [
            "Generate and human-approve one original still identity anchor for every new character.",
            "Generate and review full interoperable character cards before treating draft names, jobs or voices as canon.",
            "Record likeness and voice consent references; this plan intentionally leaves rights pending.",
        ],
    }
    dump(HERE / "character-expansion.json", expansion)

    existing_event_files = []
    for event in EVENTS:
        asset_id = event[0]
        current = runtime_assets.get(asset_id)
        existing_event_files.append(
            {
                "assetId": asset_id,
                "eventId": event[1],
                "title": event[2],
                "plannedDurationSeconds": event[3],
                "existingPath": current.get("path") if current else None,
                "existingSha256": current.get("sha256") if current else None,
                "existingStatus": current.get("status") if current else "missing",
                "existingQaVerdict": current.get("qaVerdict") if current else None,
                "r5ContentContractVerdict": current.get("r5ContractVerdict") if current else None,
                "reuseVerdictForFA": (
                    "replace-held-introduction"
                    if asset_id == "D1-A3-cast-introductions"
                    else "reuse-approved"
                ),
            }
        )

    coverage = {
        "schemaVersion": "heart-journey/gender-rotation-r6-coverage-v1",
        "eventSlotCount": len(EVENTS),
        "schemeCount": len(SCHEMES),
        "requiredRuntimeOutputs": len(EVENTS) * len(SCHEMES),
        "existingRuntimeReuseOutputs": 25,
        "existingQaApprovedReusableOutputs": 24,
        "existingHeldOutputs": 1,
        "plannedProviderOutputs": 73,
        "plannedLocalCompositeOutputs": 3,
        "coverageAfterQa": "100/100 only after all planned provider outputs and local composites pass QA",
        "events": existing_event_files,
        "schemes": SCHEMES,
        "routingContract": {
            "hardRule": "selectedScheme.gender == player.selectedGender",
            "femaleSchemes": ["F-A-jiangmi", "F-B-luyao"],
            "maleSchemes": ["M-A-chengye", "M-B-hechuan"],
            "stableRotation": "Within the matching-gender pair, choose by a stable hash of playerCharacterId + eventId; never route across gender.",
            "claimBoundary": "R6 guarantees same-gender protagonist imagery, not exact selected-face identity for all 16 characters. Exact-face event coverage is a later expansion.",
        },
    }
    dump(HERE / "event-coverage.json", coverage)

    shots = []
    local_composites = []
    for scheme in SCHEMES:
        if scheme["id"] == "F-A-jiangmi":
            selected_events = [event for event in EVENTS if event[0] == "D1-A3-cast-introductions"]
        else:
            selected_events = [event for event in EVENTS if event[4] != "local-composite"]

        for event in selected_events:
            asset_id, event_id, title, duration, cast_mode, _, audio = event
            shot_id = f"{asset_id}--{scheme['id']}--r6"
            prompt_path = PROMPT_DIR / f"{shot_id}.txt"
            prompt_path.write_text(event_prompt(event, scheme) + "\n", encoding="utf-8")
            lead_ref = (
                f"refs/characters/{scheme['leadId']}.jpg"
                if scheme["leadId"] in {item["id"] for item in NEW_CAST}
                else f"../../../frontend/public/media/portraits/{scheme['leadId']}.jpg"
            )
            pair_ref = (
                "../cast-perspective-r5/refs-r5/pair--chengye-jiangmi.jpg"
                if scheme["id"] == "M-A-chengye"
                else f"refs/pairs/{scheme['id']}.jpg"
            )
            reference_image = pair_ref if cast_mode == "pair" else lead_ref
            ref_path = HERE / reference_image
            shots.append(
                {
                    "id": shot_id,
                    "kind": "event-rotation-candidate",
                    "schemeId": scheme["id"],
                    "eventAssetId": asset_id,
                    "eventId": event_id,
                    "title": title,
                    "leadCharacterId": scheme["leadId"],
                    "leadGender": scheme["gender"],
                    "supportCharacterIds": [scheme["supportId"]] if cast_mode == "pair" else [],
                    "reference_image": reference_image,
                    "referenceStatus": "present" if ref_path.exists() else "pending",
                    "prompt_file": f"prompts-r6/{prompt_path.name}",
                    "promptSha256": digest(prompt_path),
                    "ratio": "9:16",
                    "resolution": "480p",
                    "duration": duration,
                    "generate_audio": True,
                    "audioMode": "character-speech" if cast_mode == "solo-speech" else "ambient-and-natural-dialogue",
                    "watermark": False,
                    "rightsStatus": "pending",
                    "likenessConsentRefIds": [],
                    "voiceConsentRefIds": [],
                    "output_name": f"{asset_id}--{scheme['id']}--r6-candidate.mp4",
                }
            )

        if scheme["id"] != "F-A-jiangmi":
            local_composites.append(
                {
                    "id": f"D1-A3B-cast-first-impressions--{scheme['id']}--r6",
                    "eventAssetId": "D1-A3B-cast-first-impressions",
                    "schemeId": scheme["id"],
                    "duration": 8,
                    "inputs": [
                        f"D1-A3-cast-introductions--{scheme['id']}--r6-candidate.mp4",
                        f"../../../frontend/public/media/video/CHAR-{scheme['supportId']}-portrait.mp4",
                    ],
                    "assembly": "Use 0-5s of the reviewed voiced introduction, then a 1s room-tone bridge and 2s support reaction; preserve first-play audio and produce a muted-loop-safe tail.",
                    "output_name": f"D1-A3B-cast-first-impressions--{scheme['id']}--r6-candidate.mp4",
                    "qaStatus": "pending",
                }
            )

    for card in NEW_CAST:
        shot_id = f"CHAR-{card['id']}-portrait--r6"
        prompt_path = PROMPT_DIR / f"{shot_id}.txt"
        prompt_path.write_text(portrait_prompt(card) + "\n", encoding="utf-8")
        ref = f"refs/characters/{card['id']}.jpg"
        shots.append(
            {
                "id": shot_id,
                "kind": "dynamic-portrait-candidate",
                "schemeId": None,
                "eventAssetId": None,
                "leadCharacterId": card["id"],
                "leadGender": card["gender"],
                "supportCharacterIds": [],
                "reference_image": ref,
                "referenceStatus": "present" if (HERE / ref).exists() else "pending",
                "prompt_file": f"prompts-r6/{prompt_path.name}",
                "promptSha256": digest(prompt_path),
                "ratio": "9:16",
                "resolution": "480p",
                "duration": 4,
                "generate_audio": False,
                "audioMode": "silent-loop",
                "watermark": False,
                "rightsStatus": "pending",
                "likenessConsentRefIds": [],
                "voiceConsentRefIds": [],
                "output_name": f"CHAR-{card['id']}-portrait--r6-candidate.mp4",
            }
        )

    total_seconds = sum(item["duration"] for item in shots)
    manifest = {
        "schemaVersion": "heart-journey/gender-rotation-r6-manifest-v1",
        "planId": "gender-rotation-r6-480p",
        "planStatus": "local-plan-blocked-no-provider-submission",
        "doNotSubmit": True,
        "sourceBindings": {
            "runtimeMediaManifest": {
                "path": "../../runtime-media-manifest.json",
                "sha256": digest(RUNTIME_MANIFEST),
            },
            "characterCards": {
                "path": "../../../content/character_cards.v3.json",
                "sha256": digest(CHARACTER_CARDS),
            },
            "pricingEvidence": {
                "path": "pricing-evidence-2026-08-26.json",
                "sha256": digest(PRICING_EVIDENCE),
                "status": "same-day-settled-account-evidence-plus-live-model-probe-not-price-guarantee",
            },
        },
        "defaults": {
            "provider": "fumin",
            "model": "seedance-2.0-mini",
            "ratio": "9:16",
            "resolution": "480p",
            "durationRangeSeconds": [4, 15],
            "plannedDurationRangeSeconds": [4, 12],
            "generate_audio": True,
            "watermark": False,
            "concurrency": 2,
            "maxApiRetry": 0,
            "candidateRoot": ".work-candidates",
        },
        "scope": {
            "eventSlotCount": 25,
            "rotationSchemeCount": 4,
            "requiredRuntimeEventOutputs": 100,
            "existingRuntimeReuseEventOutputs": 25,
            "existingQaApprovedReusableEventOutputs": 24,
            "existingHeldEventOutputs": 1,
            "providerEventJobs": 73,
            "providerDynamicPortraitJobs": 8,
            "providerJobCount": len(shots),
            "providerDurationSeconds": total_seconds,
            "localCompositeCount": len(local_composites),
            "resultingRuntimeEventCoverage": "100/100 after QA",
        },
        "schemes": SCHEMES,
        "identityOverlayContract": {
            "implementation": "runtime-overlay-not-baked-into-video",
            "durationSeconds": 3,
            "transition": "fade-out",
            "fields": ["displayName", "occupation", "mbti"],
            "reason": "Avoid generated pseudo-text and keep labels localizable and correct.",
        },
        "routingContract": coverage["routingContract"],
        "costEstimate": {
            "currency": "CNY",
            "pricingStatus": "same-day-account-evidence-bound-not-a-contractual-price-guarantee",
            "conservativeSameAccountSample": {
                "resolution": "480p",
                "durationSeconds": 4,
                "actualQuotaRaw": 617277,
                "quotaPerUnit": 500000,
                "priceCnyPerQuotaUnit": 0.4,
                "derivedSampleCostCny": 0.4938216,
                "derivedUnitPriceCnyPerSecond": 0.1234554,
                "pricingEvidenceRef": "pricing-evidence-2026-08-26.json#derived",
            },
            "estimatedIncrementalSpendCny": round(total_seconds * 0.1234554, 7),
            "suggestedZeroRetryHardCapCny": 60,
            "perSecondFormula": f"{total_seconds} * verifiedUnitPricePerSecond",
            "perTaskFormula": f"{len(shots)} * verifiedUnitPricePerTask",
            "manualReviewThresholdCny": 200,
            "perSecondThresholdBreakEvenCny": round(200 / total_seconds, 6),
            "perTaskThresholdBreakEvenCny": round(200 / len(shots), 6),
            "cumulativeSpendCnyFloor": 200.01,
            "cumulativeSpendEvidenceRef": "cumulative-spend-floor-2026-08-26.json",
            "cumulativeSpendThresholdState": "known-to-exceed-200-exact-ledger-value-not-claimed",
            "incrementalSpendCny": round(total_seconds * 0.1234554, 7),
            "projectedCumulativeSpendCnyFloor": round(200.01 + total_seconds * 0.1234554, 7),
            "manualOverBudgetApprovalRef": "budget-authorization-2026-08-26.md",
            "manualOverBudgetMaxAmountCny": 60,
        },
        "rights": {
            "status": "approved-for-private-candidate-generation",
            "commercialUseApproved": False,
            "publicReleaseApproved": False,
            "likenessConsentRefIds": ["original-fictional-r6-anchors:anchor-candidates-qa-2026-08-26.md"],
            "voiceConsentRefIds": ["synthetic-audio:no-human-voice-reference"],
            "referenceRightsRefIds": ["rights-review-2026-08-26.md"],
            "claimBoundary": "Approval is limited to private R6 candidate generation; commercial use and public release remain unapproved.",
        },
        "blockingConditions": [
            "Planning manifest remains doNotSubmit=true; only the guarded paid runner may execute after validating the separate approval record.",
            "Provider pricing is evidence-based, not guaranteed; the runner must stop before the R6 settled-cost ledger reaches CNY 60.",
            "Every provider success remains a candidate and requires identity, audio, motion, mobile and runtime-routing QA before integration.",
            "Commercial use and public release remain outside this approval.",
        ],
        "shots": shots,
        "localComposites": local_composites,
    }
    dump(HERE / "manifest.r6.json", manifest)

    missing_reference_paths = {
        item["reference_image"] for item in shots if item["referenceStatus"] != "present"
    }
    print(
        json.dumps(
            {
                "providerJobs": len(shots),
                "providerDurationSeconds": total_seconds,
                "localComposites": len(local_composites),
                "runtimeEventOutputsAfterQa": 100,
                "missingReferenceShotCount": sum(item["referenceStatus"] != "present" for item in shots),
                "missingReferenceFileCount": len(missing_reference_paths),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
