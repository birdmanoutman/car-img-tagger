"""
AI模型模块 - 使用CLIP、YOLO等模型进行汽车图片智能标注
"""
import torch
import clip
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
from tqdm import tqdm
import pandas as pd

from config import MODEL_CONFIG, LABEL_CONFIG, DATA_CONFIG

class CarImageTagger:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 使用设备: {self.device}")
        
        # 初始化CLIP模型
        self.clip_model, self.clip_preprocess = self._load_clip_model()
        
        # 定义汽车相关的文本提示
        self.car_prompts = self._create_car_prompts()
        
    def _load_clip_model(self):
        """加载CLIP模型"""
        print("📥 加载CLIP模型...")
        model, preprocess = clip.load(MODEL_CONFIG["clip"]["model_name"], device=self.device)
        return model, preprocess
    
    def _create_car_prompts(self) -> Dict[str, List[str]]:
        """创建汽车相关的文本提示"""
        prompts = {
            "angles": [
                "front view of a car", "rear view of a car", "side view of a car",
                "45 degree front angle of a car", "45 degree rear angle of a car",
                "car interior", "car dashboard", "car steering wheel", "car seats",
                "car headlights", "car taillights", "car grille", "car wheels",
                "car spoiler", "car console", "car door panel", "car sunroof",
                "car trunk", "car front trunk", "car air vents", "car instrument panel",
                "car diffuser", "car C-pillar", "car charging port"
            ],
            "brands": [
                "Cadillac car", "Ferrari car", "Honda car", "MINI car", 
                "Nissan car", "Porsche car", "Smart car", "Toyota car"
            ],
            "styles": [
                "electric car", "hybrid car", "sports car", "luxury car", 
                "concept car", "vintage car", "modern car", "classic car",
                "business car", "family car", "off-road car", "racing car",
                "SUV car", "sedan car", "hatchback car", "convertible car"
            ],
            "colors": [
                "black car", "white car", "silver car", "gray car", "red car",
                "blue car", "green car", "yellow car", "orange car", "purple car",
                "brown car", "gold car", "champagne car", "pearl white car"
            ]
        }
        return prompts
    
    def classify_with_clip(self, image_path: str) -> Dict[str, float]:
        """使用CLIP对图片进行分类"""
        try:
            # 加载和预处理图片
            image = Image.open(image_path).convert('RGB')
            image_input = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            results = {}
            
            # 对每个类别进行分类
            for category, prompts in self.car_prompts.items():
                # 准备文本输入
                text_inputs = clip.tokenize(prompts).to(self.device)
                
                # 计算相似度
                with torch.no_grad():
                    image_features = self.clip_model.encode_image(image_input)
                    text_features = self.clip_model.encode_text(text_inputs)
                    
                    # 计算余弦相似度
                    similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                    
                    # 获取最高分的结果
                    values, indices = similarity[0].topk(3)
                    
                    # 保存结果
                    category_results = {}
                    for i, (value, idx) in enumerate(zip(values, indices)):
                        category_results[prompts[idx]] = float(value)
                    
                    results[category] = category_results
            
            return results
            
        except Exception as e:
            print(f"❌ CLIP分类失败: {image_path}, 错误: {e}")
            return {}
    
    def extract_angle_from_clip(self, clip_results: Dict) -> Tuple[str, float]:
        """从CLIP结果中提取角度信息"""
        if "angles" not in clip_results:
            return "Unknown", 0.0
        
        angle_scores = clip_results["angles"]
        
        # 角度映射
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
            "car charging port": "24-充电口"
        }
        
        best_angle = "Unknown"
        best_score = 0.0
        
        for prompt, score in angle_scores.items():
            if prompt in angle_mapping and score > best_score:
                best_angle = angle_mapping[prompt]
                best_score = score
        
        return best_angle, best_score
    
    def extract_brand_from_clip(self, clip_results: Dict) -> Tuple[str, float]:
        """从CLIP结果中提取品牌信息"""
        if "brands" not in clip_results:
            return "Unknown", 0.0
        
        brand_scores = clip_results["brands"]
        
        # 品牌映射
        brand_mapping = {
            "Cadillac car": "Cadillac",
            "Ferrari car": "Ferrari", 
            "Honda car": "Honda",
            "MINI car": "MINI",
            "Nissan car": "Nissan",
            "Porsche car": "Porsche",
            "Smart car": "Smart",
            "Toyota car": "Toyota"
        }
        
        best_brand = "Unknown"
        best_score = 0.0
        
        for prompt, score in brand_scores.items():
            if prompt in brand_mapping and score > best_score:
                best_brand = brand_mapping[prompt]
                best_score = score
        
        return best_brand, best_score
    
    def extract_style_from_clip(self, clip_results: Dict) -> Tuple[str, float]:
        """从CLIP结果中提取风格信息"""
        if "styles" not in clip_results:
            return "Unknown", 0.0
        
        style_scores = clip_results["styles"]
        
        # 风格映射
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
            "convertible car": "敞篷车"
        }
        
        best_style = "Unknown"
        best_score = 0.0
        
        for prompt, score in style_scores.items():
            if prompt in style_mapping and score > best_score:
                best_style = style_mapping[prompt]
                best_score = score
        
        return best_style, best_score
    
    def process_single_image(self, image_path: str) -> Dict:
        """处理单张图片，返回完整的标注信息"""
        print(f"🔍 处理图片: {Path(image_path).name}")
        
        # 使用CLIP进行分类
        clip_results = self.classify_with_clip(image_path)
        
        # 提取各种信息
        angle, angle_confidence = self.extract_angle_from_clip(clip_results)
        brand, brand_confidence = self.extract_brand_from_clip(clip_results)
        style, style_confidence = self.extract_style_from_clip(clip_results)
        
        # 获取图片基本信息
        try:
            img = Image.open(image_path)
            width, height = img.size
            file_size = Path(image_path).stat().st_size
        except:
            width, height, file_size = 0, 0, 0
        
        # 构建结果
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
            "width": width,
            "height": height,
            "file_size": file_size,
            "needs_annotation": True,
            "auto_tags": [angle, brand, style],
            "manual_tags": [],
            "confidence": (angle_confidence + brand_confidence + style_confidence) / 3,
            "clip_results": clip_results
        }
        
        return result
    
    def process_brand_images(self, brand_path: Path, max_images: int = 100) -> List[Dict]:
        """处理某个品牌的所有图片"""
        print(f"🚗 处理品牌图片: {brand_path.name}")
        
        # 获取所有图片文件
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            image_files.extend(list(brand_path.rglob(ext)))
        
        # 限制处理数量
        if max_images and len(image_files) > max_images:
            image_files = image_files[:max_images]
            print(f"  📊 限制处理数量: {max_images} 张")
        
        results = []
        for img_path in tqdm(image_files, desc=f"处理 {brand_path.name}"):
            try:
                result = self.process_single_image(str(img_path))
                results.append(result)
            except Exception as e:
                print(f"❌ 处理失败: {img_path}, 错误: {e}")
        
        return results
    
    def process_all_brands(self, max_images_per_brand: int = 50) -> pd.DataFrame:
        """处理所有品牌的图片"""
        print("🚀 开始处理所有品牌图片...")
        
        all_results = []
        brand_images_path = DATA_CONFIG["brand_images"]
        
        for brand in LABEL_CONFIG["brands"]:
            brand_path = brand_images_path / brand
            if brand_path.exists():
                brand_results = self.process_brand_images(brand_path, max_images_per_brand)
                all_results.extend(brand_results)
                print(f"  ✅ {brand}: 处理了 {len(brand_results)} 张图片")
        
        # 创建DataFrame
        df = pd.DataFrame(all_results)
        
        # 保存结果
        output_path = DATA_CONFIG["processed_data"] / "auto_annotated_dataset.csv"
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✅ 自动标注数据集已保存: {len(df)} 条记录")
        print(f"📁 保存路径: {output_path}")
        
        return df

def main():
    """主函数 - 演示AI标注功能"""
    print("🤖 启动汽车图片AI标注系统...")
    
    # 初始化标注器
    tagger = CarImageTagger()
    
    # 处理所有品牌图片（限制数量以节省时间）
    df = tagger.process_all_brands(max_images_per_brand=20)
    
    # 显示统计信息
    print("\n📊 标注结果统计:")
    print(f"  总图片数: {len(df)}")
    print(f"  品牌分布: {df['brand'].value_counts().to_dict()}")
    print(f"  角度分布: {df['angle'].value_counts().to_dict()}")
    print(f"  风格分布: {df['style'].value_counts().to_dict()}")
    print(f"  平均置信度: {df['confidence'].mean():.3f}")

if __name__ == "__main__":
    main()
