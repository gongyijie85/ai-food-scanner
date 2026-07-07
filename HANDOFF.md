# 项目交接文档

> 本文档供新成员或接手开发者使用，帮助快速理解项目架构、部署流程和常见问题。

---

## 1. 项目概述

**项目名称**：拍了就懂 · AI 食品配料表识别工具  
**目标用户**：3.1 亿中国老年人 + 8300 万慢病人群  
**核心价值**：拍照配料表 → 3 秒语音播报"能不能吃"  
**技术栈**：Python 3.10+ / Streamlit / MiMo Vision API  
**部署方式**：Streamlit Cloud（公开链接）  

---

## 2. 项目结构

```
ai-food-scanner/
├── app.py                      # 主程序（2100+ 行，单文件架构）
├── requirements.txt            # Python 依赖（版本已锁定）
├── .env.example                # 环境变量模板
├── .streamlit/
│   ├── config.toml             # Streamlit 配置（XSRF/CORS/上传限制）
│   └── style.css               # 适老化样式（外置，缓存加载）
├── data/                       # 数据文件（GB 2760/疾病/过敏原/药物）
│   ├── gb2760_risk.csv         # 添加剂风险分级表
│   ├── common_diseases.json    # 常见疾病数据
│   ├── allergens.json          # 过敏原数据
│   ├── common_drugs.json       # 常见药物数据
│   ├── drug_food_conflicts.json # 药物-食物冲突数据
│   ├── history.json            # 最近 5 条历史记录（轻量）
│   └── history_full.json       # 完整历史快照（最多 20 条）
├── tests/                      # 单元测试（pytest）
│   └── test_core.py            # 核心函数测试
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD 工作流（lint/test/security/build）
├── README.md                   # 项目说明
├── CHANGELOG.md                # 版本变更记录
├── LEGAL_REVIEW.md             # 法律合规评估
├── USER_AGREEMENT.md           # 用户协议
└── PRIVACY_POLICY.md           # 隐私政策
```

---

## 3. 关键配置

### 3.1 环境变量

| 变量名 | 用途 | 本地配置 | 生产配置 |
|--------|------|----------|----------|
| `MIMO_API_KEY` | MiMo Vision API 密钥 | `.env` 文件 | Streamlit Cloud Secrets |
| `AGNES_API_KEY` | Agnes 降级备用 API 密钥（可选） | `.env` 文件 | Streamlit Cloud Secrets |
| `DEBUG` | 调试模式开关 | 本地设为 `1` 可看调试信息 | **生产环境必须为 `0` 或不设置** |

### 3.2 Streamlit 配置（`.streamlit/config.toml`）

```toml
[server]
maxUploadSize = 5              # 上传文件大小限制（MB）
enableXsrfProtection = true    # XSRF 保护（生产必须开启）
enableCORS = true              # CORS 保护（生产必须开启）

[browser]
gatherUsageStats = false       # 禁用使用统计（隐私保护）
```

### 3.3 日志配置

- **生产环境**：日志级别 `INFO`，输出到控制台
- **本地调试**：设置 `DEBUG=1`，日志级别 `DEBUG`，输出详细请求/响应信息
- **日志内容**：API 调用耗时、图片大小、HTTP 状态码、错误详情

---

## 4. 部署步骤

### 4.1 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/gongyijie85/ai-food-scanner.git
cd ai-food-scanner

# 2. 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 配置 API 密钥
cp .env.example .env
# 编辑 .env，填入 MIMO_API_KEY

# 4. 启动
streamlit run app.py
# 浏览器打开 http://localhost:8501
```

### 4.2 Streamlit Cloud 部署

1. Fork 仓库到你的 GitHub
2. 登录 https://share.streamlit.io/
3. 点击 "New app" → 选择仓库 + `app.py`
4. **Advanced settings → Secrets** 添加：
   ```toml
   MIMO_API_KEY = "tp-你的密钥"
   ```
5. 点击 Deploy，等待 2-3 分钟
6. 获得公开链接：`https://<用户名>-ai-food-scanner.streamlit.app`

### 4.3 部署后验证

- [ ] 打开公开链接，确认页面正常加载
- [ ] 上传测试图片，确认识别功能正常
- [ ] 点击"语音播报"，确认能听到中文语音
- [ ] 检查浏览器控制台无报错
- [ ] 检查 Streamlit Cloud 日志无错误

---

## 5. 回滚步骤

### 5.1 代码回滚

