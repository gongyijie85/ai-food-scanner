# 工作区提交/忽略/清理清单

## 当前状态

- 本地 `main` 已做到 **v0.15.1**，远程 `origin/main` 仍停在 **v0.10.18**
- 已跟踪文件有大量修改：核心代码、页面、样式、测试、文档
- 未跟踪文件较多：临时脚本、测试产物、诊断脚本、截图 base64 产物、本地数据库等

## 提交策略

使用现有仓库 `gongyijie85/ai-food-scanner`，将 v0.15.1 的改动拆成 2-3 个逻辑 commit 后推送：

1. `feat: P1 优化 - SQLite 历史记录、Pro 版本集中控制、健康警告修复`
2. `feat: P1 优化 - 适老化样式、页面拆分、无障碍与 UI 调整`
3. `chore: 更新 CHANGELOG 和 README 到 v0.15.1`

推送前必须确认：源码中无 API key、无 `DEBUG=true`、无 `.streamlit/secrets.toml`。

## .gitignore 需要新增

```gitignore
# 本地 SQLite 数据库（含用户扫描记录，不能入仓）
data/*.db

# 截图 base64 / 分片 / 上传产物
screenshots/*_b64.txt
screenshots/*.json
screenshots/upload_chunks/
screenshots/test_100k.txt

# 论坛/图片修复一次性脚本
check_post_content.py
fix_forum_*.py
fix_homepage_image.py
fix_update_logs.py
home_b64.txt

# 本地服务/上传辅助脚本（含个人路径或 PAT）
serve_*.py
upload_*.py
upload_*.js
start.ps1

# API 诊断脚本（含真实 key 风险）
tests/diagnose_api*.py
```

## 需要保留并提交的文件

- 新增业务模块：
  - `components/direct_conclusion.py`
  - `components/family_share.py`
  - `components/pro_lock.py`
  - `pages/compare.py`
  - `pages/medication.py`
  - `repositories/health_profile_repo.py`
  - `utils/database.py`
- 研究文档：`research/` 目录下的正式报告
- 测试更新：`tests/test_core.py`、`tests/test_profile.py` 等

## 需要删除或移出仓库的文件

- 一次性修复脚本：`fix_forum_*.py`、`fix_homepage_image.py`、`fix_update_logs.py`、`check_post_content.py`
- 本地服务脚本：`serve_demo_assets.py`、`serve_screenshots.py`
- 上传辅助脚本：`upload_new_demo_images.py`、`upload_new_screenshots.py`、`upload_screenshots.py`、`upload_via_browser.js`、`upload_with_cookie.py`
- API 诊断脚本：`tests/diagnose_api.py`、`tests/diagnose_api2.py`
- 截图产物：仅保留展示用的原始 PNG，删除 b64/JSON/chunk 文件
- `start.ps1`：建议保留在个人工作区，但不提交到仓库

## 提交前检查清单

- [ ] 运行 `pytest tests/`，核心用例通过
- [ ] 运行 `python -m compileall .` 或 CI 的 `py_compile`
- [ ] 运行 `git diff` 检查源码中无 API key 暴露
- [ ] 确认 `.env` 在 `.gitignore` 中且未提交
- [ ] 确认 `.streamlit/secrets.toml` 未提交
- [ ] 确认 `.env.example` 中 `DEMO_MODE=false`
- [ ] 确认生产环境开启 XSRF/CORS 保护

## 推送后验证

- [ ] 观察 Streamlit Cloud 构建日志是否成功
- [ ] 打开公开体验链接，走通拍照/上传 → 识别 → 结果页流程
- [ ] 验证历史记录写入与读取正常
- [ ] 验证语音播报正常播放
