# 变更日志

## v0.3.4 — 2026-07-02

### UI/UX 适老化体验优化

- **CSS 样式优化**：
  - 统一字体比例：h1=28px、h2=24px、h3=20px，避免字体过大
  - 优化语音按钮样式：图标文字对齐（24px图标 + 20px文字）
  - 评分数字从72px调整为56px，视觉更平衡
  - 添加语音控制条样式，结果页底部固定显示
- **导航优化**：
  - 顶部导航栏统一，移除右上角语音按钮（移到页面底部）
  - 侧边栏精简：首页/历史/档案大按钮，法律文件收起到折叠区
  - 高级设置（模型选择）仅在 DEBUG=1 时显示
- **首页优化**：
  - 移除不可点击的装饰性圆形按钮，保留单个功能按钮
  - 移除冗余提示气泡，界面更简洁
  - 最近扫描记录美化，添加空状态友好提示
- **扫描页优化**：
  - 隐藏模型选择等技术选项，默认使用 MiMo 模型
  - 简化上传提示，添加拍照图标引导
  - API密钥配置仅在 DEBUG=1 时显示
- **结果页优化**：
  - 整合免责提示为小字灰色文字，不占用主视觉
  - 移除多处重复的警告提示
  - 健康建议卡片添加图标
  - 结果页底部添加「再扫一个」「返回首页」快捷按钮
  - 个性化警告改为卡片式展示，减少 warning 堆叠
- **健康档案页优化**：
  - 移除敏感信息、Demo提示等冗余警告
  - 移除确认复选框，一键保存
  - 简化自由补充区域，收起到折叠区
  - 档案摘要更简洁
- **历史记录页优化**：
  - 添加空状态友好引导，有「开始扫描」按钮
  - 风险标签统一为「可食用/注意/少吃」更易懂
  - 筛选标签隐藏label，更简洁
- **底部优化**：
  - 移除页面底部大面积法律文件展开区
  - 移除跨境传输蓝色大横幅
  - 保留底部居中的小字免责提示：「AI识别仅供参考，请以包装原文为准」
  - 法律文件移到侧边栏折叠区，有独立页面展示

## v0.3.3 — 2026-07-02

### Streamlit Cloud 安全排查与加固

- **安全审计**：确认 `.env` 未进入 Git 历史，真实 API key 未写入代码，API key 通过 `os.getenv()` / `st.secrets` 读取；
- **`app.py` `get_api_key()`**：在 docstring 中补充安全说明，强调本地用 `.env`、生产用 Secrets、禁止写死 key；
- **`app.py` 扫描页**：API key 缺失提示增加「本地检查 .env / Cloud 检查 Secrets / 禁止代码中填真实密钥」的明确引导；
- **`app.py` DEBUG 信息块**：注释中明确标注生产环境严禁开启 `DEBUG=1`；
- **`README.md`**：在 Streamlit Cloud 部署章节后新增「安全提示（必读）」，覆盖 Secrets 配置、.env 不上传、DEBUG 禁用、协作者检查、定期轮换 key；
- **待用户操作**：登录 MiMo/Agnes 控制台轮换 API key，并在 Streamlit Cloud Secrets 中更新，然后 Reboot 应用。

## v0.3.2 — 2026-07-02

### 初赛资料 Review、安全加固与 Demo 帖重构

- **代码 Review**：审查 `app.py`，确认适老化设计、双模型 A/B 对比、GB 2760 客户端判定、药物-食物冲突、法律合规三件套完整。
- **安全加固**：
  - `app.py`：`st.set_page_config` 增加 `menu_items` 隐藏右上角 "View source" / "About" 菜单；
  - `.streamlit/config.toml`：`enableXsrfProtection` / `enableCORS` 改回 `true`。
- **演示视频**：生成分辨率 1080×1920、30fps、约 981KB 的 30 秒竖屏视频，覆盖痛点 → 首页 → 上传 → 结果 → 语音播报 → 体验地址。
- **论坛 Demo 帖重构**：
  - 按初赛规则整理为 4 大部分：Demo 简介、创作思路、体验地址、TRAE 实践过程；
  - 优化叙事结构，所有图片改用论坛 CDN 链接；
  - 在"体验地址"部分插入 30 秒演示视频。
