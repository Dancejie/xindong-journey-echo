# 心动之旅：MBTI 恋综模拟器

移动端优先的 EchoDrama 垂直切片，用同一份持久化状态验证三层产品能力：

1. **文字互动剧情**：先介绍七天六夜与八位嘉宾，再按“抵达—自我介绍—破冰—指定私聊—组队—心动短信”推进；每个主角的台本和三项行动由 DeepSeek 结合人物卡预生成，引擎只接受固定 ID、Intent、Patch 和下一节点。
2. **情感陪伴 Agent**：八位嘉宾各有 EchoCore v3 人物卡；DeepSeek 在同一回合生成台词、态度、七轴关系变化、独立记忆与事件建议，服务端负责白名单校验、限幅和原子提交。
3. **AI 互动影游**：只有状态提交成功后才播放对应过场，媒体触发带状态回执。
4. **恋综剧情导演 Agent**：服务端先按阶段、关系、态度、记忆、冷却和隐私条件筛出事件候选；DeepSeek 只能在候选中选择参与者并生成桥段，确定性状态机负责激活、完成或退出主任务。

核心实现：

- `content/character_cards.v3.json`：8 张证据分层、可跨文字游戏/陪伴 Agent/互动影游互通的人物母版。
- `content/day1_script_flavors.v1.json`：8 份经合同校验和人物风味复核的 DeepSeek 首日台本缓存；开局直接读取，避免同步生成造成卡顿。
- `scripts/generate-day1-script-cache.py`：使用受保护的本地 DeepSeek 配置并发生成/复核台本缓存，不把密钥写入内容或前端。
- `content/research_sources.v3.json`：原始 DOCX、MBTI 与公共领域文学行为参考的来源、证据层级和版权用途。
- `backend/game_content.py` 与 `backend/day1_script.py`：确定性剧情节点、DeepSeek 表层台本合同、非 self/目标白名单校验、事件门槛与 StatePatch。
- `content/story_event_catalog.v1.json`：16 个带前置条件、玩家任务、失败出口、回调与媒体提示的恋综事件模板，包含“水上踏板”同意边界与反差成长事件。
- `content/story_event_sources.v1.json`：恋综机制研究证据与设计用途，不复制具体节目剧情。
- `backend/story_director.py`：事件资格过滤、DeepSeek 导演提示、输出校验、主任务提交与解决。
- `backend/app.py`：SSO、PostgreSQL、Agent 网关与业务 API。
- `frontend/src/App.tsx`：节目序章、动态头像选人/观察视角、两阶段打字机、指定嘉宾亮“1”的引导私聊、非 self Agent 私聊、过场和联通回执。
- `frontend/public/media/`：经 R4 内容与技术 QA 的 Seedance 运行时 master 与稳定帧；9 个 Day 1 主事件和 16 个 StoryEvent 达到 `25/25` canonical 覆盖，25 条主合同分别对应 25 个唯一 R4 master。
- `media/production/identity-audio-r4/`：R4 生成、候选裁决、主角形象引用、音频/视觉 QA 与运行时集成证据；25 条主片均为 15.000 秒 / 360 帧，AAC 原生音轨保留。
- `scripts/validate_event_media_coverage.py`：独立校验 25 条 canonical 合同的文件、SHA、帧数、编码、音频、快速起播、全片解码与音频/视觉 QA 绑定。

## 当前验证边界

- 已实现：8 张详细人物卡、8 份 DeepSeek 主角台本缓存、首日强引导流程、七轴关系、DeepSeek 结构化角色回合、16 个研究型恋综主任务模板、剧情导演候选/激活/退出闭环、独立记忆、旧存档迁移、同一快照数据联通、Seedance 动态肖像，以及 9 个 Day 1 主事件 + 16 个 StoryEvent 的本地运行时媒体覆盖。
- 事件媒体闭环：服务端先验证并提交 `StoryEvent`，再把白名单 `runtimeAsset` 随回执返回。媒体首播是一次性电影段：不循环、默认有声，播放期间暂停旁白打字机；视频自然结束后自动关闭并从第 1 个字开始逐字旁白，只保留可选“跳过”，不存在“继续剧情”阻塞按钮。
- 后续背景语义：同一素材在正文阶段才转为静音循环的场景背景，仅提供动态氛围、不控制剧情进度；用户可手动重新开声。
- 媒体唯一性：25 条 canonical 主合同对应 25 个唯一 master SHA，主合同之间不再声明式复用物理视频。另保留 2 条历史人物变体，不计入 25 条 R4 主合同门禁。
- 内容终验：音频 QA `25/25` 通过、`P0=0` / `P1=0`；视觉 QA `25/25` 通过、`P0=0` / `P1=0`。证据分别见 `media/production/identity-audio-r4/audio-content-qa-r4.json` 与 `media/production/identity-audio-r4/visual-content-qa-r4.json`。
- 在线 Agent：只调用服务端配置的 DeepSeek。未配置、超时或输出未通过人物卡合同时，本轮明确失败且不写入任何关系参数或记忆。
- 原始 DOCX 已重新定位并用于证据对齐；当前海报/运行时阵容为 5 男 3 女，与原稿 4 男 4 女不同，本轮玩家文案只称“八位嘉宾”，阵容重制仍是独立 P1，不伪称已经解决。
- 本地剧情导演样片：`python3 scripts/sample_story_director.py`，输出到 `qa/DEEPSEEK-STORY-DIRECTOR-FLAVOR.md`；读取本机忽略文件 `.env.deepseek.local`，不会写入线上数据库。
- 未声称：完整恋综季度、多端社区/UGC、跨剧永久记忆、商业素材清权或实时生成视频。

## GitHub / Render 部署配置（当前未部署）

仓库保留 GitHub / Render 部署配置，目标形态可保留完整 MP4、PostgreSQL 角色独立记忆和服务端 Agent 接口，并把 Cowork 内网 SSO 替换成匿名访客身份。部署方式和密钥边界见 `README_RENDER.md` 与根目录 `render.yaml`；当前验收仅覆盖本地运行时，未声称已上传 GitHub、已在 Render 发布或已有公网可玩地址。DeepSeek 密钥只允许配置在 Render 环境变量，前端、人物卡和 GitHub 均不含密钥。

## Mini Tool 1.4.1 离线包

独立于完整 Cowork 版的离线投影位于 `frontend/minitool-src/`。它不携带 MP4、后端、密钥或网络调用：10 段 Seedance 运行时视频被投影为动画 WebP，8 个角色通过包内确定性角色 Agent 即时回应，并把每个角色的记忆、好感与信任分别写入本机状态，再回流到 DAY 2 剧情。

- 编码动态媒体：`cd frontend && pnpm minitool:motion`
- 构建离线运行时：`cd frontend && pnpm minitool:build`
- 严格校验：`cd frontend && pnpm minitool:validate`
- 校验并打包：`cd frontend && pnpm minitool:package`
- 上传产物：`release/xindong-journey-minitool-1.4.1.zip`

平台边界：Mini Tool 1.4.1 禁止联网，因此这里的“即时 Agent”是包内角色规则与独立记忆，不等同于完整 Cowork 版的在线模型 Agent；本地记忆也不承诺跨设备或永久保存。
