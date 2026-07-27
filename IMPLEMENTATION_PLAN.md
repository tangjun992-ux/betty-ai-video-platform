# AI 短视频平台 — 实施计划

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 从零搭建一个支持多模型接入、智能路由、异步任务队列的 AI 短视频生成平台

**Architecture:** FastAPI 后端 + Celery/Redis 任务队列 + PostgreSQL + 适配器模式 + Next.js 前端

**Tech Stack:** Python 3.12, FastAPI, Celery, Redis, PostgreSQL, SQLAlchemy, Pydantic v2, Next.js, React

---

## Phase 1: 项目骨架 (当前执行)

### Task 1.1: 创建后端目录结构和基础配置

**Objective:** 创建完整的 FastAPI 项目骨架

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/config/settings.yaml`
- Create: `backend/requirements.txt`
- Create: `backend/celery_app.py`
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`

**Step 1: FastAPI 入口 (main.py)**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的生命周期"""
    from app.config import settings
    print(f"[LIFESPAN] Starting AI Video Platform v{settings.APP_VERSION}")
    print(f"[LIFESPAN] Environment: {settings.ENV}")
    yield
    print("[LIFESPAN] Shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    description="AI 短视频自动生成平台 — 支持多模型智能路由",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from app.api import router as api_router
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": settings.APP_VERSION}
```

**Step 2: 配置管理 (config.py)**

```python
# backend/app/config.py
import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "AI Video Platform"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"
    
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aivideo"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # JWT
    JWT_SECRET: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    
    # ByteDance Seedance
    SEEDANCE_API_KEY: str = ""
    SEEDANCE_BASE_URL: str = "https://api.byteplus.com"
    
    # Kling
    KLING_ACCESS_KEY: str = ""
    KLING_SECRET_KEY: str = ""
    KLING_BASE_URL: str = "https://api.klingai.com"
    
    # 文件存储
    STORAGE_TYPE: str = "local"  # local | s3 | oss
    STORAGE_BASE_PATH: str = "/tmp/aivideo-media"
    STORAGE_BASE_URL: str = "http://localhost:8000/api/v1/media"
    
    # S3/OSS (production)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "aivideo-media"
    AWS_REGION: str = "cn-north-1"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

**Step 3: requirements.txt**

```
# FastAPI
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.9.0
pydantic-settings==2.5.0

# Database
sqlalchemy[asyncio]==2.0.35
asyncpg==0.30.0
alembic==1.13.0

# Celery
celery[redis]==5.4.0
redis==5.0.8

# HTTP
httpx==0.27.0
aiohttp==3.10.5

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9

# Storage
boto3==1.35.0
alibabacloud-oss-v2==1.0.0

# Utils
pyyaml==6.0.2
python-dotenv==1.0.1
loguru==0.7.2
```

### Task 1.2: 数据库 ORM 模型

**Objective:** 创建 User、Task、Billing 三个核心表

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/task.py`
- Create: `backend/app/models/billing.py`
- Create: `backend/app/db.py`

### Task 1.3: Celery 任务定义

**Objective:** 定义图像和视频生成的 Celery 任务

**Files:**
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/image_tasks.py`
- Create: `backend/app/tasks/video_tasks.py`
- Create: `backend/app/tasks/pipeline_tasks.py`

### Task 1.4: API 路由骨架

**Objective:** 创建核心 API 端点

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/generate.py`
- Create: `backend/app/api/tasks.py`
- Create: `backend/app/api/models_info.py`
- Create: `backend/app/api/health.py`

### Task 1.5: Docker Compose 开发环境

**Objective:** 一键启动所有依赖

**Files:**
- Create: `docker-compose.yml`

---

## Phase 2: 模型适配器

### Task 2.1: 适配器基类 + 注册表
### Task 2.2: OpenAI GPT-5.4 Image 适配器
### Task 2.3: ByteDance Seedance 适配器  
### Task 2.4: Kling v3 Pro 适配器
### Task 2.5: 适配器集成测试

---

## Phase 3: 前端页面

### Task 3.1: Next.js 项目初始化
### Task 3.2: 首页 + Prompt 输入组件
### Task 3.3: 模型选择器 + 预估面板
### Task 3.4: 任务列表 + 实时进度
### Task 3.5: 结果展示 + 下载
