# 心动之旅：MBTI 恋综模拟器

移动端优先的 EchoDrama 垂直切片，用同一份持久化状态验证三层产品能力：

1. **文字互动剧情**：选择建立场景目标，角色专属事件负责把交流结果变成新物件、线索或邀约。
2. **情感陪伴 Agent**：八位嘉宾各有 EchoCore v2 人物卡；DeepSeek 在同一回合生成台词、态度、七轴关系变化、独立记忆与事件建议，服务端负责白名单校验、限幅和原子提交。
3. **AI 互动影游**：只有状态提交成功后才播放对应过场，媒体触发带状态回执。

核心实现：

- `content/character_cards.v2.json`：8 张跨文字游戏、陪伴 Agent、互动影游互通的人物母版。
- `content/research_sources.v2.json`：MBTI 与文学行为参考的来源、证据层级和版权用途。
- `backend/game_content.py`：剧情节点、DeepSeek 输出校验、事件门槛与 StatePatch。
- `backend/app.py`：SSO、PostgreSQL、Agent 网关与业务 API。
- `frontend/src/App.tsx`：移动端剧情、8 人 Agent 私聊、过场和联通回执。
- `frontend/public/media/`：经内容与技术 QA 的 Seedance 运行时 master 与稳定帧。
- `media/production/prompts/seedance-batch.json`：可追溯的生成提示词；参考图、候选与任务信息不进入发布包。

## 当前验证边界

- 已实现：8 张详细人物卡、七轴关系、DeepSeek 结构化角色回合、8 个专属事件、独立记忆、旧存档迁移、同一快照数据联通、Seedance 动态肖像和 2 条过场、数据库持久化。
- 在线 Agent：只调用服务端配置的 DeepSeek。未配置、超时或输出未通过人物卡合同时，本轮明确失败且不写入任何关系参数或记忆。
- 当前人物事实沿用已上线 v1 设定并标记 `provisional`；原始 DOCX 缓存路径已失效，重新提供原稿后可逐字段升级为 `approved`。
- 未声称：完整恋综季度、多端社区/UGC、跨剧永久记忆、商业素材清权或实时生成视频。

## GitHub / Render 公网版

公网版保留完整 MP4、PostgreSQL 角色独立记忆和服务端 Agent 接口，并把 Cowork 内网 SSO 替换成匿名访客身份。部署方式和密钥边界见 `README_RENDER.md` 与根目录 `render.yaml`。DeepSeek 密钥只允许配置在 Render 环境变量，前端、人物卡和 GitHub 均不含密钥。

## Mini Tool 1.4.1 离线包

独立于完整 Cowork 版的离线投影位于 `frontend/minitool-src/`。它不携带 MP4、后端、密钥或网络调用：10 段 Seedance 运行时视频被投影为动画 WebP，8 个角色通过包内确定性角色 Agent 即时回应，并把每个角色的记忆、好感与信任分别写入本机状态，再回流到 DAY 2 剧情。

- 编码动态媒体：`cd frontend && pnpm minitool:motion`
- 构建离线运行时：`cd frontend && pnpm minitool:build`
- 严格校验：`cd frontend && pnpm minitool:validate`
- 校验并打包：`cd frontend && pnpm minitool:package`
- 上传产物：`release/xindong-journey-minitool-1.4.1.zip`

平台边界：Mini Tool 1.4.1 禁止联网，因此这里的“即时 Agent”是包内角色规则与独立记忆，不等同于完整 Cowork 版的在线模型 Agent；本地记忆也不承诺跨设备或永久保存。
