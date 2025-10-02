#!/usr/bin/env python3
"""
MySQL数据库备份工具
支持完整备份、增量备份、压缩备份等功能
"""

import os
import sys
import json
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from car_img_tagger.config import DATABASE_CONFIG, DATA_CONFIG
import pymysql
from pymysql.cursors import DictCursor

class DatabaseBackup:
    """数据库备份类"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DATABASE_CONFIG["mysql"]
        self.backup_dir = DATA_CONFIG["output"] / "database_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.config['host'],
            port=self.config['port'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            charset=self.config['charset'],
            cursorclass=DictCursor,
            autocommit=True
        )
    
    def get_database_info(self) -> Dict:
        """获取数据库信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取数据库版本
            cursor.execute('SELECT VERSION() as version')
            version_result = cursor.fetchone()
            
            # 获取数据库大小
            cursor.execute(f'''
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
                FROM information_schema.tables 
                WHERE table_schema = '{self.config['database']}'
            ''')
            size_result = cursor.fetchone()
            
            # 获取表信息
            cursor.execute(f'''
                SELECT 
                    table_name,
                    table_rows,
                    ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb
                FROM information_schema.tables 
                WHERE table_schema = '{self.config['database']}'
                ORDER BY size_mb DESC
            ''')
            tables_result = cursor.fetchall()
            
            return {
                'version': version_result['version'],
                'total_size_mb': size_result['size_mb'] or 0,
                'tables': [
                    {
                        'name': row.get('table_name', row.get('TABLE_NAME', '')),
                        'rows': row.get('table_rows', row.get('TABLE_ROWS', 0)),
                        'size_mb': row.get('size_mb', row.get('SIZE_MB', 0))
                    }
                    for row in tables_result
                ]
            }
    
    def export_table_data(self, table_name: str) -> List[Dict]:
        """导出表数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM {table_name}')
            return cursor.fetchall()
    
    def export_table_structure(self, table_name: str) -> str:
        """导出表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SHOW CREATE TABLE {table_name}')
            result = cursor.fetchone()
            return result[f'Create Table']
    
    def create_full_backup(self, compress: bool = True) -> str:
        """创建完整备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"full_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        print(f"创建完整备份: {backup_name}")
        
        # 获取数据库信息
        db_info = self.get_database_info()
        print(f"数据库信息:")
        print(f"  版本: {db_info['version']}")
        print(f"  总大小: {db_info['total_size_mb']} MB")
        print(f"  表数量: {len(db_info['tables'])}")
        
        # 创建备份目录
        backup_path.mkdir(exist_ok=True)
        
        # 备份元数据
        metadata = {
            'backup_type': 'full',
            'backup_time': datetime.now().isoformat(),
            'database_info': db_info,
            'config': {
                'host': self.config['host'],
                'database': self.config['database'],
                'charset': self.config['charset']
            }
        }
        
        with open(backup_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
        
        # 备份每个表
        for table_info in db_info['tables']:
            table_name = table_info['name']
            print(f"备份表: {table_name} ({table_info['rows']} 行)")
            
            # 备份表结构
            structure = self.export_table_structure(table_name)
            structure_file = backup_path / f"{table_name}_structure.sql"
            with open(structure_file, 'w', encoding='utf-8') as f:
                f.write(structure)
            
            # 备份表数据
            if table_info['rows'] > 0:
                data = self.export_table_data(table_name)
                data_file = backup_path / f"{table_name}_data.json"
                
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        # 压缩备份
        if compress:
            print("压缩备份文件...")
            compressed_path = f"{backup_path}.tar.gz"
            
            import tarfile
            with tarfile.open(compressed_path, 'w:gz') as tar:
                tar.add(backup_path, arcname=backup_name)
            
            # 删除未压缩的目录
            shutil.rmtree(backup_path)
            backup_path = Path(compressed_path)
        
        print(f"备份完成: {backup_path}")
        return str(backup_path)
    
    def create_incremental_backup(self, last_backup_time: str) -> str:
        """创建增量备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"incremental_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        print(f"🔄 创建增量备份: {backup_name}")
        
        # 创建备份目录
        backup_path.mkdir(exist_ok=True)
        
        # 备份元数据
        metadata = {
            'backup_type': 'incremental',
            'backup_time': datetime.now().isoformat(),
            'last_backup_time': last_backup_time,
            'config': {
                'host': self.config['host'],
                'database': self.config['database'],
                'charset': self.config['charset']
            }
        }
        
        with open(backup_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
        
        # 获取自上次备份以来的变更
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute(f'''
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{self.config['database']}'
            ''')
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table['table_name']
                
                # 检查表是否有时间戳字段
                cursor.execute(f'''
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = '{self.config['database']}' 
                    AND table_name = '{table_name}' 
                    AND column_name IN ('created_at', 'updated_at', 'modified_at')
                ''')
                timestamp_columns = cursor.fetchall()
                
                if timestamp_columns:
                    # 有时间戳字段，只备份变更的数据
                    timestamp_col = timestamp_columns[0]['column_name']
                    cursor.execute(f'''
                        SELECT * FROM {table_name} 
                        WHERE {timestamp_col} > %s
                    ''', (last_backup_time,))
                    
                    changed_data = cursor.fetchall()
                    if changed_data:
                        print(f"📋 备份表 {table_name} 的变更: {len(changed_data)} 行")
                        
                        data_file = backup_path / f"{table_name}_changes.json"
                        with open(data_file, 'w', encoding='utf-8') as f:
                            json.dump(changed_data, f, ensure_ascii=False, indent=2, default=str)
                else:
                    # 没有时间戳字段，备份整个表
                    print(f"📋 备份表 {table_name} (无时间戳字段)")
                    data = self.export_table_data(table_name)
                    data_file = backup_path / f"{table_name}_data.json"
                    
                    with open(data_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 增量备份完成: {backup_path}")
        return str(backup_path)
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []
        
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir():
                metadata_file = backup_path / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    backups.append({
                        'name': backup_path.name,
                        'path': str(backup_path),
                        'type': metadata.get('backup_type', 'unknown'),
                        'time': metadata.get('backup_time', 'unknown'),
                        'size': self._get_directory_size(backup_path)
                    })
            elif backup_path.suffix == '.gz':
                # 压缩备份
                backups.append({
                    'name': backup_path.stem,
                    'path': str(backup_path),
                    'type': 'compressed',
                    'time': datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat(),
                    'size': backup_path.stat().st_size
                })
        
        # 按时间排序
        backups.sort(key=lambda x: x['time'], reverse=True)
        return backups
    
    def _get_directory_size(self, path: Path) -> int:
        """获取目录大小"""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def restore_backup(self, backup_path: str) -> bool:
        """恢复备份"""
        print(f"🔄 恢复备份: {backup_path}")
        
        backup_path = Path(backup_path)
        
        # 如果是压缩备份，先解压
        if backup_path.suffix == '.gz':
            print("📦 解压备份文件...")
            import tarfile
            extract_dir = backup_path.parent / backup_path.stem
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(extract_dir)
            backup_path = extract_dir
        
        # 读取元数据
        metadata_file = backup_path / "metadata.json"
        if not metadata_file.exists():
            print("❌ 备份元数据文件不存在")
            return False
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        print(f"📋 备份信息:")
        print(f"  类型: {metadata['backup_type']}")
        print(f"  时间: {metadata['backup_time']}")
        
        # 恢复表结构
        print("🏗️ 恢复表结构...")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 禁用外键检查
            cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
            
            # 删除现有表
            for table_info in metadata['database_info']['tables']:
                table_name = table_info['name']
                cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
                print(f"🗑️ 删除表: {table_name}")
            
            # 重新创建表
            for table_info in metadata['database_info']['tables']:
                table_name = table_info['name']
                structure_file = backup_path / f"{table_name}_structure.sql"
                
                if structure_file.exists():
                    with open(structure_file, 'r', encoding='utf-8') as f:
                        create_sql = f.read()
                    
                    cursor.execute(create_sql)
                    print(f"✅ 创建表: {table_name}")
            
            # 恢复表数据
            print("📊 恢复表数据...")
            for table_info in metadata['database_info']['tables']:
                table_name = table_info['name']
                data_file = backup_path / f"{table_name}_data.json"
                
                if data_file.exists():
                    with open(data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data:
                        # 构建插入SQL
                        columns = list(data[0].keys())
                        placeholders = ', '.join(['%s'] * len(columns))
                        insert_sql = f'''
                            INSERT INTO {table_name} ({', '.join(columns)}) 
                            VALUES ({placeholders})
                        '''
                        
                        # 批量插入数据
                        cursor.executemany(insert_sql, [
                            [row[col] for col in columns] for row in data
                        ])
                        print(f"✅ 恢复表 {table_name}: {len(data)} 行")
            
            # 重新启用外键检查
            cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
            conn.commit()
        
        print("✅ 备份恢复完成")
        return True
    
    def cleanup_old_backups(self, keep_days: int = 30):
        """清理旧备份"""
        print(f"🧹 清理 {keep_days} 天前的备份...")
        
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        deleted_count = 0
        
        for backup_path in self.backup_dir.iterdir():
            if backup_path.stat().st_mtime < cutoff_time:
                try:
                    if backup_path.is_dir():
                        shutil.rmtree(backup_path)
                    else:
                        backup_path.unlink()
                    print(f"🗑️ 删除旧备份: {backup_path.name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️ 删除备份失败 {backup_path.name}: {e}")
        
        print(f"✅ 清理完成，删除了 {deleted_count} 个旧备份")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MySQL数据库备份工具")
    parser.add_argument("--action", choices=['backup', 'restore', 'list', 'info', 'cleanup'], 
                       default='backup', help="操作类型")
    parser.add_argument("--type", choices=['full', 'incremental'], 
                       default='full', help="备份类型")
    parser.add_argument("--compress", action='store_true', help="压缩备份")
    parser.add_argument("--backup-path", help="备份文件路径（用于恢复）")
    parser.add_argument("--keep-days", type=int, default=30, help="保留备份天数")
    
    args = parser.parse_args()
    
    try:
        backup = DatabaseBackup()
        
        if args.action == 'backup':
            if args.type == 'full':
                backup_path = backup.create_full_backup(args.compress)
                print(f"🎉 完整备份完成: {backup_path}")
            else:
                # 增量备份需要指定上次备份时间
                print("⚠️ 增量备份需要指定上次备份时间")
                return 1
        
        elif args.action == 'restore':
            if not args.backup_path:
                print("❌ 恢复备份需要指定备份路径")
                return 1
            
            success = backup.restore_backup(args.backup_path)
            if success:
                print("🎉 备份恢复完成")
            else:
                print("❌ 备份恢复失败")
                return 1
        
        elif args.action == 'list':
            backups = backup.list_backups()
            print(f"📋 备份列表 (共 {len(backups)} 个):")
            for backup_info in backups:
                size_mb = backup_info['size'] / 1024 / 1024
                print(f"  {backup_info['name']} - {backup_info['type']} - {size_mb:.2f} MB - {backup_info['time']}")
        
        elif args.action == 'info':
            db_info = backup.get_database_info()
            print(f"📊 数据库信息:")
            print(f"  版本: {db_info['version']}")
            print(f"  总大小: {db_info['total_size_mb']} MB")
            print(f"  表数量: {len(db_info['tables'])}")
            print(f"  表详情:")
            for table in db_info['tables']:
                print(f"    {table['name']}: {table['rows']} 行, {table['size_mb']} MB")
        
        elif args.action == 'cleanup':
            backup.cleanup_old_backups(args.keep_days)
        
        return 0
        
    except Exception as e:
        print(f"操作失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