```bash
# 查看历史版本
git log --oneline

# 回滚到指定版本
git checkout v0.3.5  # 或指定 commit hash

# 推送到远程（谨慎操作）
git push origin HEAD
```

### 5.2 Streamlit Cloud 回滚

1. 登录 https://share.streamlit.io/
2. 进入应用管理页面
3. 点击 "Reboot" → 选择要回滚的 Git commit
4. 等待重新部署完成
5. 验证公开链接正常

---

## 6. 常见故障排查

### 6.1 API 返回 401（密钥无效）

**症状**：页面提示"API 密钥无效或请求被拒绝"  
**原因**：
- MiMo API key 过期或被撤销
- Streamlit Cloud Secrets 未配置或配置错误
- 本地 `.env` 文件未正确加载

**排查步骤**：
1. 检查 Streamlit Cloud Secrets 是否正确配置 `MIMO_API_KEY`
2. 登录 MiMo Token Plan 控制台确认 key 状态
3. 本地测试：`python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('MIMO_API_KEY')[:10])"`
4. 若 key 失效，立即轮换：revoke 旧 key → 生成新 key → 更新 Secrets

### 6.2 语音播报无声音

**症状**：点击"点击播报"按钮无反应  
**原因**：
- 浏览器不支持 SpeechSynthesis API（少数老旧浏览器）
- 移动端浏览器自动播放限制（需用户手势触发）
- 系统音量为 0 或静音

**排查步骤**：
1. 检查浏览器控制台是否有 `speechSynthesis` 相关错误
2. 确认浏览器支持：https://caniuse.com/speech-synthesis
3. 移动端：确认用户已点击按钮（手势触发）
4. 检查系统音量和音频输出设备

### 6.3 上传图片慢

**症状**：上传图片后等待时间过长（>15 秒）  
**原因**：
- 图片过大（>2MB）
- 网络延迟
- API 服务端响应慢

**优化措施**：
- 图片自动压缩到 768px / quality 75
- base64 体积控制在 200KB 以内
- API 超时设置为 30 秒
- 若持续慢，检查网络环境或切换 API 集群

### 6.4 识别结果不准确

**症状**：添加剂识别遗漏或误判  
**原因**：
- 图片模糊或光线不足
- 配料表字体过小
- AI 模型理解偏差

**排查步骤**：
1. 检查上传图片质量（建议 768px 以上）
2. 对比 `data/gb2760_risk.csv` 确认添加剂是否在库中
3. 查看 DEBUG 模式下的 API 原始响应
4. 若系统性问题，反馈给 MiMo 团队优化模型

### 6.5 历史记录丢失

**症状**：刷新页面后历史记录消失  
**原因**：
- Streamlit Cloud 多用户共享文件系统，重启后数据丢失
- 当前使用 JSON 文件存储，不适合生产环境

**临时方案**：
- 历史记录仅作为演示功能，不保证持久化
- 用户如需保留结果，可截图保存

**长期方案**：
- 迁移到 SQLite（单机）或 PostgreSQL（多用户）
- 按用户 session 隔离数据

---

## 7. 数据持久化说明

### 7.1 当前方案（JSON 文件）

**存储位置**：
- `data/history.json`：最近 5 条历史记录（轻量）
- `data/history_full.json`：完整历史快照（最多 20 条）

**限制**：
- Streamlit Cloud 多用户共享文件系统，所有用户看到相同的历史记录
- 容器重启后数据丢失
- 无用户隔离，存在隐私风险

**适用场景**：
- 初赛 Demo 阶段够用
- 单机本地测试

### 7.2 迁移预案（SQLite/PostgreSQL）

**迁移时机**：
- 正式运营前必须迁移
- 用户量 >100 时建议迁移

**SQLite 方案（单机）**：
```python
# 表结构
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    product_name TEXT,
    ingredients TEXT,
    additives TEXT,
    score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# 迁移脚本思路
# 1. 读取 data/history_full.json
# 2. 解析 JSON 并插入 SQLite
# 3. 修改 load_history() / save_history() 使用 SQLite
```

**PostgreSQL 方案（多用户）**：
```python
# 表结构
CREATE TABLE history (
    id SERIAL PRIMARY KEY,
    user_id TEXT,  # 从登录态或 session 获取
    session_id TEXT,
    product_name TEXT,
    ingredients JSONB,
    additives JSONB,
    score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# 迁移脚本思路
# 1. 创建 PostgreSQL 数据库和表
# 2. 读取 JSON 文件并批量插入
# 3. 修改应用代码使用 psycopg2 / SQLAlchemy
# 4. 按 user_id 隔离数据
```

