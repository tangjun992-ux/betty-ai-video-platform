# AI 短视频自动生成平台 — 总体设计方案

---

## 一、产品定位

> **一句话描述：** 用户输入文字描述 → 系统智能选择模型 → 自动生图/生视频 → 批量交付。

**目标用户：**
- 自媒体创作者（短视频、图文内容）
- 电商从业者（商品展示、广告素材）
- 营销/设计团队（宣传物料、创意概念）
- 普通用户（娱乐、创意表达）

---

## 二、系统架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                        前端用户层 (Web)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  提示词  │  │  参数设置 │  │  任务列表 │  │  结果展示 │         │
│  │  输入框   │  │ (尺寸/风格│  │  (队列)  │  │  (图片/视频│         │
│  │          │  │  时长/模型)│  │          │  │  下载)   │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTPS / REST + WebSocket
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                       API 网关层 (FastAPI)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  用户认证 │  │  请求路由 │  │  限流鉴权 │  │  计费计量 │         │
│  │  Auth    │  │  Router  │  │  RateLimit│  │  Billing  │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      智能路由层 (Prompt Router)                   │
│                                                                  │
│  用户提示词 ──▶ 语义分析 ──▶ 策略决策 ──▶ 模型选择               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                    Prompt Analyzer                    │       │
│  │  - 内容分类: 图像 / 视频 / 多帧                       │       │
│  │  - 风格提取: 写实 / 动画 / 抽象 / 产品 / 风景         │       │
│  │  - 复杂度评估: 简单 / 中等 / 复杂                     │       │
│  │  - 情绪/氛围: 温暖 / 酷炫 / 专业 / 可爱               │       │
│  └──────────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                   Model Selector                      │       │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │       │
│  │  │GPT5.4-I │ │Seedance │ │ Kling   │ │  ...    │    │       │
│  │  │(精细图) │ │2.0 Fast │ │ v3 Pro  │ │ (扩展)  │    │       │
│  │  │         │ │(快视频) │ │(高质量) │ │         │    │       │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │       │
│  │  决策因子: 质量/速度/成本/风格匹配                    │       │
│  └──────────────────────────────────────────────────────┘       │
└──────────────────────────────┬───────────────────────────────────┘
                               │ 异步任务分发
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                       任务队列层 (Celery + Redis)                 │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │  图像队列 │  │  短视频  │  │  长视频  │                       │
│  │  image_q │  │  fast_q  │  │  pro_q   │                       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                       │
│       │              │             │                              │
│  ┌────┴──────────────┴─────────────┴─────┐                       │
│  │          Worker 集群 (可水平扩展)       │                       │
│  │   Worker-1  Worker-2  Worker-3  ...   │                       │
│  └───────────────────────────────────────┘                       │
└──────────────────────────────┬───────────────────────────────────┘
                               │ 调用各模型 API
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    模型适配层 (Model Adapters)                    │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  OpenAI Adapter │  │  ByteDance Adap │ │  Kling Adapter  │  │
│  │  ────────────── │  │  ────────────── │  │  ────────────── │  │
│  │  GPT-5.4 Image  │  │  Seedance 2.0   │  │  Video v3 Pro  │  │
│  │  DALL·E 3       │  │  Seedance 1.0   │  │  Kling v2      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐        │
│  │              统一输出格式                              │        │
│  │  { "task_id", "media_url", "thumbnail", "meta", ... }│        │
│  └──────────────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     存储层 (Storage)                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ PostgreSQL│  │  Redis   │  │  S3/OSS  │  │  CDN     │         │
│  │ (用户/任务)│  │ (队列/缓)│  │ (媒体存储)│  │ (加速分发)│         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 三、智能路由引擎设计

### 3.1 路由策略矩阵

