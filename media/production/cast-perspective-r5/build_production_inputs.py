#!/usr/bin/env python3
"""Build the complete local-only R5 Seedance production input pack.

The script performs no network requests and never reads provider credentials.
It derives exactly the ``requiresGeneration`` subset from
``runtime-variant-matrix.json``, writes one director-grade prompt per semantic
master, builds local text-free composite identity boards when more than one
recognizable character is required, and emits ``manifest.r5.json`` with a hard
``doNotSubmit=true`` gate.

Original portrait files are read-only inputs.  They are never changed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
RUNTIME_MATRIX = ROOT / "runtime-variant-matrix.json"
CHARACTER_CARDS = PROJECT / "content" / "character_cards.v3.json"
PORTRAITS = PROJECT / "frontend" / "public" / "media" / "portraits"
PROMPTS = ROOT / "prompts-r5"
REFS = ROOT / "refs-r5"
MANIFEST = ROOT / "manifest.r5.json"

CHARACTER_ORDER = [
    "shenmo",
    "linyu",
    "chengye",
    "guyan",
    "jiangwan",
    "jiangmi",
    "sunnian",
    "chensu",
]

DISPLAY = {
    "shenmo": "沈墨",
    "linyu": "林屿",
    "chengye": "程野",
    "guyan": "顾言",
    "jiangwan": "江晚",
    "jiangmi": "姜米",
    "sunnian": "苏念",
    "chensu": "陈叙",
}

INTRO_LINES = {
    "shenmo": "大家好，我是沈墨，二十九岁，做投资。我话不算多，会先观察再靠近。来这里想认真认识一个人，也练习把重要的话早点说出来。",
    "linyu": "大家好，我叫林屿，二十七岁，是建筑工程师。我比较慢热，也很容易记住生活里的小习惯。希望这七天，我能更主动一点。",
    "chengye": "嗨，我是程野，二十六岁，做极限运动品牌。我喜欢把当下过得有意思，也不太怕冷场。想聊天或者想出去玩，都可以找我。",
    "guyan": "大家好，我叫顾言，二十五岁，是游戏策划。刚见面我可能有点安静，熟了话会多。希望在这里认识真实的人，也让大家看到真实的我。",
    "jiangwan": "大家好，我是江晚，二十六岁，心理咨询师。放心，我不会随时分析大家。我喜欢认真听人说话，也想练习更勇敢地表达喜欢。",
    "jiangmi": "大家好，我是姜米，ENFP。我好奇心很重，喜欢热闹，也很吃真诚的相处。希望这七天能和大家好好认识，看看会发生什么故事。",
    "sunnian": "大家好，我是苏念，二十五岁，是插画师。我喜欢照顾身边人的小感受，也想练习别总把自己放在最后。希望大家都能自在一点。",
    "chensu": "大家好，我是陈叙，二十七岁。工作先保留一点悬念。我话不多，更习惯先把眼前的事做好。来这里，就想认真认识大家。",
}

SHORT_INTROS = {
    "shenmo": "我是沈墨，做投资，慢热，但会认真听。",
    "linyu": "我是林屿，建筑工程师，很高兴认识大家。",
    "chengye": "我是程野，做极限运动品牌，欢迎来找我玩。",
    "guyan": "我是顾言，游戏策划，刚开始可能有点安静。",
    "jiangwan": "我是江晚，心理咨询师，大家不用紧张。",
    "jiangmi": "我是姜米，ENFP，好奇心比较重。",
    "sunnian": "我是苏念，插画师，希望大家都自在一点。",
    "chensu": "我是陈叙，话不多，但会认真做事。",
}


@dataclass(frozen=True)
class EventSpec:
    title: str
    setting: str
    state_in: str
    timeline: tuple[str, str, str, str, str]
    state_out: str
    audio_mode: str
    audio: str


EVENTS: dict[str, EventSpec] = {
    "day1.arrival-context": EventSpec(
        "抵达海岛酒店",
        "DAY 1 16:50，海岛酒店外木栈道，金色夕阳、真实海风、湿润木材与远处玻璃门暖光。",
        "{a}刚下接驳车，旅行箱在身侧，尚未踏进酒店。",
        (
            "0-3s【24mm高位下降接稳定器远景】海浪和酒店先建立地理关系，镜头落到{a}背后三分之二位置；头发和衣角只受真实海风推动。",
            "3-6s【35mm侧向跟拍中全景】{a}拉起旅行箱沿栈道行走，箱轮逐个越过木板接缝，先看海再确认酒店入口，不看镜头摆拍。",
            "6-9s【50mm前方倒退中景】镜头稳定后退，{a}抬头看亮灯的玻璃门，呼吸从兴奋转为一点紧张，步伐连续自然。",
            "9-12s【85mm手部与眼神交叉近景】手指握紧箱杆后松开，眼睛被侧光照亮；只表现一次克制的心理变化。",
            "12-15s【35mm背后缓推中全景】{a}停在门前，右手离门把约十厘米，海风和箱轮声自然衰减，尾帧稳定一秒，不提前开门。",
        ),
        "{a}抵达酒店门前但尚未进入，下一幕可从推门动作开始。",
        "ambient-only",
        "连续海浪、海风、远处海鸟与真实箱轮声；没有对白、旁白、音乐或罐头笑声。",
    ),
    "day1.villa-arrival": EventSpec(
        "走进心动小屋",
        "DAY 1 17:30，同一海岛别墅玄关和挑高客厅，门外夕阳、室内暖灯、玻璃与木地板材质真实。",
        "{a}站在门外握住门把；屋内嘉宾只以背影、肩部或强虚焦轮廓存在。",
        (
            "0-3s【35mm门内低机位缓推】门把下压、门向内打开，先看见{a}与旅行箱；门轴声和海风短暂进入室内。",
            "3-6s【28mm稳定器后退中全景】镜头随{a}跨过门槛，背景轮廓自然起身但没有第二张可辨认脸。",
            "6-9s【50mm视线匹配剪辑】{a}向最近的人点头，一位虚焦轮廓让出过道，动作生活化，不形成迎宾队列。",
            "9-12s【65mm行李动作近景】箱轮在地毯边轻卡一下，{a}自己扶稳箱杆，衣料与箱轮接触关系准确。",
            "12-15s【35mm中景缓推】{a}把行李立稳，环顾客厅，画外传来稀疏问候，尾帧保留第一次开口前的停顿。",
        ),
        "{a}已经进门并放稳行李；集体问候发生但正式介绍尚未开始。",
        "ambient-only",
        "门轴、箱轮、室内低环境声、远处海浪和不可辨的自然问候；无清晰陌生人台词、旁白或配乐。",
    ),
    "day1.introductions": EventSpec(
        "第一次正式自我介绍",
        "DAY 1 18:05，海岛别墅客厅，落地窗夕阳、茶几八杯水、围坐嘉宾仅作背影或强虚焦轮廓。",
        "八人刚坐定，只互相问候过；轮到{a}第一次在大家面前正式介绍自己。",
        (
            "0-3s【35mm肩背间穿行接50mm中近景】镜头从虚焦肩背之间靠近{a}；{a}呼吸后在1秒内自然开始说姓名，眼神落向真实听众而非摄影机。",
            "3-6s【50mm中近景缓推】{a}紧接着说年龄或职业信息，语速自然不拖腔，嘴型与声音同步。",
            "6-9s【65mm轻微侧移近景】{a}用自己的口语说出一项真实性格或相处习惯，眨眼和小手势符合人物卡。",
            "9-12s【50mm肩上镜头】{a}说清这七天想尝试的改变或期待，背景轮廓有人点头但不得出现陌生正脸。",
            "12-15s【35mm反应中景】{a}在14秒前说完，松开杯沿坐回去；画外有一两声自然回应，尾帧稳定至少0.8秒。",
        ),
        "{a}完成清晰、自然、非谜语式的首次自我介绍；其他人的介绍仍需继续。",
        "character-speech",
        "由{a}本人使用自然年轻中文原声完整说：『{intro}』；允许杯子轻碰、衣料声和稀疏回应，不得改词、加旁白、加字幕或使用播音腔。",
    ),
    "day1.cast-first-impressions": EventSpec(
        "八人介绍混剪与第一印象",
        "DAY 1 18:10，同一客厅、同一座位与光向，八杯水位置连续。",
        "八人已经围坐，正式介绍依次开始；每个人必须只出现一次且脸不重复。",
        (
            "0-3s【50mm两次明确硬切】0-1.5s只拍沈墨，1.5-3s只拍林屿；每人说一句短介绍，镜头不重复面孔。",
            "3-6s【65mm两次明确硬切】3-4.5s只拍程野，4.5-6s只拍顾言；手势与停顿分别符合外向行动派和理性慢热者。",
            "6-9s【50mm两次明确硬切】6-7.5s只拍江晚，7.5-9s只拍姜米；一人温和克制，一人明亮好奇，服装无字无标。",
            "9-12s【65mm两次明确硬切】9-10.5s只拍苏念，10.5-12s只拍陈叙；陈叙先扶正杯子再开口。",
            "12-15s【35mm八人空间关系群像】八人各在固定座位形成松散圆形，镜头只做小半径侧移，结束在几个人自然相视的轻笑，不新增第九张脸。",
        ),
        "沈墨、林屿、程野、顾言、江晚、姜米、苏念、陈叙八人全部完成一句可辨自我介绍，八张脸各一次。",
        "character-speech",
        "八人依次使用不同的自然年轻中文声音说：『{group_intro}』；杯子轻响、衣料与稀疏笑声在底层，禁止旁白、掌声、音乐、字幕和第九个人声。",
    ),
    "day1.icebreaker-choice": EventSpec(
        "三张场景卡的三分钟破冰",
        "DAY 1 18:25，客厅茶几和相邻吧台，暖光延续；三张无字场景卡分别以贝壳、陶土、玻璃杯小物表达。",
        "介绍结束，{a}还没有选卡；其余嘉宾只在景深外作为不可辨轮廓。",
        (
            "0-3s【50mm俯拍缓降】三张无字卡和三个真实小物落在桌面，数量稳定，不出现任何文字、数字或图标。",
            "3-6s【65mm手部近景】{a}的手在三张卡之间停顿，先观察而不是立刻拿走；指尖、卡片和桌面接触准确。",
            "6-9s【50mm肩上镜头】{a}对照吧台、露台与行李区三个真实方向，选择一张卡，表情是听懂玩法后的好奇。",
            "9-12s【85mm物件与眼神切换】{a}翻看卡背但卡面仍完全无字，随后抬眼寻找拿同款卡的人，背景脸全部不可辨。",
            "12-15s【35mm侧向跟拍】{a}拿卡走向对应场景，停在空座位或工作台前，尾帧稳定等待另一位嘉宾进入。",
        ),
        "{a}选定一个生活场景并抵达对应位置，配对对象尚未露出可辨身份。",
        "ambient-only",
        "卡片落桌、椅脚、室内人声纹理和远处海风；无清晰对白、旁白、提示音或音乐。",
    ),
    "day1.guided-chat": EventSpec(
        "从一句你好开始的三分钟聊天",
        "DAY 1 18:28，海景吧台，客厅人声在远处；镜头为玩家主观视角，只有{a}是可辨认嘉宾。",
        "{a}刚在吧台坐下，只知道玩家的姓名；三分钟聊天刚开始。",
        (
            "0-3s【50mm玩家肩上中景缓推】{a}坐下时短暂停顿，先露出自然小表情，再主动说你好，不表演式盯镜头。",
            "3-6s【85mm近景】{a}简单重说自己的名字，并用符合人物卡的语气问一个容易回答的小问题，嘴型同步。",
            "6-9s【65mm侧面反应镜头】玩家在画外回答，{a}先听完再回应，眼神和呼吸表现真实注意力。",
            "9-12s【85mm手部与表情交叉近景】{a}轻触杯沿或转动杯子，说出一个具体而不沉重的来节目理由。",
            "12-15s【50mm中景稳定收尾】{a}把话题交还给玩家，保留继续对话空间，远处工作人员只作不可辨环境声。",
        ),
        "{a}与玩家完成真实寒暄，并主动抛出一个可继续的小问题。",
        "character-speech",
        "{a}本人自然说：『{smalltalk}』；玩家回答保持不可辨，只保留海风、杯底轻响与远处客厅人声。禁止旁白和配乐。",
    ),
    "day1.team-up": EventSpec(
        "第一次晚餐分工",
        "DAY 1 19:10，海岛酒店暖光开放式厨房，水槽、砧板、蔬菜和两个工作位清楚可见。",
        "{a}与{b}刚被分到同一晚餐搭档，食材尚未清洗，分工尚未说清。",
        (
            "0-3s【28mm推镜建立中全景】{a}与{b}从台面两端靠近，镜头先交代水槽、刀具、食材的位置与安全距离。",
            "3-6s【50mm横移双人中景】两人用一句日常话确认谁洗菜、谁切配；先看物件再看彼此，语气不表演暧昧。",
            "6-9s【85mm手部匹配剪辑】水流冲过菜叶，另一人稳定完成第一段切配，刀、手与食材数量连续。",
            "9-12s【50mm过肩双人景】一人提醒地面或水量，另一人立即调整，两人短暂相视一笑但不发生刻意肢体接触。",
            "12-15s【35mm小半径环绕】两人进入一洗一切的稳定节奏，完成第一盘备菜，尾帧清楚保留两个分开的工作区。",
        ),
        "{a}与{b}明确分工并完成第一盘备菜，厨房动线稳定。",
        "character-speech",
        "{a}自然说『我们先把分工说清？我来洗菜，你想做哪一项？』；{b}回答『可以，做不顺我们就换。』，同时保留水流、刀落砧板和碗碟声，无旁白与配乐。",
    ),
    "day1.anonymous-letter": EventSpec(
        "睡前的第一条心动短信",
        "DAY 1 22:30，海景卧室床边，暖台灯与深蓝夜色；一部无品牌手机，屏幕永远不可读。",
        "{a}独自坐在床沿，已经回想完当天互动，输入框为空。",
        (
            "0-3s【50mm窗边到床侧横移】海风轻吹窗纱，镜头落到{a}拿起手机，屏幕朝自己且完全不可读。",
            "3-6s【85mm眼神与拇指近景】{a}输入几下又删除，停顿回想一个白天的具体小动作，不展示任何文字或头像。",
            "6-9s【65mm侧面中近景】{a}重新输入，呼吸逐渐放松，屏幕只做无内容柔光，不出现收件人。",
            "9-12s【85mm拇指近景】{a}深呼吸并只点击一次发送，手机只有轻微真实触感音，不出现通知动画。",
            "12-15s【50mm定镜中景】{a}把手机屏幕朝下放在床头柜，向后靠在枕边，海风自然收尾。",
        ),
        "一条匿名短信已经发送；内容、收件人和数量继续保密。",
        "ambient-only",
        "海风、窗纱、床垫与极轻手机触感声；没有可辨电子语音、对白、旁白、配乐或提示音。",
    ),
    "day2.morning-callback": EventSpec(
        "清晨被留出来的座位",
        "DAY 2 07:18，海景早餐厅，干净晨光、八把椅子与八套餐具。镜头为玩家主观视角，只有{a}可辨认。",
        "玩家刚走近早餐厅；{a}已经坐下，身旁椅子仍收在桌下。",
        (
            "0-3s【35mm晨光建立镜头】镜头从海面反光推入餐厅，八套餐具数量清楚，{a}抬头看到玩家靠近。",
            "3-6s【65mm动作近景】{a}把旁边椅子拉出，动作平常不邀功，椅脚与地面接触同步。",
            "6-9s【50mm玩家肩上反打】{a}把符合已知偏好的饮品推到空位前，留出玩家坐下的空间。",
            "9-12s【85mm近景】{a}只用一句话确认记得玩家昨天说过的偏好，不增加未发生的秘密。",
            "12-15s【35mm侧景】玩家以不可辨手部拉近杯子，{a}转向刚开始的早餐，尾帧稳定在已被接受的座位。",
        ),
        "{a}用座位和饮品回收昨日记忆；玩家接受同桌，但关系尚未被定义。",
        "character-speech",
        "{a}自然说『早，这里给你留了位置。你昨天说过的，我记得。』；保留椅脚、杯碟和清晨海浪，无旁白、配乐或甜宠提示音。",
    ),
    "story.house.rules-friction": EventSpec(
        "被改动的值日安排",
        "DAY 2 20:10，客厅侧墙与餐桌边；墙面只用无字彩色磁条表示排班。",
        "一条值日磁条被移动；{a}站在墙边，玩家从主观视角来核实。",
        (
            "0-3s【85mm物件特写转50mm中景】镜头看见空位和被挪动的磁条，{a}走近并停在不具压迫感的位置。",
            "3-6s【65mm玩家肩上镜头】玩家画外提出事实问题，{a}先看磁条再承认自己挪过，没有防御式打断。",
            "6-9s【85mm近景】{a}用一句具体原因解释，不给他人贴标签，声音平稳且嘴型同步。",
            "9-12s【50mm手部近景】{a}把磁条移到双方都能接受的新空位，动作一次完成不复位。",
            "12-15s【35mm中景】{a}后退半步确认新安排，墙面始终无文字，尾帧清楚保留调整结果。",
        ),
        "被移动的值日安排得到事实确认和一次可执行调整。",
        "character-speech",
        "{a}自然说『是我挪的。我以为那个时间没人用，下次我会先问。』；保留磁条轻响与室内环境声，无旁白或配乐。",
    ),
    "story.identity.profession-reveal": EventSpec(
        "职业公开夜的群像反应",
        "DAY 3 20:00，长餐桌和八个无字信封，暖白吊灯；不得生成任何可读职业卡。",
        "八人各拿到一个闭合信封，职业信息尚未被公开。",
        (
            "0-3s【35mm桌面滑轨全景】八个闭合信封和八双手依次进入画面，数量严格为八。",
            "3-6s【50mm四人反应硬切】沈墨、林屿、程野、顾言各自打开信封并交换一次真实眼神，卡面始终背对镜头或过曝。",
            "6-9s【50mm四人反应硬切】江晚、姜米、苏念、陈叙依次打开信封，反应克制，不夸张惊叫。",
            "9-12s【85mm细节匹配剪辑】一只手把信封重新合上，另一人把杯子推近；职业文字始终不可读。",
            "12-15s【35mm八人中全景】八人在同一空间开始自然追问，镜头停在关系重新被观察的群像。",
        ),
        "八人职业公开环节开始，身份信息改变彼此观察，但画面不烧录任何职业文字。",
        "ambient-only",
        "信封纸声、杯碟、轻微吸气和不可辨交谈；无清晰台词、旁白、音乐或夸张综艺音效。",
    ),
    "story.date.blind-box": EventSpec(
        "约会盲盒前的一次选择",
        "DAY 3 15:20，海景露台，三个封闭无字盒子与三种材质线索：陶土、护目镜、动物脚印小印章。",
        "{a}站在三个盒子前，还不知道对应约会对象或地点。",
        (
            "0-3s【35mm推镜全景】三个盒子等距摆放，{a}从露台入口走近，背景海面稳定。",
            "3-6s【85mm材质特写】镜头依次看陶土、护目镜和脚印印章，只展示材质，不出现文字和品牌。",
            "6-9s【50mm中近景】{a}在三个线索间来回观察，表情从好奇到做出判断，不向镜头解释。",
            "9-12s【65mm手部近景】{a}只选择并打开其中一个盒盖，另外两个保持闭合且位置不动。",
            "12-15s【50mm反应近景】盒内只露出不可读的颜色卡，{a}抬眼望向出发方向，尾帧不揭示约会对象。",
        ),
        "{a}已经选择一个盲盒，目的地和同行者仍保持悬念。",
        "ambient-only",
        "海风、盒盖、纸张和远处鸟声；无对白、旁白、音乐、提示音或可读电子声。",
    ),
    "story.date.mutual-signal": EventSpec(
        "双向信号后的二十分钟",
        "DAY 3 21:00，安静海景露台，两把椅子与两张无字邀请卡，暖串灯和深蓝海面。",
        "节目组刚通知双向信号成立；{a}与{b}第一次在没有其他人的露台坐下。",
        (
            "0-3s【35mm双人建立镜头缓推】两人从不同方向走向两把椅子，彼此留出自然距离，先坐下再开口。",
            "3-6s【85mm交替近景】{a}提出一个明天可验证、可拒绝的小邀请，语气克制，不把心动等同承诺。",
            "6-9s【85mm反打】{b}先听完再给具体回应，不用空泛情话，眼神短暂相接。",
            "9-12s【65mm手部近景】两人各把一张未写字的邀请卡推到桌面中央，卡片数量稳定为二。",
            "12-15s【50mm双人侧景】海风轻动衣角，两人继续聊但声音渐远，镜头停在两张并列卡片和开放的下一步。",
        ),
        "{a}与{b}各提出一个可拒绝的下一步，两张邀请卡已放在桌上。",
        "character-speech",
        "{a}说『明天要不要一起看日出？不方便也没关系。』；{b}回答『好，我也想再聊一会儿。』；保留海风、卡片摩擦，无旁白或音乐。",
    ),
    "story.missed-timing.empty-seat": EventSpec(
        "错过的一把空椅子",
        "DAY 4 18:40，晚餐露台，长桌边一把空椅子被夕阳照亮。",
        "{a}端着水走到露台，看见期待的人没有坐在预留空位。",
        (
            "0-3s【35mm侧向建立镜头】长桌和空椅子先入画，{a}从背景走近，脚步因看见空位而放慢。",
            "3-6s【85mm空椅与眼神匹配剪辑】椅背、未动的杯子、{a}的眼神依次出现，不生成缺席者的脸。",
            "6-9s【50mm中近景】{a}把自己的水杯放下又拿回，犹豫是否坐在空位旁，动作克制。",
            "9-12s【65mm侧面跟拍】远处有人画外招呼，{a}转身选择另一把椅子，空位继续留在背景。",
            "12-15s【35mm静态中全景】{a}坐下但视线短暂回到空椅，夕阳变化自然，尾帧不替关系下结论。",
        ),
        "{a}接受了这次错过并坐到别处；空椅仍保留为后续沟通的事实。",
        "ambient-only",
        "海风、杯底、椅脚和远处不可辨招呼；无对白、旁白、音乐或煽情音效。",
    ),
    "story.care.breakfast-callback": EventSpec(
        "早餐里被记住的偏好",
        "DAY 4 08:10，明亮早餐厨房，木托盘、茶、咖啡和一份清淡早餐；玩家主观视角，只有{a}可辨。",
        "{a}已经根据一条合法记忆准备好饮品，玩家刚走到餐台。",
        (
            "0-3s【50mm手部到中景缓抬】{a}把饮品和早餐放上托盘，糖、奶或调料数量与偏好一致。",
            "3-6s【65mm玩家肩上镜头】{a}看到玩家走近，把托盘推到容易拿的位置，不直接喂食或制造肢体接触。",
            "6-9s【85mm近景】{a}用一句话说明自己记得昨天的具体偏好，不夸大关系。",
            "9-12s【85mm物件特写】玩家的手接过杯子，{a}同步收回手，杯液和托盘保持稳定。",
            "12-15s【35mm中景】{a}继续整理早餐台，玩家带走托盘，照顾成为日常行动而非邀功表演。",
        ),
        "{a}用早餐行动回收一条已知偏好；玩家接下托盘。",
        "character-speech",
        "{a}自然说『我记得你昨天说的，所以这份按你的口味留了。』；保留杯碟、咖啡机和晨间环境声，无旁白或配乐。",
    ),
    "story.triangle.reverse-invite": EventSpec(
        "反向邀约前的两张卡",
        "DAY 4 16:00，海景客厅，两张无字邀约卡分别放在沈墨和程野面前，玩家在画外。",
        "沈墨与程野同时收到邀请机会，尚未知道玩家会走向哪一边。",
        (
            "0-3s【35mm横移建立双人关系】镜头从两张分开的卡移到沈墨与程野，两人站位有距离，不摆出对峙姿势。",
            "3-6s【85mm沈墨近景】沈墨看一眼卡片又看向画外入口，表情克制，手没有抢先触碰卡。",
            "6-9s【85mm程野反打】程野轻转卡片后放回原位，外向但不挑衅，不盯住沈墨。",
            "9-12s【50mm双人中景】门外传来脚步，两人同时抬眼，身体重心自然转向入口。",
            "12-15s【35mm卡片前景双人后景】镜头停在两张卡和等待中的两人，玩家尚未入镜，选择完全开放。",
        ),
        "沈墨与程野都已准备回应邀约，玩家的选择仍未发生。",
        "ambient-only",
        "海风、卡片摩擦、远处脚步和室内低环境声；无对白、旁白、音乐或竞技音效。",
    ),
    "story.group.truth-firepit": EventSpec(
        "围炉真心话的跳过权",
        "DAY 4 21:30，海边火盆，八把椅子围成完整圆形，中央三张无字问题卡。",
        "八人都已坐下，问题卡尚未被选择，每个人保留一次跳过权。",
        (
            "0-3s【24mm环绕建立群像】镜头沿八把椅子外圈移动，八人各出现一次，火光方向和人数稳定。",
            "3-6s【85mm三张卡特写】三张无字卡被放到火光边，手在第一张前停下又收回，强调选择而非随机审问。",
            "6-9s【50mm四人反应硬切】沈墨、林屿、程野、顾言各有一个不同的倾听反应，不重复面孔。",
            "9-12s【50mm四人反应硬切】江晚、姜米、苏念、陈叙依次看向选卡的人，有人点头表示可跳过。",
            "12-15s【35mm八人中全景】一张卡被拿起，另外两张留在原位，火光稳定，回答尚未开始。",
        ),
        "八人确认可选择、可跳过；一张问题卡被选中，但私人答案尚未公开。",
        "ambient-only",
        "火焰、海风、椅脚和低声呼吸；所有人声不可辨，无旁白、音乐、惊呼或综艺提示音。",
    ),
    "story.bombshell.ninth-card": EventSpec(
        "第九张卡突然出现",
        "DAY 5 18:30，餐桌中央原有八张无字卡，门铃响后出现第九个闭合信封；新嘉宾不露脸。",
        "八位嘉宾围桌，原有八张卡数量清楚，第九张尚未被放下。",
        (
            "0-3s【35mm俯拍桌面】八张卡围成松散圆形，八双手位置清楚，门铃在画外响一次。",
            "3-6s【50mm八人群像】八人依次转向门口，反应真实克制，没有人站起冲门。",
            "6-9s【85mm门口手部特写】只出现一只不具身份特征的手，把第九个闭合信封放在门边托盘，绝不露陌生脸。",
            "9-12s【50mm反应硬切】八人各一个极短反应，脸不重复；沈墨观察，程野前倾，姜米好奇，其他人保持各自性格。",
            "12-15s【35mm桌面缓推】第九个信封被放到八张卡中央，数量变为九，尾帧稳定，不揭示来者身份。",
        ),
        "第九个信封进入小屋，原有八人关系被打破；新嘉宾身份仍未公开。",
        "ambient-only",
        "一次门铃、椅脚、信封落盘和克制的吸气声；无清晰对白、旁白、音乐或陌生人声音。",
    ),
    "story.past.consent-reveal": EventSpec(
        "是否公开一段过去",
        "DAY 5 22:00，安静海景书房，一只闭合信封和两把椅子；玩家主观视角，只有{a}可辨认。",
        "{a}拿到一只属于自己的旧事信封，尚未决定公开多少。",
        (
            "0-3s【50mm中景缓推】{a}把闭合信封放在桌上，手掌离开后停顿，先看玩家而不是立刻拆开。",
            "3-6s【85mm手部近景】指尖碰到封口又收回，信封始终闭合，不生成照片、文字或创伤画面。",
            "6-9s【85mm近景】{a}用眼神和呼吸确认玩家是否愿意继续听，情绪克制，不哭戏表演。",
            "9-12s【65mm侧景】玩家以不可辨手部把水杯推近，{a}点头，把信封转向自己而不是交出去。",
            "12-15s【50mm定镜】{a}只掀开封口一角又停住，镜头保留可以选择继续或退出的空间。",
        ),
        "{a}获得公开或保留过去的主动权；信封尚未完全打开。",
        "ambient-only",
        "海风、信封纸、杯底与呼吸声；无对白、旁白、音乐或创伤闪回音效。",
    ),
    "story.trip.last-two-days": EventSpec(
        "最后两日旅行的路线提案",
        "DAY 6 10:00，海景客厅地毯，三张无字路线照片代表山路、港口和森林；只有江晚可辨认。",
        "江晚把三张路线照片铺开，其他人尚未表达想去哪里。",
        (
            "0-3s【35mm俯拍缓降】三张无字路线照片在地毯上展开，江晚跪坐在旁，手指不遮挡关键景物。",
            "3-6s【65mm江晚中近景】江晚先看一圈画外的人，再把照片推到所有人都能看到的位置。",
            "6-9s【85mm手部特写】她不替大家做决定，只把三张照片拉成同一水平线，保持选项平等。",
            "9-12s【50mm玩家肩上镜头】江晚用一句具体话邀请大家先说真实偏好，语气温和清醒。",
            "12-15s【35mm中全景】几只不可辨的手靠近三张路线但尚未选择，江晚退开一点，尾帧保留共同决定。",
        ),
        "三条旅行路线被平等提出，江晚把决定权交还给所有人。",
        "character-speech",
        "江晚自然说『路线不急着定，我们先听听每个人真正想去哪里。』；保留照片纸声、海风和低环境声，无旁白或配乐。",
    ),
    "story.final.unsent-letter": EventSpec(
        "告白前夜没有寄出的信",
        "FINAL EVE 23:10，安静卧室书桌，暖台灯、一张空白信纸和闭合信封；画面不得出现可读文字。",
        "{a}独自坐在桌前，已经写过又划去一些内容，尚未决定是否封信。",
        (
            "0-3s【50mm书桌侧面缓推】{a}坐在台灯下，信纸只呈现不可读模糊线条，笔停在纸上方。",
            "3-6s【85mm手部近景】{a}写下一行又用单线划去，不撕纸、不情绪化揉团，墨迹始终不可读。",
            "6-9s【85mm眼神近景】{a}看向窗外回想当天行动，呼吸缓慢，情绪从急于证明转为诚实。",
            "9-12s【65mm侧景】{a}把信纸折一次，停在信封上方，随后决定先不封口。",
            "12-15s【50mm定镜】未封的信放在桌上，{a}关掉笔帽但保留台灯，尾帧让明天的选择保持开放。",
        ),
        "一封尚未封口的信被留下；{a}仍可选择说、寄出或独自离开。",
        "ambient-only",
        "笔尖、纸张、窗外海风和台灯开关的真实声音；无对白、旁白、配乐或可辨文字朗读。",
    ),
    "story.final.confession-day": EventSpec(
        "最终告白日的两条独立路径",
        "FINAL DAY 18:20，海边花园日落，两条独立石径在中央相交，远处第三条路通向出口。",
        "{a}与{b}分别站在两条路径起点，尚未看见对方的最终选择。",
        (
            "0-3s【24mm高位全景下降】三条路径关系清楚，{a}与{b}在相距较远的两个起点，夕阳方向一致。",
            "3-6s【85mm交替近景】先拍{a}再拍{b}各一次深呼吸，两人都独立决定是否迈步，不剪出承诺结果。",
            "6-9s【35mm平行跟拍】两人各自向前走一小段，速度不同，镜头不通过剪辑假造同步。",
            "9-12s【50mm路径交叉中景】两条路在前景交会，但两人仍未抵达交点；第三条独行出口始终可见。",
            "12-15s【35mm稳定远景】两人停在交点前各一步，海风与日落稳定，尾帧在最终决定发生前结束。",
        ),
        "{a}与{b}都抵达最终选择前一刻；相遇、继续了解或独自离开仍由剧情决定。",
        "ambient-only",
        "海风、脚步、衣料和远处海浪；无告白台词、旁白、音乐高潮或结局提示音。",
    ),
}


# Direct eight-face generation has repeatedly produced missing or duplicated
# identities.  These three group events therefore use eight independent
# single-identity atoms and are assembled locally after all atoms pass QA.
GROUP_ATOM_SPECS: dict[str, EventSpec] = {
    "story.identity.profession-reveal": EventSpec(
        "职业公开夜单人反应原子",
        "DAY 3 20:00，长餐桌一角、暖白吊灯与一只闭合无字信封；除{a}外其他嘉宾只作强虚焦肩背。",
        "{a}刚拿到属于自己的闭合信封，尚未打开，也尚未听到其他人的职业。",
        (
            "0-3s【50mm中近景缓推】{a}先看信封再看一眼画外的其他人，手掌停在封口旁，没有抢先表演反应。",
            "3-6s【85mm手部近景】{a}只打开一次信封，卡面始终背向镜头或轻微过曝，绝不出现可读职业文字。",
            "6-9s【85mm眼神近景】{a}读完后出现一次符合人物卡的微表情，不夸张惊叫，不看镜头。",
            "9-12s【65mm肩上反打】{a}抬眼望向画外下一位嘉宾，给出一个自然倾听或等待追问的反应。",
            "12-15s【50mm中景稳定收尾】{a}把卡片收回信封并放到桌前，姿态稳定，为本地八人混剪留下干净尾帧。",
        ),
        "{a}完成职业卡阅读并留下一个可辨的真实反应；卡面仍不可读。",
        "ambient-only",
        "信封纸、杯碟、衣料与不可辨远处交谈；无清晰台词、旁白、音乐或综艺提示音。",
    ),
    "story.group.truth-firepit": EventSpec(
        "围炉真心话单人反应原子",
        "DAY 4 21:30，海边火盆旁的一把椅子，火光方向固定；除{a}外其他人只作强虚焦轮廓。",
        "{a}已经坐下，问题卡刚被画外的人拿起，回答尚未开始。",
        (
            "0-3s【50mm侧面中景】火光先擦过{a}脸侧，{a}听见问题后抬眼，身体不夸张前倾。",
            "3-6s【85mm眼神近景】{a}看向画外提问者，先听完再呼吸一次，反应服从人物卡。",
            "6-9s【65mm手部近景】{a}把代表可跳过权的无字小木片放到自己掌边，动作清楚但不替自己做最终选择。",
            "9-12s【85mm近景】画外有人开始回答，{a}以点头、停顿或轻收表情表示尊重边界，不抢话。",
            "12-15s【50mm中景稳定收尾】{a}坐回自然姿态，火光与海风连续，为八人本地混剪留下稳定尾帧。",
        ),
        "{a}确认了可回答也可跳过的规则，并留下不越界的倾听反应。",
        "ambient-only",
        "火焰、海风、椅脚和低声呼吸；画外人声不可辨，无旁白、音乐或夸张音效。",
    ),
    "story.bombshell.ninth-card": EventSpec(
        "第九张卡出现时的单人反应原子",
        "DAY 5 18:30，餐桌边、暖光与门口方向；除{a}外其他人只作强虚焦肩背，新嘉宾完全不露脸。",
        "{a}坐在餐桌边，门铃尚未响，原有八人关系仍处于平静状态。",
        (
            "0-3s【50mm中近景定镜】{a}正在整理杯子或卡片，环境安静，先建立门铃前的日常状态。",
            "3-6s【85mm反应近景】门铃只响一次，{a}自然停手并转向门口，声音与动作同步。",
            "6-9s【65mm肩上镜头】画外一只不具身份特征的手放下闭合信封，{a}视线跟随但陌生人不得入脸。",
            "9-12s【85mm眼神与手部匹配】{a}产生一次符合人物卡的好奇、警觉或期待反应，不说戏剧化台词。",
            "12-15s【50mm中景稳定收尾】{a}重新坐正，视线仍停在第九个信封方向，为八人本地混剪留出干净尾帧。",
        ),
        "{a}看见第九个信封并留下独立反应；新嘉宾身份仍未公开。",
        "ambient-only",
        "一次门铃、信封落盘、杯底和克制呼吸声；无清晰对白、旁白、音乐或陌生人声。",
    ),
}


SMALL_TALK = {
    "shenmo": "你好，我是沈墨。刚才人多，我们先聊个具体的：你为什么会来这里？",
    "linyu": "你好，我是林屿。刚才还没好好认识你，你现在紧张吗？",
    "chengye": "你好，我是程野。三分钟挺短的，我们从最好奇的问题开始？",
    "guyan": "你好，我是顾言。我可能问得有点直接：你来这里最想验证什么？",
    "jiangwan": "你好，我是江晚。我们先聊轻松一点，你今天进门时第一个注意到什么？",
    "jiangmi": "你好，我是姜米。刚才信息量太大了，你现在最想记住哪一件小事？",
    "sunnian": "你好，我是苏念。刚才没来得及好好打招呼，你现在还适应吗？",
    "chensu": "你好，我是陈叙。你想先聊什么？简单一点也行。",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(data)


def relative_to_root(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def load_cards() -> dict[str, dict[str, Any]]:
    payload = json.loads(CHARACTER_CARDS.read_text(encoding="utf-8"))
    cards = {item["id"]: item for item in payload["cards"]}
    if set(CHARACTER_ORDER) - set(cards):
        raise RuntimeError("character_cards.v3.json does not contain the complete fixed cast")
    return cards


def load_required_masters() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(RUNTIME_MATRIX.read_text(encoding="utf-8"))
    required = [item for item in payload["masters"] if item["status"] == "requiresGeneration"]
    if len(required) != 178:
        raise RuntimeError(f"expected 178 requiresGeneration masters, found {len(required)}")
    ids = [item["targetAssetId"] for item in required]
    if len(ids) != len(set(ids)):
        raise RuntimeError("runtime matrix contains duplicate required targetAssetId values")
    unknown = sorted({item["eventId"] for item in required} - set(EVENTS))
    if unknown:
        raise RuntimeError(f"missing EventSpec entries: {unknown}")
    return payload, required


def save_jpeg(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(
        path,
        format="JPEG",
        quality=95,
        subsampling=0,
        optimize=True,
        progressive=False,
    )


def build_composite(cast: list[str]) -> Path:
    if len(cast) == 2:
        destination = REFS / f"pair--{cast[0]}-{cast[1]}.jpg"
        panels = [
            ImageOps.fit(Image.open(PORTRAITS / f"{character_id}.jpg").convert("RGB"), (480, 854), method=Image.Resampling.LANCZOS)
            for character_id in cast
        ]
        board = Image.new("RGB", (960, 854))
        for index, panel in enumerate(panels):
            board.paste(panel, (index * 480, 0))
        save_jpeg(board, destination)
        return destination
    if cast == CHARACTER_ORDER:
        destination = REFS / "group--current-eight.jpg"
        board = Image.new("RGB", (1920, 1708))
        for index, character_id in enumerate(cast):
            panel = ImageOps.fit(
                Image.open(PORTRAITS / f"{character_id}.jpg").convert("RGB"),
                (480, 854),
                method=Image.Resampling.LANCZOS,
            )
            board.paste(panel, ((index % 4) * 480, (index // 4) * 854))
        save_jpeg(board, destination)
        return destination
    raise RuntimeError(f"unsupported composite cast: {cast}")


def reference_for_cast(cast: list[str]) -> tuple[Path, str]:
    if len(cast) == 1:
        return PORTRAITS / f"{cast[0]}.jpg", "single-identity-anchor"
    return build_composite(cast), "composite-identity-board"


def reference_path_for_manifest(path: Path) -> str:
    try:
        return relative_to_root(path)
    except ValueError:
        return str(path.relative_to(ROOT).as_posix()) if path.is_relative_to(ROOT) else str(path.relative_to(PROJECT).as_posix()).join(("../../../", ""))


def manifest_reference(path: Path) -> str:
    if path.is_relative_to(ROOT):
        return relative_to_root(path)
    if path.is_relative_to(PROJECT):
        return "../../../" + path.relative_to(PROJECT).as_posix()
    raise RuntimeError(f"reference path escapes project: {path}")


def identity_lines(cast: list[str], cards: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = []
    for character_id in cast:
        card = cards[character_id]
        facts = card.get("sourceProfile", {}).get("facts", {})
        age = facts.get("age") or "年龄尚未公开"
        occupation = facts.get("occupation") or "职业尚未公开"
        mask = "、".join(card.get("psychology", {}).get("publicMask", [])[:2])
        voice = card.get("voice", {})
        lines.append(
            f"- {DISPLAY[character_id]}（{card['mbti']}，{age}，{occupation}）："
            f"表演底色为{mask}；语言为{voice.get('register', '自然口语')}，"
            f"句式遵循“{voice.get('sentenceShape', '中短句')}”。"
        )
    return "\n".join(lines)


def identity_contract(cast: list[str]) -> str:
    names = [DISPLAY[item] for item in cast]
    if len(cast) == 1:
        return (
            f"参考图中唯一人物是{names[0]}。严格迁移其脸型、五官、发型、年龄感与性别表达；"
            "只允许这一张可辨正脸，其他路人只能是背影、裁切肩部或强虚焦轮廓。"
        )
    if len(cast) == 2:
        return (
            f"参考拼板从左到右依次是{names[0]}、{names[1]}。严格保持两人的脸、发型、年龄感和性别表达；"
            "不得互换、融合、复制或新增第三张可辨脸。拼板仅用于身份，不复制分栏、接缝或原背景。"
        )
    return (
        "参考拼板上排从左到右是沈墨、林屿、程野、顾言，下排从左到右是江晚、姜米、苏念、陈叙。"
        "八张固定脸各出现一次，不得缺人、重复、融合或新增第九张脸；拼板仅用于身份，不复制网格、接缝或背景。"
    )


def format_context(master: dict[str, Any], cast_override: list[str] | None = None) -> dict[str, str]:
    cast = cast_override or master["identityCast"]
    names = [DISPLAY[item] for item in cast]
    return {
        "a": names[0],
        "b": names[1] if len(names) > 1 else "玩家",
        "intro": INTRO_LINES[cast[0]],
        "smalltalk": SMALL_TALK[cast[0]],
        "group_intro": "；".join(SHORT_INTROS[item] for item in CHARACTER_ORDER),
        "all_names": "、".join(names),
    }


def compile_prompt(
    master: dict[str, Any],
    cards: dict[str, dict[str, Any]],
    *,
    provider_job_id: str | None = None,
    cast_override: list[str] | None = None,
    spec_override: EventSpec | None = None,
) -> tuple[str, str, str, str]:
    event_id = master["eventId"]
    spec = spec_override or EVENTS[event_id]
    cast = cast_override or master["identityCast"]
    context = format_context(master, cast)
    setting = spec.setting.format_map(context)
    state_in = spec.state_in.format_map(context)
    state_out = spec.state_out.format_map(context)
    timeline = [item.format_map(context) for item in spec.timeline]
    audio = spec.audio.format_map(context)
    cast_names = "、".join(DISPLAY[item] for item in cast)
    job_id = provider_job_id or f"{master['targetAssetId']}--r5"
    semantic_names = "、".join(DISPLAY[item] for item in master["identityCast"])
    prompt = f"""15秒写实电影级竖屏互动影游事件视频｜Seedance 2.0 Mini 生产稿

