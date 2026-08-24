# 互动框架 v2 校验摘要

校验时间：2026-08-24（Asia/Shanghai）  
代码版本：`148e22d`  
公网地址：<https://xindong-journey-echo.onrender.com>

## 已通过

- 8/8 人物卡具备四类玩家策略、至少 2 个原创 few-shot、七轴关系限幅、记忆策略和专属事件。
- DeepSeek 结构化输出合同可解析：台词、镜头动作、态度、意图、七轴变化、记忆、事件建议。
- 人物卡逐轴限幅通过；越界值不会直接写入 Snapshot。
- `boundary` 回合不会增加好感或吸引。
- 专属事件可从 Agent 回合进入 `event-reveal`，并改变后续匿名信与 DAY 2 回声文本。
- v1 旧存档可迁移到 v2，既有好感/信任不丢失。
- TypeScript `--noEmit`、Vite 生产构建、Python 编译通过。
- 公网已加载 v2 资源：`index-BsLUMaZP.js`、`index-DaiMBBmJ.css`；Bootstrap 返回 8 张人物投影及专属事件标签。
- 失败的 Agent 回合保持原子性：不写关系、不写记忆、不激活事件。

## 当前外部阻断

公网请求已到达 DeepSeek，但供应商返回 HTTP 402。DeepSeek 官方将 402 定义为账户余额不足；恢复余额或更换有效 Key 后，需重跑真实回合并确认：

1. `reply` 为角色原创台词；
2. `receipt.attitude` 与 `memory.relationshipDelta` 同轮存在；
3. 一至数轮内按人物判断激活 `receipt.eventActivation`；
4. `private-window` 标题切换为专属事件；
5. 刷新页面后关系、记忆、事件仍存在。

## 内容证据边界

原始人物设定 DOCX 的 REDcity 缓存路径已失效，未把缺失文档中的内容当成已验证事实。本轮沿用线上 v1 人物事实并标记 `provisional`；MBTI 与文学作品只作为行为研究层。重新提供原稿后，应逐字段比对并把通过项升级为 `approved`。
