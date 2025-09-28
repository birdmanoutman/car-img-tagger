# Docker 快速使用指南

基于Python 3.13的Docker部署方案

## 快速启动

### 基础模式（开发/测试）
```bash
# 启动主应用和Redis
docker-compose up -d

# 访问应用
open http://localhost:8001
```

### 生产模式（完整部署）
```bash
# 启动所有服务（包括数据库、监控等）
docker-compose --profile production up -d

# 访问服务
# 主应用: http://localhost:8001
# 监控: http://localhost:9090
# 仪表板: http://localhost:3000
```

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f car-img-tagger

# 重启服务
docker-compose restart car-img-tagger

# 停止服务
docker-compose down

# 重新构建
docker-compose build
```

## 数据目录

以下目录会被挂载到容器中，数据会持久化保存：
- `./databases` - 数据库文件
- `./processed_data` - 处理后的数据
- `./models` - 模型文件
- `./output` - 输出文件
- `./reports` - 报告文件
- `./图片素材` - 原始图片素材
- `./各标签素材` - 标签分类素材

## 故障排除

如果遇到问题，可以：
1. 查看日志：`docker-compose logs -f car-img-tagger`
2. 进入容器调试：`docker-compose exec car-img-tagger bash`
3. 重启服务：`docker-compose restart car-img-tagger`

详细文档请参考：[docs/docker-deployment.md](docs/docker-deployment.md)
