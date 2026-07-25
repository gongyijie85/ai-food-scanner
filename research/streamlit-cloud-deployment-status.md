# Streamlit Cloud 部署状态检查报告

- 检查时间：2026-07-23
- 检查人：AI agent
- 关联 issue：#10（map #4）

## 1. 公开链接当前状态

URL：https://gongyijie85-ai-food-scanner-app-w4mpmt.streamlit.app/

- HTTP 状态：200 OK
- Server：nginx/1.29.5
- Content-Type：text/html; charset=utf-8
- 返回内容：Streamlit 应用壳（React app shell），说明服务在线、可访问
- 注意：Streamlit Cloud 免费版应用在无访问一段时间后会进入睡眠，首次访问可能需要 10-30 秒唤醒。当前请求返回的是正常应用壳，未出现 "Sleeping" 或错误页面。

结论：**应用在线、可访问**。

## 2. GitHub 仓库关联证据

通过 `gh api repos/gongyijie85/ai-food-scanner/hooks` 检查：

- Webhook ID：647867180
- 名称：web
- 状态：active
- 目标 URL：https://share.streamlit.io/hook
- last_response：unused

结论：**仓库仍与 Streamlit Cloud 保持关联**，推送 main 分支后会触发 Streamlit Cloud 自动拉取部署。

## 3. 当前代码版本差距（重要阻塞）

本地 main 分支已推进到 v0.15.1，但远程 origin/main 仍停留在 v0.10.18。具体差异：

- 本地最新：v0.15.1（2026-07-23）
- 远程最新：v0.10.18（初赛提交版本）
- 状态：大量修改未推送（约 25+ 文件已修改，多个新增文件未跟踪）

这意味着 Streamlit Cloud 当前部署的是旧版本 v0.10.18，而非本地最新的 v0.15.1。

## 4. Streamlit Cloud 所需 Secrets 清单

根据 `.env.example`、`utils/api.py` 和 README 部署章节，生产环境（Streamlit Cloud）需要在 Settings → Secrets 中配置：

### 必需
- `MIMO_API_KEY`：MiMo Token Plan API 密钥，主识别模型

### 推荐（可选但建议配置）
- `AGNES_API_KEY`：Agnes 备用模型密钥，MiMo 失败时自动降级

### 可选
- `DEMO_MODE=true`：演示模式，返回模拟数据，无需真实 API（仅用于评委演示或测试）
- `QWEN_API_KEY` / `QWEN_API_URL` / `QWEN_MODEL_NAME`：通义千问多模态模型
- `ZHIPU_API_KEY` / `ZHIPU_API_URL` / `ZHIPU_MODEL_NAME`：智谱 GLM 多模态模型

### 最小可运行配置
```toml
MIMO_API_KEY = "tp-你的密钥"
```

### 推荐配置
```toml
MIMO_API_KEY = "tp-你的密钥"
AGNES_API_KEY = "sk-你的密钥"
```

## 5. 安全配置检查清单

根据 `.streamlit/config.toml` 和 README 安全部署检查清单：

- [x] `enableXsrfProtection = true`
- [x] `enableCORS = true`
- [x] `maxUploadSize = 5`
- [x] `gatherUsageStats = false`
- [ ] DEBUG 禁用：生产环境不要设置 `DEBUG=1`
- [ ] 密钥通过 Secrets 注入，不在代码中写死
- [ ] 定期检查协作者和密钥轮换

## 6. 重新部署 / 唤醒步骤

### 如果只是唤醒睡眠中的应用
直接访问公开链接即可，Streamlit Cloud 会自动唤醒。

### 如果要更新到最新版本（v0.15.1）
1. 推送本地 main 到远程：
   ```bash
   git push origin main
   ```
2. Streamlit Cloud 会通过 webhook 自动检测推送并重新拉取部署。
3. 登录 https://share.streamlit.io/，进入应用管理页，确认：
   - Repository：gongyijie85/ai-food-scanner
   - Branch：main
   - Main file path：app.py
4. 检查 Settings → Secrets，确认已配置 `MIMO_API_KEY`（和可选的 `AGNES_API_KEY`）。
5. 点击 "Reboot" 或等待自动部署完成。
6. 访问公开链接，验证是否正常运行。

### 如果应用无法启动
1. 在 Streamlit Cloud 管理页查看 "Manage app" → 日志（Logs）。
2. 常见原因：
   - Secrets 未配置或密钥错误
   - 依赖缺失（检查 requirements.txt）
   - 新代码引入的语法/导入错误
3. 修复后重新推送或点击 "Reboot"。

## 7. 主要阻塞项与建议

1. **版本差距**：本地 v0.15.1 未推送到 origin/main，Streamlit Cloud 运行的是旧版本。需要先 `git push origin main`。
2. **未跟踪文件**：新增文件（如 `pages/compare.py`、`pages/medication.py`、`utils/database.py` 等）需要纳入 git 跟踪并推送，否则 Cloud 部署会缺失。
3. **Secrets 状态未知**：本次检查无法直接读取 Streamlit Cloud 后台的 Secrets，需要人工登录确认 `MIMO_API_KEY` 是否已配置。
4. **无自动部署流水线**：`.github/workflows/ci.yml` 只执行 CI（测试、lint、安全扫描），不自动部署到 Streamlit Cloud。部署依赖 Streamlit Cloud 的 GitHub 集成自动拉取。

## 8. 结论

- 公开链接 **在线、可访问**（HTTP 200）。
- GitHub 仓库 **仍与 Streamlit Cloud 关联**（webhook 活跃）。
- 需要人工确认 Streamlit Cloud Secrets 中是否配置了 `MIMO_API_KEY`。
- 当前部署的是旧版本 v0.10.18；要更新到最新版本，需要先推送本地 main 到远程。
