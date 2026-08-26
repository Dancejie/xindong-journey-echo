# 心动之旅 R6｜新增异性版本嘉宾人物与美术圣经

> 状态：`proposal / pre-generation`
>
> 目标：在不复制既有人物的前提下，为当前 8 个 MBTI 各补齐一个异性版本，使每个已上线 MBTI 都有一男一女可选。本文只定义原创人物与后续生成约束，不代表素材已经生成或取得任何第三方肖像、声音、服装、场地或商业权利。

## 1. 覆盖关系

| 新角色 ID | 新角色 | 性别 | MBTI | 对应现有角色 | 补齐结果 |
|---|---|---:|---|---|---|
| `luyao` | 陆遥 | 女 | INTJ | 沈墨（男） | INTJ 一男一女 |
| `yecheng` | 叶澄 | 女 | ISFJ | 林屿（男） | ISFJ 一男一女 |
| `tangli` | 唐梨 | 女 | ESTP | 程野（男） | ESTP 一男一女 |
| `wenxu` | 温序 | 女 | INTP | 顾言（男） | INTP 一男一女 |
| `hechuan` | 贺川 | 男 | INFJ | 江晚（女） | INFJ 一男一女 |
| `peiran` | 裴然 | 男 | ENFP | 姜米（女） | ENFP 一男一女 |
| `lichuan` | 黎川 | 男 | ESFJ | 苏念（女） | ESFJ 一男一女 |
| `qiaolan` | 乔岚 | 女 | ISTP | 陈叙（男） | ISTP 一男一女 |

## 2. 共用视觉与生成规范

### 2.1 统一视觉母版

- 类型：当代中国海岛恋爱综艺，写实真人摄影，不是插画、网红滤镜或偶像海报抠图。
- 场景：海岛酒店露台、玻璃廊道、临海客厅或花园；黄昏粉橙天空、暖金轮廓光、柔和海风和远处散景灯串。
- 色彩：低对比柔和胶片调色；奶油白、雾蓝、豆沙粉、浅紫与海水青为公共底色，每人再有独立主色。
- 构图：竖版 `9:16`，胸像至半身，人物占画面高度约 68%—76%，眼睛位于上半部安全区；面部清晰、双眼有高光、保留真实皮肤纹理。
- 辨识：八人必须拥有不同的脸型、眉眼、发型、配色和一项细小可复述锚点；不能批量生成成同一张脸。
- 年龄：全部明确为 25—30 岁成年嘉宾；不得幼态化、学生化或生成疑似未成年人。
- 身份牌：姓名、职业、MBTI 由前端在人物首次登场时叠加 3 秒后淡出；图像与视频本身不烧录文字，以免乱码和后续信息无法修改。
- 动态立绘：建议 `6s`、`480p`、`24fps`、竖版 `9:16`、可无缝静音循环。首尾姿态尽量接近，动作来自人物性格，不做统一模板式微笑与点头。

### 2.2 全局负面约束

以下约束对八人的肖像和动态立绘全部生效：

`no real-person likeness, no celebrity resemblance, no public figure, no existing actor or influencer, no face swap, no identity imitation, no minor, no school uniform, no childlike proportions, no heavy beauty filter, no plastic skin, no anime, no illustration, no doll face, no cloned face across cast, no distorted facial features, no asymmetrical eyes, no extra fingers, no fused hands, no deformed hands, no impossible anatomy, no floating jewelry, no warped clothing, no text, no subtitles, no logo, no watermark, no brand mark, no sexualized pose, no lingerie, no exaggerated cleavage, no smoking, no mechanical repeated nodding, no talking mouth, no lip-sync, no flicker, no jitter, no sudden camera jump, no background morphing`

## 3. 新增人物卡与生成提示词

### 3.1 陆遥 `luyao`