| 用户提示词特征 | 推荐模型 | 理由 |
|---------------|---------|------|
| "高清产品图"、"精美海报"、"概念设计" | OpenAI GPT-5.4 Image 2 | 细节处理最佳，适合高质量需求 |
| "快速生成"、"10秒短视频"、"动态效果" | ByteDance Seedance 2.0 Fast | 生成速度快，图像转视频能力强 |
| "电影感"、"广告片"、"高质量短片" | Kling Video v3.0 Pro | 画质电影级，支持长视频 |
| "写实人物"、"场景渲染" | Seedance + GPT-5.4 混合 | 写实能力突出，多模型交叉验证 |
| 未指定模型 | 路由引擎自动选择 | 根据语义分析结果匹配 |

### 3.2 Prompt 分析流程

```
原始提示词
    │
    ▼
┌─────────────────────────────────┐
│  Stage 1: LLM 语义分析          │
│  ─────────────────────────      │
│  调用 LLM 对提示词进行结构化提取:│
│  - 生成类型: image / video      │
│  - 风格标签: [...]              │
│  - 质量要求: fast / quality     │
│  - 场景: [... ]                 │
└────────────┬────────────────────┘
             │ 结构化标签
             ▼
┌─────────────────────────────────┐
│  Stage 2: 规则 + 评分匹配        │
│  ─────────────────────────       │
│  每个模型对标签集合进行评分:       │
│  model_score = f(风格匹配度       │
│                + 质量权重         │
│                - 成本系数         │
│                + 速度系数)        │
└────────────┬────────────────────┘
             │ 最高分模型
             ▼
┌─────────────────────────────────┐
│  Stage 3: 最终决策               │
│  ─────────                       │
│  - 用户指定→ 尊重用户选择         │
│  - 默认→ 最高分模型               │
│  - 多步任务→ 拆分模型链(图+视频)  │
└────────────┬────────────────────┘
             │ 模型选定
             ▼
         提交任务队列
```

### 3.3 路由配置示例

```yaml
# config/model_routing.yaml

routing_rules:
  image:
    # 优先：质量需求明确的用户
    "openai/gpt-5.4-image-2":
      triggers:
        keywords: ["高清", "精美", "产品图", "海报", "设计", "概念", "4K"]
        quality: "high"
      cost_per_request: 0.05
      priority: 1

    # 备选：快速生成场景
    "bytedance/seedart":
      triggers:
        keywords: ["写实", "人物", "场景"]
        quality: "medium"
      cost_per_request: 0.02
      priority: 2

  video:
    # 快速视频
    "bytedance/seedance-2-fast":
      triggers:
        keywords: ["短视频", "动态", "快速", "动画"]
        duration: "short"  # ≤10s
        cost_tier: "medium"
      priority: 1

    # 高质量视频
    "kling/video-v3-pro":
      triggers:
        keywords: ["电影", "广告", "高质量", "专业", "大片"]
        duration: "long"  # 10-60s
        cost_tier: "high"
      priority: 2

    # 默认视频模型
    "default_video":
      model: "bytedance/seedance-2-fast"
      fallback_trigger: true
      priority: 99

# 多步任务模板
task_templates:
  product_showcase:
    description: "商品展示视频"
    steps:
      - type: image
        model: "openai/gpt-5.4-image-2"
        prompt_template: "商品产品摄影，{product}，{style}风格，白色背景"
      - type: video
        model: "bytedance/seedance-2-fast"
        prompt_template: "镜头缓慢推进，展示{product}"

  brand_trailer:
    description: "品牌预告片"
    steps:
      - type: image
        model: "openai/gpt-5.4-image-2"
        prompt_template: "电影级画面，{scene}，震撼光影"
      - type: video
        model: "kling/video-v3-pro"
        prompt_template: "电影预告片风格，{scene}，缓慢拉远"
```

---

## 四、项目目录结构

