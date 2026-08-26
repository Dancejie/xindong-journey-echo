# 心动之旅 R6：480p 性别匹配四套事件视频生产与运行时记录

本目录保留 R6 从不可付费的规划 manifest、人工金额授权、受限 Seedance 执行、技术/视觉 QA，到运行时 promotion 的完整证据。canonical `manifest.r6.json` 始终保持 `doNotSubmit=true`，已经完成的任务不能借此被误重跑。

## 结论

- 角色：现有 8 个 MBTI 角色扩成每型一男一女，共 16 人（8 男、8 女）；新增 8 人的文本人物卡、身份锚点与 4 秒静音动态肖像已经接入运行时。
- 事件：25 个事件槽 × 4 套性别匹配方案，最终要求 100 个实际运行时文件，不缺片。
- 复用：姜米套 24 个已审事件原样复用；`D1-A3-cast-introductions` 因没有清楚自我介绍而不复用，必须重做。
- 新增：73 个事件 Seedance 任务 + 8 个新增人物 4 秒动态立绘 = **81 个付费任务、416 秒**。
- 本地合成：3 个 `D1-A3B-cast-first-impressions` 由已审的自我介绍与动态立绘组合，仍产出真实 MP4，但不重复付费生成。
- 运行时：81 个新生成源 + 3 个本地混剪 + 24 个既有 F-A 复用 = **108 个审核源**；对应 100 个事件轮换与 8 个新增动态肖像。
- 规格：9:16、480p、4–12 秒、事件首播原生有声、循环由运行时默认静音、无水印、并发 2、自动付费重试 0。

## 四套轮换

| 方案 | 主角性别 | 画面主角 | 状态 | 适配桶 |
|---|---|---|---|---|
| F-A-jiangmi | 女 | 姜米 ENFP | 复用 24 条 + 重做 1 条 | ENFP/ESFJ/ISFJ/ESTP |
| F-B-luyao | 女 | 陆遥 INTJ（新增） | 新制 | INTJ/INFJ/INTP/ISTP |
| M-A-chengye | 男 | 程野 ESTP | 新制 | ESTP/ISTP/ESFJ/ISFJ |
| M-B-hechuan | 男 | 贺川 INFJ（新增） | 新制 | ENFP/INFJ/INTJ/INTP |

运行时硬约束是 `selectedScheme.gender == player.selectedGender`。同一性别内用 `playerCharacterId + eventId` 的稳定哈希在两套方案间轮换，不能跨性别。R6 的边界是“主角画面性别一致”，不是 16 人全部拥有精确本人脸的 25 事件套装；后者属于下一阶段扩充。

人物身份牌不要让视频模型生成文字。运行时在可辨人物首次出现时叠加“中文名 / 职业 / MBTI”3 秒后渐隐，避免伪字，同时方便本地化与纠错。

## 成本与强制人工确认

同账户 480p、15 秒、无视频输入历史实账样本：`actual_quota=1,229,459`，`QuotaPerUnit=500,000`，`Price=CNY 0.4`，折合 CNY 0.9835672/15 秒，即 CNY 0.0655711467/秒。脱敏证据已经绑定到 `pricing-evidence-2026-08-25.json`；它可用于估算，但不是供应商当前报价保证，也不是付费授权。

- 416 秒受限批次保守估算：**CNY 51.3574464**。
- 用户书面授权：**“R6新增上限¥60”**。
- 最终结算：**CNY 41.0770200**；付费重试 **0**，未超硬上限。
- 项目历史累计已知超过 CNY 200，因此即使本批低于 200，仍必须获得独立书面确认，明确写出：**“R6 新增上限 ¥60”**。
- 普通的“生成视频”请求不等于超阈值授权；任何付费重试都需要新的金额上限。

`batch-approval.template.json` 仍是故意失败的空白模板；本轮真实授权记录在 `batch-approval.r6-20260826.json` 和 `budget-authorization-2026-08-26.md`。候选生成完成后，规划 manifest 继续永久关闭，任何付费重试都需要新的明确金额授权。

## 权利与参考图边界

- 新 8 人使用本轮生成并逐帧审核的原创身份锚图；参考输入及私有生成范围记录在 `anchor-candidates-qa-2026-08-26.md` 与 `rights-review-2026-08-26.md`。
- 供应商 `succeeded` 没有直接进入产品。81/81 候选通过技术 QA，随后经过身份/内容逐帧检查；5 条片段本地去除伪字或边框，3 条多人过场本地合成后再审核。
- 本记录只证明项目内生成、技术与运行时接入，不扩张为第三方肖像、声音或商业发行权声明；公开/商业清权仍是独立工作。

## 文件

- `character-expansion.json`：8 个新增相反性别人物的生产映射及媒体阻塞条件；人物卡正文以 `content/character_cards.v3.json` 为准。
- `event-coverage.json`：25 个事件槽、已有媒体审计和 4 套路由契约。
- `manifest.r6.json`：81 个精确任务、3 个本地合成及成本/权利状态。
- `prompts-r6/`：每个任务精确到秒的 director prompt。
- `batch-approval.schema.json` / `batch-approval.template.json`：480p 付费授权结构。
- `validate_plan.py`：纯本地完整性校验。
- `validate_batch_gate.py`：付费闸门；不提交网络任务。
- `technical-qa-r6.json` / `visual-qa-report-r6.md`：81 个候选技术结果与 108 个运行时源的紧凑视觉/音频结论。
- `visual-qa-allowlist.r6.json`：逐源路径、哈希、人物身份与音轨裁决。
- `promotion-plan-applied.r6.json`：108 项无覆盖写入运行时的确定性映射。

## 本地复现

```bash
python3 media/production/gender-rotation-r6/validate_plan.py
python3 media/production/gender-rotation-r6/qa_candidates.py
python3 -m unittest \
  media.production.gender-rotation-r6.test_prepare_promotion \
  media.production.gender-rotation-r6.test_qa_candidates
```

运行时 promotion 已完成；再次执行 `prepare_promotion.py --apply` 会因目标 ID/文件存在而 fail-closed，绝不会覆盖或重复接入。