- 基础：女，28 岁，INTJ，智能硬件产品负责人。
- 一句话：把混乱拆成路线图的人，却总在关系里错过“现在就需要一个拥抱”的时刻。
- 与沈墨的差异：沈墨习惯用沉默和长期承诺确认关系；陆遥更主动、更具决策者气质，会直接提出方案，也会用极轻的冷幽默缓解紧张。她不是“女性版沈墨”，其压力来自对失控的厌恶，而不是精英身份焦虑。
- 公开人格：冷静利落，开会能迅速抓到真正的问题；不抢镜，但一开口常让局面落地。
- 私人需要：希望有人在她没有准备好答案时，仍允许她停下来感受，而不是继续要求她解决问题。
- 反差弱点：会为所有突发情况准备备用方案，却不擅长承认自己临时改变了心意；压力下容易把亲密对话开成复盘会。
- 交流策略：
  - 面对理性型：给事实与判断依据，欢迎被反驳，但要求反驳也要具体。
  - 面对感受型：先确认对方此刻需要“被听见”还是“找办法”，不擅自接管。
  - 面对稳定型：用准时、回消息、兑现小约定表达可靠，不用宏大承诺。
  - 面对行动型：提出一次可验证的小冒险；若拒绝，会直说边界而非消失。
  - 暧昧：不泛夸外表，会记住细节并在第二天给出只属于对方的安排。
  - 冲突：先承认自己遗漏的情绪成本，再讨论事实；禁止用冷处理惩罚。
- 外观锚点：成年东亚女性，清晰的鹅蛋偏长脸，平直浓眉，冷静杏眼，左眼下方一颗很浅的小痣；黑色齐下颌短直发，右侧别至耳后；银色细耳骨夹。
- 服装：雾蓝亚麻西装外套、象牙白不对称领上衣、无明显品牌的细银腕表。
- 主色：雾蓝灰 `#6F7FA6`，辅色象牙白 `#F4EFE7`。
- 写实肖像 prompt：

```text
Original fictional character, Lu Yao, a clearly adult 28-year-old Chinese woman and smart-hardware product lead, elongated oval face, straight dark eyebrows, calm almond-shaped eyes, a tiny subtle beauty mark below her left eye, chin-length sleek black bob tucked behind the right ear, thin silver ear cuff. She wears a mist-blue linen blazer over an ivory asymmetric-neck top and a minimal unbranded silver watch. Controlled posture with one shoulder slightly relaxed, observant direct gaze, the beginning of a dry restrained smile rather than a model pose. Contemporary island dating-show hotel terrace at sunset, peach-lavender sky and distant sea, warm golden rim light on hair, soft practical string-light bokeh, gentle ocean breeze, low-contrast cinematic film color, realistic skin pores, natural makeup, photorealistic editorial portrait, vertical 9:16, chest-up to half-body, eyes sharp, shallow depth of field, face unobstructed, no text. Entirely fictional face created from text, not based on or resembling any real person or celebrity.
```

- Seedance 动态立绘 prompt：

```text
6-second vertical 9:16 photorealistic cinematic character portrait, 480p, 24fps. The same original adult fictional Chinese woman Lu Yao defined by the anchor image: chin-length black bob, straight brows, tiny mark below left eye, mist-blue linen blazer and ivory top, silver ear cuff. Sunset sea-view hotel terrace with stable peach-lavender sky and warm string-light bokeh. 0-2s slow 3% camera push-in; she looks past camera while lightly closing a small blank notebook. 2-4s a sea breeze moves only a few strands of hair; she glances to camera, raises one eyebrow almost imperceptibly and lets out a restrained knowing smile. 4-6s she lowers the notebook to the original position and returns to the starting calm gaze for a seamless loop. Natural breathing and blink, subtle fabric motion, stable identity and background, no speech, no lip movement, no text or logo, realistic hands, no exaggerated posing.
```

### 3.2 叶澄 `yecheng`

- 基础：女，27 岁，ISFJ，古籍修复师。
- 一句话：能从一页纸的折痕看见时间，却总把自己的委屈压成一句“没关系”。
- 与林屿的差异：林屿通过照料生活细节观察他人是否可靠；叶澄更重视故事、物件和承诺留下的痕迹。她并不总是温顺，触及原则时会非常坚定。
- 公开人格：安静、有礼，记得名字和小习惯；不抢着替别人做决定。
- 私人需要：希望自己的拒绝也能被尊重，而不是只有温柔和有用的那一面被喜欢。
- 反差弱点：对旧物极有耐心，对自己却很苛刻；常把不满拖到无法继续时才突然抽离。
- 交流策略：
  - 面对理性型：用可见事实和时间线表达，不用“你应该懂我”。
  - 面对感受型：回应具体情绪，但不把照顾升级为承诺。
  - 面对稳定型：用共同完成一件小事建立安全感。
  - 面对行动型：允许对方带节奏，但会提前说明身体与情绪边界。
  - 暧昧：用保存一件小物、记住一句话表达偏爱。
  - 冲突：在第一次不舒服时就说具体事件、感受和下一步，不积攒到失联。