【运行绑定】
- providerJobId：{job_id}
- semanticTargetAssetId：{master['targetAssetId']}
- eventId：{event_id}
- servedEventIds：{'、'.join(master['servedEventIds'])}
- routingMode：{master['routingMode']}
- 本次生成精确 identityCast：{cast_names}
- 最终语义母片 identityCast：{semantic_names}
- 规格：9:16，15秒，720p，24fps，原生有声，无平台水印。

【时间、地点与材质】
{setting}
写实中国青年恋爱观察节目质感，低对比度柔和胶片色调，真实肤质、布料、玻璃、木材和空气层次；生活化克制，不做广告摆拍。

【人物身份锁定】
{identity_contract(cast)}
{identity_lines(cast, cards)}
所有对白、停顿、视线和小动作必须服从人物卡，不把 MBTI 当台词，不说谜语式金句。

【State In】
{state_in}

【唯一动作与逐秒镜头计划】
只表现从上述 State In 到下述 State Out 的一次连续推进，不提前完成下一剧情选择：
1. {timeline[0]}
2. {timeline[1]}
3. {timeline[2]}
4. {timeline[3]}
5. {timeline[4]}

【光线、声音与表演】
- 光线保持同一方向和色温，浅景深只用于引导注意力，不能遮掉动作因果。
- 表演先于台词：人物先对眼前一个具体动作或词产生反应，再开口；不得一边做全套表情一边播报完整信息。
- 真人口语允许最多一次自然改口、抢半句或没说满的停顿，但不能机械塞省略号、语气词和口头禅；不要播音腔、客服腔或心理咨询式总结。
- 一次情绪转折必须由视线、呼吸、手部动作或距离变化逐步形成；禁止无铺垫地从拘谨跳到深情、从冲突跳到拥抱。
- 幽默只来自现场观察、反差或自嘲，占比不超过三成，说完即过，不用夸张反应解释笑点。
- 恋爱表达保持双方主体性：示好者不是等待评判，回应者不是拯救者或奖品；接住一个共同细节后，再清楚表达自己的感受、边界或下一步。
- 若本事件包含示好、道歉、分歧或告白，按“地点与共同物件 → 一人主动做出具体动作 → 接收者不完美反应 → 短句表达自己的选择 → 一句低压力幽默或清楚边界 → 等待确认后的共同动作”推进；得到确认前不得替关系命名或直接拥抱。
- 对白说话人必须明确；两句之间保留0.4–0.8秒自然停顿、吸气或小笑。禁止机器人式轮流念词、采访式直视镜头、长篇诗化告白和说完立刻身体接触。
- 音频归属：{spec.audio_mode}。
- {audio}
- 初次播放可听原声；运行时循环静音由前端负责，视频本体保留完整自然音轨。

