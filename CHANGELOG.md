# 变更日志

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