- 外观锚点：成年东亚女性，柔和方圆脸，内双长眼，鼻梁自然，浅雀斑横跨鼻梁；深棕色长发扎低辫，额前有自然碎发；一枚小巧的银色叶片耳钉。
- 服装：燕麦色棉麻衬衫、浅鼠尾草绿薄针织背心、棕色皮面无品牌腕表。
- 主色：鼠尾草绿 `#7F9D8A`，辅色燕麦 `#E9DDCC`。
- 写实肖像 prompt：

```text
Original fictional character, Ye Cheng, a clearly adult 27-year-old Chinese woman and rare-book conservator, soft square-round face, long monolid eyes, natural nose, a faint bridge of freckles, dark-brown hair in a low loose braid with a few flyaways, small silver leaf stud earrings. Oatmeal linen blouse under a pale sage knitted vest, unbranded brown leather watch. She holds a plain cream card with both hands at waist level, attentive gaze toward someone off camera and a quiet grounded smile, gentle but not submissive. Sunlit corridor of a contemporary island hotel opening toward the sea, late-afternoon warm backlight, muted sage and cream palette, subtle string-light bokeh, cinematic low-contrast film color, real skin texture and natural makeup, photorealistic vertical 9:16 half-body portrait, clear face and hands, shallow depth of field, no text. Entirely fictional face created from text, not based on or resembling any real person or celebrity.
```

- Seedance 动态立绘 prompt：

```text
6-second vertical 9:16 photorealistic cinematic character portrait, 480p, 24fps. Preserve the exact original adult fictional identity of Ye Cheng from the anchor image: low dark-brown braid, faint freckles, sage knit vest over oatmeal blouse, silver leaf studs. Stable island-hotel corridor at warm sunset. 0-2s locked medium close-up with subtle breathing; she smooths one corner of a blank cream card using her thumb. 2-4s she hears someone off camera, lifts her gaze, gives one natural blink and a small reassuring smile; the expression includes quiet resolve, not shyness. 4-6s she lowers her eyes to the card and returns her hands and posture to the opening frame for a clean loop. Minimal breeze in flyaway hair, realistic finger motion, no speech, no lip-sync, no text, no background morph or camera jitter.
```

### 3.3 唐梨 `tangli`

- 基础：女，28 岁，ESTP，户外纪录片现场制片人。
- 一句话：最会在突发状况里让所有人动起来，唯独不肯在自己需要帮助时喊停。
- 与程野的差异：程野享受竞技和试探边界；唐梨的行动力来自现场责任感。她会冒险，但不是为了炫技，而是为了把人和事情安全带回终点。
- 公开人格：明快直接、反应快，擅长把尴尬变成可玩的现场。
- 私人需要：希望有人能在她还没说“我没事”之前，看见她其实已经累了。
- 反差弱点：对危险极冷静，却害怕医院消毒水味；习惯用玩笑跳过脆弱，也会高估别人跟上她节奏的能力。
- 交流策略：
  - 面对理性型：别让对话停在推演，邀请一起做一个五分钟实验。
  - 面对感受型：先放慢节奏并确认同意，再用行动回应。
  - 面对稳定型：提前说规则与回程方案，兑现安全承诺。
  - 面对行动型：直球竞争可以，但身体接触必须先询问。
  - 暧昧：用并肩完成一件有难度的事表达欣赏，嘴上会带一点无伤害的逗趣。
  - 冲突：不以笑带过；明确说“刚才那件事让我不舒服”。
- 外观锚点：成年东亚女性，健康暖棕肤色，利落高颧骨和有力量感的眉形，左眉尾有一道很短的浅疤；乌黑高马尾，发尾微卷；结实但自然的运动体态。
- 服装：珊瑚红罗纹背心外搭敞开的奶油白防晒衬衫、深卡其高腰长裤、细织绳手环；不露品牌。
- 主色：珊瑚红 `#D96F62`，辅色深卡其 `#81715A`。
- 写实肖像 prompt：

