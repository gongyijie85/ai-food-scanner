# iOS 后端复用可行性评估

评估日期：2026-07-23  
关联 issue：#19（map issue：#16）

## 1. 评估目标

1. iOS App 能否直接调用 MiMo / Agnes API？
2. API Key 如何安全存放？能否硬编码在客户端？
3. 如果复用现有 Python 后端，需要新增哪些接口？
4. 当前 Streamlit 后端是否适合移动端？
5. 推荐的后端架构是什么？

## 2. 当前后端现状

- 入口：`utils/api.py` 封装了所有多模态识别调用。
- 模型路由：按 `qwen` → `zhipu` → `mimo` → `agnes` 优先级轮询。
- MiMo：
  - Base URL：`https://token-plan-sgp.xiaomimimo.com/v1/chat/completions`
  - 认证头：`api-key: tp-xxxxx`
  - 模型：`mimo-v2.5`
- Agnes：
  - Base URL：`https://apihub.agnes-ai.com/v1/chat/completions`
  - 认证头：现有代码沿用 MiMo 的 `api-key` 写法；官方文档为 `Authorization: Bearer sk-xxxxx`
  - 模型：`agnes-2.0-flash`
- 图片处理：`encode_image_to_base64()` 压缩并转 base64，控制在 2MB 以内。
- 结果后处理：`normalize_model_output()` + `parse_result()` 清洗 JSON、匹配 GB2760、计算评分。
- 密钥管理：本地 `.env`，生产环境 Streamlit Secrets，源码中不保存真实 key。

## 3. iOS 直接调用 MiMo / Agnes 的可行性

### 3.1 技术层面：可以，但不建议

- MiMo 和 Agnes 都提供标准 HTTPS REST API，兼容 OpenAI 格式，原生 iOS（Swift/URLSession）或跨平台框架（Flutter/React Native）都可以发起请求。
- 它们没有提供专用的 iOS SDK，也没有 Apple 原生的 framework，开发者需要自行封装 HTTP 调用。
- 请求体格式与现有后端一致：POST JSON，携带 base64 图片和 system prompt。

### 3.2 主要障碍

| 维度 | 说明 |
|---|---|
| **密钥安全** | API Key 是计费凭证，一旦打包进 App，可被反编译/抓包提取。 |
| **配额盗用** | 泄露的 key 会被他人调用，导致额度/余额被盗。 |
| **密钥轮换** | 客户端 key 无法灵活更新，泄露后只能强制升级 App。 |
| **后处理逻辑** | GB2760 评分、健康建议、字段清洗等逻辑需要移植到 iOS，维护成本高。 |
| **模型路由** | 多模型降级、超时重试、错误码处理需要 iOS 端完整实现。 |
| **合规/隐私** | 直接调用意味着图片直传第三方，隐私政策和用户协议需要重新评估。 |

## 4. API Key 安全方案

### 4.1 绝对不要硬编码

- 2025-2026 年多份研究报告指出，iOS App 中硬编码 API Key 是系统性问题，26% 的 LLM 类 App 存在密钥泄露。
- 任何放在 ipa 包里的字符串（包括 `Info.plist`、Swift 常量、Keychain 初始值）都可能被提取。

### 4.2 可选安全等级

| 方案 | 安全性 | 复杂度 | 适用场景 |
|---|---|---|---|
| **A. 硬编码 / xcconfig / plist** | 低 | 低 | 仅原型，禁止生产 |
| **B. Keychain 存储** | 中 | 中 | 适合短期会话 token，不适合长期 API Key |
| **C. 后端代理 + 短期 token** | 高 | 中 | 推荐方案 |
| **D. 后端代理 + Apple DeviceCheck** | 更高 | 高 | 高安全/付费场景 |

### 4.3 推荐做法

1. **App 不持有 MiMo/Agnes 真实 API Key**。
2. App 只保存一个「调用自己后端的短期 token / session token」。
3. 后端统一保管 MiMo/Agnes key，并做：
   - 用户身份校验
   - 请求限流
   - 日志审计
   - 模型路由与降级
   - key 泄露后一键轮换
4. 传输全程 HTTPS，后端可额外启用证书固定（certificate pinning）降低中间人攻击风险。

## 5. 复用现有 Python 后端需要新增的接口

当前后端是 Streamlit 应用，没有暴露 REST API。如果要让 iOS App 复用，需要拆分出一个 API 层。

### 5.1 建议新增端点

| 端点 | 方法 | 功能 | 说明 |
|---|---|---|---|
| `/api/v1/scan` | POST | 上传图片，返回识别结果 | 复用 `encode_image_to_base64` → `call_api_with_fallback` → `normalize_model_output` → `parse_result` 链路 |
| `/api/v1/health-profiles` | GET/POST/PUT | 读取/保存用户健康档案 | 移动端需要同步用户疾病、过敏、人群标签 |
| `/api/v1/history` | GET/POST | 查询/写入扫描历史 | 与现有 `utils/history.py` 和数据库对接 |
| `/api/v1/auth/token` | POST | App 登录/换取 session token | 可用简单 device-id + 验证码，或 Apple Sign-In |
| `/api/v1/compare` | POST | 多产品对比 | 复用 `pages/compare.py` 逻辑 |

### 5.2 需要重构的部分

