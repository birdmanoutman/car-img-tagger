#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车身颜色检测工具
"""

import cv2
import numpy as np
from PIL import Image
import colorsys
from collections import Counter
import torch
import torchvision.transforms as transforms

class CarColorDetector:
    def __init__(self):
        """初始化颜色检测器"""
        # 定义主要颜色类别及其HSV范围
        self.color_ranges = {
            '白色': [(0, 0, 200), (180, 30, 255)],
            '黑色': [(0, 0, 0), (180, 255, 50)],
            '灰色': [(0, 0, 50), (180, 30, 200)],
            '银色': [(0, 0, 100), (180, 30, 180)],
            '红色': [(0, 100, 50), (10, 255, 255), (170, 100, 50), (180, 255, 255)],
            '蓝色': [(100, 100, 50), (130, 255, 255)],
            '绿色': [(40, 100, 50), (80, 255, 255)],
            '黄色': [(20, 100, 50), (40, 255, 255)],
            '橙色': [(10, 100, 50), (25, 255, 255)],
            '紫色': [(130, 100, 50), (160, 255, 255)],
            '棕色': [(10, 100, 20), (20, 255, 200)],
            '金色': [(15, 100, 100), (30, 255, 255)]
        }
        
        # 颜色名称映射
        self.color_names = {
            '白色': 'white',
            '黑色': 'black', 
            '灰色': 'gray',
            '银色': 'silver',
            '红色': 'red',
            '蓝色': 'blue',
            '绿色': 'green',
            '黄色': 'yellow',
            '橙色': 'orange',
            '紫色': 'purple',
            '棕色': 'brown',
            '金色': 'gold'
        }
    
    def preprocess_image(self, image_path):
        """
        预处理图片，提取车身区域
        
        Args:
            image_path: 图片路径
            
        Returns:
            numpy.ndarray: 预处理后的图片
        """
        try:
            # 读取图片
            image = cv2.imread(image_path)
            if image is None:
                return None
                
            # 转换为RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 调整图片大小以提高处理速度
            height, width = image_rgb.shape[:2]
            if width > 800:
                scale = 800 / width
                new_width = 800
                new_height = int(height * scale)
                image_rgb = cv2.resize(image_rgb, (new_width, new_height))
            
            return image_rgb
        except Exception as e:
            print(f"图片预处理失败: {e}")
            return None
    
    def extract_dominant_colors(self, image, k=5):
        """
        使用K-means聚类提取主要颜色
        
        Args:
            image: 输入图片
            k: 聚类数量
            
        Returns:
            list: 主要颜色列表
        """
        try:
            # 重塑图片数据
            data = image.reshape((-1, 3))
            data = np.float32(data)
            
            # K-means聚类
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            
            # 计算每个聚类的像素数量
            label_counts = Counter(labels.flatten())
            
            # 按像素数量排序
            dominant_colors = []
            for label, count in label_counts.most_common():
                color = centers[label].astype(int)
                percentage = count / len(labels) * 100
                dominant_colors.append({
                    'color': color,
                    'percentage': percentage
                })
            
            return dominant_colors
        except Exception as e:
            print(f"颜色提取失败: {e}")
            return []
    
    def rgb_to_hsv(self, rgb_color):
        """
        将RGB颜色转换为HSV
        
        Args:
            rgb_color: RGB颜色值 [R, G, B]
            
        Returns:
            tuple: HSV颜色值 (H, S, V)
        """
        r, g, b = rgb_color[0] / 255.0, rgb_color[1] / 255.0, rgb_color[2] / 255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return (int(h * 180), int(s * 255), int(v * 255))
    
    def classify_color(self, rgb_color):
        """
        根据RGB颜色值分类颜色
        
        Args:
            rgb_color: RGB颜色值 [R, G, B]
            
        Returns:
            str: 颜色类别名称
        """
        hsv = self.rgb_to_hsv(rgb_color)
        h, s, v = hsv
        
        # 检查每个颜色范围
        for color_name, ranges in self.color_ranges.items():
            if len(ranges) == 2:  # 单个范围
                lower, upper = ranges
                if (lower[0] <= h <= upper[0] and 
                    lower[1] <= s <= upper[1] and 
                    lower[2] <= v <= upper[2]):
                    return color_name
            elif len(ranges) == 4:  # 两个范围（如红色）
                lower1, upper1, lower2, upper2 = ranges
                if ((lower1[0] <= h <= upper1[0] and lower1[1] <= s <= upper1[1] and lower1[2] <= v <= upper1[2]) or
                    (lower2[0] <= h <= upper2[0] and lower2[1] <= s <= upper2[1] and lower2[2] <= v <= upper2[2])):
                    return color_name
        
        # 如果没有匹配到，返回最接近的颜色
        return self.get_closest_color(rgb_color)
    
    def get_closest_color(self, rgb_color):
        """
        获取最接近的颜色类别
        
        Args:
            rgb_color: RGB颜色值
            
        Returns:
            str: 最接近的颜色类别
        """
        # 定义标准颜色值
        standard_colors = {
            '白色': [255, 255, 255],
            '黑色': [0, 0, 0],
            '灰色': [128, 128, 128],
            '银色': [192, 192, 192],
            '红色': [255, 0, 0],
            '蓝色': [0, 0, 255],
            '绿色': [0, 255, 0],
            '黄色': [255, 255, 0],
            '橙色': [255, 165, 0],
            '紫色': [128, 0, 128],
            '棕色': [165, 42, 42],
            '金色': [255, 215, 0]
        }
        
        min_distance = float('inf')
        closest_color = '灰色'  # 默认颜色
        
        for color_name, standard_rgb in standard_colors.items():
            distance = np.sqrt(sum((a - b) ** 2 for a, b in zip(rgb_color, standard_rgb)))
            if distance < min_distance:
                min_distance = distance
                closest_color = color_name
        
        return closest_color
    
    def detect_car_color(self, image_path, top_k=3):
        """
        检测车身颜色
        
        Args:
            image_path: 图片路径
            top_k: 返回前k个颜色
            
        Returns:
            list: 颜色检测结果
        """
        # 预处理图片
        image = self.preprocess_image(image_path)
        if image is None:
            return []
        
        # 提取主要颜色
        dominant_colors = self.extract_dominant_colors(image, k=8)
        
        # 分类颜色并计算置信度
        color_results = []
        for color_info in dominant_colors:
            rgb_color = color_info['color']
            percentage = color_info['percentage']
            
            # 跳过背景色（通常占比较大但颜色较浅）
            if percentage < 5:  # 占比小于5%的颜色忽略
                continue
                
            color_name = self.classify_color(rgb_color)
            
            # 计算置信度（基于颜色占比和颜色纯度）
            confidence = min(percentage / 20.0, 1.0)  # 最大置信度为1.0
            
            color_results.append({
                'color': color_name,
                'color_en': self.color_names.get(color_name, color_name),
                'rgb': rgb_color.tolist(),
                'percentage': percentage,
                'confidence': confidence
            })
        
        # 按置信度排序并去重
        color_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 去重（相同颜色只保留置信度最高的）
        unique_colors = {}
        for result in color_results:
            color_name = result['color']
            if color_name not in unique_colors or result['confidence'] > unique_colors[color_name]['confidence']:
                unique_colors[color_name] = result
        
        # 返回前k个结果
        final_results = list(unique_colors.values())[:top_k]
        return final_results

def test_color_detection():
    """测试颜色检测功能"""
    detector = CarColorDetector()
    
    # 测试图片路径
    test_images = [
        "图片素材/Ford/2015 Ford Mondeo/63.jpg",
        "图片素材/Smart/Smart Smart #1_2023/2023_smart_1_1_1920x1080.jpg"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n🔍 检测图片: {image_path}")
            colors = detector.detect_car_color(image_path)
            for i, color_info in enumerate(colors):
                print(f"  {i+1}. {color_info['color']} ({color_info['color_en']}) - 置信度: {color_info['confidence']:.2f}")

if __name__ == "__main__":
    import os
    test_color_detection()
