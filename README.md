# 心动之旅：MBTI 恋综模拟器

移动端优先的 EchoDrama 垂直切片，用同一份持久化状态验证三层产品能力：

1. **文字互动剧情**：选择先经过确定性规则，再提交 `revision` 化状态。
2. **情感陪伴 Agent**：八位嘉宾各有独立人物边界、声音与 EchoMemory；模型只负责角色表达，不直接修改数值或事实。
3. **AI 互动影游**：只有状态提交成功后才播放对应过场，媒体触发带状态回执。

核心实现：

- `backend/game_content.py`：剧情、人物、白名单意图与确定性 StatePatch。
- `backend/app.py`：SSO、PostgreSQL、Agent 网关与业务 API。
- `frontend/src/App.tsx`：移动端剧情、8 人 Agent 私聊、过场和联通回执。
- `frontend/public/media/`：经内容与技术 QA 的 Seedance 运行时 master 与稳定帧。
- `media/production/prompts/seedance-batch.json`：可追溯的生成提示词；参考图、候选与任务信息不进入发布包。

## 当前验证边界

- 已实现：单集确定性分支、8 个角色独立记忆、同一快照数据联通、剧情回调、Seedance 动态肖像和 2 条过场、SSO/数据库持久化。
- 在线 Agent：Cowork 环境存在 AI 网关时调用；网关异常时回退到角色一致的边界安全回复，状态裁决不受影响。
- 未声称：完整恋综季度、多端社区/UGC、跨剧永久记忆、商业素材清权或实时生成视频。

## GitHub / Render 公网版

公网版保留完整 MP4、PostgreSQL 角色独立记忆和服务端 Agent 接口，并把 Cowork 内网 SSO 替换成匿名访客身份。部署方式和密钥边界见 `README_RENDER.md` 与根目录 `render.yaml`。OpenAI 密钥只允许配置在 Render 环境变量；调用不可用时会明确回退到角色一致的确定性回复。

## Mini Tool 1.4.1 离线包

独立于完整 Cowork 版的离线投影位于 `frontend/minitool-src/`。它不携带 MP4、后端、密钥或网络调用：10 段 Seedance 运行时视频被投影为动画 WebP，8 个角色通过包内确定性角色 Agent 即时回应，并把每个角色的记忆、好感与信任分别写入本机状态，再回流到 DAY 2 剧情。

- 编码动态媒体：`cd frontend && pnpm minitool:motion`
- 构建离线运行时：`cd frontend && pnpm minitool:build`
- 严格校验：`cd frontend && pnpm minitool:validate`
- 校验并打包：`cd frontend && pnpm minitool:package`
- 上传产物：`release/xindong-journey-minitool-1.4.1.zip`

平台边界：Mini Tool 1.4.1 禁止联网，因此这里的“即时 Agent”是包内角色规则与独立记忆，不等同于完整 Cowork 版的在线模型 Agent；本地记忆也不承诺跨设备或永久保存。
