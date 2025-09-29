# MySQL数据库配置

## 概述

本项目已从SQLite迁移到MySQL数据库，支持开发和生产环境。

## 配置说明

### 环境变量

- `DATABASE_TYPE`: 数据库类型 (`sqlite` 或 `mysql`)
- `MYSQL_HOST`: MySQL主机地址
- `MYSQL_PORT`: MySQL端口 (默认: 3306)
- `MYSQL_USER`: MySQL用户名
- `MYSQL_PASSWORD`: MySQL密码
- `MYSQL_DATABASE`: MySQL数据库名

### Docker Compose配置

MySQL服务配置在 `docker-compose.yml` 中：

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
  volumes:
    - mysql_data:/var/lib/mysql
    - ./mysql/init:/docker-entrypoint-initdb.d:ro
  ports:
    - "3306:3306"
  profiles:
    - production
```

## 使用方法

### 1. 开发环境（使用SQLite）

```bash
# 默认使用SQLite
python scripts/run_server.py
```

### 2. 生产环境（使用MySQL）

```bash
# 启动MySQL服务
docker-compose --profile production up mysql -d

# 设置环境变量使用MySQL
export DATABASE_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=car_user
export MYSQL_PASSWORD=password
export MYSQL_DATABASE=car_tags

# 启动应用
python scripts/run_server.py
```

### 3. Docker环境

```bash
# 启动完整服务栈（包括MySQL）
docker-compose --profile production up -d

# 或者只启动MySQL
docker-compose --profile production up mysql -d
```

## 数据库表结构

### images表
- `id`: 主键
- `image_path`: 图片路径
- `image_id`: 图片唯一标识
- `source`: 图片来源
- `brand`: 品牌
- `model`: 型号
- `year`: 年份
- `width`: 宽度
- `height`: 高度
- `file_size`: 文件大小
- `created_at`: 创建时间
- `updated_at`: 更新时间

### tags表
- `id`: 主键
- `name`: 标签名称
- `category`: 标签类别
- `description`: 描述
- `created_at`: 创建时间

### image_tags表
- `id`: 主键
- `image_id`: 图片ID（外键）
- `tag_id`: 标签ID（外键）
- `confidence`: 置信度
- `is_manual`: 是否手动标注
- `created_at`: 创建时间

### annotation_history表
- `id`: 主键
- `image_id`: 图片ID（外键）
- `action`: 操作类型
- `old_tags`: 旧标签
- `new_tags`: 新标签
- `user_id`: 用户ID
- `created_at`: 创建时间

## 迁移说明

### 从SQLite迁移到MySQL

1. 导出SQLite数据：
```python
from src.car_img_tagger.database import CarTagDatabase
db = CarTagDatabase()  # 使用SQLite
# 导出数据到CSV
```

2. 切换到MySQL：
```bash
export DATABASE_TYPE=mysql
```

3. 重新导入数据：
```python
db = CarTagDatabase()  # 使用MySQL
db.import_from_csv('exported_data.csv')
```

## 故障排除

### 连接问题
- 检查MySQL服务是否启动
- 验证连接参数（主机、端口、用户名、密码）
- 确认数据库是否存在

### 字符编码问题
- MySQL使用 `utf8mb4` 字符集
- 确保客户端连接也使用相同字符集

### 权限问题
- 确保用户有足够的数据库权限
- 检查防火墙设置