- 把 `utils/api.py` 中依赖 `st.error()` / `st.toast()` 的 UI 耦合去掉，改为抛出异常或返回错误结构。
- 把 `get_api_key()` 中的 `st.secrets` 分支保留给 Streamlit Cloud，同时为 API 模式增加环境变量读取。
- 将业务逻辑（评分、建议、历史、档案）从 Streamlit pages 拆到 services 层，供 API 和 Web 共享。

## 6. Streamlit 后端是否适合移动端

### 6.1 结论：不适合直接作为移动端后端

| 维度 | Streamlit 后端 | 移动 App 所需后端 |
|---|---|---|
| **接口形态** | 页面渲染 + 会话状态 | REST/JSON API |
| **并发模型** | 单脚本重跑，状态存 session | 无状态、可水平扩展 |
| **认证授权** | 无 | 需要用户鉴权、限流 |
| **移动端调用** | 只能内嵌 WebView，体验差 | 原生请求，可控 |
| **部署平台** | Streamlit Cloud / 自托管 | 云函数 / VPS / 容器 |

### 6.2 可行但次优的方案

- 在 Streamlit 应用里用 `st.query_params` + 自定义组件提供一个「伪 API」：iOS 通过 WebView 或内嵌浏览器调用。
- 缺点：无法推送、无法离线、体验割裂、安全难控，不推荐。

## 7. 推荐后端架构

### 7.1 总体思路

**保留现有 Streamlit Web 端，新增一个轻量 Python API 服务供 iOS 调用。**

```
┌─────────────┐      HTTPS       ┌─────────────────────┐
│   iOS App   │ ───────────────▶ │  Python API Server  │
└─────────────┘                  │  (FastAPI/Flask)    │
                                 │  - auth / rate limit│
                                 │  - image scan       │
                                 │  - history / profile│
                                 └──────────┬──────────┘
                                            │
                       ┌────────────────────┼────────────────────┐
                       ▼                    ▼                    ▼
                 ┌─────────┐        ┌──────────┐        ┌──────────┐
                 │  MiMo   │        │  Agnes   │        │ Qwen/GLM │
                 └─────────┘        └──────────┘        └──────────┘
```

### 7.2 技术栈建议

| 组件 | 建议 | 理由 |
|---|---|---|
| API 框架 | FastAPI | 异步、自动生成 OpenAPI 文档、生态成熟 |
| 认证 | JWT / simple token + Apple Sign-In（可选） | 移动场景标准做法 |
| 图片上传 | multipart/form-data | 比 base64 节省 33% 流量 |
| 部署 | Fly.io / Render / 国内云服务器 | 轻量、低成本、易扩展 |
| 数据库 | 继续 SQLite 或迁移 PostgreSQL | 用户量小时 SQLite 够用 |
| 密钥管理 | 环境变量 + 云 Secret 服务 | 不进入源码和镜像 |

### 7.3 迁移路径

1. **第一阶段**：把 `utils/api.py` 中的核心调用逻辑抽象成纯函数，去掉 `streamlit` 依赖。
2. **第二阶段**：新建 `api/` 目录，用 FastAPI 实现 `/api/v1/scan`。
3. **第三阶段**：逐步迁移历史、档案、对比接口。
4. **第四阶段**：Web 端和 API 端共用 `services/` 层，Streamlit 只负责 UI。

## 8. 风险与建议

| 风险 | 建议 |
|---|---|
| Agnes 目前免费但商业模式未定 | 保留多模型路由，避免锁定单一供应商 |
| MiMo Token Plan 有配额上限 | 后端做配额统计与限流，防止单用户刷爆 |
| 图片上传包含敏感信息 | 服务端不持久化原始图片，仅保留识别结果；隐私政策需说明 |
| 客户端直传第三方合规风险 | 统一走后端代理，便于审计和用户告知 |

## 9. 结论

1. **iOS 可以直接调用 MiMo/Agnes，但生产环境不应直接调用。**
2. **API Key 绝对不能硬编码在客户端**，必须通过后端代理或短期 token 机制保护。
3. **现有 Python 后端逻辑可以复用**，但需要剥离 Streamlit UI 依赖，新增 REST API 层。
4. **当前 Streamlit 后端不适合直接服务移动 App**，建议新增 FastAPI 服务。
5. **推荐架构**：Streamlit 负责 Web，FastAPI 负责 iOS/API，共用底层 services 和模型调用逻辑。

## 10. 参考来源

- MiMo 官方文档：首次调用 API <https://mimo.mi.com/docs/zh-CN/quick-start/summary/first-api-call>
- MiMo Token Plan 快速接入 <https://platform.xiaomimimo.com/docs/en-US/tokenplan/quick-access>
- Agnes AI 官方中文文档：概述 <https://wiki.agnes-ai.com/zh-Hans/docs/overview>
- Agnes AI API 生态介绍 <https://wavespeed.ai/blog/posts/what-is-agnes-ai/>
- iOS API Key 安全最佳实践 <https://logdog.app/blog/ios-techniques-to-inject-api-keys/>
- iOS 移动 API 安全框架 <https://www.iteratorshq.com/blog/building-mobile-api-security-protecting-data-endpoints-and-monetization-logic/>
- LLM API 凭证泄露研究 <https://www.helpnetsecurity.com/2026/06/22/llm-api-credential-leakage-ios-apps/>
- CORS 机制说明（MDN）<https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>
