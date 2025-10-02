#!/usr/bin/env python3
"""
测试COS和S3连接配置
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_cos_connection():
    """测试腾讯云COS连接"""
    try:
        from qcloud_cos import CosS3Client, CosConfig
        
        # 从环境变量或.env文件加载配置
        config = CosConfig(
            Region=os.getenv('COS_REGION', 'ap-shanghai'),
            SecretId=os.getenv('TENCENT_SECRET_ID'),
            SecretKey=os.getenv('TENCENT_SECRET_KEY')
        )
        
        client = CosS3Client(config)
        bucket = os.getenv('COS_BUCKET')
        
        # 尝试列出对象
        response = client.list_objects(
            Bucket=bucket,
            MaxKeys=1
        )
        
        print("腾讯云COS连接成功")
        print(f"   Bucket: {bucket}")
        print(f"   区域: {os.getenv('COS_REGION')}")
        return True
        
    except Exception as e:
        print(f"腾讯云COS连接失败: {e}")
        return False

def test_s3_connection():
    """测试S3连接"""
    try:
        import boto3
        
        client = boto3.client(
            's3',
            endpoint_url=os.getenv('S3_ENDPOINT'),
            aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
            region_name=os.getenv('S3_REGION')
        )
        
        bucket = os.getenv('S3_BUCKET')
        
        # 尝试列出对象
        response = client.list_objects_v2(
            Bucket=bucket,
            MaxKeys=1
        )
        
        print("S3连接成功")
        print(f"   Endpoint: {os.getenv('S3_ENDPOINT')}")
        print(f"   Bucket: {bucket}")
        print(f"   区域: {os.getenv('S3_REGION')}")
        return True
        
    except Exception as e:
        print(f"S3连接失败: {e}")
        return False

def load_env_file():
    """加载.env文件"""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("已加载.env配置文件")
    else:
        print(".env文件不存在")

def main():
    """主函数"""
    print("=== COS到S3备份工具连接测试 ===\n")
    
    # 加载配置
    load_env_file()
    
    # 测试连接
    cos_ok = test_cos_connection()
    print()
    s3_ok = test_s3_connection()
    
    print("\n=== 测试结果 ===")
    if cos_ok and s3_ok:
        print("所有连接测试通过，可以开始备份")
        return True
    else:
        print("连接测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
