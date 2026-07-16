# P2：Motion 样片库 · OIDC/CDN · Stripe Price 注入

**日期：** 2026-07-16  
**原则：** 只记可复现证据；无密钥处不伪造 live 成功。

---

## 1. 交付清单

| 项 | 状态 | 证据 |
|----|------|------|
| Motion 标准输入样片库 | ✅ | `backend/fixtures/motion/{still.png,ref.mp4}` + `GET /motion/samples` |
| Motion FE「加载标准输入样片」 | ✅ | `frontend/src/app/create/motion/page.tsx` |
| Fixture harness 纳入样片检查 | ✅ | `fixture_derivative_harness.py` → `motion_library.passed` |
| OIDC discovery + CSRF state | ✅ | `oidc_ready.py` + `/auth/oidc/*` |
| FE SSO 登录 / callback | ✅ | login 按钮（configured 时）+ `/auth/callback` |
| CDN/S3 公共基址解析 | ✅ | `storage_ready.public_media_base()` + readiness `storage` |
| Stripe Price bootstrap | ✅ dry-run + mock live | `scripts/bootstrap_stripe_prices.py` |
| Stripe 真实 Dashboard Price | ⏳ 需 `STRIPE_API_KEY` | 本环境 **未设置**，无法创建真实 `price_*` |
| OIDC 真实 IdP | ⏳ 需 IdP env | 本环境 `OIDC_*` 未配；未配置返回 503（诚实） |
| CDN 生产桶 | ⏳ 需部署配置 | 代码门禁就绪；`STORAGE_TYPE` 仍为 local |

---

## 2. Motion 样片库（诚实边界）

- **是什么：** 可复现的 *输入* 资产（静帧 + 短参考视频），用于 UI 一键加载与契约/ harness 校验。
- **不是什么：** 不对标 Kling Motion / Runway Act-One 的质量样片；API `mode=best_effort`。
- **再生：** `python scripts/generate_motion_fixtures.py`
- **可选 live：** `MOTION_FIXTURE_LIVE=1`（付费；本轮未开）

**验证：**

```bash
cd backend
.venv/bin/python -m pytest tests/test_p2_motion_oidc_stripe.py -q
.venv/bin/python scripts/fixture_derivative_harness.py   # passed=true 含 motion_library
```

---

## 3. OIDC / CDN

### OIDC
- 环境变量：`OIDC_ISSUER` / `CLIENT_ID` / `SECRET` / `REDIRECT_URI`
- 可选：`OIDC_REQUIRED_IN_PRODUCTION=1` → 生产缺配阻塞 readiness
- 流程：`/auth/oidc/login` → IdP → `/auth/oidc/callback` → 前端 `/auth/callback?token=`
- Discovery：优先 `/.well-known/openid-configuration`，失败回退 `{issuer}/authorize|/token|/userinfo`
- State cookie：`betty_oidc_state`（CSRF）

### CDN / 存储
- `MEDIA_CDN_BASE_URL` 优先；否则 S3 模式下 `S3_PUBLIC_BASE_URL`
- 生产：`STORAGE_TYPE=local` 或 S3 无公共基址 → readiness blocker
- 探针：`GET /api/v1/system/readiness` → `storage` / `sso`

---

## 4. Stripe Price 注入

```bash
# 始终安全：打印与目录对齐的金额计划
python scripts/bootstrap_stripe_prices.py --dry-run --json-only

# 有 sk_test_* / sk_live_* 时真实创建（幂等：按 metadata betty_plan_id + betty_cycle）
STRIPE_API_KEY=sk_test_... python scripts/bootstrap_stripe_prices.py --write-env .env
```

写入变量：`STRIPE_PRICE_{STARTER,PERSONAL,CREATOR,PRO}_{MONTHLY,YEARLY}` + `STRIPE_PRICE_TEAM_SEAT_MONTHLY`。

**本环境事实：** `STRIPE_API_KEY` 未设置 → 仅 dry-run + SDK mock 单测验证创建/注入逻辑；**未产生真实 Stripe Price ID**。

---

## 5. 自动化验证结果（本轮）

| 探针 | 结果 |
|------|------|
| `pytest tests/test_p2_motion_oidc_stripe.py` (+ hardening) | **17+ passed**（含 write-env / state CSRF） |
| `fixture_derivative_harness.py` | `passed=true`，`motion_library.passed=true` |
| `bootstrap_stripe_prices.py --dry-run` | `mode=dry-run`，含 9 个 Price env 行 |
| `GET /motion/samples` | 200，可下载 still/ref |
| `GET /auth/oidc/login`（未配置） | **503**（预期） |
| `GET /system/readiness` | 含 `stripe` / `storage` / `sso` |

---

## 6. 分数影响（诚实）

| 维度 | 前 | 后 | 说明 |
|------|----|----|------|
| Motion | 48 | **52** | 输入样片库+UI；质量上限仍 best-effort |
| SSO | 50 | **58** | discovery/CSRF/FE；无真实 IdP |
| 计费 | 68 | **72** | bootstrap+注入脚本；无真实 Price ID |
| **综合就绪** | ~74 | **~76** | 仍受 live_video / 生产密钥拖累 |

---

## 7. 勿重复 / 下一刀

**已交付勿再做：** P0 五项；P1 退款/分享/周检；P1 成本看板/真分镜/Price 配置面；本 P2 样片库/OIDC 加固/bootstrap。

**下一优先（需密钥或上游）：**
1. 用 `sk_test_` 真跑 bootstrap 并注入 staging
2. 接真实 IdP（Auth0/Okta/Keycloak）做一轮端到端 SSO
3. `STORAGE_TYPE=s3` + CDN 部署
4. `MOTION_FIXTURE_LIVE=1` 一条付费出片（诚实记录成败）
