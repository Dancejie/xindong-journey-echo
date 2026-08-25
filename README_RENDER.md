# 心动之旅：GitHub + Render 公网部署

这个仓库包含完整 React/FastAPI 版本、8 段人物动态肖像、25 段 canonical 剧情事件视频、事件驱动剧情状态机，以及服务端 DeepSeek 角色 Agent。

## 架构

- 前端：`frontend/dist/`，由 FastAPI 同源托管，运行时视频位于 `frontend/dist/media/video/`；Render 构建会显式检查该目录已经随发布提交存在。
- 剧情与记忆：PostgreSQL 保存每位访客的剧情快照、角色独立记忆、七轴关系和专属事件。
- 角色 Agent：后端调用 DeepSeek Chat Completions API；默认模型为 `deepseek-v4-flash`。DeepSeek 同轮生成角色台词、态度、七轴变化、记忆与事件建议，服务端按人物卡校验、限幅并提交。
- 公开身份：浏览器生成匿名访客 ID，不依赖小红书内网 SSO。

## Render Blueprint 部署

仓库根目录的 `render.yaml` 会创建：

1. Python Web Service：`xindong-journey-echo`
2. Render PostgreSQL：`xindong-journey-db`

在 Render Dashboard 新建 Blueprint，选择本仓库。首次同步时填写：

```text
DEEPSEEK_API_KEY=你的有效 DeepSeek API Key
```

密钥必须只填在 Render 环境变量中，不要提交到 GitHub。未配置、调用失败或输出未通过人物卡合同时，本轮明确失败且不会写入关系、记忆或事件；`/health` 的 `agentProvider` 会显示 `deepseek` 或 `unconfigured`。

若 Agent 返回 `DeepSeek 角色判断暂时没有完成（http-402）`，DeepSeek 官方含义是账户余额不足。请在 DeepSeek Billing 检查与充值，或在 Render 中替换 `DEEPSEEK_API_KEY`；不需要把 Key 写回 GitHub。

Blueprint 默认使用 Free Web Service 和 Free PostgreSQL，适合演示。Render 官方当前说明 Free PostgreSQL 会在创建 30 天后到期，长期运行应升级数据库计划。

通过 R5 人物与内容审核的剧情片首次播放为一次性有声过场；自然结束后自动进入逐字旁白。同一素材只在正文阶段作为静音循环背景，不承担剧情推进闸门。旧姜米自我介绍因没有可辨人物台词已被暂时下线，等待八位嘉宾各自的有声版本。

R5 起，事件片还必须通过人物身份路由：只有所选主角、当前搭档与资产审核记录精确一致时才播放事件母片；否则使用正确人物的动态立绘等待对应 Seedance 变体审核，绝不回退到姜米或其他嘉宾的错误镜头。人物身份牌由前端渲染姓名、职业、MBTI 和性格提示，首次出现约三秒后淡出，循环背景不会重复弹出。

## 本地运行

```bash
cd frontend
pnpm build
cd ..

export APP_AUTH_MODE=public
export DATABASE_URL='postgresql://...'
export DEEPSEEK_API_KEY='...'
python -m backend.init_db
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

打开 `http://127.0.0.1:8000/`。

## 安全边界

- GitHub 不包含 `.redInfo`、数据库口令、DeepSeek Key、Cowork 配置缓存或本地 `.env`。
- 每个匿名访客默认每 10 分钟最多触发 20 次 DeepSeek 调用，整个服务同期最多 200 次；可分别用 `AGENT_RATE_LIMIT` 与 `AGENT_GLOBAL_RATE_LIMIT` 调整。
- 玩家输入最大 240 字；Agent 只提出人物卡允许的结构化变化，服务端才拥有状态写入权。
- 浏览器访客 ID 不是账号系统；清理站点数据会得到新的体验身份。
