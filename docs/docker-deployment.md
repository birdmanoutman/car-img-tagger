# Docker 部署指南

本文档介绍如何使用Docker部署汽车图片智能标签系统。

## 快速开始

### 1. 简化部署（推荐用于开发和小规模部署）

```bash
# 使用简化版Docker Compose启动服务
docker-compose -f docker-compose.simple.yml up -d

# 查看服务状态
docker-compose -f docker-compose.simple.yml ps

# 查看日志
docker-compose -f docker-compose.simple.yml logs -f car-img-tagger
```

访问地址：http://localhost:8001

### 2. 完整部署（推荐用于生产环境）

```bash
# 使用完整版Docker Compose启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看特定服务日志
docker-compose logs -f car-img-tagger
```

服务访问地址：
- 主应用：http://localhost:8001
- Prometheus监控：http://localhost:9090
- Grafana仪表板：http://localhost:3000 (admin/admin)
- PostgreSQL：localhost:5432
- Redis：localhost:6379

## Docker镜像说明

### 1. Dockerfile（完整版）
- 包含所有AI模型依赖
- 支持GPU加速
- 适用于生产环境

### 2. Dockerfile.simple（简化版）
- 仅包含Web服务依赖
- 轻量级部署
- 适用于开发和测试

### 3. Dockerfile.minimal（最小版）
- 最小依赖集
- 快速启动
- 适用于演示

## 构建自定义镜像

```bash
# 构建完整版镜像
docker build -t car-img-tagger:latest .

# 构建简化版镜像
docker build -f Dockerfile.simple -t car-img-tagger:simple .

# 构建最小版镜像
docker build -f Dockerfile.minimal -t car-img-tagger:minimal .
```

## 数据持久化

### 数据目录挂载
- `./databases` - 数据库文件
- `./processed_data` - 处理后的数据
- `./models` - 模型文件
- `./output` - 输出文件
- `./reports` - 报告文件
- `./图片素材` - 原始图片素材
- `./各标签素材` - 标签分类素材

### 数据库持久化
- PostgreSQL数据存储在Docker volume中
- Redis数据存储在Docker volume中
- 监控数据存储在Docker volume中

## 环境变量配置

### 主要环境变量
- `PYTHONPATH=/app/src` - Python路径
- `PYTHONUNBUFFERED=1` - Python输出缓冲
- `REDIS_URL=redis://redis:6379` - Redis连接URL
- `DATABASE_URL=postgresql://postgres:password@postgres:5432/car_tags` - 数据库连接URL

### GPU支持
- `GPU_ENABLED=true` - 启用GPU支持
- `BATCH_SIZE=8` - 批处理大小
- `MAX_WORKERS=4` - 最大工作进程数

## 健康检查

所有服务都配置了健康检查：
- 主应用：检查 `/health` 端点
- PostgreSQL：检查数据库连接
- Redis：检查Redis连接

## 监控和日志

### 监控服务
- **Prometheus**：指标收集和存储
- **Grafana**：可视化仪表板

### 日志管理
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs car-img-tagger

# 实时跟踪日志
docker-compose logs -f car-img-tagger
```

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :8001
   
   # 修改端口映射
   # 在docker-compose.yml中修改ports配置
   ```

2. **权限问题**
   ```bash
   # 检查文件权限
   ls -la databases/ processed_data/ models/
   
   # 修复权限
   sudo chown -R $USER:$USER databases/ processed_data/ models/
   ```

3. **内存不足**
   ```bash
   # 检查Docker资源使用
   docker stats
   
   # 清理未使用的镜像和容器
   docker system prune -a
   ```

4. **GPU支持问题**
   ```bash
   # 检查NVIDIA Docker支持
   docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
   
   # 确保安装了nvidia-docker2
   sudo apt-get install nvidia-docker2
   ```

### 调试模式

```bash
# 进入容器调试
docker-compose exec car-img-tagger bash

# 查看容器内部文件
docker-compose exec car-img-tagger ls -la /app

# 检查Python环境
docker-compose exec car-img-tagger python -c "import sys; print(sys.path)"
```

## 生产环境建议

1. **安全配置**
   - 修改默认密码
   - 配置SSL证书
   - 设置防火墙规则

2. **性能优化**
   - 调整资源限制
   - 配置负载均衡
   - 启用缓存策略

3. **备份策略**
   - 定期备份数据库
   - 备份模型文件
   - 配置日志轮转

4. **监控告警**
   - 配置Prometheus告警规则
   - 设置Grafana仪表板
   - 配置日志监控

## 更新和维护

### 更新应用
```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d
```

### 清理资源
```bash
# 停止所有服务
docker-compose down

# 清理未使用的资源
docker system prune -a

# 清理特定服务的资源
docker-compose down -v
```