---

## 8. 安全注意事项

### 8.1 API 密钥管理

- **禁止**：将 API key 写入代码、README、commit message、聊天记录
- **必须**：通过环境变量或 Streamlit Cloud Secrets 注入
- **建议**：每 90 天轮换一次 key，怀疑泄露时立即轮换

### 8.2 XSS 防护

- 所有动态文本（AI 返回内容、历史记录）使用 `_safe()` 函数转义
- 语音按钮的 `onclick` 文本先 HTML 转义再 JS 转义
- 避免直接拼接用户输入到 HTML

### 8.3 文件上传安全

- 文件大小限制：5MB
- 文件格式校验：仅允许 jpg/png
- 图片内容校验：`Image.open().verify()` 防止恶意文件

### 8.4 生产环境配置

- `DEBUG=0` 或不设置
- `enableXsrfProtection=true`
- `enableCORS=true`
- `maxUploadSize=5`
- 日志级别 `INFO`

---

## 9. 测试与 CI/CD

### 9.1 单元测试

```bash
# 运行测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

**测试覆盖**：
- `normalize_additive()`：添加剂等级判定
- `compute_score_from_additives()`：评分计算
- `check_drug_food_conflicts()`：药物-食物冲突检测
- `parse_result()`：JSON 解析与兜底

### 9.2 CI/CD 工作流（`.github/workflows/ci.yml`）

**触发条件**：push / PR 到 main 分支  
**步骤**：
1. 代码质量检查（black / isort / flake8）
2. 单元测试（pytest）
3. 安全扫描（bandit / safety）
4. 构建验证（语法检查 + 数据文件校验）

**查看结果**：GitHub → Actions → 选择工作流运行记录

---

## 10. 待办事项（TODO）

### 10.1 短期（初赛阶段）

- [x] P0：解决用户反馈（上传慢、注意标签、语音播报）
- [x] P0：修复 XSS 漏洞
- [x] P1：核心函数单元测试
- [x] P1：CSS 外置并缓存
- [x] P2：CI/CD 工作流
- [x] P2：日志与监控
- [x] P2：安全部署清单
- [ ] P2：数据持久化文档（本文档已完成）
- [ ] 优化 Streamlit Cloud 公开链接稳定性
- [ ] 收集真实用户反馈并迭代

### 10.2 中期（正式运营前）

- [ ] 迁移历史记录到 SQLite/PostgreSQL
- [ ] 实现用户登录态（按用户隔离数据）
- [ ] 添加 CSP/HSTS 安全头（通过反向代理）
- [ ] 性能优化：流式响应、缓存命中率提升
- [ ] 多语言支持（英文/日文）

### 10.3 长期（产品化）

- [ ] 微信小程序版
- [ ] 视频配料表识别
- [ ] 个性化推荐引擎
- [ ] 社区功能（用户分享健康食谱）

---

## 11. 联系方式

- **项目负责人**：龚益杰
- **GitHub**：https://github.com/gongyijie85/ai-food-scanner
- **TRAE 论坛 Demo 帖**：https://forum.trae.cn/t/topic/51391
- **公开体验链接**：https://gongyijie85-ai-food-scanner.streamlit.app

---

## 12. 附录

### 12.1 关键函数说明

| 函数名 | 位置 | 作用 |
|--------|------|------|
| `normalize_additive()` | app.py:876 | 判定添加剂等级（A/B/C） |
| `compute_score_from_additives()` | app.py:906 | 计算安全评分 |
| `check_drug_food_conflicts()` | app.py:928 | 检测药物-食物冲突 |
| `parse_result()` | app.py:838 | 解析 API 返回的 JSON |
| `call_api()` | app.py:476 | 统一 API 调用入口 |
| `encode_image_to_base64()` | app.py:417 | 图片压缩与 base64 编码 |
| `speak_text()` | app.py:244 | 浏览器语音播报 |

### 12.2 数据文件说明

| 文件 | 格式 | 作用 |
|------|------|------|
| `gb2760_risk.csv` | CSV | GB 2760 添加剂风险分级表 |
| `common_diseases.json` | JSON | 常见疾病数据（糖尿病/高血压等） |
| `allergens.json` | JSON | 过敏原数据 |
| `common_drugs.json` | JSON | 常见药物数据 |
| `drug_food_conflicts.json` | JSON | 药物-食物冲突数据 |

### 12.3 版本历史

查看 `CHANGELOG.md` 获取完整版本变更记录。

---

**最后更新**：2026-07-02  
**文档版本**：v1.0
