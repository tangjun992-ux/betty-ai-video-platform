=== L4 Performance Test ===
Start: Mon May 25 11:25:59 CST 2026

## 1. API 端点性能测试

--- /api/v1/health/ ---
  50次请求: 平均 6ms
--- /api/v1/tasks/ ---
  50次请求: 平均 8ms
--- /api/v1/models/ ---
  50次请求: 平均 5ms
--- POST /api/v1/generate/analyze ---
  50次请求: 平均 5ms

## 2. 前端页面加载测试

  /: 64461bytes, TTFB 31ms
  /create/image: 62220bytes, TTFB 29ms
  /create/video: 59409bytes, TTFB 24ms
  /agent: 52259bytes, TTFB 24ms
  /gallery: 46623bytes, TTFB 21ms
  /pricing: 62611bytes, TTFB 19ms
  /models: 57593bytes, TTFB 23ms
  /dashboard: 59371bytes, TTFB 22ms
  /tools: 61809bytes, TTFB 19ms
  /library: 57899bytes, TTFB 23ms

**测试完成时间: Mon May 25 11:26:01 CST 2026**
## L5 UI 视觉回归测试

### 1. 全部页面 HTTP 状态
  ❌ / → 500
  ❌ /create/image → 500
  ✅ /create/video → 200
  ✅ /agent → 200
  ✅ /gallery → 200
  ✅ /pricing → 200
  ✅ /models → 200
  ✅ /dashboard → 200
  ✅ /tools → 200
  ✅ /library → 200
  ✅ /settings → 200
  ✅ /tasks → 200

### 2. 品牌一致性检查
  ⚠️ /:  (无 betty 品牌)
  ⚠️ /create/image:  (无 betty 品牌)
  ✅ /gallery: betty — AI 内容创作平台
  ✅ /settings: betty — AI 内容创作平台

### 3. Yapper 残留扫描
  ❌ 首页发现 0
0 处 Yapper

### 4. 移动端响应式
  📱 移动端适配元素: 0
0处

**L5 测试完成: Mon May 25 12:08:46 CST 2026**