```
ai-video-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── config.py                  # 配置管理
│   │   │
│   │   ├── auth/                      # 用户认证
│   │   │   ├── __init__.py
│   │   │   ├── middleware.py          # JWT / OAuth 中间件
│   │   │   └── models.py              # User, Token 模型
│   │   │
│   │   ├── api/                       # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── generate.py            # POST /api/v1/generate
│   │   │   ├── tasks.py               # GET /api/v1/tasks/:id
│   │   │   ├── models.py              # GET /api/v1/models （可用模型列表）
│   │   │   ├── billing.py             # GET /api/v1/usage, POST /api/v1/topup
│   │   │   └── user.py                # 用户管理
│   │   │
│   │   ├── router/                    # 智能路由引擎
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py            # Prompt 语义分析
│   │   │   ├── selector.py            # 模型选择器
│   │   │   ├── templates.py           # 任务模板库
│   │   │   └── scoring.py             # 评分算法
│   │   │
│   │   ├── adapters/                  # 模型适配器（统一接口）
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # 抽象基类
│   │   │   ├── openai_adapter.py      # OpenAI GPT-5.4 Image
│   │   │   ├── seedance_adapter.py    # ByteDance Seedance
│   │   │   ├── kling_adapter.py       # 可灵 Kling
│   │   │   └── registry.py            # 适配器注册表
│   │   │
│   │   ├── tasks/                     # Celery 任务定义
│   │   │   ├── __init__.py
│   │   │   ├── image_tasks.py         # 图像生成任务
│   │   │   ├── video_tasks.py         # 视频生成任务
│   │   │   └── pipeline_tasks.py      # 多步流水线任务
│   │   │
│   │   ├── models/                    # ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── task.py                # 生成任务记录
│   │   │   ├── user.py                # 用户
│   │   │   └── billing.py             # 账单/余额
│   │   │
│   │   ├── services/                  # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── storage.py             # S3/OSS 文件存储
│   │   │   ├── notification.py        # Webhook / 消息通知
│   │   │   └── billing_service.py     # 扣费/充值
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── rate_limiter.py        # 限流
│   │       ├── prompt_enhancer.py     # Prompt 优化/翻译
│   │       └── validators.py          # 输入校验
│   │
│   ├── config/                        # 配置文件
│   │   ├── settings.yaml              # 主配置
│   │   ├── model_routing.yaml          # 路由规则
│   │   └── templates.yaml             # 任务模板
│   │
│   ├── celery_app.py                  # Celery 入口
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                          # 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.tsx              # 首页/输入
│   │   │   ├── gallery.tsx            # 作品展示
│   │   │   ├── tasks.tsx              # 我的任务列表
│   │   │   ├── pricing.tsx            # 价格
│   │   │   └── login.tsx              # 登录注册
│   │   ├── components/
│   │   │   ├── PromptInput.tsx        # 提示词输入组件
│   │   │   ├── ModelSelector.tsx      # 模型选择器
│   │   │   ├── TaskQueue.tsx          # 任务队列展示
│   │   │   ├── ResultCard.tsx         # 结果卡片
│   │   │   ├── ProgressBar.tsx        # 生成进度条
│   │   │   └── HistoryGrid.tsx        # 历史作品网格
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
│
├── infra/                             # 基础设施
│   ├── docker-compose.yml             # 本地开发编排
│   ├── nginx.conf                     # 反向代理
│   ├── k8s/                           # 生产 Kubernetes
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── terraform/                     # 云资源
│
├── docs/
│   ├── api-docs.md                    # API 文档
│   ├── deployment.md                  # 部署文档
│   └── architecture.md                # 架构图解
│
└── tests/
    ├── test_router/
    ├── test_adapters/
    └── test_api/
```

---

## 五、核心 API 设计

### 5.1 提交生成请求

```
POST /api/v1/generate
Authorization: Bearer <token>

Body:
{
  "prompt": "一段电影预告片风格的科幻城市夜景，有飞行汽车和霓虹灯光",
  "media_type": "auto",          // "image" | "video" | "auto" (自动)
  "model": "auto",               // 指定模型或 "auto"
  "quality": "high",             // "fast" | "balanced" | "high"
  "resolution": "1080p",         // "720p" | "1080p" | "4K"
  "duration": 10,                // 视频时长(秒)，仅视频
  "count": 1,                    // 生成数量
  "template": null,              // 可选模板名: "product_showcase"
  "webhook_url": null            // 完成后的回调地址（可选）
}

Response 202 Accepted:
{
  "task_id": "tsk_abc123def456",
  "status": "queued",
  "estimated_model": "kling/video-v3-pro",
  "estimated_time_seconds": 90,
  "estimated_cost_credits": 15,
  "poll_url": "/api/v1/tasks/tsk_abc123def456",
  "ws_url": "wss://api.example.com/ws/tasks/tsk_abc123def456"
}
```

