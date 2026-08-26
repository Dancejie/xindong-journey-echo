# 心动之旅 R6｜新增角色身份锚点候选来源与静帧 QA

> 检查日期：2026-08-26（Asia/Shanghai）
> 状态：`candidate / pending human identity + rights + runtime approval`
> 范围：仅检查 8 张原创虚构角色静帧候选；未复制到运行时 `refs`，未提交 Seedance，未认定商业权利或真人相似性已通过。

## 生成与参考边界

- 生成方式：Codex 内置 `image_gen`；每个角色一次独立调用，共 8 次；重试次数均为 `0`。
- 完整人物与肖像提示词：[`new-cast-art-bible.md`](./new-cast-art-bible.md) §3.1—§3.8；统一视觉规范与负面约束来自 §2.1—§2.2。
- 风格参考：项目 [`cover.jpg`](../../../cover.jpg)，`1200×674 JPEG`，SHA-256 `bfe53461a53787a37a7c68487108d110f3dfa9d7e3f65bc6eb127a2a0409c8dd`。它只用于海岛黄昏、柔和胶片色彩和恋综摄影氛围，不允许复制其人物脸、身份、发型、身体、服装、姿势或精确构图。
- 工具结果未暴露可记录的随机种子、模型版本或远端任务 ID；不得补写或推断。
- 所有候选均为 `941×1672 PNG`，约为竖版 `9:16`；以下 SHA-256 已对项目候选文件重新计算。

## 候选来源清单

| 角色 | 原始生成文件 | 项目候选文件 | SHA-256 | 字节数 |
|---|---|---|---|---:|
| 陆遥 `luyao` | `/Users/dangsijie/.codex/generated_images/01a023dc-899a-7753-bc5c-91d99bc239a2/exec-ca0a85b5-d94f-49fe-96b4-addf45b897bd.png` | `/Users/dangsijie/.openclaw/workspace/cowork/xindong-journey-echo/media/production/gender-rotation-r6/.work-candidates/anchors/luyao-candidate-v1.png` | `7a4a3a4afe44e0d6d568efcdc07d21675df78e6ab67c1ca4162759e8a1d35f3f` | 1,972,835 |
| 叶澄 `yecheng` | `/Users/dangsijie/.codex/generated_images/01a03c12-bfa5-7b23-91b1-5c41bfdc7a3c/exec-5ad0b1be-0418-4ced-9b07-02f88a28eab5.png` | `/Users/dangsijie/.openclaw/workspace/cowork/xindong-journey-echo/media/production/gender-rotation-r6/.work-candidates/anchors/yecheng-candidate-v1.png` | `f6635cad9f5130ba6f4f46a812cc730f5add8e57be6c1701df0cb8da0b6f5816` | 2,223,351 |
| 唐梨 `tangli` | `/Users/dangsijie/.codex/generated_images/01a03c13-0c68-7e50-a62f-d58a3866de09/exec-17db08a9-35df-4004-a41e-535c6d806a14.png` | `/Users/dangsijie/.openclaw/workspace/cowork/xindong-journey-echo/media/production/gender-rotation-r6/.work-candidates/anchors/tangli-candidate-v1.png` | `70a314d6bc7fa643ab928365a7f9b6182feb21921d3d7dfb3353f6c1d60d4a92` | 2,053,540 |
| 温序 `wenxu` | `/Users/dangsijie/.codex/generated_images/01a03c13-597a-77d1-98f4-bed646e3a868/exec-63ba24e3-13b5-4910-804e-aa9d5dc01406.png` | `/Users/dangsijie/.openclaw/workspace/cowork/xindong-journey-echo/media/production/gender-rotation-r6/.work-candidates/anchors/wenxu-candidate-v1.png` | `4772c1687c9a1bf9e14d0b4b7e6e54e46cb1057f4c7df978487c074e6a9eded1` | 1,949,676 |
| 贺川 `hechuan` | `/Users/dangsijie/.codex/generated_images/01a023dc-899a-7753-bc5c-91d99bc239a2/exec-caa80dc4-f27e-42df-ac65-51c2521f74e4.png` | `/Users/dangsijie/.openclaw/workspace/cowork/xindong-journey-echo/media/production/gender-rotation-r6/.work-candidates/anchors/hechuan-candidate-v1.png` | `cdbe11376e33f4cbcc785039e2ce2ea7d9ccba1595bb16388c22f89857b358b4` | 1,900,074 |
| 裴然 `peiran` | `/Users/dangsijie/.codex/generated_images/01a03c12-bfa5-7b23-91b1-5c41bfdc7a3c/exec-f3836145-f6e6-4856-97eb-b6e7f4479be2.png` | `/Users/dangsijie/.openclaw/workspace/cowork/xindong-journey-echo/media/production/gender-rotation-r6/.work-candidates/anchors/peiran-candidate-v1.png` | `94c7dda6f13ae434b357a0fe03e57cf8819727a990c0764705a18c30466f08fd` | 1,817,305 |
| 黎川 `lichuan` | `/Users/dangsijie/.codex/generated_images/01a03c13-0c68-7e50-a62f-d58a3866de09/exec-96e09731-6a99-477d-8dd3-d7697cbe3443.png` | `/Users/dangsijie/.openclaw/workspace/cowork/xindong-journey-echo/media/production/gender-rotation-r6/.work-candidates/anchors/lichuan-candidate-v1.png` | `4b49ba77cc7ed765da9c59c6fc73898e53bab72c8f29b25bb201d1f7fcfc5d79` | 1,888,004 |
| 乔岚 `qiaolan` | `/Users/dangsijie/.codex/generated_images/01a03c13-597a-77d1-98f4-bed646e3a868/exec-d89ed504-e69c-4468-b789-37ec6e47eaf4.png` | `/Users/dangsijie/.openclaw/workspace/cowork/xindong-journey-echo/media/production/gender-rotation-r6/.work-candidates/anchors/qiaolan-candidate-v1.png` | `c7fa8591f372ebcbe33ee78c4ea254a9487d1d1c026a63ab6199470dca614881` | 1,954,952 |

