# MySQL数据库迁移总结

## 🎯 迁移概述

本项目已成功从SQLite迁移到MySQL数据库，支持开发和生产环境的灵活切换。

## 📋 更改文件列表

### 1. Docker配置
- **docker-compose.yml**: 将PostgreSQL替换为MySQL 8.0
- **Dockerfile**: 添加MySQL客户端库依赖

### 2. 核心代码
- **src/car_img_tagger/database.py**: 完全重写，支持MySQL和SQLite双数据库
- **src/car_img_tagger/config.py**: 添加MySQL配置和环境变量支持
- **requirements.txt**: 添加PyMySQL连接器

### 3. 新增文件
- **mysql/init/01-init.sql**: MySQL初始化脚本
- **mysql/README.md**: MySQL配置说明文档
- **scripts/test_mysql_connection.py**: 数据库连接测试脚本
- **scripts/migrate_to_mysql.py**: SQLite到MySQL迁移脚本

### 4. 文档更新
- **README.md**: 更新使用说明，添加MySQL相关配置

## 🔧 技术实现

### 数据库抽象层
- 通过环境变量 `DATABASE_TYPE` 控制数据库类型
- 统一的数据库接口，支持MySQL和SQLite
- 自动处理两种数据库的SQL语法差异

### 环境变量配置
```bash
# 数据库类型选择
DATABASE_TYPE=mysql  # 或 sqlite

# MySQL连接配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=car_user
MYSQL_PASSWORD=password
MYSQL_DATABASE=car_tags
```

### Docker服务配置
```yaml
mysql:
  image: mysql:8.0
  environment:
    - MYSQL_ROOT_PASSWORD=rootpassword
    - MYSQL_DATABASE=car_tags
    - MYSQL_USER=car_user
    - MYSQL_PASSWORD=password
    - MYSQL_CHARSET=utf8mb4
    - MYSQL_COLLATION=utf8mb4_unicode_ci
  profiles:
    - production
```

## 🚀 使用方法

### 开发环境（SQLite）
```bash
# 默认使用SQLite，无需额外配置
python scripts/run_server.py
```

### 生产环境（MySQL）
```bash
# 1. 启动MySQL服务
docker-compose --profile production up mysql -d

# 2. 设置环境变量
export DATABASE_TYPE=mysql

# 3. 启动应用
python scripts/run_server.py
```

### 数据迁移
```bash
# 从SQLite迁移到MySQL
python scripts/migrate_to_mysql.py
```

### 连接测试
```bash
# 测试数据库连接
python scripts/test_mysql_connection.py
```

## 📊 数据库表结构

### images表
- 存储图片基本信息（路径、ID、品牌、型号等）
- 支持UTF8MB4字符集，兼容emoji和特殊字符

### tags表
- 存储标签定义（名称、类别、描述）
- 支持标签分类管理

### image_tags表
- 图片和标签的多对多关联
- 包含置信度和标注类型信息

### annotation_history表
- 记录标注历史变更
- 支持审计和回滚功能

## 🔍 主要特性

### 1. 双数据库支持
- 开发环境：SQLite（轻量级，单文件）
- 生产环境：MySQL（高并发，企业级）

### 2. 自动切换
- 通过环境变量自动选择数据库类型
- 无需修改代码即可切换数据库

### 3. 数据迁移
- 提供完整的SQLite到MySQL迁移工具
- 支持数据验证和完整性检查

### 4. 错误处理
- 完善的异常处理机制
- 详细的错误信息和故障排除指南

## 🛠️ 故障排除

### 常见问题

1. **连接失败**
   - 检查MySQL服务是否启动
   - 验证连接参数是否正确
   - 确认用户权限是否足够

2. **字符编码问题**
   - MySQL使用utf8mb4字符集
   - 确保客户端连接也使用相同字符集

3. **权限问题**
   - 确保用户有足够的数据库权限
   - 检查防火墙设置

### 调试工具
- `scripts/test_mysql_connection.py`: 测试连接和基本操作
- `scripts/migrate_to_mysql.py`: 数据迁移和验证
- Docker日志: `docker-compose logs mysql`

## 📈 性能优化

### MySQL优化
- 使用InnoDB存储引擎
- 创建适当的索引
- 配置连接池
- 使用utf8mb4字符集

### 查询优化
- 使用预编译语句
- 避免N+1查询问题
- 合理使用索引

## 🔒 安全考虑

### 数据库安全
- 使用非root用户连接
- 设置强密码
- 限制网络访问
- 定期备份数据

### 环境变量安全
- 敏感信息通过环境变量传递
- 避免在代码中硬编码密码
- 使用Docker secrets管理敏感数据

## 📝 后续计划

1. **性能监控**: 添加数据库性能监控
2. **备份策略**: 实现自动备份机制
3. **高可用**: 支持MySQL主从复制
4. **缓存优化**: 集成Redis缓存层
5. **数据压缩**: 优化大文件存储

## ✅ 验证清单

- [x] MySQL服务正常启动
- [x] 数据库连接测试通过
- [x] 表结构创建成功
- [x] 数据迁移功能正常
- [x] Web应用正常运行
- [x] 环境变量配置正确
- [x] Docker服务编排正常
- [x] 文档更新完整

## 🎉 总结

本次迁移成功实现了：
1. **无缝切换**: 开发和生产环境数据库分离
2. **向后兼容**: 保持原有SQLite功能
3. **企业级**: MySQL提供更好的并发和稳定性
4. **易用性**: 简单的环境变量配置
5. **可维护性**: 完整的文档和工具支持

项目现在具备了更好的扩展性和企业级部署能力！