### 5.2 查询任务状态（轮询）

```
GET /api/v1/tasks/{task_id}

Response 200:
// 进行中
{
  "task_id": "tsk_abc123def456",
  "status": "processing",         // queued | processing | completed | failed
  "progress": 45,                 // 百分比
  "current_stage": "generating",  // analyzing | routing | generating | uploading
  "model": "kling/video-v3-pro",
  "started_at": "2026-05-23T12:00:00Z",
  "estimated_completion": "2026-05-23T12:01:30Z"
}

// 完成
{
  "task_id": "tsk_abc123def456",
  "status": "completed",
  "results": [
    {
      "type": "video",
      "url": "https://cdn.example.com/videos/tsk_abc123.mp4",
      "thumbnail": "https://cdn.example.com/thumbs/tsk_abc123.jpg",
      "duration": 10,
      "resolution": "1920x1080",
      "model": "kling/video-v3-pro"
    }
  ],
  "cost_credits": 12,
  "completed_at": "2026-05-23T12:01:28Z"
}
```

### 5.3 WebSocket 实时推送

```
WS wss://api.example.com/ws/tasks/{task_id}

// 服务端推送事件
{"event": "progress", "percent": 30, "stage": "routing"}
{"event": "progress", "percent": 60, "stage": "generating"}
{"event": "completed", "results": [...]}
{"event": "failed", "error": "模型服务暂时不可用"}
```

---

## 六、统一模型适配器接口

```python
# backend/app/adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class GenerationResult:
    media_url: str          # 媒体文件 URL
    thumbnail_url: str      # 缩略图 URL
    media_type: str         # "image" | "video"
    model: str              # 实际使用的模型
    resolution: str         # 如 "1080x1920"
    duration: Optional[float]  # 视频时长
    cost: float             # 实际消耗
    meta: dict              # 额外元数据

class BaseModelAdapter(ABC):
    """所有模型适配器必须实现的抽象接口"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """供应商名称"""
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """支持的模型列表"""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> dict:
        """能力描述
        {
            "media_types": ["image", "video"],
            "max_resolution": "4K",
            "max_duration": 60,
            "avg_latency_s": 30,
            "styles": ["realistic", "anime", "cinematic", ...],
            "cost_per_image": 0.05,
            "cost_per_video_s": 0.02,
        }
        """
        ...

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "auto",
        count: int = 1,
    ) -> list[GenerationResult]:
        """生成图像"""
        ...

    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,  # 可选的参考图
        duration: int = 5,
        quality: str = "high",
    ) -> GenerationResult:
        """生成视频"""
        ...

    @abstractmethod
    async def check_status(self) -> bool:
        """健康检查"""
        ...


# 适配器注册
# backend/app/adapters/registry.py
from .openai_adapter import OpenAIAdapter
from .seedance_adapter import SeedanceAdapter
from .kling_adapter import KlingAdapter

MODEL_REGISTRY: dict[str, BaseModelAdapter] = {
    "openai": OpenAIAdapter(),
    "bytedance": SeedanceAdapter(),
    "kling": KlingAdapter(),
}

def get_adapter(model_name: str) -> BaseModelAdapter:
    """根据模型名获取适配器"""
    for key, adapter in MODEL_REGISTRY.items():
        if model_name in adapter.supported_models:
            return adapter
    raise ValueError(f"Unknown model: {model_name}")
```

---

## 七、Prompt 路由引擎核心逻辑

