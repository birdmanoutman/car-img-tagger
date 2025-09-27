"""全局配置：路径、标签体系、模型参数。"""
from __future__ import annotations

import os
from pathlib import Path

# 项目根目录（src/car_img_tagger/ -> src -> project）
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 数据路径配置
DATA_CONFIG = {
    # 原始数据路径
    "brand_images": PROJECT_ROOT / "图片素材",
    "angle_samples": PROJECT_ROOT / "各标签素材",

    # 处理后数据路径
    "processed_data": PROJECT_ROOT / "processed_data",
    "annotations": PROJECT_ROOT / "processed_data" / "annotations",
    "models": PROJECT_ROOT / "models",
    "databases": PROJECT_ROOT / "databases",

    # 输出路径
    "output": PROJECT_ROOT / "output",
    "reports": PROJECT_ROOT / "reports",
}

# 标签体系配置
LABEL_CONFIG = {
    # 角度标签（24个）
    "angles": [
        "1-前45", "2-正侧", "3-后45", "4-正前", "5-正后",
        "6-头灯", "7-尾灯", "8-格栅", "8-轮毂", "9-尾翼",
        "10-内饰", "11-方向盘", "12-中控屏", "13-CONSOLE", "14-座椅",
        "15-门板", "16-旋钮", "16-球头", "17-天窗", "18-后备箱",
        "19-前备箱", "20-出风口", "21-仪表屏", "22-扩散器", "23-C柱", "24-充电口",
    ],

    # 品牌标签
    "brands": [
        "Cadillac", "Ferrari", "Honda", "MINI",
        "Nissan", "Porsche", "Smart", "Toyota",
    ],

    # 设计风格标签
    "styles": [
        "新能源", "运动", "豪华", "概念车", "复古", "现代", "经典", "未来感",
        "商务", "家用", "越野", "跑车", "SUV", "轿车", "掀背车", "敞篷车",
    ],

    # 颜色标签
    "colors": [
        "黑色", "白色", "银色", "灰色", "红色", "蓝色", "绿色", "黄色",
        "橙色", "紫色", "棕色", "金色", "香槟色", "珍珠白", "金属漆",
    ],

    # 内饰精细标签（面向专业部件）
    "interior_parts": [
        "方向盘细节", "换挡球头", "换挡杆", "中控旋钮", "空调出风口环",
        "座椅包覆", "门板饰条", "驾驶模式旋钮",
    ],
}

# 模型配置
MODEL_CONFIG = {
    # CLIP模型配置（向后兼容）
    "clip": {
        "model_name": "ViT-B/32",
        "batch_size": 32,
        "device": "cuda" if os.system("nvidia-smi") == 0 else "cpu",
    },

    # YOLO配置
    "yolo": {
        "model_size": "yolov8n.pt",  # nano版本，速度快
        "confidence_threshold": 0.5,
        "iou_threshold": 0.45,
    },

    # 分类模型配置
    "classification": {
        "input_size": (224, 224),
        "batch_size": 64,
        "learning_rate": 1e-4,
        "epochs": 50,
    },

    # 新的视觉语言主干
    "vision_language": {
        "provider": "siglip",
        "model_name": "google/siglip-base-patch16-224",
        "revision": None,
        "dtype": "fp16",
    },

    # 主动学习阈值
    "active_learning": {
        "entropy_threshold": 1.1,
        "margin_threshold": 0.25,
    },

    # 推理部署设置
    "deployment": {
        "onnx_path": DATA_CONFIG["models"] / "vision_language.onnx",
        "engine_path": DATA_CONFIG["models"] / "vision_language.plan",
    },
}

# 数据库配置
DATABASE_CONFIG = {
    "sqlite": {
        "path": DATA_CONFIG["databases"] / "car_tags.db",
    },
    "mongodb": {
        "host": "localhost",
        "port": 27017,
        "database": "car_tags",
    },
}

# API配置
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8001,
    "debug": True,
}

# 创建必要的目录
for path in DATA_CONFIG.values():
    if isinstance(path, Path):
        path.mkdir(parents=True, exist_ok=True)
