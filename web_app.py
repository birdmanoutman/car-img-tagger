"""
Web应用模块 - 标签管理和展示界面
"""
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from PIL import Image
import io
import base64

from database import CarTagDatabase
from config import DATA_CONFIG, API_CONFIG

# 创建FastAPI应用
app = FastAPI(title="汽车图片智能标签系统", version="1.0.0")

# 设置模板和静态文件
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化数据库
db = CarTagDatabase()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首页"""
    try:
        stats = db.get_statistics()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "stats": stats
        })
    except Exception as e:
        return HTMLResponse(f"""
        <html>
        <head><title>汽车图片标签系统</title></head>
        <body>
            <h1>🚗 汽车图片智能标签系统</h1>
            <p>系统正在启动中，请稍候...</p>
            <p>错误信息: {str(e)}</p>
            <p><a href="/api/statistics">查看API状态</a></p>
        </body>
        </html>
        """)

@app.get("/api/images")
async def get_images(
    brand: Optional[str] = None,
    angle: Optional[str] = None,
    style: Optional[str] = None,
    year: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """获取图片列表"""
    filters = {}
    if brand: filters['brand'] = brand
    if angle: filters['angle'] = angle
    if style: filters['style'] = style
    if year: filters['year'] = year
    
    images = db.search_images(filters)
    
    # 分页
    start = (page - 1) * limit
    end = start + limit
    paginated_images = images[start:end]
    
    return {
        "images": paginated_images,
        "total": len(images),
        "page": page,
        "limit": limit,
        "total_pages": (len(images) + limit - 1) // limit
    }

@app.get("/api/image/{image_id}")
async def get_image_detail(image_id: str):
    """获取图片详情"""
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM images WHERE image_id = ?', (image_id,))
        image = cursor.fetchone()
        
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 获取标签
        tags = db.get_image_tags(image_id)
        
        return {
            "image": dict(zip([desc[0] for desc in cursor.description], image)),
            "tags": tags
        }

@app.post("/api/image/{image_id}/tags")
async def update_image_tags(
    image_id: str,
    tags: List[str] = Form(...),
    is_manual: bool = Form(True)
):
    """更新图片标签"""
    try:
        # 清除现有标签
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM image_tags WHERE image_id = ?', (image_id,))
            conn.commit()
        
        # 添加新标签
        for tag in tags:
            db.add_image_tag(image_id, tag, 1.0, is_manual)
        
        return {"message": "标签更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_images(
    q: str,
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """搜索图片"""
    # 这里可以实现更复杂的搜索逻辑
    filters = {}
    if category:
        filters[category] = q
    
    images = db.search_images(filters)
    
    # 分页
    start = (page - 1) * limit
    end = start + limit
    paginated_images = images[start:end]
    
    return {
        "images": paginated_images,
        "total": len(images),
        "query": q,
        "page": page,
        "limit": limit
    }

@app.get("/api/statistics")
async def get_statistics():
    """获取统计信息"""
    return db.get_statistics()

@app.get("/api/brands")
async def get_brands():
    """获取所有品牌"""
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT brand FROM images WHERE brand != "Unknown" ORDER BY brand')
        brands = [row[0] for row in cursor.fetchall()]
        return brands

@app.get("/api/angles")
async def get_angles():
    """获取所有角度"""
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT name FROM tags WHERE category = "angles" ORDER BY name')
        angles = [row[0] for row in cursor.fetchall()]
        return angles

@app.get("/api/styles")
async def get_styles():
    """获取所有风格"""
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT name FROM tags WHERE category = "styles" ORDER BY name')
        styles = [row[0] for row in cursor.fetchall()]
        return styles

@app.get("/api/years")
async def get_years():
    """获取所有年份"""
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT year FROM images WHERE year != "Unknown" ORDER BY year DESC')
        years = [row[0] for row in cursor.fetchall()]
        return years

@app.get("/image/{image_id}")
async def serve_image(image_id: str):
    """提供图片服务"""
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT image_path FROM images WHERE image_id = ?', (image_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        image_path = result[0]
        if not Path(image_path).exists():
            raise HTTPException(status_code=404, detail="图片文件不存在")
        
        return FileResponse(image_path)

@app.get("/thumbnail/{image_id}")
async def serve_thumbnail(image_id: str, size: int = 200):
    """提供缩略图服务"""
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT image_path FROM images WHERE image_id = ?', (image_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        image_path = result[0]
        if not Path(image_path).exists():
            raise HTTPException(status_code=404, detail="图片文件不存在")
        
        # 生成缩略图
        try:
            with Image.open(image_path) as img:
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                # 直接返回图片数据
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG')
                buffer.seek(0)
                
                return Response(
                    content=buffer.getvalue(),
                    media_type="image/jpeg",
                    headers={"Cache-Control": "max-age=3600"}
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"缩略图生成失败: {str(e)}")

def create_templates():
    """创建HTML模板"""
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # 创建基础模板
    base_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}汽车图片智能标签系统{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .image-card { transition: transform 0.2s; }
        .image-card:hover { transform: scale(1.02); }
        .tag-badge { margin: 2px; }
        .stats-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="bi bi-car-front"></i> 汽车图片标签系统
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/">首页</a>
                <a class="nav-link" href="/search">搜索</a>
                <a class="nav-link" href="/statistics">统计</a>
            </div>
        </div>
    </nav>
    
    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""
    
    # 创建首页模板
    index_template = """
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h1 class="mb-4">
            <i class="bi bi-car-front"></i> 汽车图片智能标签系统
        </h1>
    </div>
