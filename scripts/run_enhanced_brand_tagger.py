#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的品牌图片标注器 - 支持多标签、置信度过滤和颜色检测
"""

import os
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from tqdm import tqdm

warnings.filterwarnings('ignore')

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from car_img_tagger.color_detection import CarColorDetector

class EnhancedBrandImageTagger:
    def __init__(self, model_path='models/ensemble_car_angle_classifier.pth', 
                 confidence_threshold=0.8, top_k=3, enable_color_detection=True):
        """
        初始化增强的品牌图片标注器
        
        Args:
            model_path: 模型文件路径
            confidence_threshold: 置信度阈值，低于此值的标签将被过滤
            top_k: 返回前k个最可能的标签
            enable_color_detection: 是否启用颜色检测
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.top_k = top_k
        self.enable_color_detection = enable_color_detection
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.class_names = None
        self.transform = None
        self.color_detector = None
        
        # 加载模型和类别名称
        self.load_model()
        self.setup_transforms()
        
        # 初始化颜色检测器
        if self.enable_color_detection:
            self.color_detector = CarColorDetector()
        
    def load_model(self):
        """加载训练好的模型"""
        print(f"🔄 正在加载模型: {self.model_path}")
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
        
        # 加载模型检查点
        checkpoint = torch.load(self.model_path, map_location=self.device)
        
        # 获取类别名称
        if 'class_names' in checkpoint:
            self.class_names = checkpoint['class_names']
        else:
            # 如果没有保存类别名称，使用默认的24个类别
            self.class_names = [
                '1-前45', '2-正侧', '3-后45', '4-正前', '5-正后',
                '6-头灯', '7-尾灯', '8-格栅', '8-轮毂', '9-尾翼',
                '10-内饰', '11-方向盘', '12-中控屏', '13-CONSOLE', '14-座椅',
                '15-门板', '16-旋钮', '16-球头', '17-天窗', '18-后备箱',
                '19-前备箱', '20-出风口', '21-仪表屏', '22-扩散器', '23-C柱', '24-充电口'
            ]
        
        # 加载模型架构
        from ensemble_train_model import EnsembleModel
        self.model = EnsembleModel(num_classes=len(self.class_names))
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()
        
        print(f"✅ 模型加载完成，类别数: {len(self.class_names)}")
        print(f"📱 使用设备: {self.device}")
        
    def setup_transforms(self):
        """设置图像预处理变换"""
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
    def process_image_angles(self, image_path):
        """
        处理图片的角度分类
        
        Args:
            image_path: 图片路径
            
        Returns:
            dict: 角度预测结果
        """
        try:
            # 加载和预处理图片
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # 获取图片信息
            width, height = image.size
            file_size = os.path.getsize(image_path)
            
            # 模型预测
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                
            # 获取前k个预测结果
            top_probs, top_indices = torch.topk(probabilities, self.top_k, dim=1)
            
            # 过滤低置信度标签
            valid_predictions = []
            for i in range(self.top_k):
                prob = top_probs[0][i].item()
                class_idx = top_indices[0][i].item()
                class_name = self.class_names[class_idx]
                
                if prob >= self.confidence_threshold:
                    valid_predictions.append({
                        'class': class_name,
                        'confidence': prob
                    })
            
            # 如果没有满足阈值的预测，返回最高置信度的预测
            if not valid_predictions:
                best_prob = top_probs[0][0].item()
                best_class = self.class_names[top_indices[0][0].item()]
                valid_predictions = [{
                    'class': best_class,
                    'confidence': best_prob
                }]
            
            return {
                'predictions': valid_predictions,
                'width': width,
                'height': height,
                'file_size': file_size,
                'needs_annotation': len(valid_predictions) == 0 or valid_predictions[0]['confidence'] < self.confidence_threshold
            }
            
        except Exception as e:
            print(f"❌ 角度分类失败 {image_path}: {str(e)}")
            return None
    
    def process_image_colors(self, image_path):
        """
        处理图片的颜色检测
        
        Args:
            image_path: 图片路径
            
        Returns:
            list: 颜色检测结果
        """
        if not self.enable_color_detection or self.color_detector is None:
            return []
        
        try:
            colors = self.color_detector.detect_car_color(image_path, top_k=3)
            return colors
        except Exception as e:
            print(f"❌ 颜色检测失败 {image_path}: {str(e)}")
            return []
    
    def process_image(self, image_path):
        """
        处理单张图片，返回角度和颜色预测结果
        
        Args:
            image_path: 图片路径
            
        Returns:
            dict: 包含预测结果的字典
        """
        # 角度分类
        angle_result = self.process_image_angles(image_path)
        if angle_result is None:
            return None
        
        # 颜色检测
        color_result = self.process_image_colors(image_path)
        
        # 合并结果
        result = angle_result.copy()
        result['colors'] = color_result
        
        return result
    
    def process_brand_folder(self, brand_path):
        """
        处理单个品牌文件夹
        
        Args:
            brand_path: 品牌文件夹路径
            
        Returns:
            list: 标注结果列表
        """
        brand_name = os.path.basename(brand_path)
        results = []
        
        print(f"🔄 正在处理品牌: {brand_name}")
        
        # 遍历车型文件夹
        car_models = [d for d in os.listdir(brand_path) 
                     if os.path.isdir(os.path.join(brand_path, d))]
        
        for car_model in tqdm(car_models, desc=f"处理 {brand_name}"):
            car_model_path = os.path.join(brand_path, car_model)
            
            # 获取图片文件
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
                image_files.extend(Path(car_model_path).glob(ext))
            
            for image_file in image_files:
                image_path = str(image_file)
                image_id = f"brand_{os.path.basename(image_path).split('.')[0]}"
                
                # 处理图片
                result = self.process_image(image_path)
                if result is None:
                    continue
                
                # 构建结果记录
                record = {
                    'image_path': image_path,
                    'image_id': image_id,
                    'brand': brand_name,
                    'car_model': car_model,
                    'width': result['width'],
                    'height': result['height'],
                    'file_size': result['file_size'],
                    'source': 'brand_images',
                    'needs_annotation': result['needs_annotation'],
                    'auto_tags': [pred['class'] for pred in result['predictions']],
                    'manual_tags': [],
                    'confidence_scores': [pred['confidence'] for pred in result['predictions']],
                    'primary_angle': result['predictions'][0]['class'] if result['predictions'] else 'unknown',
                    'primary_confidence': result['predictions'][0]['confidence'] if result['predictions'] else 0.0,
                    'total_predictions': len(result['predictions']),
                    'colors': [color['color'] for color in result['colors']],
                    'color_confidences': [color['confidence'] for color in result['colors']],
                    'primary_color': result['colors'][0]['color'] if result['colors'] else 'unknown',
                    'primary_color_confidence': result['colors'][0]['confidence'] if result['colors'] else 0.0,
                    'color_details': result['colors']
                }
                
                results.append(record)
        
        return results
    
    def process_all_brands(self, brands_dir='图片素材', output_file='processed_data/enhanced_brand_images_annotated.csv'):
        """
        处理所有品牌文件夹
        
        Args:
            brands_dir: 品牌文件夹目录
            output_file: 输出CSV文件路径
        """
        print(f"🚀 开始处理所有品牌图片...")
        print(f"📁 品牌目录: {brands_dir}")
        print(f"🎯 置信度阈值: {self.confidence_threshold}")
        print(f"🔢 返回前{self.top_k}个预测")
        print(f"🎨 颜色检测: {'启用' if self.enable_color_detection else '禁用'}")
        
        all_results = []
        
        # 获取所有品牌文件夹
        brand_folders = [d for d in os.listdir(brands_dir) 
                        if os.path.isdir(os.path.join(brands_dir, d))]
        
        for brand_folder in brand_folders:
            brand_path = os.path.join(brands_dir, brand_folder)
            brand_results = self.process_brand_folder(brand_path)
            all_results.extend(brand_results)
        
        # 保存结果到CSV
        if all_results:
            df = pd.DataFrame(all_results)
            df.to_csv(output_file, index=False, encoding='utf-8')
            
            # 统计信息
            total_images = len(df)
            high_confidence = len(df[df['primary_confidence'] >= self.confidence_threshold])
            multi_label = len(df[df['total_predictions'] > 1])
            needs_annotation = len(df[df['needs_annotation'] == True])
            has_colors = len(df[df['primary_color'] != 'unknown'])
            
            print(f"\n📊 处理完成统计:")
            print(f"   📸 总图片数: {total_images}")
            print(f"   ✅ 高置信度图片: {high_confidence} ({high_confidence/total_images*100:.1f}%)")
            print(f"   🏷️  多标签图片: {multi_label} ({multi_label/total_images*100:.1f}%)")
            print(f"   ⚠️  需要人工标注: {needs_annotation} ({needs_annotation/total_images*100:.1f}%)")
            if self.enable_color_detection:
                print(f"   🎨 检测到颜色: {has_colors} ({has_colors/total_images*100:.1f}%)")
            print(f"   📁 结果已保存到: {output_file}")
            
            return df
        else:
            print("❌ 没有处理任何图片")
            return None

def main():
    """主函数"""
    # 创建增强的标注器
    tagger = EnhancedBrandImageTagger(
        model_path='models/ensemble_car_angle_classifier.pth',
        confidence_threshold=0.8,  # 80%置信度阈值
        top_k=3,  # 返回前3个预测
        enable_color_detection=True  # 启用颜色检测
    )
    
    # 处理所有品牌
    results_df = tagger.process_all_brands()
    
    if results_df is not None:
        print("\n🎉 增强的品牌图片标注完成！")
        print("💡 现在每张图片包含:")
        print("   - 多个角度标签（置信度过滤）")
        print("   - 车身颜色检测")
        print("   - 详细的置信度信息")

if __name__ == "__main__":
    main()
