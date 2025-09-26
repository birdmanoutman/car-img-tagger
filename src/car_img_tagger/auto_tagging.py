"""AI模型模块：负责视觉语言打标与主动学习队列。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
from PIL import Image
from tqdm import tqdm

from .active_learning import compute_uncertainty
from .config import DATA_CONFIG, LABEL_CONFIG, MODEL_CONFIG
from .modeling.vision_language import VisionLanguageConfig, VisionLanguageModel
from .deployment import build_tensorrt_engine, export_onnx


class CarImageTagger:
    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 使用设备: {self.device}")

        self.active_learning_cfg = MODEL_CONFIG.get("active_learning", {})
        self.vision_language_cfg = VisionLanguageConfig(**MODEL_CONFIG.get("vision_language", {}))
        self.vl_model = VisionLanguageModel(self.vision_language_cfg, device=self.device)

        self.car_prompts = self._create_car_prompts()
        self.category_uncertainties: Dict[str, Dict[str, float]] = {}

    def _create_car_prompts(self) -> Dict[str, List[str]]:
        prompts = {
            "angles": [
                "front view of a car", "rear view of a car", "side view of a car",
                "45 degree front angle of a car", "45 degree rear angle of a car",
                "car interior", "car dashboard", "car steering wheel", "car seats",
                "car headlights", "car taillights", "car grille", "car wheels",
                "car spoiler", "car console", "car door panel", "car sunroof",
                "car trunk", "car front trunk", "car air vents", "car instrument panel",
                "car diffuser", "car C-pillar", "car charging port",
            ],
            "brands": [
                "Cadillac car", "Ferrari car", "Honda car", "MINI car",
                "Nissan car", "Porsche car", "Smart car", "Toyota car",
            ],
            "styles": [
                "electric car", "hybrid car", "sports car", "luxury car",
                "concept car", "vintage car", "modern car", "classic car",
                "business car", "family car", "off-road car", "racing car",
                "SUV car", "sedan car", "hatchback car", "convertible car",
            ],
            "colors": [
                "black car", "white car", "silver car", "gray car", "red car",
                "blue car", "green car", "yellow car", "orange car", "purple car",
                "brown car", "gold car", "champagne car", "pearl white car",
            ],
            "interior_parts": [
                "close up of a car gear shifter", "car gear knob detail", "luxury car gear lever",
                "close up of car steering wheel controls", "car drive mode dial", "close up of car seat stitching",
                "close up of car door trim", "car climate control vent detail",
            ],
        }
        return prompts

    def classify_with_clip(self, image_path: str) -> Dict[str, Dict[str, float]]:
        """Backward-compatible API name; now delegates to the vision-language backbone."""
        return self.classify_with_model(image_path)

    def classify_with_model(self, image_path: str) -> Dict[str, Dict[str, float]]:
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:  # pragma: no cover - IO guard
            print(f"❌ 无法打开图片: {image_path}, 错误: {exc}")
            return {}

        predictions: Dict[str, Dict[str, float]] = {}
        self.category_uncertainties = {}

        for category, prompts in self.car_prompts.items():
            probabilities = self.vl_model.predict_probabilities(image, prompts)
            probabilities_np = probabilities.detach().cpu().numpy().astype(float)
            scores = {prompt: float(probabilities_np[idx]) for idx, prompt in enumerate(prompts)}

            top_k = min(3, len(prompts))
            top_indices = np.argsort(probabilities_np)[::-1][:top_k]
            top_results = {prompts[idx]: float(probabilities_np[idx]) for idx in top_indices}
            predictions[category] = dict(sorted(top_results.items(), key=lambda item: item[1], reverse=True))

            unc = compute_uncertainty(probabilities_np)
            self.category_uncertainties[category] = {
                "entropy": unc.entropy,
                "margin": unc.margin,
                "max_confidence": unc.max_confidence,
            }

            predictions[f"{category}_full"] = scores

        return predictions

    def extract_angle_from_clip(self, clip_results: Dict) -> Tuple[str, float]:
        if "angles" not in clip_results:
            return "Unknown", 0.0

        angle_mapping = {
            "front view of a car": "4-正前",
            "rear view of a car": "5-正后",
            "side view of a car": "2-正侧",
            "45 degree front angle of a car": "1-前45",
            "45 degree rear angle of a car": "3-后45",
            "car interior": "10-内饰",
            "car dashboard": "10-内饰",
            "car steering wheel": "11-方向盘",
            "car seats": "14-座椅",
            "car headlights": "6-头灯",
            "car taillights": "7-尾灯",
            "car grille": "8-格栅",
            "car wheels": "8-轮毂",
            "car spoiler": "9-尾翼",
            "car console": "13-CONSOLE",
            "car door panel": "15-门板",
            "car sunroof": "17-天窗",
            "car trunk": "18-后备箱",
            "car front trunk": "19-前备箱",
            "car air vents": "20-出风口",
            "car instrument panel": "21-仪表屏",
            "car diffuser": "22-扩散器",
            "car C-pillar": "23-C柱",
            "car charging port": "24-充电口",
        }

        angle_scores = clip_results.get("angles_full", {})
        best_prompt = max(angle_scores, key=angle_scores.get, default=None)
        if best_prompt is None:
            return "Unknown", 0.0
        return angle_mapping.get(best_prompt, "Unknown"), float(angle_scores.get(best_prompt, 0.0))

    def extract_brand_from_clip(self, clip_results: Dict) -> Tuple[str, float]:
        if "brands" not in clip_results:
            return "Unknown", 0.0

        brand_mapping = {
            "Cadillac car": "Cadillac",
            "Ferrari car": "Ferrari",
            "Honda car": "Honda",
            "MINI car": "MINI",
            "Nissan car": "Nissan",
            "Porsche car": "Porsche",
            "Smart car": "Smart",
            "Toyota car": "Toyota",
        }
        brand_scores = clip_results.get("brands_full", {})
        best_prompt = max(brand_scores, key=brand_scores.get, default=None)
        if best_prompt is None:
            return "Unknown", 0.0
        return brand_mapping.get(best_prompt, "Unknown"), float(brand_scores.get(best_prompt, 0.0))

    def extract_style_from_clip(self, clip_results: Dict) -> Tuple[str, float]:
        if "styles" not in clip_results:
            return "Unknown", 0.0

        style_mapping = {
            "electric car": "新能源",
            "hybrid car": "新能源",
            "sports car": "运动",
            "luxury car": "豪华",
            "concept car": "概念车",
            "vintage car": "复古",
            "modern car": "现代",
            "classic car": "经典",
            "business car": "商务",
            "family car": "家用",
            "off-road car": "越野",
            "racing car": "跑车",
            "SUV car": "SUV",
            "sedan car": "轿车",
            "hatchback car": "掀背车",
            "convertible car": "敞篷车",
        }
        style_scores = clip_results.get("styles_full", {})
        best_prompt = max(style_scores, key=style_scores.get, default=None)
        if best_prompt is None:
            return "Unknown", 0.0
        return style_mapping.get(best_prompt, "Unknown"), float(style_scores.get(best_prompt, 0.0))

    def extract_interior_from_results(self, clip_results: Dict) -> Tuple[str, float]:
        if "interior_parts" not in clip_results:
            return "Unknown", 0.0
        interior_mapping = {
            "close up of a car gear shifter": "16-球头",
            "car gear knob detail": "16-球头",
            "luxury car gear lever": "16-旋钮",
            "close up of car steering wheel controls": "11-方向盘",
            "car drive mode dial": "16-旋钮",
            "close up of car seat stitching": "14-座椅",
            "close up of car door trim": "15-门板",
            "car climate control vent detail": "20-出风口",
        }
        part_scores = clip_results.get("interior_parts_full", {})
        best_prompt = max(part_scores, key=part_scores.get, default=None)
        if best_prompt is None:
            return "Unknown", 0.0
        return interior_mapping.get(best_prompt, "Unknown"), float(part_scores.get(best_prompt, 0.0))

    def process_single_image(self, image_path: str) -> Dict:
        print(f"🔍 处理图片: {Path(image_path).name}")

        clip_results = self.classify_with_model(image_path)

        angle, angle_confidence = self.extract_angle_from_clip(clip_results)
        brand, brand_confidence = self.extract_brand_from_clip(clip_results)
        style, style_confidence = self.extract_style_from_clip(clip_results)
        interior, interior_confidence = self.extract_interior_from_results(clip_results)

        try:
            img = Image.open(image_path)
            width, height = img.size
            file_size = Path(image_path).stat().st_size
        except Exception:  # pragma: no cover - IO guard
            width = height = file_size = 0

        auto_tags = [tag for tag in [angle, brand, style, interior] if tag and tag != "Unknown"]

        angle_unc = self.category_uncertainties.get("angles", {})
        review_required = self._needs_review(angle_unc)

        category_uncertainties = {
            key: value.copy() if isinstance(value, dict) else value
            for key, value in self.category_uncertainties.items()
        }
        confidence_terms = [angle_confidence, brand_confidence, style_confidence, interior_confidence]
        scores = [score for score in confidence_terms if score > 0]
        mean_confidence = float(np.mean(scores)) if scores else 0.0

        result = {
            "image_path": str(image_path),
            "image_id": f"auto_{Path(image_path).stem}",
            "source": "brand_images",
            "brand": brand,
            "brand_confidence": brand_confidence,
            "angle": angle,
            "angle_confidence": angle_confidence,
            "style": style,
            "style_confidence": style_confidence,
            "interior_part": interior,
            "interior_confidence": interior_confidence,
            "width": width,
            "height": height,
            "file_size": file_size,
            "needs_annotation": review_required,
            "auto_tags": auto_tags,
            "manual_tags": [],
            "confidence": mean_confidence,
            "clip_results": clip_results,
            "uncertainty": category_uncertainties,
        }
        return result

    def _needs_review(self, metrics: Dict[str, float]) -> bool:
        entropy_threshold = self.active_learning_cfg.get("entropy_threshold", 1.1)
        margin_threshold = self.active_learning_cfg.get("margin_threshold", 0.25)
        entropy = metrics.get("entropy", 0.0)
        margin = metrics.get("margin", 1.0)
        return entropy >= entropy_threshold or margin <= margin_threshold

    def process_brand_images(self, brand_path: Path, max_images: int = 100) -> List[Dict]:
        print(f"🚗 处理品牌图片: {brand_path.name}")

        image_files: List[Path] = []
        for ext in ["*.jpg", "*.jpeg", "*.png"]:
            image_files.extend(brand_path.rglob(ext))

        if max_images and len(image_files) > max_images:
            image_files = image_files[:max_images]
            print(f"  📊 限制处理数量: {max_images} 张")

        results = []
        for img_path in tqdm(image_files, desc=f"处理 {brand_path.name}"):
            try:
                result = self.process_single_image(str(img_path))
                results.append(result)
            except Exception as exc:  # pragma: no cover - runtime guard
                print(f"❌ 处理失败: {img_path}, 错误: {exc}")

        return results

    def process_all_brands(self, max_images_per_brand: int = 50) -> pd.DataFrame:
        print("🚀 开始处理所有品牌图片...")

        all_results = []
        brand_images_path = DATA_CONFIG["brand_images"]

        for brand in LABEL_CONFIG["brands"]:
            brand_path = brand_images_path / brand
            if brand_path.exists():
                brand_results = self.process_brand_images(brand_path, max_images_per_brand)
                all_results.extend(brand_results)
                print(f"  ✅ {brand}: 处理了 {len(brand_results)} 张图片")

        df = pd.DataFrame(all_results)
        if not df.empty:
            def _to_json_serializable(value):
                if isinstance(value, (dict, list)):
                    return json.dumps(value, ensure_ascii=False)
                return value

            for column in ["clip_results", "uncertainty", "auto_tags", "manual_tags"]:
                if column in df.columns:
                    df[column] = df[column].apply(_to_json_serializable)

        output_path = DATA_CONFIG["processed_data"] / "auto_annotated_dataset.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"✅ 自动标注数据集已保存: {len(df)} 条记录")
        print(f"📁 保存路径: {output_path}")

        return df

    def export_image_encoder(self) -> None:
        """Export the SigLIP image encoder to ONNX/TensorRT."""
        if self.vision_language_cfg.provider != "siglip":
            raise NotImplementedError("ONNX导出目前仅针对SigLIP配置")

        deployment_cfg = MODEL_CONFIG.get("deployment", {})
        onnx_path = deployment_cfg.get("onnx_path")
        engine_path = deployment_cfg.get("engine_path")
        if onnx_path is None or engine_path is None:
            raise ValueError("缺少部署路径配置")

        processor = getattr(self.vl_model, "processor", None)
        image_size = 224
        if processor is not None:
            size = getattr(processor, "image_size", getattr(processor, "size", {}))
            if isinstance(size, dict):
                image_size = size.get("height", image_size)
            elif isinstance(size, int):
                image_size = size

        dummy = torch.randn(1, 3, image_size, image_size, device=self.device, dtype=self.vl_model.model.dtype)
        vision_encoder = getattr(self.vl_model.model, "vision_model", None)
        if vision_encoder is None:
            raise AttributeError("SigLIP模型缺少vision_model子模块")

        export_onnx(vision_encoder, dummy, Path(onnx_path))
        engine = build_tensorrt_engine(Path(onnx_path), Path(engine_path))
        if engine:
            print(f"⚡ TensorRT引擎已生成: {engine}")
        else:
            print("⚠️ 未安装TensorRT，已仅导出ONNX。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Car image auto-tagging utilities")
    parser.add_argument("--max-per-brand", type=int, default=20, help="Limit number of images per brand during batch tagging")
    parser.add_argument("--export-encoder", action="store_true", help="Export SigLIP image encoder to ONNX/TensorRT and exit")
    args = parser.parse_args()

    print("🤖 启动汽车图片AI标注系统...")

    tagger = CarImageTagger()
    if args.export_encoder:
        tagger.export_image_encoder()
        return

    df = tagger.process_all_brands(max_images_per_brand=args.max_per_brand)

    print("\n📊 标注结果统计:")
    print(f"  总图片数: {len(df)}")
    if not df.empty:
        print(f"  品牌分布: {df['brand'].value_counts().to_dict()}")
        print(f"  角度分布: {df['angle'].value_counts().to_dict()}")
        print(f"  风格分布: {df['style'].value_counts().to_dict()}")
        print(f"  平均置信度: {df['confidence'].mean():.3f}")


if __name__ == "__main__":
    main()
