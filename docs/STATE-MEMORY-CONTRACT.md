# 文字剧情 × 陪伴 Agent × 互动影游联通合同

## 单一事实源

每个 `game_run` 只有一个 PostgreSQL `snapshot`。文字选择和 Agent 私聊都必须携带当前 `revision`，并在数据库事务中加锁、裁决、写入新版本；过期请求返回 409，不重复写记忆。

## 写入路径

`人物卡 + 当前场景 + 七轴关系 + 私有记忆 + 用户输入 → DeepSeek 结构化角色回合 → 白名单/限幅验证 → StatePatch → transaction commit → receipt → UI / cinematic`

- DeepSeek 必须在同一次角色判断里生成：`dialogue`、`stageDirection`、`attitude`、`intentId`、七轴 `relationshipDelta`、结构化 `memory` 与可选 `proposedEventId`。
- DeepSeek 可以提出人物卡允许的参数变化与事件意图，但不能直接写数据库、跳转节点或创造剧情事实。
- 服务端按人物卡逐轴限幅（普通回合通常 -1..1，强事件最多 -3..3）、校验意图与事件白名单，再原子提交；越界输出整轮拒绝，不部分写入。
- 角色记忆按 `run_id + owner_id + character_id` 隔离。
- `boundary` 回合不能增加好感或吸引；边界是否影响信任、尊重、压力或芥蒂由该人物卡和本轮 DeepSeek 判断共同决定。
- 影像只在新节点已提交后播放；播放器错误不能回滚已提交剧情。

首日台本使用另一条只读表层链路：

`当前主角完整人物卡 + 群像自我介绍上下文 + 同场嘉宾公共卡 + 已提交选择/记忆 + 确定性首日骨架 → DeepSeek 短 beat / 台本 / 行动选项措辞 → 合同校验 → 主角缓存 → 运行时投影`

- DeepSeek 只能改 `title / text / textBeats / action / speakerId / choice.label / choice.hint / cast-first-impressions.targetCharacterId / icebreaker.targetCharacterId`；不能改 choice ID、Intent、Patch、下一节点或状态。
- 自我介绍提交后必须先进入 `cast-first-impressions`：其余七位嘉宾完成介绍，主角留下一条带人物、依据和待验证点的第一印象；引擎把它写成 `firstImpressionSeed`，供晚餐、短信与清晨回声回收。它不是模型可直接改写的关系结论。
- `icebreaker-choice` 必须说清三张地点/人物卡、选择后的行动、三分钟交流目的与返回后的完成条件；三项按钮必须同时显示人物姓名、具体开场和取舍，不能只交头像或人格标签。
- 每份缓存绑定人物卡版本、模型和生成时间；启动新旅程时直接读取，避免同步生成造成开局卡顿。
- 主角不得被写成 NPC 对自己说话；机械任务话术、旧钥匙任务、重复选项、self 目标和不在白名单的 speaker 会整份拒绝。

## 剧情导演与主任务

剧情导演使用另一条受约束写入路径：

`已提交快照 → 确定性资格过滤 → 候选事件 → DeepSeek 选择/桥段 → 事件合同校验 → 确定性主任务提交`

- 事件母版在 `content/story_event_catalog.v1.json`，每个模板明确阶段、前置关系、参与人数、剧情问题、玩家目标、截止点、成功证据、退出路径、冷却、记忆回收、隐私边界和媒体提示。
- DeepSeek 只能输出 `proposedEventId`、合法 `participantIds`、桥段文字、执行切口、公开原因和允许回调的记忆 ID；任何 `statePatch`、新角色、新事件、范围外参与者、编造时间或越权记忆都会被拒绝或丢弃。
- 真正显示在 UI 的主任务目标来自事件库，而不是模型自由生成；模型生成的执行切口只作为补充。关系轴、剧情阶段、节点和结局都由服务端提交。
- 同一时刻只允许一个 `storyMission.status=active`。玩家可提交 `completed`、`declined` 或 `expired`；拒绝使用事件模板的退出路径，不自动扣关系分。
- “鲶鱼”与前任披露模板默认锁定：前者必须先存在完整审核人物卡和 `bombshell` cast tag，后者必须有 `consentedPastDisclosure` 明示同意标记。
- API：`POST /api/runs/{run_id}/story-director` 激活或等待；`POST /api/runs/{run_id}/story-missions/{mission_id}/resolve` 确定性提交结果。

## EchoCore 互通人物卡

人物母版存放于 `content/character_cards.v3.json`。每张卡包含：

- 身份与独立兴趣：角色不围着玩家待机；
- 七个人格轴、公开面具、欲望、价值、恐惧、盲点、边界与冲突策略；
- 四类玩家人格的沟通策略，以及脆弱、暧昧、冲突、边界场景策略；
- 原创 few-shot、记忆范围/召回方法与专属剧情事件；
- DeepSeek 可输出的意图、事件和每一关系轴的变化范围。

v3 额外明确四层证据：原始 DOCX 人物事实、运行时改编、MBTI 偏好、公共领域文学研究锚点。证据冲突时以前者优先；文学微引文不进入玩家对白，只帮助作者提取“如何观察、如何决策、如何在压力下改变句式”。

同一人物卡可通过 Surface Adapter 投影给文字游戏、情感陪伴 Agent 和互动影游；三种表面共享同一个 Runtime Snapshot，不各自维护“另一套好感”。MBTI 只是参考层，不覆盖原始人物事实。

## 关系与记忆

关系不是单一好感值，而是有方向的七轴：`trust / affection / respect / fear / debt / attraction / resentment`。旧版 `affection` 与 `trust` 字段只保留为 UI 兼容投影。

每条记忆至少保存：原话、事实摘要、角色解释、显著度、情绪效价、来源回合和允许回调的事件。角色解释是主观 Belief，不升级为客观 Fact。

## 首次联通验收

1. 玩家看完节目背景、进入别墅并完成自我介绍选择。
2. 玩家听完其余七位嘉宾的介绍，留下一个以后可由行动验证的第一印象；随后才看到大白话版三分钟破冰规则。
3. 玩家从三项同时显示姓名与开场动作的破冰行动中选定一位非 self 嘉宾；该头像亮“1”并主动进入 1 对 1。
4. DeepSeek 基于该角色完整人物卡生成台词、态度、七轴变化、记忆和事件建议。
5. 服务端校验并写入该角色的独立 `agent_memories` 与运行快照。
6. 一段真实寒暄写入指定角色的独立记忆后，确定性解锁组队三选项；不要求首聊立刻触发专属事件。
7. “心动短信”排除玩家自己，并让第二天回声读取同一对象与记忆。
8. UI 回执公开态度、参数提交原因与事件激活，但不暴露人物卡私密字段或系统提示词。

## 隐私和发布边界

发布包不含原海报、参考视频、供应商任务 ID、密钥、候选文件或本地绝对路径。玩家界面只看到角色、剧情、关系回执和运行时媒体。
