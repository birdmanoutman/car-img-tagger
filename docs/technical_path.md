# 目标技术路径说明

## 1. 战略概览
- 面向 A5000 GPU 的端到端流水线：SigLIP 负责多维标签，轻量蒸馏模型保障实时交互。
- “主动学习 + 人工审核”闭环：高置信度自动入库，低置信度通过 review_queue 脚本推送到 Label Studio。
- 所有训练、推理、导出流程统一由 `src/car_img_tagger/auto_tagging.py`、`scripts/build_review_queue.py`、`src/car_img_tagger/deployment.py` 协调，便于持续迭代。

## 2. 模型方案
- **主干**: `google/siglip-base-patch16-224`，以视觉-语言对齐覆盖角度、品牌、风格、内饰部件。配置见 `MODEL_CONFIG["vision_language"]`。
- **微调策略**: 采用 LoRA/Adapter（后续脚本补充）对 SigLIP 进行领域适配，重点增强内饰细粒度类别；训练日志与混淆矩阵写入 `reports/`。
- **补充模型**: EfficientNet/ConvNeXt 作为监督式对照实验，用于评估 SigLIP 改进幅度；颜色识别继续使用 HSV + K-Means 管线。

## 3. 数据与主动学习
- `src/car_img_tagger/auto_tagging.py` 为每张图片输出 `clip_results` 与 `uncertainty`（熵、边际、最大置信度），并保存为 JSON 字段，供二次分析。
- `scripts/build_review_queue.py` 读取 `processed_data/auto_annotated_dataset.csv`，根据配置阈值筛选低置信样本，生成 `processed_data/review_queue.json` 供 Label Studio 导入。
- 标注更新后，通过 `CarTagDatabase.import_from_csv` 或 API 写回数据库，确保模型、数据、审核日志三者同步。

## 4. 训练流程
1. 收集/整理困难样本（内饰、细节件）至增量数据集。
2. 使用未来的 `finetune_siglip.py`（规划中）执行 LoRA 微调，加载 SigLIP 主干，冻结大部分参数，仅训练低秩适配层。
3. 监控指标：内饰类别 F1、品牌/角度准确率、平均置信度；结果写入 `reports/` 并在 PR 中说明。
4. 将微调权重合并、导出或注册到 `models/`，并更新 `MODEL_CONFIG` 指向最新版本。

## 5. 推理与部署
- `python scripts/auto_tag.py --export-encoder` 调用 `src/car_img_tagger/deployment.py` 完成 ONNX 导出及 TensorRT FP16 编译，输出路径由 `MODEL_CONFIG["deployment"]` 定义。
- 推理阶段推荐批量大小 ≥32；对 Web/API 请求，可先使用默认 SigLIP PyTorch 模式，异步触发 TensorRT 引擎做补充评估。
- 如需落地服务，可将导出的 `.plan` 文件挂载到 FastAPI 后端或独立推理服务，通过 gRPC/REST 调用。

## 6. 观测与维护
- 指标面板（待构建）需至少跟踪：批处理耗时、GPU 占用、主动学习队列规模、审核通过率。
- 所有大文件（模型、数据集、TensorRT 引擎）需在外部对象存储托管，仓库内只保留引用与校验信息。
- 每次更新模型需同步调整 `AGENTS.md` 与 `docs/requirements.md`，确保贡献者了解最新技术栈。

## 7. 后续扩展路线
1. **LoRA 训练脚本**: 实现分布式/多 GPU 支持、自动早停与最佳权重保存。
2. **Distillation**: 以 SigLIP 预测为软标签蒸馏出轻量 CNN/Transformer 以服务低延迟场景。
3. **内饰检测专线**: 结合目标检测模型（YOLOv8/DETR）与 SigLIP 文本提示，实现区域级标注。
4. **在线评估**: 集成 nightly 任务，对最新数据集跑全量推理，输出漂移/退化报告。
5. **多模态检索**: 借助 SigLIP 向量，打通相似图检索与文本搜索能力，服务后续数据管理需求。