```python
# backend/app/router/selector.py
from dataclasses import dataclass
from .analyzer import PromptAnalysis
from .scoring import ScoreModel

@dataclass
class RoutingDecision:
    primary_model: str
    fallback_model: str
    reason: str
    confidence: float      # 0-1，匹配置信度
    estimated_cost: float
    estimated_time: int    # 秒

class ModelSelector:
    def select(
        self,
        analysis: PromptAnalysis,
        user_preferences: dict = None,
        budget_limit: float = None,
    ) -> RoutingDecision:
        """
        智能模型选择

        流程：
        1. 加载路由规则配置
        2. 对每个可用模型进行评分
        3. 排序选出最优模型和备选模型
        4. 考虑预算约束
        """
        # 评分算法：
        # score = (
        #     style_match * 0.35        # 风格匹配度权重 35%
        #   + quality_fit * 0.25        # 质量匹配度权重 25%
        #   + speed_fit * 0.15          # 速度匹配度权重 15%
        #   cost_penalty * 0.15         # 成本惩罚权重 15%
        #   + availability * 0.10       # 可用性权重 10%
        # )
        ...

    def select_chain(
        self,
        analysis: PromptAnalysis,
    ) -> list[RoutingDecision]:
        """
        多步任务链选择

        例如：先生成关键帧图片 → 再以图生视频
        """
        if analysis.needs_image_to_video:
            return [
                self._select_image_model(analysis),   # 第一步：生图
                self._select_video_model(analysis),   # 第二步：图生视频
            ]
        elif analysis.needs_multi_scene:
            return self._select_multi_scene_models(analysis)
        else:
            return [self.select(analysis)]
```

---

## 八、前端页面设计

### 8.1 首页（创作页）

