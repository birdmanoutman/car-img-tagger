# 腾讯云COS到bmnas S3备份工具使用指南

## 功能特性

- ✅ **完整备份**: 支持从腾讯云COS完整备份到bmnas S3存储
- ✅ **增量备份**: 自动检测文件变化，只备份新增或修改的文件
- ✅ **断点续传**: 支持中断后继续备份，避免重复传输
- ✅ **进度显示**: 实时显示备份进度和统计信息
- ✅ **错误处理**: 记录失败文件，支持重试机制
- ✅ **状态保存**: 保存备份状态，便于监控和管理

## 安装依赖

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 安装必要的依赖包
pip install cos-python-sdk-v5 boto3 tqdm requests
```

## 配置说明

确保 `.env` 文件包含以下配置：

```env
# 腾讯云COS配置
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key
COS_BUCKET=your_cos_bucket
COS_REGION=ap-shanghai

# bmnas S3配置
S3_ENDPOINT=https://minio.birdmanoutman.com
S3_BUCKET=tencent-cos-backup
S3_REGION=ap-shanghai
S3_ACCESS_KEY=birdmanoutman
S3_SECRET_KEY=your_secret_key
```

## 使用方法

### 1. 完整备份

```bash
# 备份所有文件
python scripts/cos_to_s3_backup.py

# 备份指定前缀的文件
python scripts/cos_to_s3_backup.py --prefix "images/"

# 限制备份文件数量（测试用）
python scripts/cos_to_s3_backup.py --max-files 100
```

### 2. 断点续传

```bash
# 启用断点续传
python scripts/cos_to_s3_backup.py --resume
```

### 3. 重试失败文件

```bash
# 重试之前备份失败的文件
python scripts/cos_to_s3_backup.py --retry
```

### 4. 查看备份状态

```bash
# 显示当前备份状态
python scripts/cos_to_s3_backup.py --status
```

## 输出文件

- `backup.log`: 详细的备份日志
- `backup_state.json`: 备份状态文件，包含：
  - 已完成的文件列表
  - 失败的文件列表
  - 备份统计信息

## 注意事项

1. **网络稳定性**: 确保网络连接稳定，大文件传输可能需要较长时间
2. **存储空间**: 确保S3存储有足够空间
3. **权限配置**: 确保COS和S3的访问权限正确配置
4. **临时文件**: 脚本会创建临时目录存储下载的文件，确保有足够的本地磁盘空间

## 故障排除

### 常见错误

1. **认证失败**: 检查Secret ID和Secret Key是否正确
2. **网络超时**: 检查网络连接，可以尝试重试
3. **权限不足**: 检查COS和S3的访问权限
4. **存储空间不足**: 检查S3存储空间是否足够

### 日志分析

查看 `backup.log` 文件获取详细的错误信息：

```bash
# 查看最近的错误
tail -f backup.log | grep ERROR

# 查看备份进度
tail -f backup.log | grep "备份进度"
```

## 性能优化建议

1. **分批处理**: 对于大量文件，建议分批备份
2. **网络优化**: 在网络条件好的时候进行备份
3. **监控资源**: 监控CPU和内存使用情况
4. **定期清理**: 定期清理临时文件和日志

## 示例用法

```bash
# 首次完整备份
python scripts/cos_to_s3_backup.py --resume

# 查看备份状态
python scripts/cos_to_s3_backup.py --status

# 重试失败的文件
python scripts/cos_to_s3_backup.py --retry

# 备份特定目录
python scripts/cos_to_s3_backup.py --prefix "car_images/" --resume
```

