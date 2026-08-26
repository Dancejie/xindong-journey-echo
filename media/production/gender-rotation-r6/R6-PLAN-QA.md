# R6 媒体生产计划 QA

日期：2026-08-26
范围：R6 规划、受限付费执行、候选技术/视觉/音频 QA 与运行时 promotion。

## 校验结果

- Canonical 角色：现有 8 人 + 新增 `luyao / yecheng / tangli / wenxu / hechuan / peiran / lichuan / qiaolan`，共 16 人，8 男 8 女，8 个 MBTI 均为一男一女。
- 四套事件方案：`F-A-jiangmi / F-B-luyao / M-A-chengye / M-B-hechuan`，女 2 套、男 2 套。
- 旧错误角色 ID 在 R6 目录中 0 处残留。
- 事件覆盖：25 槽 × 4 套 = 100 个运行时输出；已有运行时文件 25，其中 24 个 `approved-runtime + qaVerdict=passed`，1 个 `D1-A3-cast-introductions` 为 held 并进入重做任务。
- 任务：73 个事件候选 + 8 个动态立绘 = 81 个 Seedance 候选任务；另有 3 个本地合成；总供应商时长 416 秒。
- 规格：480p、9:16、允许 4–15 秒（本批实际 4–12 秒）、事件首播原生有声、重试 0、并发 2。
- Prompt：81/81 存在、SHA 匹配；事件 prompt 均包含 State In、State Out、精确时间线、声音和身份安全区约束。
- 执行：81/81 provider 任务完成；一次轮询网络异常通过已有 task ID 只读对账，没有新增 POST 或付费重试。
- 技术 QA：81/81 通过；缺失、重复、意外文件和技术失败均为 0。
- 运行时源：81 个生成 + 3 个本地混剪 + 24 个既有复用 = 108；promotion 后 108/108 文件存在、哈希一致、runtime ID 唯一。
- 运行时全片解码：100 个事件轮换 + 16 个动态肖像 = 116/116 通过；运行时 manifest SHA-256 为 `7cd8befdc78bab1948e2b043a6bfd73b6ea0062f66671a80f7198c21eb10fedc`。
- 音频：100/100 首播事件源为非静音 AAC；8/8 新动态肖像无音轨。音频未做逐字转写。
- 视觉：身份硬失败 0；5 条伪字/边框片段完成本地修复，12 条非阻塞偏差保留在 `visual-qa-report-r6.md`。
- 成本：用户明确授权“R6新增上限¥60”；最终结算 CNY 41.0770200，自动付费重试 0。
- 权利边界：项目内生成与运行时技术接入已审；不据此声称第三方肖像、声音或商业发行权。

最终校验输出：

```text
R6_TECHNICAL_QA_PASS: 81/81
R6_VISUAL_ALLOWLIST_BUILT: 108/108
R6_PROMOTION_APPLIED: 108 assets, 0 missing, 0 hash mismatch
```
