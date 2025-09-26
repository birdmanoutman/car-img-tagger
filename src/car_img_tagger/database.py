"""
数据库模块 - 标签存储和检索系统
"""
import sqlite3
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib

from .config import DATABASE_CONFIG, DATA_CONFIG

class CarTagDatabase:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DATABASE_CONFIG["sqlite"]["path"]
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        print("🗄️ 初始化数据库...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建图片表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT UNIQUE NOT NULL,
                    image_id TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    year TEXT,
                    width INTEGER,
                    height INTEGER,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建标签表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建图片标签关联表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id TEXT NOT NULL,
                    tag_id INTEGER NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    is_manual BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (image_id) REFERENCES images (image_id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id),
                    UNIQUE(image_id, tag_id)
                )
            ''')
            
            # 创建标注历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS annotation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    old_tags TEXT,
                    new_tags TEXT,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (image_id) REFERENCES images (image_id)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_brand ON images(brand)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_source ON images(source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_tags_image_id ON image_tags(image_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id)')
            
            conn.commit()
        
        print("✅ 数据库初始化完成")
    
    def add_image(self, image_data: Dict) -> str:
        """添加图片记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO images 
                (image_path, image_id, source, brand, model, year, width, height, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                image_data['image_path'],
                image_data['image_id'],
                image_data['source'],
                image_data.get('brand', 'Unknown'),
                image_data.get('model', 'Unknown'),
                image_data.get('year', 'Unknown'),
                image_data.get('width', 0),
                image_data.get('height', 0),
                image_data.get('file_size', 0)
            ))
            
            conn.commit()
            return image_data['image_id']
    
    def add_tag(self, name: str, category: str, description: str = "") -> int:
        """添加标签"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO tags (name, category, description)
                VALUES (?, ?, ?)
            ''', (name, category, description))
            
            # 获取标签ID
            cursor.execute('SELECT id FROM tags WHERE name = ?', (name,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def add_image_tag(self, image_id: str, tag_name: str, confidence: float = 1.0, 
                     is_manual: bool = False) -> bool:
        """为图片添加标签"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 获取标签ID
            cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            tag_result = cursor.fetchone()
            
            if not tag_result:
                print(f"❌ 标签不存在: {tag_name}")
                return False
            
            tag_id = tag_result[0]
            
            # 添加图片标签关联
            cursor.execute('''
                INSERT OR REPLACE INTO image_tags 
                (image_id, tag_id, confidence, is_manual)
                VALUES (?, ?, ?, ?)
            ''', (image_id, tag_id, confidence, is_manual))
            
            conn.commit()
            return True
    
    def get_image_tags(self, image_id: str) -> List[Dict]:
        """获取图片的所有标签"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT t.name, t.category, it.confidence, it.is_manual, it.created_at
                FROM image_tags it
                JOIN tags t ON it.tag_id = t.id
                WHERE it.image_id = ?
                ORDER BY it.confidence DESC
            ''', (image_id,))
            
            results = cursor.fetchall()
            return [
                {
                    'name': row[0],
                    'category': row[1],
                    'confidence': row[2],
                    'is_manual': bool(row[3]),
                    'created_at': row[4]
                }
                for row in results
            ]
    
    def search_images(self, filters: Dict) -> List[Dict]:
        """搜索图片"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if filters.get('brand'):
                conditions.append("i.brand = ?")
                params.append(filters['brand'])
            
            if filters.get('angle'):
                conditions.append("t.name = ?")
                params.append(filters['angle'])
            
            if filters.get('style'):
                conditions.append("t.name = ?")
                params.append(filters['style'])
            
            if filters.get('year'):
                conditions.append("i.year = ?")
                params.append(filters['year'])
            
            # 构建SQL查询
            if conditions:
                where_clause = " AND ".join(conditions)
                sql = f'''
                    SELECT DISTINCT i.*, 
                           GROUP_CONCAT(t.name) as tags,
                           GROUP_CONCAT(t.category) as tag_categories
                    FROM images i
                    LEFT JOIN image_tags it ON i.image_id = it.image_id
                    LEFT JOIN tags t ON it.tag_id = t.id
                    WHERE {where_clause}
                    GROUP BY i.image_id
                    ORDER BY i.created_at DESC
                '''
            else:
                sql = '''
                    SELECT i.*, 
                           GROUP_CONCAT(t.name) as tags,
                           GROUP_CONCAT(t.category) as tag_categories
                    FROM images i
                    LEFT JOIN image_tags it ON i.image_id = it.image_id
                    LEFT JOIN tags t ON it.tag_id = t.id
                    GROUP BY i.image_id
                    ORDER BY i.created_at DESC
                '''
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            # 转换为字典格式
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 总图片数
            cursor.execute('SELECT COUNT(*) FROM images')
            total_images = cursor.fetchone()[0]
            
            # 按品牌统计
            cursor.execute('''
                SELECT brand, COUNT(*) as count 
                FROM images 
                GROUP BY brand 
                ORDER BY count DESC
            ''')
            brand_stats = dict(cursor.fetchall())
            
            # 按标签类别统计
            cursor.execute('''
                SELECT t.category, COUNT(DISTINCT it.image_id) as count
                FROM tags t
                JOIN image_tags it ON t.id = it.tag_id
                GROUP BY t.category
                ORDER BY count DESC
            ''')
            tag_stats = dict(cursor.fetchall())
            
            # 按来源统计
            cursor.execute('''
                SELECT source, COUNT(*) as count 
                FROM images 
                GROUP BY source 
                ORDER BY count DESC
            ''')
            source_stats = dict(cursor.fetchall())
            
            return {
                'total_images': total_images,
                'brand_distribution': brand_stats,
                'tag_distribution': tag_stats,
                'source_distribution': source_stats
            }
    
    def import_from_csv(self, csv_path: str):
        """从CSV文件导入数据"""
        print(f"📥 从CSV导入数据: {csv_path}")
        
        df = pd.read_csv(csv_path)
        
        # 导入标签定义
        from .config import LABEL_CONFIG
        
        for category, tags in LABEL_CONFIG.items():
            if isinstance(tags, list):
                for tag in tags:
                    self.add_tag(tag, category)
        
        # 导入图片数据
        for _, row in df.iterrows():
            # 添加图片记录
            image_data = {
                'image_path': row['image_path'],
                'image_id': row['image_id'],
                'source': row['source'],
                'brand': row.get('brand', 'Unknown'),
                'model': row.get('model', 'Unknown'),
                'year': row.get('year', 'Unknown'),
                'width': row.get('width', 0),
                'height': row.get('height', 0),
                'file_size': row.get('file_size', 0)
            }
            
            self.add_image(image_data)
            
            # 添加标签
            auto_tags = eval(row.get('auto_tags', '[]')) if isinstance(row.get('auto_tags'), str) else row.get('auto_tags', [])
            manual_tags = eval(row.get('manual_tags', '[]')) if isinstance(row.get('manual_tags'), str) else row.get('manual_tags', [])
            
            for tag in auto_tags:
                self.add_image_tag(row['image_id'], tag, row.get('confidence', 1.0), False)
            
            for tag in manual_tags:
                self.add_image_tag(row['image_id'], tag, 1.0, True)
        
        print(f"✅ 导入完成: {len(df)} 条记录")

def main():
    """主函数 - 演示数据库功能"""
    print("🗄️ 初始化汽车标签数据库...")
    
    # 创建数据库实例
    db = CarTagDatabase()
    
    # 导入角度样本数据
    csv_path = DATA_CONFIG["processed_data"] / "angle_samples_dataset.csv"
    if csv_path.exists():
        db.import_from_csv(str(csv_path))
        
        # 显示统计信息
        stats = db.get_statistics()
        print("\n📊 数据库统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    print("✅ 数据库初始化完成")

if __name__ == "__main__":
    main()