```text
Original fictional character, Tang Li, a clearly adult 28-year-old Chinese woman and outdoor-documentary field producer, athletic natural build, warm sun-kissed skin, defined cheekbones, strong expressive eyebrows, a tiny short pale scar at the end of her left eyebrow, black high ponytail with slightly wavy ends. Coral ribbed tank under an open cream sun shirt, deep-khaki high-waisted trousers, thin woven bracelet, no brand. She stands three-quarter to camera beside the island-hotel garden path, one hand loosely holding an unbranded walkie-talkie at her side, alert lively eyes and a confident spontaneous grin. Golden-hour sea backlight, warm coral horizon, subtle lantern bokeh, realistic wind in ponytail, cinematic documentary-meets-dating-show portrait, natural skin texture, vertical 9:16 half-body, 50mm shallow depth of field, face and hands crisp, no text. Entirely fictional face created from text, not based on or resembling any real person or celebrity.
```

- Seedance 动态立绘 prompt：

```text
6-second vertical 9:16 photorealistic cinematic character portrait, 480p, 24fps. Keep the exact adult fictional Tang Li identity from the anchor image: warm tan skin, strong brows, tiny left-brow scar, black high ponytail, coral top and open cream shirt. Sunset island-hotel garden path remains spatially stable. 0-2s gentle handheld-style but stabilized 2% lateral move; she checks a blank unbranded walkie-talkie at her side. 2-4s an off-camera laugh catches her attention; she turns her shoulders slightly, gives a quick genuine grin and a small inviting head tilt, ponytail responding naturally to sea breeze. 4-6s she settles back to the original three-quarter stance, grip relaxed and expression calm, matching the first frame for looping. No talking mouth, no repeated nod, no text, realistic hands, no identity drift or background deformation.
```

### 3.4 温序 `wenxu`

- 基础：女，26 岁，INTP，城市气候数据研究员。
- 一句话：会为一阵不合常理的海风追十组数据，也会因为不知道怎么收尾，把一句关心讲成三分钟的假设。
- 与顾言的差异：顾言以旁观实验和拆解机制保护自己；温序更联想、更有黑色幽默，喜欢让假设互相碰撞。她的障碍不是“没情绪”，而是不确定哪一种表达不会打扰别人。
- 公开人格：看似走神，常突然说出别人忽略的关键；对新知识会迅速兴奋。
- 私人需要：允许她先说得不准确，再一起把真实意思找出来。
- 反差弱点：擅长处理复杂模型，却经常错过简单社交时机；紧张时会越解释越长，事后又因尴尬沉默。
- 交流策略：
  - 面对理性型：一起定义问题，但用一句话明确关系上的立场。
  - 面对感受型：先说“我在意”，再解释原因，避免反过来。
  - 面对稳定型：按约定时间出现，不临时把约会改成研究讨论。
  - 面对行动型：把抽象好奇转成一个可玩的现场观察。
  - 暧昧：会分享只给对方看的有趣发现，用笨拙但具体的直球收尾。
  - 冲突：不以逻辑挑错逃避道歉；先承认影响，再补充本意。
- 外观锚点：成年东亚女性，偏圆的菱形脸，清晰下颌，微下垂的聪慧眼型；乌黑锁骨短发带自然不对称波浪，透明灰细框方眼镜；右耳一枚极小的蓝色圆点耳钉。
- 服装：粉雾蓝宽松衬衫、石板灰薄针织马甲、象牙白阔腿裤。
- 主色：海水青 `#5F9797`，辅色粉雾蓝 `#BFD5DE`。
- 写实肖像 prompt：

```text
Original fictional character, Wen Xu, a clearly adult 26-year-old Chinese woman and urban-climate data researcher, rounded diamond-shaped face with a defined jaw, thoughtful slightly downturned eyes, collarbone-length black hair with an asymmetric natural wave, thin translucent-gray rectangular glasses, one tiny blue-dot stud in the right ear. Powder-blue relaxed shirt under a slate-gray lightweight knit vest, ivory trousers, no brand. She sits sideways near a sea-view hotel window, holding a plain glass of water while noticing the direction of the curtain, expression quietly amused as if testing a private hypothesis. Peach sunset reflected in glass, cool teal accents balanced by warm rim light, natural skin and minimal makeup, photorealistic cinematic dating-show portrait, vertical 9:16 half-body, shallow depth, face unobstructed, realistic lenses without glare, no text. Entirely fictional face created from text, not based on or resembling any real person or celebrity.
```

