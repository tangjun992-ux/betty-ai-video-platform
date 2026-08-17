# Betty MCP / API 分发面（对标 Yapper）

**日期：** 2026-08-17  
**对标：** [yapper.so/mcp](https://yapper.so/mcp)  
**原则：** 做可连接的协议面，不只做营销页；不虚标货架、不伪造 OAuth。

## Yapper 公开面

- 产品页 `/mcp`：Connect / Capabilities / 54+ models / Who / FAQ
- 托管连接器 `https://yapper.so/mcp/connector`（宣称账号登录、免 API Key）
- 另售 REST + API Key

## Betty 落地

| 面 | 路径 | 诚实口径 |
|----|------|----------|
| 产品页 | `/mcp` | 结构对标；文案写明 Key / active / 非 2.5 |
| 连接器发现 | `GET /api/v1/mcp/connector` | transport + tools + auth.oauth=false |
| JSON-RPC | `POST /api/v1/mcp/connector` | initialize / tools/list / tools/call |
| REST | `/api/v1/public/{generate,quote,models,credits,tasks,assets}` | 与 Web 同一账户积分 |
| 密钥 | `/developer` | 已有 `sk_betty_` |

工具：`list_models`（可无 Key）· `get_credits` · `quote_generation` · `generate` · `get_task` · `list_assets`。

## 明确不做

- 不宣称 54+ / Seedance 2.5 / Sora / Veo
- 不伪造账号 OAuth「免 Key」
- 不把 demo 3 秒写成 SLA
- 入队仍依赖 Celery/Redis/上游 Key；环境缺失时诚实失败
