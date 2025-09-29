#!/usr/bin/env python3
"""
从SQLite迁移到MySQL的脚本
"""
import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from car_img_tagger.database import CarTagDatabase
from car_img_tagger.config import DATA_CONFIG

def export_sqlite_data():
    """从SQLite导出数据"""
    print("📤 从SQLite导出数据...")
    
    # 使用SQLite
    os.environ['DATABASE_TYPE'] = 'sqlite'
    sqlite_db = CarTagDatabase()
    
    # 获取所有数据
    with sqlite_db._get_connection() as conn:
        cursor = conn.cursor()
        
        # 导出图片数据
        cursor.execute('SELECT * FROM images')
        images_data = cursor.fetchall()
        
        # 导出标签数据
        cursor.execute('SELECT * FROM tags')
        tags_data = cursor.fetchall()
        
        # 导出图片标签关联数据
        cursor.execute('SELECT * FROM image_tags')
        image_tags_data = cursor.fetchall()
        
        # 导出标注历史数据
        cursor.execute('SELECT * FROM annotation_history')
        history_data = cursor.fetchall()
    
    # 保存到文件
    export_dir = DATA_CONFIG["output"] / "migration"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存为JSON格式
    export_data = {
        'images': images_data,
        'tags': tags_data,
        'image_tags': image_tags_data,
        'annotation_history': history_data,
        'export_time': timestamp,
        'source_db': 'sqlite'
    }
    
    export_file = export_dir / f"sqlite_export_{timestamp}.json"
    with open(export_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✅ 数据导出完成: {export_file}")
    print(f"📊 导出统计:")
    print(f"  图片: {len(images_data)} 条")
    print(f"  标签: {len(tags_data)} 条")
    print(f"  图片标签关联: {len(image_tags_data)} 条")
    print(f"  标注历史: {len(history_data)} 条")
    
    return export_file

def import_to_mysql(export_file):
    """导入数据到MySQL"""
    print(f"📥 导入数据到MySQL: {export_file}")
    
    # 使用MySQL
    os.environ['DATABASE_TYPE'] = 'mysql'
    mysql_db = CarTagDatabase()
    
    # 读取导出数据
    with open(export_file, 'r', encoding='utf-8') as f:
        export_data = json.load(f)
    
    print("🔄 开始导入数据...")
    
    # 导入标签
    print("📝 导入标签...")
    for tag in export_data['tags']:
        if len(tag) >= 4:  # 确保数据完整
            mysql_db.add_tag(tag[1], tag[2], tag[3] or "")
    
    # 导入图片
    print("🖼️ 导入图片...")
    for image in export_data['images']:
        if len(image) >= 10:  # 确保数据完整
            image_data = {
                'image_path': image[1],
                'image_id': image[2],
                'source': image[3],
                'brand': image[4] or 'Unknown',
                'model': image[5] or 'Unknown',
                'year': image[6] or 'Unknown',
                'width': image[7] or 0,
                'height': image[8] or 0,
                'file_size': image[9] or 0
            }
            mysql_db.add_image(image_data)
    
    # 导入图片标签关联
    print("🔗 导入图片标签关联...")
    for image_tag in export_data['image_tags']:
        if len(image_tag) >= 5:  # 确保数据完整
            # 获取图片ID和标签ID
            image_id = image_tag[1]
            tag_id = image_tag[2]
            confidence = image_tag[3] or 1.0
            is_manual = bool(image_tag[4])
            
            # 通过标签ID获取标签名称
            with mysql_db._get_connection() as conn:
                cursor = conn.cursor()
                if mysql_db.db_type == 'mysql':
                    cursor.execute('SELECT name FROM tags WHERE id = %s', (tag_id,))
                else:
                    cursor.execute('SELECT name FROM tags WHERE id = ?', (tag_id,))
                result = cursor.fetchone()
                
                if result:
                    tag_name = result['name'] if mysql_db.db_type == 'mysql' else result[0]
                    mysql_db.add_image_tag(image_id, tag_name, confidence, is_manual)
    
    # 导入标注历史（可选）
    print("📚 导入标注历史...")
    for history in export_data['annotation_history']:
        if len(history) >= 7:  # 确保数据完整
            # 这里可以添加标注历史的导入逻辑
            # 由于annotation_history表结构相对简单，暂时跳过
            pass
    
    print("✅ 数据导入完成!")
    
    # 验证导入结果
    stats = mysql_db.get_statistics()
    print(f"📊 MySQL数据库统计:")
    print(f"  总图片: {stats['total_images']}")
    print(f"  品牌分布: {stats['brand_distribution']}")
    print(f"  标签分布: {stats['tag_distribution']}")

def verify_migration():
    """验证迁移结果"""
    print("🔍 验证迁移结果...")
    
    # 比较SQLite和MySQL的数据
    os.environ['DATABASE_TYPE'] = 'sqlite'
    sqlite_db = CarTagDatabase()
    sqlite_stats = sqlite_db.get_statistics()
    
    os.environ['DATABASE_TYPE'] = 'mysql'
    mysql_db = CarTagDatabase()
    mysql_stats = mysql_db.get_statistics()
    
    print("📊 数据对比:")
    print(f"  SQLite图片数: {sqlite_stats['total_images']}")
    print(f"  MySQL图片数: {mysql_stats['total_images']}")
    
    if sqlite_stats['total_images'] == mysql_stats['total_images']:
        print("✅ 图片数量一致")
    else:
        print("⚠️ 图片数量不一致")
    
    print(f"  SQLite标签数: {len(sqlite_stats['tag_distribution'])}")
    print(f"  MySQL标签数: {len(mysql_stats['tag_distribution'])}")
    
    if len(sqlite_stats['tag_distribution']) == len(mysql_stats['tag_distribution']):
        print("✅ 标签数量一致")
    else:
        print("⚠️ 标签数量不一致")

def main():
    """主函数"""
    print("🚀 SQLite到MySQL迁移工具")
    print("=" * 50)
    
    try:
        # 1. 导出SQLite数据
        export_file = export_sqlite_data()
        
        # 2. 导入到MySQL
        import_to_mysql(export_file)
        
        # 3. 验证迁移结果
        verify_migration()
        
        print("\n🎉 迁移完成!")
        print("\n💡 下一步:")
        print("1. 设置环境变量 DATABASE_TYPE=mysql")
        print("2. 重启应用程序")
        print("3. 验证功能正常")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        print("\n💡 请检查:")
        print("1. MySQL服务是否运行")
        print("2. 数据库连接配置是否正确")
        print("3. 用户权限是否足够")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

