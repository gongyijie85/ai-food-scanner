# 拍了就懂 · AI 食品配料表识别工具

> 老人打开手机，拍照配料表，**3 秒内语音读出**"这块食品能不能吃"。

![版本](https://img.shields.io/badge/version-0.9.0-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-green) ![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

**公开体验地址**：https://gongyijie85-ai-food-scanner-app-w4mpmt.streamlit.app/

**评委快速体验**（自动跳过法律同意与引导）：https://gongyijie85-ai-food-scanner-app-w4mpmt.streamlit.app/?demo=1

## 一句话介绍

面向 **3.1 亿中国老年人** 和 **8300 万慢病人群** 的食品配料表识别工具。
拍照 → 自动 OCR → 三色风险标注 → 语音播报。**3 步 3 秒**。

## 最新更新

- **v0.9.0（2026-07-10）**：全站 UI 视觉升级。在保留适老化（大字号、大按钮、高对比）基础上，统一 6 个核心页面的视觉风格：首页新增标题副标题、心形健康档案入口、脉冲光环扫描按钮、顶部提示气泡避免重叠；扫描页改为取景框 + 扫描线动画 + 底部双大按钮；结果页评分改为环形进度条，新增个人风险提示 banner、A/B/C 等级添加剂卡片、营养进度条、吸底语音播报；健康档案页疾病/过敏原改为带图标的网格卡片；历史记录页改为圆角搜索 + 筛选胶囊 + 横向评分徽章卡片；引导页增加大图标、步骤卡片和跳过按钮。同步更新版本号与文档。
- **v0.8.3（2026-07-10）**：参赛最终优化。彻底移除所有 DEBUG 模式代码，日志级别强制设为 INFO；调整首页扫描按钮位置，减少上方留白，提示气泡移到按钮下方；扩展 TTS 语音选择优先级，优先选择 Microsoft Xiaoxiao、Google 普通话等高质量中文语音；更新 Demo 帖版本号与更新记录。
- **v0.8.2（2026-07-10）**：执行 ponytail-audit 极限优化。删除本地临时诊断脚本 `diag_tts_*.py`、`inspect_btn.py` 和 `.worktrees/` 目录；移除 `repositories/additive_risk.py` 中仅有单一实现的 `AdditiveRiskRepository` ABC 抽象层，`CsvAdditiveRiskRepository` 直接使用；`utils/score.py` 将 `normalize_additive()` 与 `compute_score_from_additives()` 各自重复创建的 `AdditiveMatcher` 合并为模块级单一实例，避免每次评分重复加载 GB 2760 CSV；同步更新 `repositories/__init__.py`、`services/additive_matcher.py` 的导入与类型提示。`py_compile`、`pytest` 66 项、`black --check`、`flake8` 全量通过。
- **v0.8.1（2026-07-10）**：优化配料识别准确性，减少 AI 幻觉与漏字。提高图片压缩默认参数至 `max_size=4000/quality=90`，优先保留清晰度以减少小字漏识；收紧 `utils/api.py` system prompt，强制模型忽略风景/营销文案并只读取配料表区域；新增 `ocr_text` 一致性校验，为未在配料表原文中找到的 `additives` 标记 `ai_inferred`；结果页添加剂卡片展示"AI 推断，请以包装原文为准"提示；扩展单元测试覆盖压缩策略与 ai_inferred 标记；修复 v0.8.0 遗留的 flake8 警告。`py_compile`、`pytest` 66 项、`black --check`、`flake8` 全量通过。
- **v0.8.0（2026-07-10）**：完成架构深化与健康风险提示引擎落地。拆分 GB 2760 风险数据仓库（`repositories/additive_risk.py`）与添加剂分类器（`services/additive_matcher.py`），新增 `HealthWarningEngine` 统一生成药物冲突、过敏原、疾病敏感、原料风险四类警告；结果页（普通食品/保健食品）统一调用引擎并渲染个性化警告；扩展单元测试覆盖 repository/service 模块。`py_compile`、`pytest` 63 项、`black --check` 全量通过。
- **v0.7.7（2026-07-10）**：继续优化配料表小字识别与异常交互。根据 MiMo 图片理解文档，Base64 编码图片上限为 50MB，因此进一步提高 `utils/api.py` 中 `encode_image_to_base64` 默认 `max_size` 从 1200 到 2000，base64 上限从 106KB 放宽到 2MB（仍保留自适应 quality 降级与 1600px 回退保护），让配料表小字获得更多像素；扫描页识别失败时（API 异常或 JSON 解析失败）新增大号「重新拍摄/选择图片」按钮，引导老人直接重拍而不用手动返回上一步；结果页原有免责声明保留不变。`py_compile`、`pytest` 51 项、`black --check` 全量通过。
- **v0.7.6（2026-07-09）**：修复测试反馈的山楂糕配料表识别不稳定问题。同一包装多次扫描结果不一致，判断图片压缩可能损失了小字细节。在 `utils/api.py` 中把 `encode_image_to_base64` 默认 `max_size` 从 768 提高到 1200，插值从 `BILINEAR` 改为 `LANCZOS`，默认 `quality` 从 75 提高到 85，并新增 106KB base64 上限自适应保护（超限时自动降 quality，仍超限则回退 768px）。`py_compile`、`pytest` 51 项全量通过。
- **v0.7.5（2026-07-09）**：修复测试反馈的 OCR 误识别问题。同一款山楂糕配料表实际为「山楂（添加量≥50%）、低聚果糖（益生元）（添加量≥35%）、浓缩苹果汁」，但模型返回的 `ocr_text` 是「配料：山楂、白砂糖、食用盐」，说明 OCR 阶段就把包装上的其他文字误当成配料表。在 `utils/api.py` 中新增环境变量 `PRIMARY_PROVIDER=agnes` 切换主模型，默认 MiMo 为主、Agnes 兜底，设置后 Agnes 为主、MiMo 兜底，方便快速对比两个模型对同一配料表的识别效果。`py_compile`、`pytest` 51 项全量通过。
- **v0.7.4（2026-07-09）**：修复测试反馈的两项问题。针对山楂糕配料表实际只有「山楂、低聚果糖、浓缩苹果汁」却被 AI 补全「水、白砂糖、食用盐、柠檬酸、低聚木糖」等未显示成分的问题，在 `utils/api.py` system prompt 中新增 `ocr_text` 必填字段，强制模型**先完整 OCR 配料表原文，再从原文提取 ingredients/additives**，并新增山楂糕反例禁止「常见配方推断」；结果页在「全部配料」下方展示识别到的配料表原文，方便老人对照包装核对。同时修复首页「扫描配料表」大按钮位置过低，将 `.home-scan-area` 改为垂直居中并降低 `min-height`，减少上方留白。`py_compile`、`pytest` 51 项全量通过。
- **v0.7.3（2026-07-09）**：修复测试反馈的两项问题。扫描页文件上传器内文件名/大小标签在窄屏下仍可能溢出，为 `[data-testid="stFileUploaderFile"]` 及其子容器增加 `min-width: 0` 与截断样式，确保长文件名显示省略号；优化 `utils/api.py` system prompt 与用户消息，强制配料识别必须基于图片中实际出现的文字，禁止根据产品类型或常识推测未显示的配料，降低 AI 幻觉。`py_compile`、`pytest` 51 项全量通过，并修复 `black` 格式检查。
- **v0.7.2（2026-07-09）**：综合代码审计修复。修复 CI 流水线名存实亡（6 个步骤 `continue-on-error: true` 全部改为正常阻断）与 lint 范围过窄（仅查 `app.py` 改为全仓库 `.`）；`call_api` 拆分 4xx 错误提示（401/403→密钥无效、429→服务繁忙、404→地址错误、其他→请求异常），避免把限流误判为密钥问题；`_err` 的 `detail` 改为仅写入日志，不再在 DEBUG 折叠区展示 `resp.text`，防泄露上游鉴权信息；扫描页 DEBUG 模式的 API key 输入框增加 Host 本地判断，Streamlit Cloud 误配 DEBUG=1 时不再暴露输入框；`history_full` 上限从 20 对齐到 50，修复详情页索引越界导致第 21~50 条记录读不到完整快照；引导完成时初始化 `user_profile={"drugs":[],"allergens":[]}`，新用户首扫即可触发药物/过敏个性化警告。Ponytail 清理约 80 行死代码：删除 8 个 `render_*_mobile/desktop` 别名、9 个未用 SVG 图标（`_ICON_BACK/_ICON_HEART/_ICON_HOME` 等）、`speak_text` 与 `render_loading` 未用函数、`HEALTH_GROUPS` 与 `ADVICE_TEMPLATES["孕妇/儿童"]` 未用常量。`py_compile`、`pytest` 51 项全量通过。
- **v0.7.1（2026-07-08）**：修复手机端页面比例/垂直居中导致首屏内容下沉。根因是底部导航 CSS 选择器命中了包含全部内容的外层 `stVerticalBlock`，将其固定到底部并限高 72px，导致标题、扫描按钮、相机区域被推到首屏外。将导航固定目标改为 `stLayoutWrapper`，仅固定导航栏本身，内容恢复顶部对齐、正常撑开。本地 Playwright 移动端截图验证首页扫描按钮与扫描页相机区域均已进入首屏。`py_compile`、`pytest` 51 项全量通过。
- **v0.7.0（2026-07-08）**：修复手机端拍照页显示不全与疾病图标重复问题。移动端扫描页隐藏示例图、简化说明文字、为相机/上传组件设置最小高度，确保拍照区域首屏可见；将疾病卡片从汉字首字图标（如「糖 糖尿病」）改为语义化 emoji 小图标（🩺/🫀/🧠/🥗/🤧/🧒/🤰），并改为图标+文字水平排列，消除首个字重复。`py_compile`、`pytest` 51 项全量通过。
- **v0.6.9（2026-07-08）**：测试反馈修复 UI/UX 专项。疾病卡片增加图标，选中态改为绿底白字 + 右上角 ✓ 对勾，手机端卡片高度降至 80px；修复引导页说明卡片固定高度导致文字溢出框外；健康档案页过敏原从复选框改为与疾病卡片一致的风格；扫描页预览区单独渲染文件名并使用 ellipsis 截断，防止标签溢出；首页将健康标签与扫描大按钮聚合为白底圆角卡片，改善手机端松散感。`py_compile`、`pytest` 51 项全量通过。
- **v0.6.8（2026-07-08）**：测试反馈修复。引导页第 2 步初始健康档案从简单 `multiselect` 改为与详细档案页一致的卡片网格布局，解决“维护过于简单”；修复健康档案页疾病按钮“糖糖尿病”“压高血压”等双字重复；优化疾病卡片 `white-space` 与换行，修复字体框体布局；为文件上传器文件名/大小标签增加截断，防止上传图片标签溢出；统一结果页语音“停止”按钮与主播报按钮的高度、圆角和配色；历史页与侧边栏历史记录标签视觉层级优化。`py_compile`、`pytest` 51 项全量通过。
- **v0.6.7（2026-07-08）**：优化首页与历史记录交互。移除首页右侧「最近扫描」重复区域，历史记录统一由侧边栏/历史页承载；历史页与侧边栏历史记录改为整行可点击，直接跳转产品详情，移除独立「查看」大按钮；CSS 选择器精确限定扫描大按钮样式，避免误伤其他按钮。新增 `smoke_test.py` 本地冒烟测试覆盖首页、历史页、详情页关键路径。`py_compile`、`pytest` 51 项、`smoke_test` 全量通过。
- **v0.6.6（2026-07-08）**：修复 `components/navigation.py` 移动端底部导航循环解包错误（v0.6.3 SVG 清理后遗症），手机端访问不再崩溃；版本号同步到 v0.6.6。`py_compile` 与 `pytest` 51 项全量通过。
- **v0.6.5（2026-07-08）**：参赛 Demo 体验优化。新增 `?demo=1` 评委快速模式：自动完成法律同意、跳过 4 步引导、预填默认健康档案；评委模式下隐藏侧边栏模型切换与扫描页“拍照/相册”单选，让评委 3 秒内进入核心功能。同步 README 真实公开链接与 Demo 帖资料。`py_compile` 与 `pytest` 51 项全量通过。
- **v0.6.4（2026-07-08）**：参赛前收口整理。统一文档版本与叙事（README、HANDOFF、隐私政策），修正 HANDOFF 中过时的单文件架构/行号描述，收紧隐私政策中数据保存期限为“本应用不主动持久化，第三方服务按其政策处理”，将未跟踪的 `ui_ux_report.html` 排除在最终提交外，清理 D:\\GBT 外层含真实 API key 的脚本痕迹。`py_compile` 与 `pytest` 51 项全量通过。
- **v0.6.3（2026-07-08）**：修复扫描页示例图缺失导致的崩溃；全局替换已过期 `use_container_width=True` 为 `width="stretch"`（10 个文件 32 处）；为 `@st.cache_data` 添加 `ttl=300` 参数；修复 `st.button` label 中内联 SVG 被显示为源码乱码的问题（移动端底部导航、侧边栏、历史页、扫描页、结果页共 16 处），并修复语音播报面板 HTML 按钮中文本被 `_safe()` 误转义的问题；在 `.streamlit/config.toml` 中禁用原生多页面侧边栏导航，避免与自定义导航重复显示；`py_compile` 与 `pytest` 51 项全量通过。
- **v0.6.2（2026-07-08）**：真正修复 Streamlit Cloud `ModuleNotFoundError: No module named 'pages'` 部署错误。根因是 `.gitignore` 仍忽略 `pages/`，导致生产页面模块未进入 Git 仓库；已移除该忽略规则并将 `pages/` 全部文件加入跟踪。`py_compile` 与 `pytest` 51 项全量通过。
- **v0.6.1（2026-07-08）**：尝试修复 Streamlit Cloud 部署后 `ModuleNotFoundError: No module named 'pages'` 错误。在 `app.py` 顶部动态将项目根目录加入 `sys.path`，确保 Cloud 运行 `app.py` 时能正确导入 `pages`、`components`、`utils` 等同级模块；版本号同步到 v0.6.1。`py_compile` 与 `pytest` 51 项全量通过。
- **v0.6.0（2026-07-07）**：组件化 + 页面模块化架构重构。新增 `components/` 模块，将 `app.py` 中 7 个可复用 UI 组件与 14 个 SVG 图标常量抽离到独立文件；新增 `components/state.py` 统一空态/错误态/加载态组件，替换页面中重复的空状态 HTML 与 emoji；`components/additive_card.py` 实现添加剂清单折叠（默认前 5 项、高风险优先）。新增 `pages/` 模块，将 15 个页面渲染函数拆分为 7 个文件；新增 `utils/constants.py` 集中存放项目级常量；`app.py` 从约 1489 行精简至约 230 行。`py_compile` 与 `pytest` 51 项全量通过。
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

本项目公开体验地址：**https://gongyijie85-ai-food-scanner-app-w4mpmt.streamlit.app/**

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
│   ├── navigation.py       # 移动端底部导航 / 桌面端侧边栏
│   ├── score_hero.py       # 评分英雄区
│   ├── additive_card.py    # 添加剂清单卡片
│   ├── nutrition_bars.py   # 营养成分 NRV 可视化条
│   ├── voice_panel.py      # 语音播报面板
│   ├── personal_warnings.py # 个性化健康档案警告
│   └── state.py            # 统一空态 / 错误态 / 加载态
├── pages/                  # 页面渲染模块
│   ├── __init__.py         # 统一暴露页面渲染函数
│   ├── home.py             # 首页（移动端 / 桌面端）
│   ├── scan.py             # 扫描上传页
│   ├── result.py           # 识别结果页
│   ├── history.py          # 历史记录与详情页
│   ├── profile.py          # 健康档案页
│   ├── onboarding.py       # 首次引导页
│   └── legal.py            # 法律同意与法律文件页
├── utils/                  # 工具模块
│   ├── api.py              # API 调用、提示词、结果归一化
│   ├── constants.py        # 项目级共享常量
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
- [x] v2.5 公开链接部署
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