```
┌───────────────────────────────────────────────────────┐
│  AI 视频创作平台                                       │
├───────────────────────────────────────────────────────┤
│                                                       │
│   ┌─ [🎯 任务模板] ─ 短视频 / 产品 / 广告 / 自由创作 ─┘│
│                                                       │
│   ┌─────────────────────────────────────────────────┐ │
│   │  ✍️ 描述你想要的画面...                          │ │
│   │                                                 │ │
│   │  [文本域，支持多行，placeholder: "比如：一段..."] │ │
│   │                                                 │ │
│   └─────────────────────────────────────────────────┘ │
│                                                       │
│   ┌─────────────────────────────────────────────────┐ │
│   │  输出类型：🖼️ 图片  |  🎬 视频  |  ⚡ 自动选择   │ │
│   └─────────────────────────────────────────────────┘ │
│                                                       │
│   [ 画质 ]  ⚡快 | ⚖️平衡 | 🌟精细                     │
│   [ 时长 ]  5s | 10s | 30s | 60s   (视频时)            │
│   [ 尺寸 ]  1:1 | 16:9 | 9:16                         │
│   [ 数量 ]  1 | 2 | 4                                 │
│   [ 模型 ]  自动选择 ▼  (可手动指定)                    │
│                                                       │
│   ┌─────────────────────────────────────────────────┐ │
│   │  预估：🤖 Kling v3 Pro  |  ⏱️ ~90秒  |  💰 15积分│ │
│   └─────────────────────────────────────────────────┘ │
│                                                       │
│                    [ 🚀 立即生成 ]                     │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### 8.2 任务队列页

```
┌────────────────────────────────────────────────┐
│  我的生成任务                                  │
├────────────────────────────────────────────────┤
│                                                │
│  ✅ 已完成 (12)    ⏳ 进行中 (1)    ❌ 失败 (0)  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │ ⏳ 生成中...                    [查看]    │  │
│  │ "科幻城市夜景，霓虹灯光"                  │  │
│  │  Kling v3 Pro  |  ▓▓▓▓▓░░░░ 65%  |  ~30s│  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ [预览图]  │  │ [预览图]  │  │ [预览图]  │     │
│  │ 已完成   │  │ 已完成   │  │ 已完成   │     │
│  │ 2分钟前  │  │ 1小时前  │  │ 昨天     │     │
│  │ [下载]    │  │ [下载]    │  │ [下载]    │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                │
└────────────────────────────────────────────────┘
```

---

## 九、计费系统设计

### 9.1 积分体系

| 操作 | 消耗积分 | 说明 |
|------|---------|------|
| GPT-5.4 Image 生成 1 张 | 5 | 高质量图 |
| Seedance 图片生成 | 3 | 中等质量 |
| Seedance 2.0 Fast 5s 视频 | 8 | 快速视频 |
| Seedance 2.0 Fast 10s 视频 | 15 | |
| Kling v3 Pro 5s 视频 | 15 | 高质量 |
| Kling v3 Pro 30s 视频 | 45 | |
| Kling v3 Pro 60s 视频 | 90 | |

### 9.2 套餐

| 套餐 | 价格/月 | 积分 | 并发 | 优先队列 |
|------|--------|------|------|---------|
| 体验免费 | ¥0 | 10积分/天 | 1 | ❌ |
| 创作者 | ¥49 | 500积分 | 2 | ❌ |
| 专业版 | ¥199 | 3000积分 | 5 | ✅ |
| 企业版 | 自定义 | 自定义 | 10+ | ✅ |

---

## 十、分阶段实施路线

### Phase 1：MVP（2-3 周）

**目标：** 跑通单个模型的完整流程

- [ ] 搭建 FastAPI 后端骨架
- [ ] 实现 2 个模型适配器（OpenAI + Seedance）
- [ ] 实现基础 Prompt → 模型调用 → 返回结果
- [ ] 简单前端表单 + 结果展示
- [ ] Celery + Redis 异步任务队列
- [ ] 基础用户注册/登录

### Phase 2：路由引擎（2 周）

**目标：** 智能路由 + 多模型支持

- [ ] Prompt 语义分析模块
- [ ] 模型评分选择器
- [ ] Kling 适配器
- [ ] 路由规则配置化（YAML）
- [ ] 多步任务流水线（图→视频）

### Phase 3：商业化（2 周）

**目标：** 用户计费 + 平台化

- [ ] 积分计费系统
- [ ] 任务队列页 + 历史记录
- [ ] WebSocket 实时进度推送
- [ ] 套餐/支付集成
- [ ] 任务模板库

### Phase 4：扩展优化（持续）

**目标：** 更多模型 + 更好的体验

- [ ] 扩展更多模型（Runway, Luma, Pika, Midjourney）
- [ ] Prompt 自动优化/翻译（中文→英文）
- [ ] A/B 测试路由策略
- [ ] 批量生成 API
- [ ] 社区/作品分享功能
- [ ] API 开放给第三方

---

## 十一、关键技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 后端框架 | **FastAPI** (Python) | 异步支持好，AI 生态原生，开发快 |
| 任务队列 | **Celery + Redis** | 成熟稳定，支持多队列、优先级、重试 |
| 数据库 | **PostgreSQL** | 关系型，用户/账单/任务数据可靠性高 |
| 缓存 | **Redis** | 快速会话、限流、队列、状态缓存 |
| 文件存储 | **阿里云 OSS / AWS S3** | 大规模媒体存储，便宜可靠 |
| CDN | **阿里云 CDN** | 中国大陆加速分发 |
| 前端 | **Next.js + React** | SSR + 组件化，生态成熟 |
| API 文档 | **OpenAPI/Swagger** | FastAPI 自动生成 |
| 部署 | **Docker + K8s / Docker Compose** | 容器化，水平扩展 |
| Gateway | **Nginx + OpenResty** | 限流、反向代理、负载均衡 |
| 监控 | **Prometheus + Grafana** | 任务成功率、延迟、成本追踪 |

---

## 十二、安全与合规

1. **内容审核**：所有提示词和生成结果接入内容审核 API，防止违规内容
2. **频率限制**：按用户等级设置生成频率上限，防止滥用
3. **API Key 保护**：模型 API Key 存储在 Vault/环境变量，不透出到前端
4. **水印/标识**：自动给生成内容添加 "AI 生成" 水印
5. **数据隔离**：用户数据行级权限，结果文件 URL 带签名
6. **隐私保护**：提示词不用于模型训练，任务完成后 N 天自动清理原始数据

---

*本文档是平台总体设计，后续按 Phase 拆分为详细实施计划。*
