# 腾讯云COS图片标注使用指南

## 📋 概述

本系统支持对腾讯云COS存储桶中的图片进行批量标注，包括角度分类和颜色检测。

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装腾讯云COS SDK
pip install cos-python-sdk-v5

# 安装其他依赖
pip install torch torchvision pandas pillow requests tqdm
```

### 2. 配置腾讯云COS

编辑 `cos_config.json` 文件：

```json
{
    "cos_config": {
        "region": "ap-beijing",
        "secret_id": "你的SecretId",
        "secret_key": "你的SecretKey"
    },
    "processing_config": {
        "confidence_threshold": 0.8,
        "top_k": 3,
        "enable_color_detection": true,
        "max_workers": 4
    }
}
```

### 3. 运行标注

```bash
# 方式1: 直接从COS批量处理
python cos_batch_processor.py

# 方式2: 使用单个标注器
python tencent_cos_image_tagger.py
```

## 📁 文件结构

```
├── tencent_cos_image_tagger.py      # 腾讯云COS图片标注器
├── cos_batch_processor.py           # 批量处理器
├── cos_config.json                  # 配置文件
├── color_detection_utils.py         # 颜色检测工具
└── processed_data/
    └── cos_images_annotated.csv     # 标注结果
```

## 🔧 配置说明

### COS配置

- `region`: 腾讯云COS区域，如 `ap-beijing`
- `secret_id`: 腾讯云API密钥ID
- `secret_key`: 腾讯云API密钥Key

### 处理配置

- `confidence_threshold`: 置信度阈值，默认0.8
- `top_k`: 返回前k个预测，默认3
- `enable_color_detection`: 是否启用颜色检测，默认true
- `max_workers`: 并发处理数，默认4

## 📊 使用方式

### 方式1: 直接从COS处理

```python
from cos_batch_processor import COSBatchProcessor

# 创建处理器
processor = COSBatchProcessor('cos_config.json')

# 直接从COS处理
results_df = processor.process_from_cos(
    bucket_name='your-bucket-name',
    prefix='cars/',
    max_images=100
)
```

### 方式2: 从CSV文件处理

创建CSV文件 `image_list.csv`：

```csv
image_id,source_type,bucket_name,object_key,brand,car_model
cos_001,cos,your-bucket,cars/ford/mondeo/001.jpg,Ford,Mondeo
cos_002,url,,https://example.com/car.jpg,Smart,ForTwo
```

然后运行：

```python
results_df = processor.process_from_csv('image_list.csv')
```

### 方式3: 手动创建图片列表

```python
image_list = [
    {
        'image_id': 'cos_001',
        'image_source': {
            'type': 'cos',
            'bucket_name': 'your-bucket-name',
            'object_key': 'cars/ford/mondeo/001.jpg'
        },
        'brand': 'Ford',
        'car_model': 'Mondeo'
    }
]

results_df = processor.process_batch(image_list)
```

## 📈 输出结果

标注结果保存在CSV文件中，包含以下字段：

- `image_id`: 图片ID
- `image_source`: 图片源信息（JSON格式）
- `brand`: 品牌
- `car_model`: 车型
- `width/height`: 图片尺寸
- `primary_angle`: 主要角度标签
- `primary_confidence`: 角度置信度
- `primary_color`: 主要颜色
- `primary_color_confidence`: 颜色置信度
- `auto_tags`: 自动标签列表
- `needs_annotation`: 是否需要人工标注

## 🎯 性能优化

### 1. 并发处理

调整 `max_workers` 参数：

```json
{
    "processing_config": {
        "max_workers": 8  // 根据CPU核心数调整
    }
}
```

### 2. 批量大小

对于大量图片，建议分批处理：

```python
# 分批处理，每批100张
for i in range(0, total_images, 100):
    batch = image_list[i:i+100]
    results = processor.process_batch(batch, f'batch_{i//100}.csv')
```

### 3. 网络优化

- 使用CDN加速图片下载
- 调整超时时间
- 使用多线程下载

## ⚠️ 注意事项

### 1. 权限配置

确保COS密钥具有以下权限：
- `cos:GetObject` - 读取对象
- `cos:ListBucket` - 列出对象

### 2. 网络要求

- 稳定的网络连接
- 足够的带宽支持图片下载
- 考虑网络延迟对处理时间的影响

### 3. 存储空间

- 临时文件会占用磁盘空间
- 建议定期清理临时文件
- 监控磁盘使用情况

### 4. 成本控制

- 监控COS API调用次数
- 考虑使用CDN降低流量成本
- 合理设置并发数避免超限

## 🔍 故障排除

### 1. 认证失败

```
❌ COS客户端初始化失败: InvalidAccessKeyId
```

**解决方案：**
- 检查SecretId和SecretKey是否正确
- 确认密钥是否有效
- 检查区域设置是否正确

### 2. 网络超时

```
❌ 下载图片失败: ReadTimeout
```

**解决方案：**
- 增加超时时间
- 检查网络连接
- 减少并发数

### 3. 内存不足

```
❌ 处理图片失败: OutOfMemoryError
```

**解决方案：**
- 减少并发数
- 增加系统内存
- 分批处理图片

### 4. 模型加载失败

```
❌ 模型加载失败: FileNotFoundError
```

**解决方案：**
- 确认模型文件存在
- 检查文件路径
- 重新训练模型

## 📞 技术支持

如果遇到问题，请检查：

1. 配置文件格式是否正确
2. 网络连接是否稳定
3. 腾讯云COS权限是否充足
4. 系统资源是否足够

## 🎉 总结

通过本系统，你可以：

- ✅ 批量处理腾讯云COS中的图片
- ✅ 自动进行角度分类和颜色检测
- ✅ 支持多种输入方式（COS、URL、CSV）
- ✅ 提供详细的处理统计和结果
- ✅ 支持并发处理提高效率

开始使用吧！🚀
