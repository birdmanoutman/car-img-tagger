#!/usr/bin/env python3
"""简化的Web服务器启动脚本，避免加载AI模型依赖"""
from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 创建简化的FastAPI应用
app = FastAPI(title="汽车图片智能标签系统", version="1.0.0")

# 设置模板和静态文件
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": {
            "total_images": 0,
            "brand_distribution": {},
            "tag_distribution": {},
            "source_distribution": {}
        }
    })

@app.get("/api/statistics")
async def get_statistics():
    """获取统计信息"""
    return {
        "total_images": 0,
        "brand_distribution": {},
        "tag_distribution": {},
        "source_distribution": {}
    }

@app.get("/api/brands")
async def get_brands():
    """获取所有品牌"""
    return ["Cadillac", "Ferrari", "Honda", "MINI", "Nissan", "Porsche", "Smart", "Toyota"]

@app.get("/api/angles")
async def get_angles():
    """获取所有角度"""
    return ["1-前45", "2-正侧", "3-后45", "4-正前", "5-正后"]

@app.get("/api/styles")
async def get_styles():
    """获取所有风格"""
    return ["新能源", "运动", "豪华", "概念车", "复古", "现代", "经典", "未来感"]

@app.get("/api/images")
async def get_images(
    brand: str = None,
    angle: str = None,
    style: str = None,
    page: int = 1,
    limit: int = 20
):
    """获取图片列表"""
    return {
        "images": [],
        "total": 0,
        "page": page,
        "limit": limit,
        "total_pages": 0
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "message": "服务运行正常"}

def main() -> None:
    """主函数"""
    print("🌐 启动汽车图片标签Web应用 (简化版)...")
    print("📍 服务地址: http://localhost:8001")
    print("🔍 API文档: http://localhost:8001/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )

if __name__ == "__main__":
    main()