## 本地静帧初检

共同结论：八人均呈现为明确成年人；脸型、发型、服装主色和姿态可互相区分；未见烧录文字、字幕、品牌标记或水印；单帧中未发现明显多指、融合手、严重面部畸变或移动端竖版裁切阻断。该结论只代表本地视觉初检，不能替代真人相似性筛查、权利审查、用户选角确认或视频身份连续性验收。

| 角色 | 静帧初检结果 | 需要人工确认的细节 |
|---|---|---|
| 陆遥 | 雾蓝西装、短直发、左眼下浅痣与耳骨夹清晰；冷静气质成立。 | 人脸与公众人物无相似性的结论仍需人工审查。 |
| 叶澄 | 低辫、雀斑、鼠尾草针织与双手持空白卡片清晰；手部自然。 | 耳钉更接近小花/几何形而非明确叶片，若该锚点重要需人工决定是否接受。 |
| 唐梨 | 高马尾、珊瑚色服装、运动体态和底部对讲机可辨；人物与其余角色差异明显。 | 左眉尾浅疤在常规缩略图中不够显眼；动态引用时应以整张脸与服装为主锚点。 |
| 温序 | 透明灰方框眼镜、短发、粉雾蓝与灰色针织层次清晰；水杯与双手自然。 | 视频需重点检查眼镜边缘、镜片反射和手持水杯连续性。 |
| 贺川 | 可可针织、微卷短发与沉静成年气质成立；坐姿和双手无明显异常。 | 右脸浅酒窝在当前非正笑表情下不突出；不得仅靠酒窝判断视频身份。 |
| 裴然 | 卷发、左耳银圈、杏色/薄荷配色与外向表情清晰；双手可用。 | 手中纸片更像两层空白纸而非稳定折纸形状，做动态立绘时应简化或固定道具，避免形变。 |
| 黎川 | 鼠尾草衬衫、右眉断眉、餐桌与空杯场景成立；与其他男嘉宾可区分。 | 动态需检查手指触杯和前景人物轮廓是否引发形变或身份漂移。 |
| 乔岚 | 肩长直发、海军蓝工装、银圈与黑表清晰；人物气质和配色差异明显。 | 手中多功能工具呈打开/结构复杂的视觉，和“闭合工具”提示略有偏差；动态时建议移除道具或要求始终闭合，重点检查手/工具几何。 |

## 接触表与后续门禁

- 临时接触表顺序：第一排 `陆遥 → 叶澄 → 唐梨 → 温序`；第二排 `贺川 → 裴然 → 黎川 → 乔岚`。
- 接触表仅用于本轮本地差异性检查，生成在 `/tmp/r6-anchor-contact-sheet-20260826.png`，检查后删除，不作为项目产物；删除后回收 `1,148,258` 字节。
- 进入 Seedance 前必须由用户/人工逐一确认这 8 张脸、角色锚点偏差和权利边界；只把通过的单一主版本写入运行时引用。静帧候选、API 成功或本报告均不等于运行时批准。
