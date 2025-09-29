"""
数据库模块 - 标签存储和检索系统（支持MySQL和SQLite）
"""
import os
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime
import hashlib

from .config import DATABASE_CONFIG, DATA_CONFIG

# 根据环境变量选择数据库类型
DB_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')

if DB_TYPE == 'mysql':
    import pymysql
    from pymysql.cursors import DictCursor
else:
    import sqlite3

class CarTagDatabase:
    def __init__(self, db_config: Optional[Dict] = None):
        self.db_type = DB_TYPE
        self.db_config = db_config or self._get_db_config()
        self.connection = None
        self.init_database()
    
    def _get_db_config(self) -> Dict:
        """获取数据库配置"""
        if self.db_type == 'mysql':
            return DATABASE_CONFIG["mysql"]
        else:
            return DATABASE_CONFIG["sqlite"]
    
    def _get_connection(self):
        """获取数据库连接"""
        if self.db_type == 'mysql':
            return pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset=self.db_config['charset'],
                cursorclass=DictCursor,
                autocommit=True
            )
        else:
            return sqlite3.connect(self.db_config['path'])
    
    def init_database(self):
        """初始化数据库表结构"""
        print(f"🗄️ 初始化{self.db_type.upper()}数据库...")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # MySQL和SQLite的语法差异处理
            if self.db_type == 'mysql':
                # MySQL语法
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS images (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        image_path VARCHAR(500) UNIQUE NOT NULL,
                        image_id VARCHAR(100) UNIQUE NOT NULL,
                        source VARCHAR(100) NOT NULL,
                        brand VARCHAR(100),
                        model VARCHAR(100),
                        year VARCHAR(20),
                        width INT,
                        height INT,
                        file_size BIGINT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tags (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        category VARCHAR(50) NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS image_tags (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        image_id VARCHAR(100) NOT NULL,
                        tag_id INT NOT NULL,
                        confidence FLOAT DEFAULT 1.0,
                        is_manual BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (image_id) REFERENCES images (image_id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE,
                        UNIQUE KEY unique_image_tag (image_id, tag_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS annotation_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        image_id VARCHAR(100) NOT NULL,
                        action VARCHAR(50) NOT NULL,
                        old_tags TEXT,
                        new_tags TEXT,
                        user_id VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (image_id) REFERENCES images (image_id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_brand ON images(brand)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_source ON images(source)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_tags_image_id ON image_tags(image_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id)')
                
            else:
                # SQLite语法
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
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        category TEXT NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if self.db_type == 'mysql':
                cursor.execute('''
                    INSERT INTO images 
                    (image_path, image_id, source, brand, model, year, width, height, file_size)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    source = VALUES(source),
                    brand = VALUES(brand),
                    model = VALUES(model),
                    year = VALUES(year),
                    width = VALUES(width),
                    height = VALUES(height),
                    file_size = VALUES(file_size),
                    updated_at = CURRENT_TIMESTAMP
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
            else:
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if self.db_type == 'mysql':
                cursor.execute('''
                    INSERT IGNORE INTO tags (name, category, description)
                    VALUES (%s, %s, %s)
                ''', (name, category, description))
                
                # 获取标签ID
                cursor.execute('SELECT id FROM tags WHERE name = %s', (name,))
                result = cursor.fetchone()
                return result['id'] if result else None
            else:
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取标签ID
            if self.db_type == 'mysql':
                cursor.execute('SELECT id FROM tags WHERE name = %s', (tag_name,))
                tag_result = cursor.fetchone()
                
                if not tag_result:
                    print(f"❌ 标签不存在: {tag_name}")
                    return False
                
                tag_id = tag_result['id']
                
                # 添加图片标签关联
                cursor.execute('''
                    INSERT INTO image_tags 
                    (image_id, tag_id, confidence, is_manual)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    confidence = VALUES(confidence),
                    is_manual = VALUES(is_manual)
                ''', (image_id, tag_id, confidence, is_manual))
            else:
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if self.db_type == 'mysql':
                cursor.execute('''
                    SELECT t.name, t.category, it.confidence, it.is_manual, it.created_at
                    FROM image_tags it
                    JOIN tags t ON it.tag_id = t.id
                    WHERE it.image_id = %s
                    ORDER BY it.confidence DESC
                ''', (image_id,))
                
                results = cursor.fetchall()
                return [
                    {
                        'name': row['name'],
                        'category': row['category'],
                        'confidence': row['confidence'],
                        'is_manual': bool(row['is_manual']),
                        'created_at': row['created_at']
                    }
                    for row in results
                ]
            else:
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if filters.get('brand'):
                conditions.append("i.brand = %s" if self.db_type == 'mysql' else "i.brand = ?")
                params.append(filters['brand'])
            
            if filters.get('angle'):
                conditions.append("t.name = %s" if self.db_type == 'mysql' else "t.name = ?")
                params.append(filters['angle'])
            
            if filters.get('style'):
                conditions.append("t.name = %s" if self.db_type == 'mysql' else "t.name = ?")
                params.append(filters['style'])
            
            if filters.get('year'):
                conditions.append("i.year = %s" if self.db_type == 'mysql' else "i.year = ?")
                params.append(filters['year'])
            
            # 构建SQL查询
            if conditions:
                where_clause = " AND ".join(conditions)
                if self.db_type == 'mysql':
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
                if self.db_type == 'mysql':
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
            
            if self.db_type == 'mysql':
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
    
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 总图片数
            cursor.execute('SELECT COUNT(*) FROM images')
            if self.db_type == 'mysql':
                total_images = cursor.fetchone()['COUNT(*)']
            else:
                total_images = cursor.fetchone()[0]
            
            # 按品牌统计
            cursor.execute('''
                SELECT brand, COUNT(*) as count 
                FROM images 
                GROUP BY brand 
                ORDER BY count DESC
            ''')
            brand_results = cursor.fetchall()
            if self.db_type == 'mysql':
                brand_stats = {row['brand']: row['count'] for row in brand_results}
            else:
                brand_stats = dict(brand_results)
            
            # 按标签类别统计
            cursor.execute('''
                SELECT t.category, COUNT(DISTINCT it.image_id) as count
                FROM tags t
                JOIN image_tags it ON t.id = it.tag_id
                GROUP BY t.category
                ORDER BY count DESC
            ''')
            tag_results = cursor.fetchall()
            if self.db_type == 'mysql':
                tag_stats = {row['category']: row['count'] for row in tag_results}
            else:
                tag_stats = dict(tag_results)
            
            # 按来源统计
            cursor.execute('''
                SELECT source, COUNT(*) as count 
                FROM images 
                GROUP BY source 
                ORDER BY count DESC
            ''')
            source_results = cursor.fetchall()
            if self.db_type == 'mysql':
                source_stats = {row['source']: row['count'] for row in source_results}
            else:
                source_stats = dict(source_results)
            
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
    print(f"🗄️ 初始化汽车标签数据库（{DB_TYPE.upper()}）...")
    
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