</div>

<!-- 统计卡片 -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card stats-card">
            <div class="card-body text-center">
                <h3>{{ stats.total_images }}</h3>
                <p class="mb-0">总图片数</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stats-card">
            <div class="card-body text-center">
                <h3>{{ stats.brand_distribution|length }}</h3>
                <p class="mb-0">品牌数量</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stats-card">
            <div class="card-body text-center">
                <h3>{{ stats.tag_distribution|length }}</h3>
                <p class="mb-0">标签类别</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stats-card">
            <div class="card-body text-center">
                <h3>{{ stats.source_distribution|length }}</h3>
                <p class="mb-0">数据源</p>
            </div>
        </div>
    </div>
</div>

<!-- 搜索区域 -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">快速搜索</h5>
                <div class="row">
                    <div class="col-md-3">
                        <select class="form-select" id="brandFilter">
                            <option value="">所有品牌</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <select class="form-select" id="angleFilter">
                            <option value="">所有角度</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <select class="form-select" id="styleFilter">
                            <option value="">所有风格</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <button class="btn btn-primary w-100" onclick="searchImages()">
                            <i class="bi bi-search"></i> 搜索
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- 图片展示区域 -->
<div class="row" id="imagesContainer">
    <!-- 图片将通过JavaScript动态加载 -->
</div>

<!-- 分页 -->
<nav aria-label="图片分页" class="mt-4">
    <ul class="pagination justify-content-center" id="pagination">
        <!-- 分页将通过JavaScript动态生成 -->
    </ul>
</nav>
{% endblock %}

{% block scripts %}
<script>
let currentPage = 1;
const pageSize = 20;

// 加载筛选选项
async function loadFilters() {
    try {
        const [brands, angles, styles] = await Promise.all([
            fetch('/api/brands').then(r => r.json()),
            fetch('/api/angles').then(r => r.json()),
            fetch('/api/styles').then(r => r.json())
        ]);
        
        const brandSelect = document.getElementById('brandFilter');
        const angleSelect = document.getElementById('angleFilter');
        const styleSelect = document.getElementById('styleFilter');
        
        brands.forEach(brand => {
            brandSelect.innerHTML += `<option value="${brand}">${brand}</option>`;
        });
        
        angles.forEach(angle => {
            angleSelect.innerHTML += `<option value="${angle}">${angle}</option>`;
        });
        
        styles.forEach(style => {
            styleSelect.innerHTML += `<option value="${style}">${style}</option>`;
        });
    } catch (error) {
        console.error('加载筛选选项失败:', error);
    }
}

// 搜索图片
async function searchImages(page = 1) {
    const brand = document.getElementById('brandFilter').value;
    const angle = document.getElementById('angleFilter').value;
    const style = document.getElementById('styleFilter').value;
    
    const params = new URLSearchParams({
        page: page,
        limit: pageSize
    });
    
    if (brand) params.append('brand', brand);
    if (angle) params.append('angle', angle);
    if (style) params.append('style', style);
    
    try {
        const response = await fetch(`/api/images?${params}`);
        const data = await response.json();
        
        displayImages(data.images);
        updatePagination(data.page, data.total_pages);
        currentPage = page;
    } catch (error) {
        console.error('搜索失败:', error);
    }
}

// 显示图片
function displayImages(images) {
    const container = document.getElementById('imagesContainer');
    
    if (images.length === 0) {
        container.innerHTML = '<div class="col-12"><div class="alert alert-info">没有找到匹配的图片</div></div>';
        return;
    }
    
    container.innerHTML = images.map(image => `
        <div class="col-md-3 mb-4">
            <div class="card image-card h-100">
                <img src="/thumbnail/${image.image_id}" class="card-img-top" alt="${image.brand} ${image.model}">
                <div class="card-body">
                    <h6 class="card-title">${image.brand} ${image.model}</h6>
                    <p class="card-text small text-muted">${image.year} | ${image.width}×${image.height}</p>
                    <div class="mb-2">
                        ${(image.tags || '').split(',').filter(tag => tag.trim()).map(tag => 
                            `<span class="badge bg-secondary tag-badge">${tag.trim()}</span>`
                        ).join('')}
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewImage('${image.image_id}')">
                        <i class="bi bi-eye"></i> 查看详情
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// 更新分页
function updatePagination(currentPage, totalPages) {
    const pagination = document.getElementById('pagination');
    let html = '';
    
    for (let i = 1; i <= Math.min(totalPages, 10); i++) {
        html += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="searchImages(${i})">${i}</a>
            </li>
        `;
    }
    
    pagination.innerHTML = html;
}

// 查看图片详情
function viewImage(imageId) {
    window.open(`/image/${imageId}`, '_blank');
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadFilters();
    searchImages(1);
});
</script>
{% endblock %}
"""
    
    # 写入模板文件
    (templates_dir / "base.html").write_text(base_template, encoding='utf-8')
    (templates_dir / "index.html").write_text(index_template, encoding='utf-8')

def main():
    """主函数"""
    print("🌐 启动汽车图片标签Web应用...")
    
    # 创建模板文件
    create_templates()
    
    # 启动服务器
    uvicorn.run(
        app,
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        reload=API_CONFIG["debug"]
    )

if __name__ == "__main__":
    main()