【State Out】
{state_out}
最后至少稳定0.8秒；人物和物件不得在尾帧复位。

【手机安全区】
关键脸和主要动作置于画面中央55%；顶部12%留 HUD，底部24%留半透明旁白/选项；不得让手部动作或表情被底部遮挡。

【一票否决】
无烧录文字、姓名牌、字幕、UI、Logo、品牌、水印、时间码；无陌生正脸；无身份漂移、换脸、同脸复制、脸部融合；无畸形手指、肢体穿模、漂浮道具；无跳帧、机械重复、逆向动作、镜头抖动；无亲吻、强制拥抱或替玩家做出恋爱结局。

【参考边界】
参考图只迁移固定人物的脸、发型、年龄感和性别表达；禁止迁移参考图背景、裁切、拼板布局、接缝、色块或任何可能的文字痕迹。场景、服装、动作和运镜以本生产稿为准。
"""
    return prompt, state_in, state_out, spec.audio_mode


def cleanup_previous_generated_inputs() -> None:
    """Remove only files explicitly owned by the previous generated manifest."""
    if not MANIFEST.is_file():
        return
    try:
        previous = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    owned: set[Path] = set()
    for shot in previous.get("shots", []):
        for field, root in (("prompt_file", PROMPTS), ("reference_image", REFS)):
            raw = shot.get(field)
            if not isinstance(raw, str):
                continue
            candidate = (ROOT / raw).resolve()
            if candidate.is_relative_to(root.resolve()):
                owned.add(candidate)
    for path in owned:
        if path.is_file():
            path.unlink()


def build() -> dict[str, Any]:
    cleanup_previous_generated_inputs()
    for character_id, line in INTRO_LINES.items():
        if not 35 <= len(line) <= 72:
            raise RuntimeError(f"{character_id} introduction length {len(line)} does not fit a natural 15s delivery")
    PROMPTS.mkdir(parents=True, exist_ok=True)
    REFS.mkdir(parents=True, exist_ok=True)
    cards = load_cards()
    runtime, required = load_required_masters()
    matrix_hash = sha256_file(RUNTIME_MATRIX)
    character_cards_hash = sha256_file(CHARACTER_CARDS)
    shots: list[dict[str, Any]] = []
    composites: list[dict[str, Any]] = []

    def append_shot(
        master: dict[str, Any],
        *,
        provider_job_id: str,
        cast: list[str],
        provider_job_role: str,
        kind: str,
        spec_override: EventSpec | None = None,
        atom_character_id: str | None = None,
    ) -> dict[str, Any]:
        target = master["targetAssetId"]
        reference, reference_role = reference_for_cast(cast)
        prompt, state_in, state_out, audio_mode = compile_prompt(
            master,
            cards,
            provider_job_id=provider_job_id,
            cast_override=cast,
            spec_override=spec_override,
        )
        prompt_path = PROMPTS / f"{provider_job_id}.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        prompt_hash = sha256_file(prompt_path)
        reference_hash = sha256_file(reference)
        state_contract = {
            "stateIn": state_in,
            "stateOut": state_out,
            "providerIdentityCast": cast,
            "semanticIdentityCast": master["identityCast"],
            "eventId": master["eventId"],
            "servedEventIds": master["servedEventIds"],
        }
        shot = {
            "id": provider_job_id,
            "kind": kind,
            "providerJobRole": provider_job_role,
            "atomCharacterId": atom_character_id,
            "targetAssetId": target,
            "semanticTargetAssetId": target,
            "targetRuntimeAssetId": target,
            "eventId": master["eventId"],
            "servedEventIds": master["servedEventIds"],
            "routingMode": master["routingMode"],
            "perspectiveCharacterId": master["perspectiveCharacterId"],
            "applicablePerspectiveCharacterIds": master["applicablePerspectiveCharacterIds"],
            "participantIds": master["participantIds"],
            "semanticIdentityCast": master["identityCast"],
            "identityCast": cast,
            "reference_image": manifest_reference(reference),
            "referenceImageSha256": reference_hash,
            "referenceImageRole": reference_role,
            "prompt_file": relative_to_root(prompt_path),
            "promptSha256": prompt_hash,
            "generationModel": "seedance-2.0-mini",
            "audioMode": audio_mode,
            "rightsStatus": "pending",
            "rightsRefIds": [],
            "likenessConsentRefIds": [],
            "voiceConsentRefIds": [],
            "stateIn": state_in,
            "stateOut": state_out,
            "stateInSha256": sha256_text(state_in),
            "stateOutSha256": sha256_text(state_out),
            "identityCastSha256": canonical_hash(cast),
            "stateContractSha256": canonical_hash(state_contract),
            "sourceRuntimeMatrixSha256": matrix_hash,
            "sourceCharacterCardsSha256": character_cards_hash,
            "identityNotes": identity_contract(cast),
            "output_name": f"{provider_job_id}-candidate.mp4",
        }
        shots.append(shot)
        return shot

    masters_by_target = {master["targetAssetId"]: master for master in required}
    current_eight = [master for master in required if master["routingMode"] == "current-eight"]
    d1a3b_target = "D1-A3B-cast-first-impressions--group-current-eight"

    for master in required:
        target = master["targetAssetId"]
        if master["routingMode"] == "current-eight":
            # D1-A3B is cut directly from the eight already-required voiced
            # introduction jobs.  The other three group events use eight
            # single-identity atoms so no provider job must preserve 8 faces.
            if target == d1a3b_target:
                continue
            spec = GROUP_ATOM_SPECS[master["eventId"]]
            for character_id in CHARACTER_ORDER:
                append_shot(
                    master,
                    provider_job_id=f"{target}--atom-{character_id}--r5",
                    cast=[character_id],
                    provider_job_role="single-identity-current-eight-atom",
                    kind="current-eight-atom",
                    spec_override=spec,
                    atom_character_id=character_id,
                )
            continue
        append_shot(
            master,
            provider_job_id=f"{target}--r5",
            cast=master["identityCast"],
            provider_job_role="direct-semantic-master-candidate",
            kind="self-introduction" if master["eventId"] == "day1.introductions" else "runtime-variant",
        )

    intro_source_ids = [f"D1-A3-cast-introductions--p-{character_id}--r5" for character_id in CHARACTER_ORDER]
    composite_source_map = {d1a3b_target: intro_source_ids}
    for master in current_eight:
        target = master["targetAssetId"]
        if target != d1a3b_target:
            composite_source_map[target] = [f"{target}--atom-{character_id}--r5" for character_id in CHARACTER_ORDER]
        source_ids = composite_source_map[target]
        context = format_context(master)
        spec = EVENTS[master["eventId"]]
        state_in = spec.state_in.format_map(context)
        state_out = spec.state_out.format_map(context)
        source_start = 0.8 if target == d1a3b_target else 3.0
        segment_duration = 1.75
        segments = [
            {
                "order": index + 1,
                "characterId": character_id,
                "displayName": DISPLAY[character_id],
                "sourceProviderJobId": source_ids[index],
                "sourceStartSeconds": source_start,
                "durationSeconds": segment_duration,
                "transition": "hard-cut",
            }
            for index, character_id in enumerate(CHARACTER_ORDER)
        ]
        assembly_contract = {
            "targetRuntimeAssetId": target,
            "identityCast": CHARACTER_ORDER,
            "sourceProviderJobIds": source_ids,
            "openingRoomToneSeconds": 0.5,
            "segments": segments,
            "closingHoldSeconds": 0.5,
            "durationSeconds": 15.0,
            "audioPolicy": "preserve each approved source excerpt; hard-cut with 35ms equal-power audio crossfade; normalize final integrated loudness only after speech QA",
        }
        composites.append(
            {
                "id": f"{target}--r5-local-composite",
                "kind": "local-current-eight-composite",
                "status": "planned-awaiting-approved-source-candidates",
                "doNotSubmit": True,
                "targetRuntimeAssetId": target,
                "eventId": master["eventId"],
                "servedEventIds": master["servedEventIds"],
                "routingMode": master["routingMode"],
                "identityCast": CHARACTER_ORDER,
                "sourceProviderJobIds": source_ids,
                "stateIn": state_in,
                "stateOut": state_out,
                "stateInSha256": sha256_text(state_in),
                "stateOutSha256": sha256_text(state_out),
                "identityCastSha256": canonical_hash(CHARACTER_ORDER),
                "assembly": assembly_contract,
                "assemblyContractSha256": canonical_hash(assembly_contract),
                "output_name": f"{target}--r5-local-composite-candidate.mp4",
            }
        )

    if len(shots) != 198:
        raise RuntimeError(f"refusing to write manifest with {len(shots)} provider jobs")
    if len(composites) != 4:
        raise RuntimeError(f"refusing to write manifest with {len(composites)} local composites")
    if sum(1 for shot in shots if shot["kind"] == "self-introduction") != 8:
        raise RuntimeError("expected exactly eight voiced self-introduction jobs")

    manifest = {
        "schemaVersion": "cast-perspective-r5/provider-manifest-v2",
        "planId": "heart-journey-r5-semantic-gap-178-provider-198-local",
        "planStatus": "archived-never-submit",
        "doNotSubmit": True,
        "taskMatrix": "task-matrix.json",
        "scope": "Archived 198-job planning artifact retained for reproducibility only. Product scope moved to the 480p gender-rotation plan; this manifest must never be submitted.",
        "defaults": {
            "doNotSubmit": True,
            "ratio": "9:16",
            "duration": 15,
            "resolution": "720p",
            "generate_audio": True,
            "watermark": False,
        },
        "policy": {
            "provider": "fumin",
            "model": "seedance-2.0-mini",
            "expectedSemanticMasterGap": 178,
            "expectedTaskCount": 198,
            "expectedLocalCompositeOutputs": 4,
            "concurrency": 2,
            "maxApiRetry": 0,
            "candidateRoot": ".work-candidates",
            "approvalRule": "Provider outputs remain candidates until identity, frame, speech, audio, continuity, mobile and rights QA pass.",
        },
        "sourceBindings": {
            "runtimeVariantMatrix": {
                "path": "runtime-variant-matrix.json",
                "sha256": matrix_hash,
                "totalUniqueMasters": runtime["summary"]["totalUniqueMasters"],
                "currentReusable": runtime["summary"]["currentReusable"],
                "requiresGeneration": runtime["summary"]["generationGap"],
            },
            "characterCards": {
                "path": "../../../content/character_cards.v3.json",
                "sha256": character_cards_hash,
            },
        },
        "shots": shots,
        "localCompositeOutputs": composites,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = build()
    prompt_bytes = sum(path.stat().st_size for path in PROMPTS.glob("*.txt"))
    ref_bytes = sum(path.stat().st_size for path in REFS.glob("*.jpg"))
    print(
        json.dumps(
            {
                "manifest": str(MANIFEST),
                "doNotSubmit": result["doNotSubmit"],
                "semanticMasterGap": result["policy"]["expectedSemanticMasterGap"],
                "providerJobs": len(result["shots"]),
                "localCompositeOutputs": len(result["localCompositeOutputs"]),
                "voicedIntroductions": sum(1 for shot in result["shots"] if shot["kind"] == "self-introduction"),
                "promptFiles": len(list(PROMPTS.glob("*.txt"))),
                "compositeBoards": len(list(REFS.glob("*.jpg"))),
                "promptBytes": prompt_bytes,
                "compositeBoardBytes": ref_bytes,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
