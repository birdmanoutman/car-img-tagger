#!/usr/bin/env python3
"""
腾讯云COS到bmnas S3存储的完整备份脚本
支持增量备份、断点续传、进度显示等功能
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import hashlib
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from qcloud_cos import CosS3Client, CosConfig
    from qcloud_cos.cos_exception import CosClientError, CosServiceError
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    from tqdm import tqdm
    import requests
except ImportError as e:
    print(f"缺少必要的依赖包: {e}")
    print("请运行: pip install cos-python-sdk-v5 boto3 tqdm requests")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class COSToS3Backup:
    """腾讯云COS到S3的备份类"""
    
    def __init__(self, config_file: str = ".env"):
        """初始化备份器"""
        self.config = self._load_config(config_file)
        self.cos_client = self._init_cos_client()
        self.s3_client = self._init_s3_client()
        self.backup_state_file = "backup_state.json"
        self.backup_state = self._load_backup_state()
        
    def _load_config(self, config_file: str) -> Dict[str, str]:
        """加载配置文件"""
        config = {}
        config_path = Path(config_file)
        
        if not config_path.exists():
            logger.error(f"配置文件 {config_file} 不存在")
            sys.exit(1)
            
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        # 验证必要的配置
        required_keys = [
            'TENCENT_SECRET_ID', 'TENCENT_SECRET_KEY', 'COS_BUCKET', 'COS_REGION',
            'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_ENDPOINT', 'S3_BUCKET', 'S3_REGION'
        ]
        
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            logger.error(f"缺少必要的配置项: {missing_keys}")
            sys.exit(1)
            
        return config
    
    def _init_cos_client(self) -> CosS3Client:
        """初始化腾讯云COS客户端"""
        try:
            config = CosConfig(
                Region=self.config['COS_REGION'],
                SecretId=self.config['TENCENT_SECRET_ID'],
                SecretKey=self.config['TENCENT_SECRET_KEY']
            )
            return CosS3Client(config)
        except Exception as e:
            logger.error(f"初始化COS客户端失败: {e}")
            sys.exit(1)
    
    def _init_s3_client(self):
        """初始化S3客户端"""
        try:
            return boto3.client(
                's3',
                endpoint_url=self.config['S3_ENDPOINT'],
                aws_access_key_id=self.config['S3_ACCESS_KEY'],
                aws_secret_access_key=self.config['S3_SECRET_KEY'],
                region_name=self.config['S3_REGION']
            )
        except Exception as e:
            logger.error(f"初始化S3客户端失败: {e}")
            sys.exit(1)
    
    def _load_backup_state(self) -> Dict:
        """加载备份状态"""
        if os.path.exists(self.backup_state_file):
            try:
                with open(self.backup_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载备份状态失败: {e}")
        return {
            'last_backup_time': None,
            'completed_files': {},
            'failed_files': {},
            'total_files': 0,
            'backed_up_files': 0
        }
    
    def _save_backup_state(self):
        """保存备份状态"""
        try:
            with open(self.backup_state_file, 'w', encoding='utf-8') as f:
                json.dump(self.backup_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存备份状态失败: {e}")
    
    def _get_cos_file_list(self, prefix: str = "") -> List[Dict]:
        """获取COS文件列表"""
        files = []
        marker = ""
        
        try:
            while True:
                response = self.cos_client.list_objects(
                    Bucket=self.config['COS_BUCKET'],
                    Prefix=prefix,
                    Marker=marker,
                    MaxKeys=1000
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'etag': obj['ETag'].strip('"')
                        })
                
                if response.get('IsTruncated', False):
                    marker = response.get('NextMarker', '')
                else:
                    break
                    
        except (CosClientError, CosServiceError) as e:
            logger.error(f"获取COS文件列表失败: {e}")
            return []
        
        logger.info(f"发现 {len(files)} 个文件需要备份")
        return files
    
    def _get_file_md5(self, cos_key: str) -> str:
        """获取COS文件的MD5值"""
        try:
            response = self.cos_client.head_object(
                Bucket=self.config['COS_BUCKET'],
                Key=cos_key
            )
            return response.get('ETag', '').strip('"')
        except Exception as e:
            logger.warning(f"获取文件 {cos_key} MD5失败: {e}")
            return ""
    
    def _download_from_cos(self, cos_key: str, local_path: str) -> bool:
        """从COS下载文件到本地"""
        try:
            response = self.cos_client.get_object(
                Bucket=self.config['COS_BUCKET'],
                Key=cos_key
            )
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                for chunk in response['Body'].iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            logger.error(f"下载文件 {cos_key} 失败: {e}")
            return False
    
    def _upload_to_s3(self, local_path: str, s3_key: str) -> bool:
        """上传文件到S3"""
        try:
            with open(local_path, 'rb') as f:
                self.s3_client.upload_fileobj(
                    f,
                    self.config['S3_BUCKET'],
                    s3_key
                )
            return True
            
        except Exception as e:
            logger.error(f"上传文件 {s3_key} 到S3失败: {e}")
            return False
    
    def _file_exists_in_s3(self, s3_key: str) -> bool:
        """检查文件是否已存在于S3"""
        try:
            self.s3_client.head_object(
                Bucket=self.config['S3_BUCKET'],
                Key=s3_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def _backup_file(self, file_info: Dict, temp_dir: str = "temp_backup") -> bool:
        """备份单个文件"""
        cos_key = file_info['key']
        s3_key = cos_key  # 保持相同的路径结构
        
        # 检查是否已经备份过
        if cos_key in self.backup_state['completed_files']:
            completed_info = self.backup_state['completed_files'][cos_key]
            if completed_info.get('etag') == file_info['etag']:
                logger.debug(f"文件 {cos_key} 已备份，跳过")
                return True
        
        # 检查S3中是否已存在
        if self._file_exists_in_s3(s3_key):
            logger.debug(f"文件 {s3_key} 在S3中已存在，跳过")
            return True
        
        local_path = os.path.join(temp_dir, cos_key)
        
        # 下载文件
        if not self._download_from_cos(cos_key, local_path):
            return False
        
        # 上传到S3
        if not self._upload_to_s3(local_path, s3_key):
            return False
        
        # 清理临时文件
        try:
            os.remove(local_path)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
        
        # 更新备份状态
        self.backup_state['completed_files'][cos_key] = {
            'etag': file_info['etag'],
            'size': file_info['size'],
            'backup_time': datetime.now().isoformat()
        }
        
        return True
    
    def backup(self, prefix: str = "", max_files: Optional[int] = None, 
               resume: bool = True) -> bool:
        """执行备份"""
        logger.info("开始备份...")
        
        # 获取文件列表
        files = self._get_cos_file_list(prefix)
        if not files:
            logger.warning("没有找到需要备份的文件")
            return True
        
        # 限制文件数量
        if max_files:
            files = files[:max_files]
        
        self.backup_state['total_files'] = len(files)
        self.backup_state['backed_up_files'] = 0
        
        # 创建临时目录
        temp_dir = "temp_backup"
        os.makedirs(temp_dir, exist_ok=True)
        
        success_count = 0
        failed_count = 0
        
        try:
            # 使用进度条显示备份进度
            with tqdm(total=len(files), desc="备份进度") as pbar:
                for file_info in files:
                    cos_key = file_info['key']
                    
                    try:
                        if self._backup_file(file_info, temp_dir):
                            success_count += 1
                            self.backup_state['backed_up_files'] += 1
                        else:
                            failed_count += 1
                            self.backup_state['failed_files'][cos_key] = {
                                'error': '备份失败',
                                'time': datetime.now().isoformat()
                            }
                    
                    except Exception as e:
                        logger.error(f"备份文件 {cos_key} 时发生异常: {e}")
                        failed_count += 1
                        self.backup_state['failed_files'][cos_key] = {
                            'error': str(e),
                            'time': datetime.now().isoformat()
                        }
                    
                    pbar.update(1)
                    pbar.set_postfix({
                        '成功': success_count,
                        '失败': failed_count
                    })
                    
                    # 定期保存状态
                    if success_count % 100 == 0:
                        self._save_backup_state()
        
        finally:
            # 清理临时目录
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
            
            # 保存最终状态
            self.backup_state['last_backup_time'] = datetime.now().isoformat()
            self._save_backup_state()
        
        logger.info(f"备份完成！成功: {success_count}, 失败: {failed_count}")
        return failed_count == 0
    
    def get_backup_status(self) -> Dict:
        """获取备份状态"""
        return self.backup_state
    
    def retry_failed_files(self) -> bool:
        """重试失败的文件"""
        failed_files = self.backup_state.get('failed_files', {})
        if not failed_files:
            logger.info("没有失败的文件需要重试")
            return True
        
        logger.info(f"重试 {len(failed_files)} 个失败的文件")
        
        # 清空失败文件列表
        self.backup_state['failed_files'] = {}
        
        # 重新获取文件信息并备份
        files = self._get_cos_file_list()
        files_to_retry = [f for f in files if f['key'] in failed_files]
        
        success_count = 0
        for file_info in files_to_retry:
            if self._backup_file(file_info):
                success_count += 1
        
        logger.info(f"重试完成，成功: {success_count}/{len(files_to_retry)}")
        return success_count == len(files_to_retry)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="腾讯云COS到S3备份工具")
    parser.add_argument("--config", default=".env", help="配置文件路径")
    parser.add_argument("--prefix", default="", help="备份文件前缀")
    parser.add_argument("--max-files", type=int, help="最大备份文件数量")
    parser.add_argument("--resume", action="store_true", help="断点续传")
    parser.add_argument("--retry", action="store_true", help="重试失败的文件")
    parser.add_argument("--status", action="store_true", help="显示备份状态")
    
    args = parser.parse_args()
    
    try:
        backup = COSToS3Backup(args.config)
        
        if args.status:
            status = backup.get_backup_status()
            print(json.dumps(status, ensure_ascii=False, indent=2))
            return
        
        if args.retry:
            success = backup.retry_failed_files()
        else:
            success = backup.backup(
                prefix=args.prefix,
                max_files=args.max_files,
                resume=args.resume
            )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("用户中断备份")
        sys.exit(1)
    except Exception as e:
        logger.error(f"备份过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