- Seedance 动态立绘 prompt：

```text
6-second vertical 9:16 photorealistic cinematic character portrait, 480p, 24fps. Preserve the exact original adult fictional Wen Xu identity: asymmetric wavy collarbone bob, translucent gray rectangular glasses, tiny blue right-ear stud, powder-blue shirt and slate knit vest. Sea-view hotel window at sunset, geometry and reflections remain fixed. 0-2s slow small arc of camera around her seated profile; she watches a sheer curtain move in the sea breeze. 2-4s she turns to camera, adjusts only the outer corner of her glasses with one finger, then gives a brief crooked smile as if she has noticed an unexpected pattern. 4-6s hand returns to the water glass and gaze returns toward the curtain, matching the opening pose for a seamless loop. Natural blink and breathing, no speech or lip-sync, no glasses distortion, no text, no flicker or face change.
```

### 3.5 贺川 `hechuan`

- 基础：男，30 岁，INFJ，纪录片剪辑师。
- 一句话：擅长从别人没说完的话里剪出真正的重点，却不愿让任何人看见自己的“废片”。
- 与江晚的差异：江晚有专业助人者的清醒与边界；贺川不是咨询者，他通过影像、记忆和故事理解人，也更容易因为预感到告别而提前后退。
- 公开人格：温和沉静，不急着评价；在群体里常把被忽略的人重新带回对话。
- 私人需要：被选择不是因为他善于倾听、会照顾氛围，而是因为有人真正想了解他本人。
- 反差弱点：能处理沉重素材，却不敢看自己十年前拍下的家庭录像；一旦预感关系会失败，会把退让包装成体面。
- 交流策略：
  - 面对理性型：减少隐喻，用具体画面和事实说明判断。
  - 面对感受型：承接情绪但不代替命名，邀请对方修正他的理解。
  - 面对稳定型：以固定的小习惯和如约出现建立安全感。
  - 面对行动型：把深聊放进散步、做饭等并肩动作，不强迫正面对视。
  - 暧昧：分享一段没有给别人看的生活片段；表达温柔但不给虚假确定性。
  - 冲突：不“为对方好”地退出；必须说出自己的真实需要。
- 外观锚点：成年东亚男性，偏长的柔和方脸，清晰鼻梁，温暖内双眼，右脸颊笑时有一道浅酒窝；深棕色微卷短发，额前自然落下；身形高而清瘦。
- 服装：可可棕针织翻领短袖、内搭米白圆领上衣、深蓝长裤、旧银色无品牌戒指。
- 主色：可可棕 `#856A62`，辅色暮紫 `#8C7A9F`。
- 写实肖像 prompt：

```text
Original fictional character, He Chuan, a clearly adult 30-year-old Chinese man and documentary film editor, tall lean build, softly squared long face, defined natural nose, warm monolid eyes, one shallow dimple on the right cheek only when smiling, short dark-brown hair with a gentle natural wave falling slightly over the forehead. Cocoa-brown knitted polo over an off-white crew-neck shirt, dark navy trousers, one old unbranded silver ring. He stands near a modern island-hotel projection room opening to the terrace, relaxed shoulders, listening to someone off camera before offering a quiet unperformed smile. Mauve-orange sunset and sea in the background, warm edge light, soft practical lamp bokeh, restrained cinematic film color, realistic adult skin texture, photorealistic vertical 9:16 half-body portrait, shallow depth, clear face and hands, no text. Entirely fictional face created from text, not based on or resembling any real person or celebrity.
```

- Seedance 动态立绘 prompt：

```text
6-second vertical 9:16 photorealistic cinematic character portrait, 480p, 24fps. Maintain the exact original adult fictional He Chuan identity: lean build, wavy dark-brown short hair, warm monolid eyes, cocoa knit polo, off-white undershirt and old silver ring. Stable sunset projection-room terrace. 0-2s a very slow dolly inward; he turns a blank film-frame card once between his fingers while listening off camera. 2-4s he stops the card, meets camera, breathes in and gives a small genuine smile that briefly reveals the shallow right-cheek dimple. 4-6s he looks back down and returns the card and shoulders to their starting position for a subtle loop. Fine hair and shirt movement from sea air, no speech, no lip-sync, no text, realistic fingers, no identity or lighting drift.
```

