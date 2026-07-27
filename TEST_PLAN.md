# betty 平台专业测试方案

> 版本: 1.0 | 更新: 2026-05-25

---

## 一、测试层级

| 层级 | 描述 | 工具 |
|------|------|------|
| **L1 单元测试** | API 端点、适配器、工具函数 | curl / pytest |
| **L2 集成测试** | 前后端联调、Celery 任务 | curl + 轮询 |
| **L3 E2E 测试** | 浏览器端完整用户流程 | Playwright |
| **L4 性能测试** | 并发、响应时间、资源消耗 | ab / wrk |
| **L5 UI 一致性** | 视觉回归、响应式、无障碍 | Playwright 截图对比 |

---

## 二、L1 API 测试用例

### 2.1 生成端点

| ID | 用例 | 预期 |
|----|------|------|
| API-01 | POST /generate/ 空 prompt | 422 |
| API-02 | POST /generate/ 正常图片 prompt | 202 + task_id |
| API-03 | POST /generate/ 正常视频 prompt | 202 + task_id |
| API-04 | POST /generate/ 指定模型 | 202 + estimated_model 匹配 |
| API-05 | POST /generate/ media_type=auto | 202 + 自动检测 |
| API-06 | POST /generate/ 超长 prompt | 422 |
| API-07 | POST /generate/ count>4 | 422 |

### 2.2 任务端点

| ID | 用例 | 预期 |
|----|------|------|
| TASK-01 | GET /tasks/{id} 存在 | 200 + status |
| TASK-02 | GET /tasks/{id} 不存在 | 404 |
| TASK-03 | GET /tasks/ 列表 | 200 + tasks 数组 |
| TASK-04 | 任务完成 | results 非空 |

---

## 三、L3 E2E 测试用例

| ID | 场景 | 步骤 | 预期 |
|----|------|------|------|
| E2E-01 | 首页加载 | 访问 / | 200, 显示Hero标题 |
| E2E-02 | 图片生成 | 输入prompt → 点击生成 → 等待→ | 结果图片出现 |
| E2E-03 | 视频生成 | 输入prompt → 点击生成 → 等待 | 结果视频出现 |
| E2E-04 | 导航切换 | 点击侧边栏各链接 | 正确跳转 |
| E2E-05 | 定价页 | 访问/pricing | 4档方案展示 |
| E2E-06 | Agent对话 | 输入消息→发送 | AI 回复 |
| E2E-07 | Library搜索 | 访问/library→搜索 | 过滤结果 |
| E2E-08 | 响应式 | 移动端视口 | 抽屉导航 |
| E2E-09 | 模型选择 | 切换模型→生成 | 使用选定模型 |

---

## 四、L5 UI 一致性检查

| ID | 页面 | 检查项 |
|----|------|--------|
| UI-01 | 全局 | 暗黑主题色一致 |
| UI-02 | 全局 | Navbar 固定顶部 |
| UI-03 | 全局 | Sidebar 可折叠 |
| UI-04 | /create/image | 三栏布局 |
| UI-05 | /create/video | 视频特有参数可见 |
| UI-06 | /agent | 对话气泡样式 |
| UI-07 | 全部页面 | 无控制台错误 |
| UI-08 | 全部页面 | 加载态 skeleton |

---

## 五、测试执行记录

| 日期 | 通过 | 失败 | 阻塞 | 备注 |
|------|------|------|------|------|
| 2026-05-25 | - | - | - | 初始建立 |
