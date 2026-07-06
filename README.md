# 拍了就懂 · AI 食品配料表识别工具

> 老人打开手机，拍照配料表，**3 秒内语音读出**"这块食品能不能吃"。

![版本](https://img.shields.io/badge/version-0.4.5-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-green) ![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

## 一句话介绍

面向 **3.1 亿中国老年人** 和 **8300 万慢病人群** 的食品配料表识别工具。
拍照 → 自动 OCR → 三色风险标注 → 语音播报。**3 步 3 秒**。

## 最新更新

- **v0.4.5（2026-07-06）**：修复扫描页上传图片后无法滚动的严重问题（根因：Streamlit `layout=centered` 下 `.stApp` 被设为 `position:absolute;height:100vh`，CSS 覆盖后内容可正常滚动）；修复结果页 `voice-float-bar` 和 `bottom-action-bar` 的 div 无法包裹 Streamlit 组件导致样式失效的问题，改用 `st.container()` + CSS `:has` 选择器；修复顶部导航栏 sticky 失效；移除 `load_css()` 的 `@st.cache_data` 缓存，确保 CSS 修改即时生效。
- **v0.4.4（2026-07-05）**：重构扫描页为卡片式布局，移除全屏黑屏遮罩，改为内联预览与「重新选择 / 使用照片」操作；优化响应式布局，桌面端与手机端分别适配。
- **v0.4.3（2026-07-02）**：结果页字体进一步放大、语音播报移动端兼容修复、按画布设计稿优化结果页与首页布局，完成手机端适配。
- **v0.4.1（2026-07-02）**：历史记录页、产品详情页完整对齐 7 页适老化设计稿，新增搜索栏、风险筛选标签、扫描信息卡片与底部操作栏。

---

## 项目背景

我爸爸 79 岁，**10 年以上脑梗**。每次回家吃饭他都让我帮他看配料表。

他自己看不了：
- **看不清**（1.5-2mm 小字 + 老花眼 + 视力下降）
- **看不懂**（化学名词如"特丁基对苯二酚"是天书）
- **判不准**（不知道添加剂对脑梗有没有影响）
- **记不住**（子女叮嘱转头就忘）
- **不敢买**（只能吃白饭青菜）

**子女想买给老人，老人用不起来** — 这是适老化 App 最深的痛。

---

## 三大核心能力

| 能力 | 说明 |
|------|------|
| OCR 识别 | 拍照即可识别小字号配料表 |
| 添加剂分类 | 自动识别 GB 2760 添加剂（含 INS 号） |
| 三色风险标注 | 绿/黄/红 + 图标 + 文字三重编码，色盲友好 |
| 个性化建议 | 根据用户健康档案（糖尿病/高血压/过敏等）给建议 |
| 药物-食物冲突 | 根据健康档案用药，提示配料中的潜在冲突 |
| 语音播报 | 老人不用看，AI 读出来（Microsoft Yaoyao 1.0x） |
| 历史记录 | 保存最近扫描，支持详情回看 |
| 健康档案 | 6 类慢病/过敏/用药档案，个性化风险提示 |

---

## 适老化设计

- **18pt 最小字号**（国标要求 ≥ 14pt）
- **56px 大按钮**（国标要求 ≥ 48px）
- **高对比度色块**（绿/黄/红三色 + 图标 + 文字）
- **3 步极简流程**（拍照 → 识别 → 听结果）
- **零配置健康档案**（默认 脑梗 + 高血压）

---

## 差异化（对比 5 大主流竞品）

Yuka（8000 万用户）、薄荷健康、营养盒子、Foodvisor、MyFitnessPal 都有 OCR，但**5 大共性缺口**：

1. ❌ 没有真正的"适老化"（界面复杂，字体小）
2. ❌ 没有"语音播报"（只显示文字）
3. ❌ 没有"中国 GB 标准本土化"（用国外添加剂库）
4. ❌ 没有"六大人群定制"（一刀切建议）
5. ❌ 没有"3 秒极简流程"（5 步以上操作）

**我们全部补齐** ✅

---

## 技术栈

| 层 | 选型 | 原因 |
|----|------|------|
| 多模态 API | MiMo Vision (mimo-v2.5) | 小米自研，Token Plan 价格低，已验证支持图片输入 |
| 框架 | Streamlit | Python 一键 Web 化，开发快，演示友好 |
| 适老化样式 | 自研 CSS | 18pt 最小字号、48pt 触摸区域、高对比度 |
| 语音播报 | 浏览器原生 SpeechSynthesis | 零依赖，Microsoft Yaoyao 女声 |

**成本测算**：
- 单次识别约 ¥0.0023（MiMo Vision 定价）
- 1 万日活 × 5 次/天 = ¥1150/月
- 配合缓存可降至 ¥300/月

---

## 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/gongyijie85/ai-food-scanner.git
cd ai-food-scanner

# 2. 安装依赖（推荐清华源）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 配置 API 密钥（推荐 .env）
cp .env.example .env
# 编辑 .env，填入你的 MiMo Token Plan 密钥：
# MIMO_API_KEY=tp-你的密钥

# 4. 启动
streamlit run app.py
# 浏览器打开 http://localhost:8501
```

---

## 部署（Streamlit Cloud）

1. Fork 或 clone 本仓库到你自己的 GitHub
2. 登录 https://share.streamlit.io/
3. 点击 "New app" → 选择本仓库 + `app.py`
4. **Advanced settings → Secrets** 填入：
   ```toml
   MIMO_API_KEY = "tp-你的密钥"
   ```
5. 点击 Deploy，等待 2-3 分钟即可获得公开链接

**公开链接格式**：`https://<你的用户名>-ai-food-scanner.streamlit.app`

### 安全提示（必读）

- **API 密钥必须通过 Streamlit Cloud Secrets 配置**，不要把真实 key 写入代码、README、issue、commit message 或聊天记录；
- **`.env` 文件仅用于本地开发**，已被 `.gitignore` 排除，提交前务必确认没有误加入仓库；
- **生产环境不要开启 `DEBUG=1`**，否则页面会展示 key 长度与末 4 位等调试信息；
- **定期检查 GitHub 仓库协作者和 Streamlit Cloud Collaborators**，移除不认识的人员；
- **建议定期轮换 API key**，若怀疑密钥泄露应立即 revoke 并重新生成。

### 安全部署检查清单

部署到生产环境前，请逐项确认：

- [ ] **Secrets 配置**：API key 通过 Streamlit Cloud Secrets 或环境变量注入，未写入代码
- [ ] **DEBUG 禁用**：生产环境 `DEBUG` 环境变量未设置或为 `0`
- [ ] **XSRF/CORS 保护**：`.streamlit/config.toml` 中 `enableXsrfProtection=true`、`enableCORS=true`
- [ ] **上传限制**：`maxUploadSize` 设置为 `5`（MB），防止大文件攻击
- [ ] **依赖安全**：运行 `pip-audit` 无 Critical/High 漏洞
- [ ] **日志级别**：生产环境日志级别为 `INFO`，非 `DEBUG`
- [ ] **HTTPS**：Streamlit Cloud 默认启用 HTTPS；若自建部署，确保反向代理配置 SSL
- [ ] **安全头**（自建部署）：通过 Nginx/Cloudflare 添加 `X-Content-Type-Options`、`X-Frame-Options`、`Content-Security-Policy`
- [ ] **密钥轮换**：每 90 天轮换一次 API key，或怀疑泄露时立即轮换
- [ ] **访问控制**：GitHub 仓库协作者和 Streamlit Cloud Collaborators 列表已审查

---

## 法律合规提示

- **服务定位**：本仓库当前为参赛技术展示 Demo，不构成医疗诊断、治疗建议或消费推荐。
- **跨境传输**：识别服务部署于境外服务器（Streamlit Cloud / MiMo / Agnes），上传图片及识别结果可能涉及跨境数据传输。
- **备案评估**：初赛 Demo 阶段通常无需 ICP 备案、算法备案、互联网药品信息服务备案；详见 `LEGAL_REVIEW.md`。
- **数据保护**：Demo 不保存用户上传图片，健康档案与历史记录仅在当前浏览器会话中使用，关闭页面后自动清空。
- **正式运营前**：务必聘请专业律师或合规顾问重新评估。

---

## 项目结构

```
ai-food-scanner/
├── app.py                  # 主程序（Streamlit）
├── requirements.txt        # Python 依赖
├── LEGAL_REVIEW.md         # 法律合规评估记录
├── USER_AGREEMENT.md       # 用户协议及免责声明
├── PRIVACY_POLICY.md       # 隐私政策
├── .streamlit/
│   └── config.toml         # Streamlit 配置
├── pages/                  # UI 设计稿（HTML）
│   ├── home.html
│   ├── camera.html
│   ├── result.html
│   ├── health-profile.html
│   ├── history.html
│   ├── detail.html
│   └── onboarding.html
├── test_images/            # 真实配料表测试图片（gitignore 排除）
│   └── README.md           # 图片来源说明
├── download_test_images.py # 测试图片下载脚本
└── README.md
```

---

## 演示视频

30 秒竖屏演示视频（1080×1920，30fps），用 [HyperFrames](https://hyperframes.heygen.com/) 制作：

- **文件**：`d:\GBT\hyperframes-demo-video\renders\hyperframes-demo-video_2026-07-02_11-05-08.mp4`
- **内容**：痛点引入 → 产品标题 → App 首页 → 识别结果 → 健康档案 → 扫码体验
- **优化点**：结尾使用真实二维码，扫码即可打开公开体验链接
- **重新渲染**：
  ```bash
  cd d:\GBT\hyperframes-demo-video
  npm run render
  ```

## 参赛信息

- **赛事**：TRAE AI 创造力大赛 - 附加赛题「智慧助老」
- **报名帖**：https://forum.trae.cn/t/topic/46161
- **Demo 帖**：https://forum.trae.cn/t/topic/51391
- **赛道**：附加赛题 - 智慧助老
- **报名通道**：专业评审（300 席）
- **一号用户**：我爸爸（79 岁，10 年以上脑梗）

---

## 路线图

- [x] v1.0 最小原型（MiMo API 验证）
- [x] v1.5 基础 UI（Streamlit 单页）
- [x] v1.8 适老化样式 + 语音播报
- [x] v1.9 英文产品名兜底 + 默认健康档案
- [x] v2.0 双模式（食品 + 保健食品）+ 强制免责
- [x] v2.0.3 Phase 0.5 合规披露 + 跨境传输 + 数据保护
- [ ] v2.5 公开链接部署
- [ ] v3.0 SQLite 历史记录
- [ ] v3.5 多模态（视频配料表）
- [ ] v4.0 微信小程序版

---

## License

MIT License

---

## 致谢

- 感谢 **TRAE IDE** 帮我完成 UI 设计 + 代码原型 + 文档撰写
- 感谢 **小米 MiMo** 提供多模态 API
- 特别感谢我爸爸 — 他是这个项目的**一号用户**和**永久顾问**
