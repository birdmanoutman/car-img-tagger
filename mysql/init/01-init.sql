-- MySQL数据库初始化脚本
-- 创建数据库和用户（如果不存在）

-- 确保使用utf8mb4字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS car_tags 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE car_tags;

-- 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'car_user'@'%' IDENTIFIED BY 'password';

-- 授权
GRANT ALL PRIVILEGES ON car_tags.* TO 'car_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 显示创建结果
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User = 'car_user';

