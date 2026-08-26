# 心动之旅 R6｜双角色库本地骨架校验

校验日期：2026-08-25

## 已实现范围

- 角色库由 8 人扩展为 16 人：8 个现有 MBTI 均有一男一女两张独立人物卡。
- 单局仍为 8 位嘉宾。玩家选定 MBTI 与性别后，系统以稳定 seed 生成并持久化本局阵容；阵容保持 4 男 4 女，并包含同 MBTI 的另一性别嘉宾。
- 旧存档继续沿用原 8 人阵容；迁移幂等，不重抽已经持久化的阵容。
- 私聊、事件参与者、底部角色列表和心动短信候选均受本局阵容约束；主角不能和自己私聊或给自己发短信，场外角色也不能被选中。
- 事件媒体支持四套稳定轮换：`F-A-jiangmi`、`F-B-luyao`、`M-A-chengye`、`M-B-hechuan`。运行时先硬校验玩家性别，再校验轮换锚点与媒体 manifest 的 `leadGender`；拒绝跨性别主角画面。
- 精确人物事件片不存在时，只回退到玩家自己的同性动态肖像；新角色没有动态资产时回退到明确标记的静态占位图，且 `audioAvailable=false`。

## 新增角色身份事实源

| ID | 姓名 | 性别 | MBTI | 年龄 | 职业 |
|---|---|---|---|---:|---|
| `luyao` | 陆遥 | 女 | INTJ | 28 | 智能硬件产品负责人 |
| `yecheng` | 叶澄 | 女 | ISFJ | 27 | 古籍修复师 |
| `tangli` | 唐梨 | 女 | ESTP | 28 | 户外纪录片现场制片人 |
| `wenxu` | 温序 | 女 | INTP | 26 | 城市气候数据研究员 |
| `hechuan` | 贺川 | 男 | INFJ | 30 | 纪录片剪辑师 |
| `peiran` | 裴然 | 男 | ENFP | 27 | 儿童博物馆体验策展人 |
| `lichuan` | 黎川 | 男 | ESFJ | 29 | 精品酒店餐饮运营经理 |
| `qiaolan` | 乔岚 | 女 | ISTP | 28 | 舞台机械工程师 |

身份、职业和视觉意图以 `media/production/gender-rotation-r6/new-cast-art-bible.md` 为生产事实源，运行时人物卡正文以 `content/character_cards.v3.json` 为准；两者已同步到人物卡构建脚本、对白 prompt 和本地 fallback 文案。当前 art bible 不是已审视觉锚图或肖像权证明。

## 自动校验结果

- `PYTHONDONTWRITEBYTECODE=1 .local-runtime/venv/bin/python -m unittest backend.test_game_content backend.test_story_director backend.test_app_auth`：69 项通过。
- `python3 -m compileall -q backend scripts/build_character_cards_v3.py scripts/generate-day1-script-cache.py`：通过。
- `frontend/node_modules/.bin/tsc --noEmit`：通过。
- `frontend/node_modules/.bin/vite build`：通过，31 modules；`pnpm build` 仅被环境供应链策略 `ERR_PNPM_IGNORED_BUILDS(esbuild)` 阻止执行依赖脚本，不是 TypeScript 或 Vite 编译失败。
- `git diff --check`：通过。
- 旧提案职业关键词残留扫描：0 命中。
- 覆盖的关键不变量包括：16 个主角 × 多 seed 阵容稳定性、4/4 性别平衡、同 MBTI 异性同场、旧存档迁移幂等、自己/场外禁聊、自己/场外禁发短信、错性别媒体轮换拒绝、缺片安全降级。

## 本地运行验收

- 专用匿名 QA 身份以陆遥（INTJ、女性）开局：返回 8 人、4 男 4 女，并包含同 MBTI 异性嘉宾沈墨。
- 陆遥没有已审视频时，场景返回 `src=""`、`poster=/media/portraits-placeholders/luyao.svg`、`audioAvailable=false`、`identityCast=["luyao"]`，没有借用姜米或其他人物。
- 打开自己的私聊返回 HTTP 400；打开本局之外的林屿返回 HTTP 404；打开本局内沈墨返回 HTTP 200，并给出人物卡驱动的自然自我介绍和三类建议语。
- 390×844：节目介绍 → 8 个 MBTI → INTJ 一男一女两张小角色卡 → 陆遥详情完整可读。
- 390×720 与 390×620：文档宽度均为 390，无横向溢出，主按钮仍在首屏可见。
- 测试完成后已精确删除专用 QA run、用户记录及临时 JSON；没有改动已有用户存档。

## 明确边界与风险

- 本轮没有调用 Seedance、DeepSeek 或任何付费 API，也没有提交或部署。
- 新增 8 人的正式肖像、动态立绘、声音和事件视频尚未生成或审核。当前只有明确标记的静态占位图；人物卡媒体状态为 `planned / pending-original-generation / blocked`。
- 现有已审核媒体继续复用。四套轮换的代码合同已经就绪，但只有在对应 R6 manifest 资产通过预算门禁、身份一致性和运行时审核后才会启用。
- 旧版 DeepSeek Day 1 缓存只覆盖原 8 人；新增角色目前使用人物卡驱动的本地自然语言 fallback，直到生成并审核新的缓存。
- 前端两步选择、当局 8 人 Dock、自身不可私聊标记、空视频静态降级和无声音按钮均已完成并通过移动端 QA。
- 付费媒体计划本地校验为 81 个候选任务、698 秒，按历史同账户样本估算约 CNY 45.77、建议增量硬上限 CNY 60；由于项目累计已超过 CNY 200 且视觉权利/参考图仍待审，`doNotSubmit=true`，付费闸门按设计失败。没有得到写明最高金额的人工确认前不得提交。
