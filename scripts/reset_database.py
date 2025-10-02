#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置数据库表结构
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

from car_img_tagger.config import DATABASE_CONFIG
import pymysql
from pymysql.cursors import DictCursor

def reset_database():
    """重置数据库表结构"""
    print("🗑️ 重置数据库表结构...")
    
    config = DATABASE_CONFIG["mysql"]
    
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config['charset'],
            cursorclass=DictCursor,
            autocommit=True
        )
        
        cursor = conn.cursor()
        
        # 禁用外键检查
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
        
        # 删除所有表（按依赖顺序）
        tables_to_drop = [
            'annotation_history',
            'image_tags', 
            'tags',
            'images',
            'image_analysis'  # 添加这个表
        ]
        
        for table in tables_to_drop:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
                print(f"✅ 删除表: {table}")
            except Exception as e:
                print(f"⚠️ 删除表 {table} 时出错: {e}")
        
        # 重新启用外键检查
        cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
        
        conn.commit()
        conn.close()
        
        print("✅ 数据库重置完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库重置失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 数据库重置工具")
    print("=" * 50)
    
    success = reset_database()
    
    if success:
        print("\n🎉 数据库重置成功!")
        print("现在可以重新运行数据库初始化")
        return 0
    else:
        print("\n⚠️ 数据库重置失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
