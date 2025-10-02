#!/usr/bin/env python3
"""
MySQL数据库备份工具 - 简化版
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from car_img_tagger.config import DATABASE_CONFIG, DATA_CONFIG
import pymysql
from pymysql.cursors import DictCursor

def get_database_info():
    """获取数据库信息"""
    config = DATABASE_CONFIG["mysql"]
    
    with pymysql.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset=config['charset'],
        cursorclass=DictCursor,
        autocommit=True
    ) as conn:
        cursor = conn.cursor()
        
        # 获取数据库版本
        cursor.execute('SELECT VERSION() as version')
        version_result = cursor.fetchone()
        
        # 获取数据库大小
        cursor.execute(f'''
            SELECT 
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
            FROM information_schema.tables 
            WHERE table_schema = '{config['database']}'
        ''')
        size_result = cursor.fetchone()
        
        # 获取表信息
        cursor.execute(f'''
            SELECT 
                table_name,
                table_rows,
                ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb
            FROM information_schema.tables 
            WHERE table_schema = '{config['database']}'
            ORDER BY size_mb DESC
        ''')
        tables_result = cursor.fetchall()
        
        return {
            'version': version_result['version'],
            'total_size_mb': size_result['size_mb'] or 0,
            'tables': [
                {
                    'name': row.get('table_name', ''),
                    'rows': row.get('table_rows', 0),
                    'size_mb': row.get('size_mb', 0)
                }
                for row in tables_result
            ]
        }

def create_backup():
    """创建数据库备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = DATA_CONFIG["output"] / "database_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_name = f"backup_{timestamp}"
    backup_path = backup_dir / backup_name
    backup_path.mkdir(exist_ok=True)
    
    print(f"创建数据库备份: {backup_name}")
    
    # 获取数据库信息
    db_info = get_database_info()
    print(f"数据库信息:")
    print(f"  版本: {db_info['version']}")
    print(f"  总大小: {db_info['total_size_mb']} MB")
    print(f"  表数量: {len(db_info['tables'])}")
    
    # 保存元数据
    metadata = {
        'backup_time': datetime.now().isoformat(),
        'database_info': db_info,
        'config': {
            'host': DATABASE_CONFIG["mysql"]['host'],
            'database': DATABASE_CONFIG["mysql"]['database']
        }
    }
    
    with open(backup_path / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
    
    # 备份每个表
    config = DATABASE_CONFIG["mysql"]
    with pymysql.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset=config['charset'],
        cursorclass=DictCursor,
        autocommit=True
    ) as conn:
        cursor = conn.cursor()
        
        for table_info in db_info['tables']:
            table_name = table_info['name']
            if not table_name:  # 跳过空表名
                continue
                
            print(f"备份表: {table_name} ({table_info['rows']} 行)")
            
            try:
                # 备份表结构
                cursor.execute(f'SHOW CREATE TABLE `{table_name}`')
                result = cursor.fetchone()
                create_sql = result[f'Create Table']
                
                structure_file = backup_path / f"{table_name}_structure.sql"
                with open(structure_file, 'w', encoding='utf-8') as f:
                    f.write(create_sql)
                
                # 备份表数据
                if table_info['rows'] > 0:
                    cursor.execute(f'SELECT * FROM `{table_name}`')
                    data = cursor.fetchall()
                    
                    data_file = backup_path / f"{table_name}_data.json"
                    with open(data_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                        
            except Exception as e:
                print(f"备份表 {table_name} 失败: {e}")
                continue
    
    print(f"备份完成: {backup_path}")
    return str(backup_path)

def list_backups():
    """列出所有备份"""
    backup_dir = DATA_CONFIG["output"] / "database_backups"
    
    if not backup_dir.exists():
        print("没有找到备份目录")
        return
    
    backups = []
    for backup_path in backup_dir.iterdir():
        if backup_path.is_dir():
            metadata_file = backup_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                backups.append({
                    'name': backup_path.name,
                    'time': metadata.get('backup_time', 'unknown'),
                    'size': sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
                })
    
    # 按时间排序
    backups.sort(key=lambda x: x['time'], reverse=True)
    
    print(f"备份列表 (共 {len(backups)} 个):")
    for backup in backups:
        size_mb = backup['size'] / 1024 / 1024
        print(f"  {backup['name']} - {size_mb:.2f} MB - {backup['time']}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MySQL数据库备份工具")
    parser.add_argument("--action", choices=['backup', 'list', 'info'], 
                       default='info', help="操作类型")
    
    args = parser.parse_args()
    
    try:
        if args.action == 'backup':
            backup_path = create_backup()
            print(f"备份完成: {backup_path}")
        
        elif args.action == 'list':
            list_backups()
        
        elif args.action == 'info':
            db_info = get_database_info()
            print(f"数据库信息:")
            print(f"  版本: {db_info['version']}")
            print(f"  总大小: {db_info['total_size_mb']} MB")
            print(f"  表数量: {len(db_info['tables'])}")
            print(f"  表详情:")
            for table in db_info['tables']:
                print(f"    {table['name']}: {table['rows']} 行, {table['size_mb']} MB")
        
        return 0
        
    except Exception as e:
        print(f"操作失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