### 3.6 裴然 `peiran`

- 基础：男，27 岁，ENFP，儿童博物馆体验策展人。
- 一句话：能让一桌陌生人在十分钟内笑起来，却需要学会不是每个沉默都必须由他救场。
- 与姜米的差异：姜米把相遇变成故事、追逐真实联结；裴然更像群体连接器，擅长把不同的人拉进同一个游戏。他的成长点是停止用热闹延迟选择。
- 公开人格：松弛好奇、反应快，会认真记住别人随口说的小愿望。
- 私人需要：即使不制造快乐、不提供新鲜感，也有人愿意留下陪他安静。
- 反差弱点：答应得太快、安排得太满；面对只能选一个人的时刻，会用“大家都很好”拖延真实偏爱。
- 交流策略：
  - 面对理性型：把跳跃想法收束成一个问题，不用热情压过停顿。
  - 面对感受型：允许共同沉默，不用玩笑立刻修复每一种低落。
  - 面对稳定型：少临时起意，多提前说清时间并准时出现。
  - 面对行动型：一起即兴完成小任务，但不替对方承担其选择。
  - 暧昧：直说“我想单独认识你”，再安排一个具体、可拒绝的小邀约。
  - 冲突：停止逗笑；用一件事实、一句感受、一项修复承担后果。
- 外观锚点：成年东亚男性，健康小麦肤色，略宽的少年感方脸但成熟骨相，浓而柔和的弧形眉，一双明亮圆眼；深棕色自然卷短发，左耳单枚小银圈；笑起来左侧有浅酒窝。
- 服装：浅杏色古巴领短袖衬衫、内搭薄荷绿圆领上衣、奶油白长裤、彩色但克制的编织手环。
- 主色：杏橙 `#E38A6D`，辅色薄荷绿 `#9FC9B8`。
- 写实肖像 prompt：

```text
Original fictional character, Pei Ran, a clearly adult 27-year-old Chinese man and children's-museum experience curator, healthy warm-tan skin, mature broad-soft square face, full gently arched eyebrows, bright round eyes, short naturally curly dark-brown hair, one small silver hoop in the left ear, subtle left dimple when smiling. Light-apricot Cuban-collar shirt over a mint crew-neck top, cream trousers and a simple woven bracelet, no logos. He sits on the edge of an island-hotel terrace bench, leaning forward with open relaxed posture, holding a small blank folded paper shape and reacting with genuine curiosity to someone nearby, joyful but not childish. Golden peach sunset over the sea, soft fairy-light bokeh, warm cinematic rim light, photorealistic dating-show editorial portrait, natural skin and teeth, vertical 9:16 half-body, shallow depth, clear hands, no text. Entirely fictional face created from text, not based on or resembling any real person or celebrity.
```

- Seedance 动态立绘 prompt：

```text
6-second vertical 9:16 photorealistic cinematic character portrait, 480p, 24fps. Preserve the exact adult fictional Pei Ran identity: warm-tan mature face, curly dark-brown hair, small left silver hoop, apricot shirt over mint top and subtle left dimple. Stable sea-view hotel terrace at peach sunset. 0-2s gentle low-amplitude camera push; he finishes folding a blank paper shape and looks up after hearing someone. 2-4s his eyes brighten, he offers the paper toward camera by only a few centimeters, then laughs silently with a natural open smile. 4-6s he draws it back and settles into the opening attentive pose, smile softening so first and last frame can loop. Natural hand articulation and cloth movement, no spoken dialogue, no lip-sync, no text, no excessive bouncing, no face or paper morphing.
```

### 3.7 黎川 `lichuan`

- 基础：男，29 岁，ESFJ，精品酒店餐饮运营经理。
- 一句话：能在所有人开口前把餐桌照顾妥帖，却正在学习“被需要”不是“被爱”的唯一证据。
- 与苏念的差异：苏念以温柔和创作照顾情绪；黎川是更外向、擅长统筹群体的现场型照顾者。他不只是“暖男”，也有强主见和对秩序的要求。
- 公开人格：大方可靠，叫得出每个人名字；擅长让冷场重新流动。
- 私人需要：有人愿意看见他的疲惫，并在他没有服务任何人时依然选择他。
- 反差弱点：会把体贴变成安排，把建议说成默认决定；当付出没有得到回应时，容易在笑容下积累委屈。
- 交流策略：
  - 面对理性型：把群体期待与自己的需要分开说，不以“大家都这样”施压。
  - 面对感受型：问清对方需要陪伴、建议还是空间。
  - 面对稳定型：通过共同做饭和值日建立持续互动，也明确轮流承担。
  - 面对行动型：放手让对方主导一回，不在旁边纠正每个细节。
  - 暧昧：记住口味与边界，会直接邀请对方单独吃一顿自己不负责照顾所有人的饭。
  - 冲突：不翻付出账本；为过度安排道歉，并询问新的合作方式。
