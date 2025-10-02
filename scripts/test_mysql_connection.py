#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MySQL数据库连接
"""
import os
import sys
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from car_img_tagger.database import CarTagDatabase
from car_img_tagger.config import DATABASE_CONFIG

def test_mysql_connection():
    """测试MySQL连接"""
    print("🔍 测试MySQL数据库连接...")
    
    try:
        # 创建数据库实例
        db = CarTagDatabase()
        print("✅ MySQL连接成功!")
        
        # 测试基本操作
        print("\n📊 测试数据库操作...")
        
        # 添加测试标签
        tag_id = db.add_tag("测试标签", "测试类别", "这是一个测试标签")
        print(f"✅ 添加标签成功，ID: {tag_id}")
        
        # 添加测试图片
        test_image = {
            'image_path': '/test/path/image.jpg',
            'image_id': 'test_image_001',
            'source': 'test',
            'brand': 'TestBrand',
            'model': 'TestModel',
            'year': '2024',
            'width': 1920,
            'height': 1080,
            'file_size': 1024000
        }
        
        image_id = db.add_image(test_image)
        print(f"✅ 添加图片成功，ID: {image_id}")
        
        # 添加图片标签关联
        success = db.add_image_tag(image_id, "测试标签", 0.95, False)
        print(f"✅ 添加图片标签关联: {success}")
        
        # 获取图片标签
        tags = db.get_image_tags(image_id)
        print(f"✅ 获取图片标签: {tags}")
        
        # 获取统计信息
        stats = db.get_statistics()
        print(f"✅ 数据库统计: {stats}")
        
        print("\n🎉 所有测试通过!")
        
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
        print("\n💡 请确保:")
        print("1. MySQL服务正在运行")
        print("2. 环境变量配置正确")
        print("3. 用户权限足够")
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 MySQL数据库连接测试")
    print("=" * 50)
    
    # 显示当前配置
    print(f"📋 当前数据库配置:")
    print(f"  MySQL: {DATABASE_CONFIG['mysql']}")
    
    # 测试MySQL
    mysql_ok = test_mysql_connection()
    
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    print(f"  MySQL: {'✅ 通过' if mysql_ok else '❌ 失败'}")
    
    if mysql_ok:
        print("\n🎉 MySQL数据库连接测试通过!")
        return 0
    else:
        print("\n⚠️ MySQL数据库连接测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