- **待用户操作**：登录 [share.streamlit.io](https://share.streamlit.io/) 手动 Reboot 应用，确保公开链接可访问。

## v0.3.1 — 2026-07-02

### 手机浏览器语音播报修复

- **文件**：`app.py`
- **问题**：
  1. 手机浏览器（iOS Safari / Android Chrome）对语音合成有严格的自动播放限制，只有用户明确交互才能触发；
  2. 原 `speak_text` 和 `voice_control_panel` 使用 `st.button` + Python rerun 链路，导致用户手势上下文丢失，播报被拦截；
  3. 结果页自动播报逻辑在页面渲染时触发，非用户交互，被手机浏览器阻止。
- **修复**：
  1. `speak_text` 改为注入纯 HTML `<button>` + 内联 `onclick` JS，点击时直接在浏览器端调用 `speechSynthesis.speak()`，不经过 Python rerun；
  2. `voice_control_panel` 的 4 个控制按钮（重播/慢速/暂停/继续）全部改为纯 HTML 按钮 + 内联 JS，确保移动端手势同步触发；
  3. `render_top_nav` 的 voice 分支也改为纯 HTML 按钮；
  4. 移除结果页自动播报逻辑，仅保存播报内容供按钮使用。

## v0.3.0 — 2026-07-02

### 语音播报功能修复

- **文件**：`app.py`
- **问题**：
  1. `render_top_nav` 传了 `right_action="voice"` 但未实现，结果页/详情页右上角语音按钮缺失；
  2. `speak_text` 和 `_js_speech_control` 使用 `st.components.v1.html(js, height=0)`，iframe height=0 在部分浏览器不执行 JS；
  3. voices 异步加载时只有一次 500ms 兜底，不够健壮。
- **修复**：
  1. `render_top_nav` 补充 `right_action="voice"` 分支，渲染「🔊 播报」按钮；
  2. 将 `st.components.v1.html(js, height=0)` 全部替换为 `st.markdown(js, unsafe_allow_html=True)`，在主页面执行 JS；
  3. `speak_text` 增加 voices 空时递归重试（最多 5 次，每次间隔 300ms）+ 500ms/1500ms 双兜底；
  4. 增加 `u.onerror` 回调，便于排查播报失败原因；
  5. voice 属性增加 null 安全检查（`v.name &&`）。

## v0.2.9 — 2026-07-01

### 赛前最终打磨与提交

- **文件**：`app.py`、`README.md`、`.env.example`、`CHANGELOG.md`、Demo 帖 ID 51391
- **内容**：
  - 统一版本号为 v0.2.9（app.py / README / CHANGELOG）；
  - README 改为优先 `.env` 配置，新增 `.env.example`；
  - 人工收集淘宝/京东真实配料表图片到 `test_images/`，填充 `test_images/README.md` 来源信息；
  - 清理非最终提交脚本：`collect_test_images.py`、`prototype_mimo.py`；
  - 更新 `README.md` 项目结构，补充 `test_images/` 与 `download_test_images.py`；
  - 用真实电商图片完成本地业务回归测试，通过率 ≥80%；
  - 推送代码到 GitHub，验证 Streamlit Cloud 部署与公开链接可用；
  - 用最新真实运行截图更新社区 Demo 帖。
- **待用户操作**：若 Streamlit Cloud 返回 401，需更新 Secrets 中的 `MIMO_API_KEY`。

## v0.2.7 — 2026-07-01

### UI 统一优化与本地回归测试

- `app.py`
  - 新增 `session_state["page"]` 路由，`switch_page()`、`render_top_nav()` 工具函数。
  - 新增 `render_home_page()`、`render_scan_page()`、`render_result_page()`、`render_history_page()`、`render_detail_page()`、`render_health_profile_page()` 页面函数。
  - 重写 `main()` 为页面分发器；侧边栏改为弱化导航。
  - `inject_elder_css()` 统一注入设计稿变量和页面组件 CSS。
  - `render_food()` / `render_supplement()` 按设计稿卡片化。
  - 新增 `_get_level_info()`、`_render_score_hero()`、`_clip_path()`、`_render_additive_card()` 等 helper。
  - 新增 `data/history_full.json` 读写（`load_history_full()` / `save_history_full()`），最多保存 20 条完整识别快照。
  - `add_history()` 识别成功后同步保存完整快照。
- 新增页面
  - 历史记录页：搜索、筛选、竖向列表。
  - 产品详情页：评分英雄区、扫描信息、添加剂/营养/建议卡片。
- 回归测试
  - 本地 `streamlit run app.py` 跑通上传 → 识别 → 语音播报 → 保存历史 → 详情页流程。
  - 修复按钮失效、样式错位、session_state 丢失等回归问题。

## v0.2.6 — 2026-07-01

### Phase 3：适老化体验补齐（Task 7 / 8 / 9 / 10）

#### Task 7：语音播报增强
- **`app.py` `speak_text()`**
  - 新增 `rate` 参数（默认 1.0），支持 0.7x 慢速 / 1.0x 正常 / 1.3x 快速 / 0.75x 慢速重播
  - 限制 rate 范围 [0.5, 2.0]，避免极端值
- **`app.py` 新增 `_js_speech_control(action)`**
  - 通过 JS 调用 `speechSynthesis.pause() / resume() / cancel()`
- **`app.py` 新增 `voice_control_panel(speak_content, key_prefix)`**
  - 统一语音控制面板：语速 radio（横排三选一）+ 4 个按钮（重播 / 慢速重播 / 暂停 / 继续播放）
  - 用 `session_state["tts_rate"]` 记忆语速选择
- **`app.py` `render_food()` / `render_supplement()`**
  - 识别结果返回后自动触发语音播报（用 `session_state["last_spoken_key"]` 防止 rerun 重复播报）
  - 替换原「语音播报」单按钮为完整控制面板
  - 原按钮 key `btn_speak` 移除，改为 `tts_food_*` / `tts_supp_*`

#### Task 8：添加剂风险编码色盲友好
- **`app.py` `inject_elder_css()`**
  - 新增 `.score-shape` 样式（评分等级形状图标，56px）
  - 新增 `.additive-shape` / `.additive-level` 样式（添加剂卡片三重编码：颜色+形状+文字）
  - 评分色块 `.score-box` 改为 flex 布局，容纳形状图标
- **`app.py` `render_food()` 评分卡片**
  - 新增形状图标：80+ 绿圆 ● / 60-79 橙三角 ▲ / <60 红方块 ■
  - 与颜色、文字组成三重编码
- **`app.py` `render_food()` 添加剂卡片**
  - `level_map` 扩展为三元组 `(标签, 颜色, 形状)`
  - 每张卡片右侧显示带边框的等级徽章：形状图标 + 等级文字 + 背景色
- **对比度**：橙色/黄色背景配深色文字 `#333333`（v0.2.4 已确认，本次保持）

#### Task 9：简化健康档案与首次引导
- **`app.py` `render_onboarding()`**
  - 第 2 步默认勾选「脑梗/心血管 + 高血压」（`session_state["onboarding_groups"]` 初始化）
  - 第 2 步新增「⏭️ 跳过，稍后设置」按钮，点击后保留默认档案直接进入第 3 步
- **`app.py` `render_health_profile()`**
  - 基础疾病区新增 3 个一键组合按钮：「💔 我有三高」（高血压+高脂血症+2型糖尿病）/「🧠 脑梗/心血管」（高血压+脑梗死+冠心病）/「🗑️ 清空疾病」
  - 过敏原区新增 2 个一键组合按钮：「🥜 花生/牛奶过敏」（花生及其制品+乳及乳制品）/「🗑️ 清空过敏原」
  - 按钮点击后通过 `st.session_state[key]` 直接更新 multiselect widget 状态，再 `st.rerun()`
- **`app.py` `inject_elder_css()`**
  - `.stCheckbox > label > div` 设置 `min-width/height: 32px`，复选框放大到 32px
  - `.stCheckbox > label` 字体放大到 20px
  - 选中状态由 Streamlit 默认勾选图标 + CSS 边距提供双重反馈

#### Task 10：首页与结果页视觉还原
- **`app.py` `inject_elder_css()`**
  - 新增 `.scan-circle-btn` 样式：200x200 圆形渐变绿按钮，带阴影
  - 新增 `.nrv-bar-wrap` / `.nrv-bar-label` / `.nrv-bar-track` / `.nrv-bar-fill` 营养成分可视化条样式
  - 新增 `.sticky-voice-bar` 底部固定语音按钮样式（sticky + 顶部绿色边框）
- **`app.py` `main()` 扫描识别页**
  - 在 `file_uploader` 上方新增大圆形扫描按钮（视觉引导，标注「📷 拍照 / 上传配料表」）
- **`app.py` 新增 `render_nutrition_bars(result)`**
  - 营养成分可视化条：钠/糖/脂肪 NRV% 占比
  - 仅当识别结果含 `nutrition_nrv` 或 `nutrition` 字段时显示（模型可选返回）
  - 颜色分级：<5% 绿（低）/ 5-20% 橙（中）/ >20% 红（高）
- **`app.py` `render_food()`**
  - 全部配料后调用 `render_nutrition_bars(result)`
  - 末尾新增底部固定语音按钮「🔊 再听一遍结果」，复用 `last_speak_content`
- **历史卡片竖向列表**：`show_history()` 已是竖向 div 列表，无横向滚动 CSS（验证确认）
- **引导页下一步大按钮**：`render_onboarding()` 末尾已有 `use_container_width=True` 的「下一步 ➡️」按钮，适老化 56px 高（验证确认）

#### 版本与文档
- **`app.py` 顶部版本注释** 从 `v0.2.5` 更新为 `v0.2.6`
- **`.trae/specs/competition-strategy-and-next-steps/tasks.md`**
  - Task 7 及全部 SubTask（7.1 / 7.2 / 7.3 / 7.4）标记为完成（7.4 iOS Safari 测试为代码层兼容性实现，实际设备测试待用户验证）
  - Task 8 及全部 SubTask（8.1 / 8.2 / 8.3 / 8.4）标记为完成
  - Task 9 及全部 SubTask（9.1 / 9.2 / 9.3 / 9.4）标记为完成
  - Task 10 及全部 SubTask（10.1 / 10.2 / 10.3 / 10.4 / 10.5）标记为完成
- **`.trae/specs/competition-strategy-and-next-steps/checklist.md`**
  - 适老化体验 16 项检查项中，14 项代码实现相关项全部勾选
  - 「语音播报在 iOS Safari / 微信内置浏览器测试通过」一项标注为待用户设备验证

#### 验证
- `python -m py_compile app.py` 通过（exit_code=0）
- 适老化基础样式（18px 字体、56px 按钮）保持不变
- 法律合规弹窗、风险提示、跨境披露、AI 不确定性提示、医疗免责声明等功能保持不变

## v0.2.5 — 2026-07-01

### Phase 4：技术健壮性改进（Task 11 / 12 / 13）

#### Task 11：API 调用健壮性与错误脱敏
- **`app.py` `call_api()`**
  - 新增最多 2 次指数退避重试：第 1 次重试等 2 秒，第 2 次重试等 4 秒
  - 仅网络错误（`Timeout`/`RequestException`）或 5xx 状态码才重试；4xx 直接返回不重试
  - 重试循环共 3 次尝试（1 次初始 + 2 次重试）
- **`app.py` 新增 `_show_friendly_error()`**
  - 错误提示统一使用用户友好文案（如「识别服务暂时不可用，请稍后重试」），不再直接展示 `resp.text`
  - 原始错误信息（HTTP 状态码、`resp.text` 前 1000 字符、异常堆栈）仅在 `DEBUG=1` 时通过折叠区展示
- **Agnes 调试代码审查结论**
  - 经审查，当前代码中无「默认开启的 Agnes A/B 对比调试代码」
  - 侧边栏「模型选择」radio 默认选中 MiMo（列表第 1 项），Agnes 需用户主动选择
  - DEBUG 信息块中的 Agnes 配置展示受 `DEBUG=1` 控制，非默认开启
  - 因此无需移除代码，已满足「默认关闭」要求

#### Task 12：数据文件加载校验
- **`app.py` 新增 `validate_data_files()`**
  - 启动时校验 5 个关键数据文件的存在性与结构：
    - `data/gb2760_risk.csv`（必需列：`cn_name`、`risk_level`）
    - `data/common_diseases.json`（必需键：`categories`）
    - `data/allergens.json`（必需键：`categories`）
    - `data/common_drugs.json`（必需键：`categories`）
    - `data/drug_food_conflicts.json`（必需键：`conflicts`）
  - 返回问题列表 `list[str]`，空列表表示全部通过
  - 不阻断运行，仅返回问题清单
- **`app.py` 新增 `_DATA_FILE_SPEC` 常量**
  - 数据文件 → 必需键/列 的对照表，便于后续扩展
- **`app.py` `main()`**
  - 主页标题之后调用 `validate_data_files()`
  - 异常时通过 `st.warning()` 在页面顶部显示具体缺失的文件和问题
  - 即使部分数据缺失，应用仍可运行（相关功能不可用，但不会 `exit`）

#### Task 13：历史记录持久化（初赛版本）
- **`app.py` 新增 `load_history()`**
  - 读取本地 `data/history.json`，文件不存在或损坏时返回空列表
  - 不抛异常，刷新页面不丢失
- **`app.py` 新增 `save_history(record)`**
  - 追加一条记录到本地 JSON，自动保留最近 50 条，超出自动删除最旧的
  - 写入失败静默忽略，不阻断识别主流程
  - 兜底调用 `os.makedirs(_DATA_DIR, exist_ok=True)` 确保 data 目录存在
- **`app.py` `add_history()` 重写**
  - 改为构造 record 并调用 `save_history(record)` 写入本地 JSON
  - 记录字段：`timestamp`（ISO 格式）、`product_name`、`score`、`type`（food/supplement）、`additives_count`
  - 不保存图片数据（隐私保护，已在 Phase 0 确认）
  - 同步写入 `session_state` 便于其他逻辑即时读取
- **`app.py` `show_history()` 重写**
  - 改为从 `load_history()` 读取，刷新页面不丢失
  - 历史卡片新增「类型标签」（食品 / 保健食品）和「时间显示」（YYYY-MM-DD HH:MM）
  - 文案从「仅保存在当前会话」改为「最近 50 条记录保存在本地」
- **`app.py` 新增常量**
  - `_HISTORY_PATH = data/history.json`
  - `_HISTORY_MAX = 50`
- **`app.py` import 调整**
  - 新增 `import time`（指数退避重试用）
  - 新增 `from datetime import datetime`（历史记录时间戳用）

#### 版本与文档
- **`app.py` 顶部版本注释** 从 `v0.2.4` 更新为 `v0.2.5`
- **`.trae/specs/competition-strategy-and-next-steps/tasks.md`**
  - Task 11 及全部 SubTask（11.1 / 11.2 / 11.3）标记为完成
  - Task 12 及全部 SubTask（12.1 / 12.2 / 12.3）标记为完成
  - Task 13 及全部 SubTask（13.1 / 13.2 / 13.3）标记为完成
- **`.trae/specs/competition-strategy-and-next-steps/checklist.md`**
  - 技术健壮性 5 项检查全部勾选：
    - MiMo/Agnes API 调用有最多 2 次指数退避重试
    - Agnes 调试代码已移除或默认关闭
    - 启动时校验关键数据文件存在性与结构
    - 数据异常时在页面顶部显示警告
    - 历史记录使用本地 JSON 持久化，刷新不丢失
  - （API 错误提示用户友好文案、CHANGELOG 版本一致性 两项已在 v0.2.4 勾选）

#### 验证
- `python -m py_compile app.py` 通过（exit_code=0）
- 适老化样式、法律合规弹窗、风险提示、跨境披露、AI 不确定性提示等功能保持不变

## v0.2.4 — 2026-07-01

### 合规：医疗文案去医疗化、添加剂表述中性化、AI 不确定性提示（Phase 0.2-0.4 + Task 2）

- **`app.py` `render_personal_warnings()`**
  - 药物-食物冲突展示完全科普化：不再直接展示 `drug_food_conflicts.json` 中的 `description/mechanism/recommendation`
  - 统一输出文案：「{药物} 与 {配料} 可能存在相互作用，具体用药方案请咨询医生或药师」
  - 冲突区块末尾强制附加「本工具不提供用药建议」
- **`app.py` `render_food()`**
  - 评分标签从「安全/注意/警告」改为「较常见/特定人群建议关注/建议咨询专业人士」，与 A/B/C 等级文案一致
  - 评分大色块橙色背景（#FF9800）改用深色文字（#333333），避免黄底白字对比度不足
  - 每条添加剂卡片内新增逐条提示：「在 GB 2760 合规使用范围内是安全的。」
- **`app.py` `build_system_prompt()`**
  - 健康建议收尾文案从「建议咨询医生」扩展为「请咨询医生/药师/营养师」
- **`app.py` `render_supplement()`**
  - 语音播报与底部免责声明同步使用「请咨询医生/药师/营养师」
- **`d:\GBT\.trae\specs\competition-strategy-and-next-steps\checklist.md`**
  - Task 0.2、0.3、0.4 及全部 SubTask 标记为完成
  - Task 2 及全部 SubTask 标记为完成
- **`d:\GBT\.trae\specs\competition-strategy-and-next-steps\checklist.md`**
  - 勾选 12 项相关合规检查项
- **`app.py`**
  - 修正文件顶部版本注释为 `v0.2.4`，与 `CHANGELOG.md` 保持一致
- **`d:\GBT\.trae\specs\competition-strategy-and-next-steps\checklist.md`**
  - 第七步 QA 验证：勾选 Phase 0/1 全部 27 项合规与医疗安全项
  - 勾选技术健壮性可立即验证项：API 错误提示不泄露原始响应、CHANGELOG 版本与代码一致

## v0.2.3 — 2026-07-01

### 新增与强化：公开 Demo 风险提示与跨境披露（Phase 0.5）
- **首页显著风险提示** (`app.py`)
  - 标题下方新增高对比度橙色横幅："本 Demo 仅供技术展示，不构成任何医疗或消费建议"
  - 采用大字号（20px）、粗体、左侧色条，确保老人可见
- **跨境传输披露常驻化** (`app.py`)
  - 页面底部改为蓝色高对比度横幅："服务部署于境外服务器，识别过程可能涉及跨境数据传输"
  - 侧边栏底部同步常驻展示同一提示
- **法律合规评估文件** (`LEGAL_REVIEW.md`)
  - 新增备案评估记录，覆盖 ICP 备案、算法备案、互联网药品信息服务备案
  - 结论：初赛 Demo 阶段通常无需上述备案，正式上线前需聘请律师/合规顾问重新评估
- **法律合规评估入口** (`app.py`)
  - 侧边栏「用户协议与隐私政策」旁新增「法律合规评估」展开入口，可直接查看 `LEGAL_REVIEW.md`
- **Demo 数据保护强化** (`app.py`)
  - 历史记录不再保存用户上传图片，仅保留匿名化摘要（产品名、分数、添加剂数量、建议）
  - 历史记录区域增加提示："历史记录仅保存在当前会话，不存储图片，Demo 结束后自动清空"
  - 健康档案页增加 Demo 提示：建议不要输入真实姓名、身份证号、详细病史等真实个人信息

## v0.2.2 — 2026-07-01

### 修复：医疗安全与数据准确性（Phase 1）
- **`data/drug_food_conflicts.json`**
  - 移除 `DFC0051` 氯吡格雷-PPI 药物-药物相互作用条目
  - 修正 `DFC0015` 阿卡波糖「单独用药或低糖饮食易致低血糖」错误表述
  - `DFC0036` 氨茶碱移除证据不足关键词（高蛋白低糖）、弱化描述、severity 调整为 medium
  - 全量 recommendation 去指令化：避免「严禁」「必须避免」「危及生命」「小时禁食」等诊疗措辞
  - 补充 `DFC0060` 甲硝唑、`DFC0061` 替硝唑双硫仑样反应条目
  - 所有冲突条目标注权威来源（NMPA 说明书/指南）
- **`data/common_drugs.json`**
  - 抗感染分类新增甲硝唑（D363）、替硝唑（D364），id 唯一
- **`app.py`**
  - `render_personal_warnings()` 去掉 emoji，并在药物冲突区块末尾统一附加「本工具不提供用药建议」

## v0.2.1 — 2026-07-01

### 修复：公开 Demo 可访问性（Phase 0.6）
- **API 密钥读取逻辑确认** (`get_api_key()`)
  - 环境变量优先，其次 `st.secrets`，异常时返回空字符串
  - MiMo 与 Agnes 分别读取 `MIMO_API_KEY` / `AGNES_API_KEY`
- **移除响应内容泄露** (`call_api()`)
  - 错误状态码 / 解析失败时不再直接展示 `resp.text[:500]`
  - 仅在 `DEBUG=1` 时通过折叠区展示原始响应
- **新增 DEBUG 信息块** (`main()` 顶部)
  - 仅当环境变量 `DEBUG=1` 时显示
  - 显示 API URL、Model、Key 长度与末4位、Auth Header 类型
  - 不展示完整 API Key

### 待用户操作
- 在 Streamlit Cloud Secrets 中更新有效的 `MIMO_API_KEY` 后重新部署验证

## v0.2.0 — 2026-07-01

### 新增
- **法律文件入口** (`app.py`)
  - 在侧边栏增加「用户协议与隐私政策」展开入口
  - 用户可随时重新查看《用户协议及免责声明》和《隐私政策》
- **未成年人与老年人使用提示**
  - `USER_AGREEMENT.md` 新增第十条「未成年人与老年人使用提示」
  - `PRIVACY_POLICY.md` 第八条增加老年人使用提示，标题调整为「儿童、未成年人与老年人保护」

### 调整
- 无破坏性改动，仅在现有法律合规基础上补充入口与特殊人群提示。

## v0.2.0 — 2026-07-01

### 新增
- **法律合规同意流程** (`app.py`)
  - 新增 `render_legal_consent()`：首次访问强制阅读《用户协议及免责声明》《隐私政策》
  - 使用 `st.session_state["legal_agreed"]` 记录同意状态
  - 两个复选框全部勾选后「开始使用」按钮才可用
  - 未同意前无法进入引导页和主功能
- **健康档案敏感信息单独同意** (`render_health_profile()`)
  - 页面顶部增加敏感个人信息提示
  - 「保存档案」前增加确认复选框，未勾选时按钮禁用
- **公开 Demo 风险提示与跨境披露** (`main()`)
  - 首页标题下方增加「本 Demo 仅供技术展示，不构成任何医疗或消费建议」
  - 页面底部增加「服务部署于境外服务器，识别过程可能涉及跨境数据传输」
- **AI 识别不确定性与过敏原提示**
  - `render_food()` 顶部增加「AI 识别可能存在错误，请以包装原文为准」
  - `render_supplement()` 顶部免责声明增加「内容为包装原文摘录，不代表本工具立场」
  - 过敏原匹配区域增加「配料表识别可能遗漏致敏物质，严重过敏者请勿仅依赖本工具」

### 调整
- **食品添加剂表述中性化** (`render_food()`)
  - level_map 标签从「安全/注意/规避」改为「较常见/特定人群建议关注/建议咨询专业人士」
  - 同时兼容 A/B/C 与 green/yellow/red 两种 level 值
  - 评分区域增加「评分仅供参考，不构成安全判断」
  - 添加剂列表增加「在 GB 2760 合规使用范围内是安全的」提示
- **药物-食物冲突科普化展示** (`render_personal_warnings()`)
  - 标题改为「检测到可能与您的用药相关的食物信息，仅供参考」
  - 用 ⚠️ 统一替换 🔴🟠🟡 颜色图标
  - expander 标题中「风险」改为「关注」
  - 详情标题改为「相关介绍/涉及原理/日常注意」
  - 每个冲突详情底部强制附加用药建议免责提示
- **语音播报内容更新** (`render_food()`)
  - 在 advice 后附加「本工具仅供参考，不构成医疗建议」

### 数据透明
- 添加剂列表底部增加「数据来源：GB 2760-2024」
- 健康档案疾病/过敏原/用药区域保留已有数据来源说明

## v0.1.0 — 2026-06-25

### 新增
- **首次引导页** (`pages/onboarding.html`)
  - 3 屏可滑动引导轮播（触摸 + 鼠标拖拽）
  - 第 1 屏：产品价值「拍照即知添加剂风险」，SVG 扫描动画插图
  - 第 2 屏：核心功能「3秒识别，语音播报」，SVG 时钟 + 声波动画插图
  - 第 3 屏：健康档案设置入口，6 个慢病标签可点选（糖尿病/高血压/肾病/痛风/心脏病/食物过敏）
  - 底部进度点指示器，最后一屏显示「开始使用」按钮
  - 右上角「跳过引导」链接（18pt 最小字号）
  - 适老化设计：48px 最小触摸目标、24pt 圆角按钮、大字体
  - 引用 `colors_and_type.css` 品牌设计变量
  - `data-dom-id="btn-start"` / `data-dom-id="btn-skip"` 交互标记
