#!/usr/bin/env python3
"""
综合备份管理工具
整合数据库备份和COS到S3存储备份
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from car_img_tagger.config import DATA_CONFIG

class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.backup_dir = DATA_CONFIG["output"] / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def backup_database(self) -> str:
        """备份数据库"""
        print("开始数据库备份...")
        
        try:
            result = subprocess.run([
                sys.executable, "scripts/simple_db_backup.py", "--action", "backup"
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                print("数据库备份成功")
                return "success"
            else:
                print(f"数据库备份失败: {result.stderr}")
                return "failed"
                
        except Exception as e:
            print(f"数据库备份异常: {e}")
            return "error"
    
    def backup_cos_to_s3(self) -> str:
        """备份COS到S3"""
        print("开始COS到S3备份...")
        
        try:
            result = subprocess.run([
                sys.executable, "scripts/cos_to_s3_backup.py", "--resume"
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                print("COS到S3备份成功")
                return "success"
            else:
                print(f"COS到S3备份失败: {result.stderr}")
                return "failed"
                
        except Exception as e:
            print(f"COS到S3备份异常: {e}")
            return "error"
    
    def get_backup_status(self) -> dict:
        """获取备份状态"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'database_backups': [],
            'cos_s3_backups': [],
            'overall_status': 'unknown'
        }
        
        # 检查数据库备份
        db_backup_dir = DATA_CONFIG["output"] / "database_backups"
        if db_backup_dir.exists():
            for backup_path in db_backup_dir.iterdir():
                if backup_path.is_dir():
                    metadata_file = backup_path / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        status['database_backups'].append({
                            'name': backup_path.name,
                            'time': metadata.get('backup_time', 'unknown'),
                            'size': sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file()),
                            'tables': len(metadata.get('database_info', {}).get('tables', []))
                        })
        
        # 检查COS到S3备份状态
        backup_state_file = project_root / "backup_state.json"
        if backup_state_file.exists():
            with open(backup_state_file, 'r', encoding='utf-8') as f:
                cos_backup_state = json.load(f)
            
            status['cos_s3_backups'] = {
                'last_backup_time': cos_backup_state.get('last_backup_time'),
                'total_files': cos_backup_state.get('total_files', 0),
                'backed_up_files': cos_backup_state.get('backed_up_files', 0),
                'failed_files': len(cos_backup_state.get('failed_files', {}))
            }
        
        # 确定整体状态
        if status['database_backups'] and status['cos_s3_backups']:
            status['overall_status'] = 'healthy'
        elif status['database_backups'] or status['cos_s3_backups']:
            status['overall_status'] = 'partial'
        else:
            status['overall_status'] = 'no_backup'
        
        return status
    
    def create_full_backup(self) -> bool:
        """创建完整备份"""
        print("开始完整备份...")
        print("=" * 50)
        
        # 1. 数据库备份
        db_result = self.backup_database()
        
        # 2. COS到S3备份
        cos_result = self.backup_cos_to_s3()
        
        # 3. 保存备份报告
        report = {
            'backup_time': datetime.now().isoformat(),
            'database_backup': db_result,
            'cos_s3_backup': cos_result,
            'overall_success': db_result == 'success' and cos_result == 'success'
        }
        
        report_file = self.backup_dir / f"backup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print("=" * 50)
        print("备份完成!")
        print(f"数据库备份: {db_result}")
        print(f"COS到S3备份: {cos_result}")
        print(f"整体状态: {'成功' if report['overall_success'] else '部分失败'}")
        print(f"备份报告: {report_file}")
        
        return report['overall_success']
    
    def show_status(self):
        """显示备份状态"""
        status = self.get_backup_status()
        
        print("备份状态报告")
        print("=" * 50)
        print(f"检查时间: {status['timestamp']}")
        print(f"整体状态: {status['overall_status']}")
        
        print("\n数据库备份:")
        if status['database_backups']:
            for backup in status['database_backups']:
                size_mb = backup['size'] / 1024 / 1024
                print(f"  {backup['name']} - {backup['tables']} 表 - {size_mb:.2f} MB - {backup['time']}")
        else:
            print("  无数据库备份")
        
        print("\nCOS到S3备份:")
        if status['cos_s3_backups']:
            cos_status = status['cos_s3_backups']
            print(f"  最后备份时间: {cos_status.get('last_backup_time', '未知')}")
            print(f"  总文件数: {cos_status.get('total_files', 0)}")
            print(f"  已备份文件: {cos_status.get('backed_up_files', 0)}")
            print(f"  失败文件: {cos_status.get('failed_files', 0)}")
        else:
            print("  无COS到S3备份记录")
        
        print("\n建议:")
        if status['overall_status'] == 'no_backup':
            print("  - 建议立即创建完整备份")
        elif status['overall_status'] == 'partial':
            print("  - 建议检查失败的备份并重试")
        else:
            print("  - 备份状态良好，建议定期检查")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="综合备份管理工具")
    parser.add_argument("--action", choices=['backup', 'status', 'db-only', 'cos-only'], 
                       default='status', help="操作类型")
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    try:
        if args.action == 'backup':
            success = manager.create_full_backup()
            return 0 if success else 1
        
        elif args.action == 'status':
            manager.show_status()
            return 0
        
        elif args.action == 'db-only':
            result = manager.backup_database()
            return 0 if result == 'success' else 1
        
        elif args.action == 'cos-only':
            result = manager.backup_cos_to_s3()
            return 0 if result == 'success' else 1
        
        return 0
        
    except Exception as e:
        print(f"操作失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