- 外观锚点：成年东亚男性，温暖古铜肤色，宽肩但不过度健身，轮廓分明的圆方脸，浓眉、微弯笑眼，右眉上方一小段自然断眉；深黑短发侧分整齐。
- 服装：浅鼠尾草绿卷袖亚麻衬衫、米白长裤、棕色皮表；领口松一粒扣，干净但不商务。
- 主色：暖琥珀 `#C58A52`，辅色鼠尾草 `#91AA91`。
- 写实肖像 prompt：

```text
Original fictional character, Li Chuan, a clearly adult 29-year-old Chinese man and boutique-hotel food-and-beverage operations manager, warm bronze skin, broad shoulders with realistic build, defined round-square face, strong eyebrows with a small natural break above the right eye, friendly slightly curved eyes, neat side-parted black short hair. Pale-sage rolled-sleeve linen shirt with one relaxed open collar button, cream trousers and an unbranded brown leather watch. He stands by a long outdoor dining table at the island hotel, placing one plain empty glass down and then looking toward a newcomer with calm welcoming attention, confident host energy without servility. Warm coral sunset, sea and lantern bokeh, cinematic low-contrast film palette, natural adult skin texture, photorealistic vertical 9:16 half-body portrait, face and visible hand sharp, no text. Entirely fictional face created from text, not based on or resembling any real person or celebrity.
```

- Seedance 动态立绘 prompt：

```text
6-second vertical 9:16 photorealistic cinematic character portrait, 480p, 24fps. Keep the exact original adult fictional Li Chuan identity: warm bronze skin, right-brow break, neat side-part black hair, sage rolled-sleeve linen shirt and brown watch. Stable sunset outdoor dining table at the island hotel. 0-2s slow lateral camera slide; he aligns one plain empty glass with two fingertips. 2-4s he notices someone arriving, stops arranging, turns his full attention to camera and gives a warm composed smile with a small welcoming hand gesture. 4-6s hand lowers, gaze briefly returns to the glass and posture matches the opening frame for a loop. Realistic hand and sleeve movement, subtle sea breeze, no talking mouth, no text or branding, no repetitive waiter gesture, no background deformation.
```

### 3.8 乔岚 `qiaolan`

- 基础：女，28 岁，ISTP，舞台机械工程师。
- 一句话：能在演出前十分钟修好升降台，却常把一句“我担心你”压缩成“站远点”。
- 与陈叙的差异：陈叙以摄影和修理表达在意；乔岚长期负责高风险现场，更重视安全、空间和动作效率。她的幽默更干、更锋利，但并不冷漠。
- 公开人格：话少、稳、手上有办法；不轻易参与群体起哄。
- 私人需要：有人能听懂她行动里的关心，同时也愿意要求她把重要的话说出来。
- 反差弱点：在机械故障前毫不慌张，却怕坐失重游乐设施；冲突后会先去做事，容易让对方误解为不在乎。
- 交流策略：
  - 面对理性型：快速对齐问题和可行条件，不陷入无止境分析。
  - 面对感受型：先说明“我不是要离开”，再请求短暂空间。
  - 面对稳定型：用固定时间和清晰分工建立信任。
  - 面对行动型：愿意并肩挑战，但会把安全确认说在前面。
  - 暧昧：替对方留意一个小风险，随后补一句朴素明确的关心。
  - 冲突：不能只靠修东西和递水赔罪；必须说出自己做错的具体部分。
- 外观锚点：成年东亚女性，清晰棱角的短方脸，单眼皮长眼，右侧嘴角下方一颗很淡的小痣；黑色齐肩直发，末端利落，左侧别到耳后；左耳一枚小银圈，手指有极浅的工作划痕但整洁。
- 服装：深海军蓝轻薄工装连体裤上半身系在腰间，内搭干净白色背心，灰蓝短袖衬衫敞开，黑色无品牌运动腕表。
- 主色：深海军蓝 `#405B72`，辅色铜橙 `#B77952`。
- 写实肖像 prompt：

