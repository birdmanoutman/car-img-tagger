# 🚗 汽车图片智能标签系统

一个基于AI的汽车图片智能标注和管理系统，支持自动识别汽车品牌、角度、风格等标签，并提供Web界面进行管理和检索。

## ✨ 功能特性

### 🎯 核心功能
- **智能标注**: 使用CLIP模型和深度学习模型自动识别汽车角度、品牌、风格
- **多维度标签**: 支持24个角度标签、8个品牌、16种设计风格
- **半自动流水线**: AI预标注 + 人工审核的混合标注模式
- **Web管理界面**: 直观的图片浏览、搜索、标签管理界面
- **数据库存储**: SQLite数据库存储图片和标签信息
- **颜色检测**: 自动检测汽车主要颜色
- **腾讯云COS支持**: 支持从腾讯云COS批量处理图片

### 📊 标签体系
- **角度标签** (24个): 前45°、正侧、后45°、正前、正后、头灯、尾灯、格栅、轮毂、内饰、方向盘、中控屏等
- **品牌标签** (8个): Cadillac、Ferrari、Honda、MINI、Nissan、Porsche、Smart、Toyota
- **风格标签** (16个): 新能源、运动、豪华、概念车、复古、现代、经典、未来感、商务、家用、越野、跑车、SUV、轿车、掀背车、敞篷车

## 🚀 快速开始

### 1. 环境准备
```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动Web应用
```bash
# 启动Web服务
uvicorn web_app:app --reload --port 8000
```

访问 http://localhost:8000 查看Web界面

### 3. 训练模型（可选）
```bash
# 训练角度分类模型
python advanced_train_model.py

# 运行品牌图片标注
python enhanced_brand_image_tagger.py
```

## 📁 项目结构

```
car-img-tagger/
├── 📊 核心模块
│   ├── web_app.py                    # FastAPI Web应用
│   ├── ai_models.py                  # AI模型封装
│   ├── database.py                   # 数据库操作
│   ├── color_detection_utils.py     # 颜色检测工具
│   └── config.py                     # 系统配置
├── 🤖 训练和推理
│   ├── advanced_train_model.py       # 高级模型训练
│   └── enhanced_brand_image_tagger.py # 品牌图片标注
├── 📁 数据目录
│   ├── 各标签素材/                   # 角度样本图片
│   ├── processed_data/               # 处理后数据
│   ├── databases/                    # SQLite数据库
│   ├── models/                       # 训练好的模型
│   └── output/                       # 输出结果
├── 🌐 Web资源
│   ├── templates/                    # HTML模板
│   └── static/                       # 静态文件
├── 📖 文档
│   ├── docs/                         # 详细文档
│   │   ├── 使用指南.md
│   │   ├── 腾讯云COS图片标注使用指南.md
│   │   └── 项目总结.md
│   ├── README.md                     # 项目说明
│   └── AGENTS.md                     # 开发指南
├── 🐳 部署配置
│   ├── docker-compose.yml            # Docker编排
│   └── requirements.txt              # 依赖列表
└── 📊 报告
    └── reports/                      # 分析报告
```

## 🔧 使用指南

### Web界面功能
- **图片浏览**: 按品牌、角度、风格筛选图片
- **搜索功能**: 多维度搜索和过滤
- **标签管理**: 查看和编辑图片标签
- **统计面板**: 显示总图片数、品牌分布、标签统计

### AI模型训练
```bash
# 训练角度分类模型
python advanced_train_model.py

# 运行品牌图片标注
python enhanced_brand_image_tagger.py
```

### 腾讯云COS集成
详细使用说明请参考 [腾讯云COS图片标注使用指南](docs/腾讯云COS图片标注使用指南.md)

## 🌐 Web界面功能

### 主要页面
- **首页**: 系统概览和统计信息
- **图片浏览**: 按品牌、角度、风格筛选图片
- **搜索功能**: 多维度搜索和过滤
- **标签管理**: 查看和编辑图片标签

### 核心功能
- 📊 **统计面板**: 显示总图片数、品牌分布、标签统计
- 🔍 **智能搜索**: 支持品牌、角度、风格、年份筛选
- 🖼️ **图片展示**: 缩略图预览，点击查看大图
- 🏷️ **标签显示**: 每张图片显示相关标签
- 📱 **响应式设计**: 支持桌面和移动设备

## 🤖 AI模型说明

### CLIP模型
- **用途**: 图像-文本匹配，识别汽车角度、品牌、风格
- **优势**: Zero-shot学习，无需训练即可识别
- **配置**: 使用ViT-B/32预训练模型

### 深度学习模型
- **角度分类**: 基于ResNet的角度分类模型
- **颜色检测**: 自动检测汽车主要颜色
- **品牌识别**: 支持8个主要汽车品牌识别

## 📊 数据统计

当前系统包含：
- **总图片数**: 880张（角度样本）
- **品牌分布**: 8个主要品牌
- **角度覆盖**: 24个不同角度
- **标签类别**: 角度、品牌、风格、颜色

## 🔄 工作流程

### 1. 数据准备阶段
- 扫描角度样本图片
- 提取文件名元数据
- 建立标签体系

### 2. AI标注阶段
- 使用CLIP模型进行预标注
- 训练深度学习模型
- 生成置信度评分

### 3. 数据管理阶段
- 存储到SQLite数据库
- 提供Web界面管理
- 支持搜索和筛选

## 🛠️ 技术栈

- **后端**: Python, FastAPI, SQLite
- **AI模型**: CLIP, PyTorch, ResNet
- **前端**: HTML, CSS, JavaScript, Bootstrap
- **数据处理**: Pandas, NumPy, PIL
- **部署**: Docker, Docker Compose

## 📈 扩展计划

### 短期目标
- [ ] 增加YOLO目标检测功能
- [ ] 支持批量图片上传
- [ ] 添加标签编辑功能
- [ ] 优化搜索性能

### 长期目标
- [ ] 支持更多汽车品牌
- [ ] 集成深度学习模型训练
- [ ] 添加图片相似度搜索
- [ ] 支持API接口

## 📖 文档

- [使用指南](docs/使用指南.md) - 详细的使用说明
- [腾讯云COS图片标注使用指南](docs/腾讯云COS图片标注使用指南.md) - COS集成说明
- [项目总结](docs/项目总结.md) - 项目完成总结
- [开发指南](AGENTS.md) - 开发规范和指南
