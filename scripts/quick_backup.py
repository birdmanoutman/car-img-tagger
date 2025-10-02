#!/usr/bin/env python3
"""
快速启动COS到S3备份
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """主函数"""
    print("=== 腾讯云COS到bmnas S3备份工具 ===\n")
    
    # 检查虚拟环境
    if not os.path.exists(".venv"):
        print("❌ 虚拟环境不存在，请先创建虚拟环境")
        print("运行: python -m venv .venv")
        return False
    
    # 激活虚拟环境并运行备份
    if sys.platform == "win32":
        activate_script = ".venv\\Scripts\\activate"
        python_exe = ".venv\\Scripts\\python.exe"
    else:
        activate_script = ".venv/bin/activate"
        python_exe = ".venv/bin/python"
    
    # 检查依赖
    print("检查依赖包...")
    try:
        result = subprocess.run([
            python_exe, "-c", 
            "import cos_python_sdk_v5, boto3, tqdm, requests; print('依赖包检查通过')"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ 缺少必要的依赖包")
            print("正在安装依赖包...")
            subprocess.run([python_exe, "-m", "pip", "install", 
                           "cos-python-sdk-v5", "boto3", "tqdm", "requests"])
    except Exception as e:
        print(f"依赖检查失败: {e}")
        return False
    
    # 测试连接
    print("\n测试连接...")
    result = subprocess.run([python_exe, "scripts/test_backup_connections.py"])
    if result.returncode != 0:
        print("❌ 连接测试失败")
        return False
    
    # 开始备份
    print("\n开始备份...")
    print("提示: 使用 Ctrl+C 可以中断备份")
    
    try:
        result = subprocess.run([
            python_exe, "scripts/cos_to_s3_backup.py", "--resume"
        ])
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n用户中断备份")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 备份完成！")
    else:
        print("\n❌ 备份失败或中断")
    sys.exit(0 if success else 1)