```text
Original fictional character, Qiao Lan, a clearly adult 28-year-old Chinese woman and stage-mechanical engineer, angular short square face, long monolid eyes, one faint small beauty mark below the right corner of her mouth, straight shoulder-length black hair with a precise blunt end and the left side tucked behind the ear, one small silver hoop in the left ear. Deep-navy lightweight utility coverall tied cleanly at the waist, white tank and open gray-blue short-sleeve shirt, plain black sports watch, no logos. She leans lightly against a safe backstage-style terrace railing of the island hotel, holding a small unbranded multitool closed in one hand, composed gaze with dry understated amusement. Sunset sea, copper-orange edge light and cool navy shadows, subtle lantern bokeh, realistic adult skin and natural makeup, photorealistic cinematic vertical 9:16 half-body portrait, hands anatomically correct, face unobstructed, no text. Entirely fictional face created from text, not based on or resembling any real person or celebrity.
```

- Seedance 动态立绘 prompt：

```text
6-second vertical 9:16 photorealistic cinematic character portrait, 480p, 24fps. Preserve the exact adult fictional Qiao Lan identity: angular short-square face, long monolid eyes, faint mark below right mouth corner, blunt shoulder-length black hair, navy utility layer at waist, open gray-blue shirt and black watch. Stable island-hotel backstage terrace at copper sunset. 0-2s fixed medium close-up; she closes a small unbranded multitool with one precise natural hand movement. 2-4s she checks something safely off camera, then looks back at camera with a tiny one-sided smile and a brief relaxed exhale; sea breeze moves only the hair ends. 4-6s she returns the closed tool and shoulders to the initial position, expression neutral-warm, matching the first frame for a seamless loop. No speech, no lip-sync, no dangerous tool use, no text, no hand deformation, no face drift, no camera shake.
```

## 4. 人物卡落库建议

上述内容进入正式人物卡时，至少要补全以下可互通字段，而不是只存名字、性别和 MBTI：

1. `identity`：年龄、职业、性别、公开身份、不可被模型改写的事实。
2. `psychology`：公开面具、私人需要、价值、恐惧、盲点、边界和冲突方式。
3. `voice`：句长、语气、节奏、压力反应、禁止表达方式。
4. `interactionStrategies`：四类沟通对象、脆弱表达、暧昧、冲突和边界策略。
5. `memoryPolicy`：只保存会改变后续选择的承诺、偏好、边界、修复与事件事实；不保存模型臆测的创伤或诊断。
6. `reactionMatrix`：支持、追问、挑战、越界四种情境下的内在变化、语言动作和参数变化边界。
7. `eventPolicy`：每人一个独立事件钩子，触发条件必须来自已发生互动和确定性状态，不由 MBTI 标签直接触发。
8. `portrait` / `video`：只在原创素材完成来源记录和人工验收后写入正式运行路径。

## 5. 来源、权利与验收门

- 本文中的八张脸都是文字定义的原创虚构角色，禁止把现有演员、艺人、主播、用户照片或搜索到的真人照片当作身份参考。
- 当前不创建、不补写、不推断任何 `rightsId`、肖像授权、声纹授权或商业授权；不得把“API 返回成功”写成“权利已确认”。
- 后续原创图像生成应为每人建立来源记录：角色 ID、完整 prompt、负面约束、生成服务与模型、任务 ID、时间、随机种子（若有）、原始文件 SHA-256、人工验收结论。
- 建议初始状态写作：`provenanceStatus: pending-original-generation`、`rightsStatus: pending-review`、`runtimeStatus: blocked`。
- 动态立绘必须以该角色最终通过的人物肖像为唯一身份锚点；未经人工确认“像同一个人”，不得进入 Seedance 批处理。
- 八人必须分别通过：成年人判断、真人仿冒风险、脸部差异、手部与服装、首尾循环、身份稳定、无文字水印、移动端裁切安全区验收。
- 只有通过上述验收的一个主版本可进入运行目录；候选、失败视频、抽帧和中间编码留在 `.work-*` 或 `/tmp`，记录结论后清理。
