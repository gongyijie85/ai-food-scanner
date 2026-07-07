# 拍了就懂 · AI 食品配料表识别工具

> 老人打开手机，拍照配料表，**3 秒内语音读出**"这块食品能不能吃"。

![版本](https://img.shields.io/badge/version-0.6.0-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-green) ![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

## 一句话介绍

面向 **3.1 亿中国老年人** 和 **8300 万慢病人群** 的食品配料表识别工具。
拍照 → 自动 OCR → 三色风险标注 → 语音播报。**3 步 3 秒**。

## 最新更新

- **v0.6.0（2026-07-07）**：组件化架构重构。新增 `components/` 模块，将 `app.py` 中 7 个可复用 UI 组件（顶部导航、评分英雄区、添加剂卡片、营养成分条、语音面板、个性化警告）与 14 个 SVG 图标常量抽离到独立文件；`app.py` 移除对应实现并通过 `components/` 引入，页面渲染函数保持不变；版本号升级到 v0.6.0。`py_compile` 与 `pytest` 51 项全量通过。
- **v0.5.9（2026-07-07）**：同事反馈 P0/P1 快速收尾。关键位置 emoji 统一替换为内联 SVG（返回、健康档案、首页、历史、健康档案、扫描、再扫一个、返回首页、语音播报、重新选择、使用照片、重新评分、分享给家人），避免跨平台渲染差异；统一 secondary 按钮为绿色主题；修复健康档案页 HTML 标签直接显示为文本的问题；修复结果页营养成分条字段别名；扫描页增加「拍照 / 从相册选择」入口；模型选择折叠到「高级设置」并加中文说明；移动端 body 字号从 18px 提升至 19px；补齐 `test_label.jpg` 示例图。`py_compile` 与 `pytest` 51 项全量通过。
- **v0.5.8（2026-07-07）**：加回 Agnes 作为降级备用模型（仅 MiMo 失败时自动切换，正常流程不增加延迟）；`call_api()` 参数化支持双端点；新增 `call_api_with_fallback()` + `st.toast` 切换提示；新增 `TestBuildSystemPrompt` 和 `TestCallApiWithFallback` 共 8 项测试；恢复 `.env.example` 和 CI 中的 `AGNES_API_KEY` 环境变量配置；文档统一说明 Agnes 降级定位；版本号同步到 v0.5.8。
- **v0.5.7（2026-07-07）**：执行 ponytail-audit 生产就绪清理。删除 GBT/、pages/、pages-redesign/ 等废弃目录与 README_PROTOTYPE.md、colors_and_type.css、download_test_images.py、diag_verify_ui.py；合并 `load_css()` + `inject_elder_css()` 为 `inject_css()`；内联 `_clip_path()` 与 `_show_friendly_error()`；删除 `render_home_page` 等四个单转发函数并内联设备分发；移除 `?test=1` / `?mock=1` 调试入口和 `_inject_mock_result`；`_js_attr_safe()` 改用标准库 `_safe()`；移除历史页无功能麦克风按钮。同步更新 .gitignore，py_compile、pytest 30 项全量通过。
- **v0.5.6（2026-07-07）**：双端独立页面重构。新增 `detect_device_type()`，支持 URL 参数、session_state 缓存、User-Agent 判断，默认 mobile；首页、扫描页、结果页拆分为 `*_mobile()` / `*_desktop()` 两套渲染函数，桌面端左右双栏、最大宽度 900px，移动端单列堆叠；CSS 新增 `.device-mobile` / `.device-desktop` 设备类名规则；新增 7 个 `detect_device_type()` 单元测试。py_compile、pytest 全量通过。
- **v0.5.4（2026-07-06）**：修复结果页语音按钮仍无声音问题：voice_control_panel() 与慢速重听按钮均改为 MutationObserver + data-* 属性绑定，彻底移除内联 onclick（React hydration 会剥离 onclick）；同时清理 3 处未使用变量；py_compile、pytest、diag_verify_ui、真实浏览器 TTS 出声验证全部通过。
- **v0.5.3（2026-07-06）**：执行 ponytail-audit 安全清理：删除未生效的 CSS 大字模式变量规则、简化语音面板 HTML 拼接、移除未使用的 `textwrap` import、合并重复的 TTS 诊断脚本；版本号同步升级到 v0.5.3。
- **v0.5.2（2026-07-06）**：修复语音播报无声音问题，在页面加载时预注入 TTS 命名空间；补全 API 失败时的状态更新与错误提示；清理未使用的数据校验函数；健康档案常量提取到模块级；记录并展示真实识别引擎（MiMo/Agnes）。
- **v0.5.1（2026-07-06）**：修复电脑端扫描页布局畸变与语音播报无声音问题。桌面端最大内容宽度从 900px 放宽至 1200px；移除桌面端主内容区白色卡片背景，避免扫描卡片“卡片套卡片”；改进扫描页网格逻辑，无预览图时上传卡占满整行、有预览图时双列并排；修复 `st.status` 组件文字竖排；语音播报在点击时同步调用 `speechSynthesis.resume()` 以绕过 Chrome/Edge autoplay 限制，并为 `speechSynthesis.speak()` 增加 try/catch 兜底。
- **v0.5.0（2026-07-06）**：三端前端彻底重构。CSS 架构优化：简化媒体查询，统一设计系统，消除冗余规则；扫描页修复：解决文字竖排、按钮布局错乱、平板截断问题；结果页修复：移除 expander 黑方块，优化语音按钮状态更新；首页修复：移除重复免责声明；响应式优化：手机/平板/桌面三端布局规范化。
- **v0.4.7（2026-07-06）**：修复结果页语音播报组件中多行内联 JS 被 Streamlit Markdown 解析器渲染为可见 `<pre>/<code>` 代码块的问题。新增 `_render_tts_namespace()` 将 TTS 逻辑注入 `<script>` 标签，`voice_control_panel` 与 `speak_text` 的按钮改为单属性 `onclick="window.foodScannerTts.speak(...)"` 调用；同步更新 `diag_verify_ui.py` 断言，确保首页/结果页/扫描页均无可见 JS 代码块。
- **v0.4.6（2026-07-06）**：修复结果页语音按钮依赖 `last_speak_content` 可能丢失的问题；修复结果页底部操作栏 CSS 未生效的问题；优化扫描页上传卡片/预览卡片视觉容器，使 Streamlit 组件真正被卡片包裹；恢复桌面端扫描页上传卡与预览卡并排布局；测试模式新增 `mock=1` 参数，便于 Playwright 自动化验证结果页。
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
| 降级备用 | Agnes-2.0-Flash | MiMo 失败时自动切换，免费额度兜底 |
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
- **跨境传输**：识别服务部署于境外服务器（Streamlit Cloud / MiMo / Agnes 备用），上传图片及识别结果可能涉及跨境数据传输。
- **备案评估**：初赛 Demo 阶段通常无需 ICP 备案、算法备案、互联网药品信息服务备案；详见 `LEGAL_REVIEW.md`。
- **数据保护**：Demo 不保存用户上传图片，健康档案与历史记录仅在当前浏览器会话中使用，关闭页面后自动清空。
- **正式运营前**：务必聘请专业律师或合规顾问重新评估。

---

## 项目结构

```
ai-food-scanner/
├── app.py                  # 主程序（Streamlit 页面路由与渲染）
├── requirements.txt        # Python 依赖
├── CHANGELOG.md            # 版本变更记录
├── LEGAL_REVIEW.md         # 法律合规评估记录
├── USER_AGREEMENT.md       # 用户协议及免责声明
├── PRIVACY_POLICY.md       # 隐私政策
├── .streamlit/
│   ├── config.toml         # Streamlit 配置
│   └── style.css           # 适老化自定义样式
├── components/             # 可复用 UI 组件
│   ├── __init__.py         # 统一暴露组件与图标
│   ├── icons.py            # SVG 图标常量
│   ├── top_nav.py          # 顶部导航栏
│   ├── score_hero.py       # 评分英雄区
│   ├── additive_card.py    # 添加剂清单卡片
│   ├── nutrition_bars.py   # 营养成分 NRV 可视化条
│   ├── voice_panel.py      # 语音播报面板
│   └── personal_warnings.py # 个性化健康档案警告
├── utils/                  # 工具模块
│   ├── api.py              # API 调用、提示词、结果归一化
│   ├── data.py             # 本地数据加载（GB 2760、疾病、过敏原等）
│   ├── helpers.py          # 页面切换、设备检测
│   ├── history.py          # 识别历史读写与展示
│   ├── score.py            # 添加剂评分与药物-食物冲突检测
│   └── security.py         # HTML 转义等安全工具
├── data/                   # 本地数据文件（GB 2760、疾病、过敏原、历史记录等）
├── tests/                  # 核心函数单元测试
└── test_images/            # 真实配料表测试图片（gitignore 排除）
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
