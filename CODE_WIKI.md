# AI 食品配料表识别工具 - Code Wiki

> 版本：v0.4.7 | 更新时间：2026-07-06

---

## 1. 项目概述

### 1.1 项目定位

面向 3.1 亿中国老年人和 8300 万慢病人群的食品配料表识别工具。用户拍照配料表 → AI 自动 OCR 识别 → 三色风险标注（绿/黄/红）→ 语音播报结果，全程 3 步 3 秒。

项目参与 TRAE AI 创造力大赛「智慧助老」赛道。

### 1.2 核心能力

| 能力 | 说明 |
|------|------|
| OCR 识别 | 拍照即可识别小字号配料表 |
| 添加剂分类 | 自动识别 GB 2760 添加剂（含 INS 号） |
| 三色风险标注 | 绿/黄/红 + 图标 + 文字三重编码，色盲友好 |
| 个性化建议 | 根据用户健康档案（糖尿病/高血压/过敏等）给建议 |
| 药物-食物冲突 | 根据健康档案用药，提示配料中的潜在冲突 |
| 语音播报 | 浏览器原生 SpeechSynthesis，Microsoft Yaoyao 1.0x |
| 历史记录 | 本地 JSON 持久化，保存最近 50 条扫描 |
| 健康档案 | 6 类慢病/过敏/用药档案，个性化风险提示 |
| 双模式识别 | 自动区分普通食品与保健食品（蓝帽子） |

### 1.3 适老化设计标准

- 18pt 最小字号（国标要求 ≥ 14pt）
- 56px 大按钮（国标要求 ≥ 48px）
- 高对比度色块（绿/黄/红三色 + 图标 + 文字）
- 3 步极简流程（拍照 → 识别 → 听结果）
- 零配置健康档案（默认脑梗 + 高血压）

---

## 2. 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 前端框架 | Streamlit 1.58+ | Python 一键 Web 化 |
| 多模态 API | MiMo Vision (mimo-v2.5) | 小米自研，新加坡集群 |
| 备选模型 | Agnes-2.0-Flash | A/B 对比用 |
| 语音播报 | 浏览器原生 SpeechSynthesis | 零依赖，Microsoft Yaoyao 女声 |
| 样式 | 自研 CSS（.streamlit/style.css） | 适老化主题 |
| 图片处理 | Pillow | 压缩、格式转换、base64 编码 |
| 测试框架 | pytest | 核心函数单元测试 |
| CI/CD | GitHub Actions | py_compile + pytest + 安全扫描 |
| 部署平台 | Streamlit Cloud | 公开免费部署 |

### 2.1 依赖清单（requirements.txt）

```
streamlit>=1.40.0      # Web 框架
requests>=2.31.0       # HTTP 请求（API 调用）
pillow>=10.0.0         # 图片处理
python-dotenv>=1.0.0   # 环境变量加载
pytest>=8.0.0          # 单元测试
```

---

## 3. 项目结构

```
ai-food-scanner/
├── app.py                      # 主程序（~2223 行，Streamlit 单文件应用）
├── requirements.txt            # Python 依赖
├── CHANGELOG.md                # 版本变更记录
├── README.md                   # 项目说明
├── HANDOFF.md                  # 交接文档
├── LEGAL_REVIEW.md             # 法律合规评估
├── USER_AGREEMENT.md           # 用户协议及免责声明
├── PRIVACY_POLICY.md           # 隐私政策
├── .env.example                # 环境变量模板
├── .gitignore
│
├── .streamlit/
│   ├── config.toml             # Streamlit 配置（安全/主题/上传限制）
│   └── style.css               # 适老化自定义 CSS
│
├── data/                       # 数据文件（本地持久化 + 参考数据）
│   ├── gb2760_risk.csv         # GB 2760 添加剂风险分级表
│   ├── common_diseases.json    # 常见疾病分类数据
│   ├── allergens.json          # 过敏原分类数据
│   ├── common_drugs.json       # 常见药物分类数据
│   ├── drug_food_conflicts.json# 药物-食物冲突数据
│   ├── history.json            # 历史记录摘要（自动生成）
│   └── history_full.json       # 历史记录完整快照（自动生成）
│
├── tests/
│   ├── __init__.py
│   └── test_core.py            # 核心函数单元测试（17 个用例）
│
├── pages/                      # UI 设计稿（HTML 静态页面）
│   ├── home.html
│   ├── camera.html
│   ├── result.html
│   ├── history.html
│   ├── detail.html
│   └── onboarding.html
│
├── pages-redesign/
│   └── home.html
│
├── test_images/                # 测试图片（gitignore 排除）
│   └── README.md
│
├── diag_shots/                 # 诊断截图
│   ├── home_test.png
│   ├── scan_test.png
│   └── final.png
│
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD 工作流
│
├── download_test_images.py     # 测试图片下载脚本
├── diag_verify_ui.py           # UI 诊断验证脚本
└── colors_and_type.css         # 颜色与字体参考
```

---

## 4. 整体架构

### 4.1 架构分层

```
┌─────────────────────────────────────────────────────┐
│                    表现层（UI）                       │
│  首页 / 扫描页 / 结果页 / 历史页 / 详情页 / 档案页    │
│  顶部导航 / 底部操作栏 / 浮动语音播报                  │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  业务逻辑层                           │
│  页面路由 / 状态管理 / 结果渲染 / 历史记录             │
│  健康档案管理 / 个性化警告 / 药物冲突检测              │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  核心服务层                           │
│  API 调用（MiMo/Agnes）/ 图片编码 / 结果解析          │
│  GB 2760 权威判定 / 评分计算 / 语音播报                │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  数据层                               │
│  GB 2760 CSV / 疾病 JSON / 过敏原 JSON               │
│  药物 JSON / 冲突 JSON / 历史记录 JSON                │
└─────────────────────────────────────────────────────┘
```

### 4.2 核心数据流

```
用户上传图片
    │
    ▼
encode_image_to_base64()  压缩图片 → base64
    │
    ▼
build_system_prompt()     构建 system 提示词（含健康档案）
    │
    ▼
call_api()                调用 MiMo Vision API（指数退避重试）
    │
    ▼
parse_result()            解析 JSON → 客户端 GB 2760 覆盖判定
    │
    ├── normalize_additive()       查 GB 2760 库
    └── compute_score_from_additives()  计算评分
    │
    ▼
add_history()             保存历史记录（摘要 + 完整快照）
    │
    ▼
render_food() / render_supplement()  渲染结果页
    │
    └── voice_control_panel()       语音播报按钮
```

---

## 5. 模块与关键函数说明

### 5.1 配置与常量模块

**文件位置**：[app.py#L42-L84](file:///d:/GBT/ai-food-scanner/app.py#L42-L84)

| 常量名 | 值 | 说明 |
|--------|----|------|
| `API_URL` | `https://token-plan-sgp.xiaomimimo.com/v1/chat/completions` | MiMo 新加坡集群端点 |
| `MODEL_NAME` | `mimo-v2.5` | 多模态模型名称 |
| `AGNES_API_URL` | `https://apihub.agnes-ai.com/v1/chat/completions` | Agnes 备选模型端点 |
| `AGNES_MODEL_NAME` | `agnes-2.0-flash` | Agnes 模型名 |
| `HEALTH_GROUPS` | 6 类人群列表 | 糖尿病/高血压/脑梗/减脂/过敏/孕妇儿童 |
| `SCORE_PENALTY` | `{A:0, B:8, C:25}` | 添加剂扣分规则 |
| `SUPPLEMENT_EXCIPIENTS` | 8 种辅料集合 | 保健品辅料白名单（不扣分） |
| `_HISTORY_MAX` | `50` | 历史记录最大条数 |
| `_HISTORY_FULL_MAX` | `20` | 完整快照最大条数 |

### 5.2 数据加载模块

#### `load_gb2760_risk()` — GB 2760 风险数据加载

- **位置**：[app.py#L121-L139](file:///d:/GBT/ai-food-scanner/app.py#L121-L139)
- **装饰器**：`@st.cache_resource`（全局缓存一次）
- **返回**：`dict[中文名] → {level, adi, warnings, note}`
- **数据源**：`data/gb2760_risk.csv`
- **作用**：加载 GB 2760 食品添加剂风险分级表，用于客户端权威判定

#### `load_health_data()` — 健康档案数据加载

- **位置**：[app.py#L110-L118](file:///d:/GBT/ai-food-scanner/app.py#L110-L118)
- **装饰器**：`@st.cache_resource`
- **返回**：`{diseases, allergens, drugs, conflicts}`
- **数据源**：4 个 JSON 文件
- **作用**：统一加载所有健康相关参考数据

#### `validate_data_files()` — 数据文件启动校验

- **位置**：[app.py#L155-L194](file:///d:/GBT/ai-food-scanner/app.py#L155-L194)
- **返回**：`list[str]` 问题列表（空列表表示全部通过）
- **校验内容**：5 个关键数据文件的存在性 + 必需列/键
- **特点**：不阻断运行，仅返回问题清单

### 5.3 页面路由模块

#### `switch_page(page, **kwargs)` — 页面切换

- **位置**：[app.py#L199-L206](file:///d:/GBT/ai-food-scanner/app.py#L199-L206)
- **参数**：
  - `page`：目标页面名称（home/scan/result/history/detail/profile）
  - `**kwargs`：额外状态存入 session_state
- **作用**：统一页面跳转，自动保存 prev_page，调用 `st.rerun()`

#### `render_top_nav(title, show_back, back_target, right_action, align)` — 顶部导航

- **位置**：[app.py#L209-L230](file:///d:/GBT/ai-food-scanner/app.py#L209-L230)
- **参数**：
  - `title`：标题文字
  - `show_back`：是否显示返回按钮（默认 True）
  - `back_target`：返回目标页面（默认 home）
  - `right_action`：右侧按钮，可选 "profile" / None
  - `align`：标题对齐，"center" / "left"
- **实现**：`st.container()` + CSS `:has(.top-nav-title)` 实现 sticky 效果

### 5.4 样式与适老化模块

#### `load_css()` — 加载 CSS 文件

- **位置**：[app.py#L235-L242](file:///d:/GBT/ai-food-scanner/app.py#L235-L242)
- **特点**：不使用缓存（v0.4.5 起移除 `@st.cache_data`），确保 CSS 修改即时生效

#### `inject_elder_css()` — 注入适老化 CSS

- **位置**：[app.py#L245-L249](file:///d:/GBT/ai-food-scanner/app.py#L245-L249)
- **作用**：将 style.css 内容通过 `st.markdown(..., unsafe_allow_html=True)` 注入页面

### 5.5 语音播报模块

#### `voice_control_panel(speak_content, key_prefix, button_text, wrapper_class)` — 语音控制面板

- **位置**：[app.py#L334-L459](file:///d:/GBT/ai-food-scanner/app.py#L334-L459)
- **核心参数**：
  - `speak_content`：要播报的文本
  - `key_prefix`：组件唯一标识前缀，避免多按钮冲突
  - `wrapper_class`：外层 div 的 class，传 `'voice-float-bar voice-control-wrap'` 可实现浮动效果
- **技术要点**：
  - 纯 HTML 按钮 + 内联 onclick JS，确保移动端用户手势同步触发
  - 优先选择 Microsoft Yaoyao 语音，兜底任意中文语音
  - 支持 onvoiceschanged 事件等待语音列表加载
  - iOS Safari 用 setTimeout(0) 确保在手势上下文执行
  - 含语速调整折叠面板（0.7x / 1.0x / 1.3x）

#### `_preload_tts_voices()` — 预加载语音列表

- **位置**：[app.py#L462-L484](file:///d:/GBT/ai-food-scanner/app.py#L462-L484)
- **作用**：页面加载时预触发语音列表加载，提升首次播报成功率
- **实现**：`<script>` 标签注入，监听 onvoiceschanged 事件

#### `_safe(text)` / `_js_attr_safe(text)` — XSS 防护

- **位置**：[app.py#L86-L88](file:///d:/GBT/ai-food-scanner/app.py#L86-L88)、[app.py#L254-L257](file:///d:/GBT/ai-food-scanner/app.py#L254-L257)
- **作用**：
  - `_safe()`：HTML 转义，用于动态文本插入 HTML
  - `_js_attr_safe()`：HTML 转义 + JS 字符串转义，用于内联 onclick 属性

### 5.6 API 调用模块

#### `get_api_key(model)` — 获取 API 密钥

- **位置**：[app.py#L489-L504](file:///d:/GBT/ai-food-scanner/app.py#L489-L504)
- **参数**：`model` — "mimo" 或 "agnes"
- **读取顺序**：环境变量 → `st.secrets`
- **安全原则**：密钥不在代码中硬编码，不输出到日志

#### `encode_image_to_base64(image_file, max_size=768)` — 图片编码

- **位置**：[app.py#L507-L518](file:///d:/GBT/ai-food-scanner/app.py#L507-L518)
- **参数**：
  - `image_file`：文件对象或路径
  - `max_size`：最长边像素（默认 768）
- **压缩参数**：JPEG quality=75，BILINEAR 缩放，optimize=True
- **返回**：base64 字符串（不含 data: 前缀）
- **目标大小**：base64 约 ≤ 106 KB

#### `build_system_prompt(groups)` — 构建系统提示词

- **位置**：[app.py#L521-L555](file:///d:/GBT/ai-food-scanner/app.py#L521-L555)
- **参数**：`groups` — 用户健康档案人群列表
- **提示词结构**：
  1. 角色定义：食品/保健食品标签解读助手
  2. 产品类型判断规则（supplement / food）
  3. type=supplement 的 12 个必填字段说明
  4. type=food 的 5 个必填字段说明
  5. 强制规则（中文产品名、原文引用、禁止医疗措辞等）

#### `call_api(api_key, image_b64, system_prompt, model="mimo")` — API 调用

- **位置**：[app.py#L566-L670](file:///d:/GBT/ai-food-scanner/app.py#L566-L670)
- **参数**：
  - `api_key`：API 密钥
  - `image_b64`：base64 编码图片
  - `system_prompt`：系统提示词
  - `model`："mimo" / "agnes"
- **重试策略**：
  - 最多 3 次尝试（1 次初始 + 2 次重试）
  - 指数退避：第 1 次等 2s，第 2 次等 4s
  - 可重试错误：网络超时、连接错误、5xx 状态码
  - 不重试错误：4xx 状态码、响应解析失败
- **超时**：30 秒
- **max_tokens**：2048（优化性能）
- **日志**：记录请求开始、成功/失败、耗时、响应长度

### 5.7 结果解析与 GB 2760 判定模块

#### `parse_result(raw, health_groups=None)` — 解析模型返回

- **位置**：[app.py#L673-L707](file:///d:/GBT/ai-food-scanner/app.py#L673-L707)
- **参数**：
  - `raw`：模型返回的原始文本（可能带 markdown code block）
  - `health_groups`：健康档案人群列表
- **返回**：解析成功返回 dict，失败返回 None
- **处理逻辑**：
  1. 去除 ```json ``` 包裹
  2. JSON 解析
  3. 纯英文 product_name 强制改为 "该产品"
  4. **仅对 type=food 做客户端权威判定**：
     - 逐个添加剂调用 `normalize_additive()` 覆盖 level
     - 调用 `compute_score_from_additives()` 重新计算 score

#### `normalize_additive(name)` — 添加剂标准化与风险判定

- **位置**：[app.py#L712-L739](file:///d:/GBT/ai-food-scanner/app.py#L712-L739)
- **参数**：`name` — 添加剂名称
- **返回**：`(level, ins_no, note)` 三元组
- **匹配优先级**：
  1. 保健品辅料豁免（鱼油、明胶等）→ level=A
  2. GB 2760 库精确匹配
  3. 去括号/空格/INS 号后再匹配
  4. 模糊匹配（长度差 ≤ 2，避免误匹配长名称）
  5. 兜底：默认 B 级（保守策略，宁严勿宽）

#### `compute_score_from_additives(additives, health_groups=None)` — 评分计算

- **位置**：[app.py#L742-L761](file:///d:/GBT/ai-food-scanner/app.py#L742-L761)
- **公式**：`100 - C级×25 - B级×8 - 特殊人群敏感性×4`
- **特殊人群敏感性**：添加剂 warnings 字段命中健康档案人群时额外扣 4 分
- **范围**：0 ~ 100 分
- **评分等级**：≥80 绿色（安全）/ 60-79 黄色（注意）/ <60 红色（高风险）

#### `check_drug_food_conflicts(ingredients_list, user_drugs)` — 药物-食物冲突检测

- **位置**：[app.py#L764-L794](file:///d:/GBT/ai-food-scanner/app.py#L764-L794)
- **参数**：
  - `ingredients_list`：识别到的配料列表
  - `user_drugs`：用户用药列表（每项含 id 和 name）
- **返回**：冲突列表，每项含 `{drug, food, matched_keyword, severity, description, recommendation, mechanism, source}`
- **匹配逻辑**：遍历冲突库，按 drug_id 筛选用户药物，检查配料中是否包含食物关键词

### 5.8 历史记录模块

#### `load_history()` — 加载历史摘要

- **位置**：[app.py#L805-L819](file:///d:/GBT/ai-food-scanner/app.py#L805-L819)
- **装饰器**：`@st.cache_data(ttl=300)`
- **数据源**：`data/history.json`
- **返回**：`list[dict]`，每条含 timestamp/product_name/score/type/additives_count

#### `save_history(record)` — 保存历史摘要

- **位置**：[app.py#L822-L837](file:///d:/GBT/ai-food-scanner/app.py#L822-L837)
- **特点**：异常时静默忽略，写入失败不阻断主流程

#### `add_history(result)` — 识别成功后添加历史

- **位置**：[app.py#L864-L884](file:///d:/GBT/ai-food-scanner/app.py#L864-L884)
- **作用**：同时保存摘要（history.json）和完整快照（history_full.json）
- **隐私保护**：不保存图片数据

### 5.9 页面渲染模块

#### `render_home_page()` — 首页

- **位置**：[app.py#L1703-L1781](file:///d:/GBT/ai-food-scanner/app.py#L1703-L1781)
- **组成**：
  - 顶部导航（居左标题 + 健康档案入口）
  - 健康标签行（显示已选人群）
  - 大圆形扫描按钮区
  - 最近扫描卡片（前 3 条）
  - 查看全部历史记录入口
  - 免责声明

#### `render_scan_page()` — 扫描上传页

- **位置**：[app.py#L1784-L1886](file:///d:/GBT/ai-food-scanner/app.py#L1784-L1886)
- **核心流程**：
  1. 卡片式上传区（支持 jpg/png，最大 5MB）
  2. 图片内联预览 + 「重新选择 / 使用照片」操作
  3. 点击使用照片后：
     - 验证图片格式
     - 压缩并转 base64
     - 调用 API 识别
     - 解析结果
     - 保存历史
     - 跳转结果页
- **布局**：桌面端并排（上传卡 + 预览卡），手机端堆叠

#### `render_food(result)` — 普通食品结果页

- **位置**：[app.py#L1023-L1089](file:///d:/GBT/ai-food-scanner/app.py#L1023-L1089)
- **组成**（从上到下）：
  1. 顶部导航栏
  2. 评分英雄区（大数字 + 颜色 + 形状图标 + 慢速重听）
  3. 免责声明
  4. 添加剂清单卡片（含色盲图例）
  5. 营养成分可视化条（钠/糖/脂肪 NRV%）
  6. 健康建议卡片
  7. 个性化警告（药物冲突 + 过敏原）
  8. 查看全部配料（折叠区）
  9. 底部浮动语音播报按钮（sticky）
  10. 底部操作栏（再扫一个 / 返回首页）

#### `render_supplement(result)` — 保健食品结果页

- **位置**：[app.py#L1212-L1312](file:///d:/GBT/ai-food-scanner/app.py#L1212-L1312)
- **特有内容**：
  - 顶部红色保健食品警示卡
  - 产品摘要
  - 批准文号
  - 标志性成分
  - 保健功能（包装原文）
  - 适宜/不适宜人群（包装原文）
  - 食用方法（包装原文）
- **强制规则**：所有包装引用严格按原文，不评价、不推荐

#### `render_history_page()` — 历史记录页

- **位置**：[app.py#L1903-L2008](file:///d:/GBT/ai-food-scanner/app.py#L1903-L2008)
- **功能**：
  - 搜索栏（产品名称搜索）
  - 风险筛选标签（全部/安全/注意/高风险）
  - 竖向列表（分数 + 名称 + 状态 + 日期）
  - 点击条目跳转详情页

#### `render_detail_page()` — 产品详情页

- **位置**：[app.py#L2011-L2081](file:///d:/GBT/ai-food-scanner/app.py#L2011-L2081)
- **数据源**：`history_full.json` 完整快照
- **组成**：评分英雄区 + 扫描信息卡 + 添加剂 + 营养 + 建议 + 全部配料 + 底部操作栏

#### `render_health_profile_page()` — 健康档案页

- **位置**：[app.py#L2083-L2086](file:///d:/GBT/ai-food-scanner/app.py#L2083-L2086)
- **调用**：`render_health_profile()`
- **内容**：基本信息 + 6 类健康状况 + 8 种过敏原 + 常见药物选择 + 补充说明

#### `render_onboarding()` — 首次引导（4 步）

- **位置**：[app.py#L1398-L1526](file:///d:/GBT/ai-food-scanner/app.py#L1398-L1526)
- **步骤**：
  1. 欢迎页（工具介绍）
  2. 选择健康人群（默认脑梗+高血压，可跳过）
  3. 使用说明（3 步图示）
  4. 准备好了页

#### `render_legal_consent()` — 法律同意弹窗

- **位置**：[app.py#L1359-L1393](file:///d:/GBT/ai-food-scanner/app.py#L1359-L1393)
- **内容**：用户协议 + 隐私政策 + 两个必选 checkbox + 开始使用按钮

### 5.10 主程序入口

#### `main()` — 主函数

- **位置**：[app.py#L2091-L2219](file:///d:/GBT/ai-food-scanner/app.py#L2091-L2219)
- **执行顺序**：
  1. `st.set_page_config()` — 页面配置（隐藏菜单）
  2. 注入 viewport meta 标签（移动端适配）
  3. `inject_elder_css()` — 注入适老化 CSS
  4. `_preload_tts_voices()` — 预加载语音
  5. DEBUG 信息块（仅 DEBUG=1 时显示）
  6. 测试模式支持（`?test=1` 跳过法律和引导）
  7. 法律同意检查 → 首次引导检查
  8. 侧边栏渲染（导航 + 历史 + 法律入口）
  9. 根据 `st.session_state["page"]` 分发页面

---

## 6. 数据文件说明

### 6.1 gb2760_risk.csv — GB 2760 添加剂风险表

| 列名 | 说明 |
|------|------|
| `cn_name` | 中文名称（主键） |
| `risk_level` | 风险等级：A/B/C |
| `adi_value` | ADI 值（每日允许摄入量） |
| `health_warnings` | 健康警告（用 / 分隔的人群标签） |
| `note` | 备注说明 |

### 6.2 common_diseases.json — 常见疾病分类

```json
{
  "categories": [
    {
      "name": "分类名称",
      "diseases": [
        {"id": "disease_xxx", "name": "疾病名"}
      ]
    }
  ]
}
```

### 6.3 allergens.json — 过敏原分类

```json
{
  "categories": [
    {
      "name": "分类名称",
      "allergens": [
        {"name": "过敏原名", "examples": ["示例1", "示例2"]}
      ]
    }
  ]
}
```

### 6.4 common_drugs.json — 常见药物分类

```json
{
  "categories": [
    {
      "name": "分类名称",
      "drugs": [
        {"id": "drug_xxx", "name": "药物名"}
      ]
    }
  ]
}
```

### 6.5 drug_food_conflicts.json — 药物-食物冲突

```json
{
  "conflicts": [
    {
      "drug_id": "drug_xxx",
      "drug_name": "药物名",
      "food_keywords": ["关键词1", "关键词2"],
      "severity": "high/medium/low",
      "description": "冲突描述",
      "recommendation": "建议",
      "mechanism": "作用机制",
      "source": "数据来源"
    }
  ]
}
```

### 6.6 history.json — 历史记录摘要（自动生成）

```json
[
  {
    "timestamp": "2026-07-06T12:00:00",
    "product_name": "产品名",
    "score": 85,
    "type": "food",
    "additives_count": 3
  }
]
```

---

## 7. 状态管理（session_state）

### 7.1 核心状态

| 键名 | 类型 | 说明 |
|------|------|------|
| `page` | str | 当前页面：home/scan/result/history/detail/profile |
| `prev_page` | str | 上一页面，用于返回导航 |
| `legal_agreed` | bool | 是否已同意法律协议 |
| `onboarded` | bool | 是否已完成首次引导 |
| `onboarding_step` | int | 引导当前步骤（1-4） |
| `last_result` | dict | 最近一次识别结果（完整对象） |
| `last_speak_content` | str | 最近一次播报文本 |
| `tts_rate` | float | 语速：0.7/1.0/1.3 |
| `health_profile` | dict | 健康档案：name/age/diseases/allergens/drugs |
| `user_profile` | dict | 简化用户档案：drugs/allergens |
| `history` | list | 内存中的历史记录（同步自文件） |
| `selected_history_index` | int | 选中的历史索引（详情页用） |
| `model_choice` | str | 当前选择的模型 |
| `scan_upload_key` | int | 上传组件 key 计数器（重新选择用） |
| `history_filter` | str | 历史筛选标签：全部/安全/注意/高风险 |

---

## 8. 样式与主题

### 8.1 主题色（config.toml）

| 变量 | 值 | 用途 |
|------|----|------|
| `primaryColor` | `#1976D2` | 主色（蓝） |
| `backgroundColor` | `#FFFFFF` | 背景色 |
| `secondaryBackgroundColor` | `#F5F5F5` | 次要背景 |
| `textColor` | `#212121` | 文字颜色 |
| `font` | `sans serif` | 字体 |

### 8.2 风险等级色

| 等级 | 颜色 | 形状 | 文字 |
|------|------|------|------|
| A / 绿色 / 安全 | `#43A047` | ● 圆形 | 可放心食用 |
| B / 黄色 / 中等 | `#FF9800` | ▲ 三角 | 特定人群注意 |
| C / 红色 / 高风险 | `#E53935` | ■ 方块 | 建议咨询医生 |

### 8.3 关键 CSS 类

| 类名 | 作用 |
|------|------|
| `.top-nav-title` | 顶部导航标题（sticky 定位） |
| `.result-score-hero` | 评分英雄区 |
| `.result-card` | 结果卡片通用样式 |
| `.voice-float-bar` | 浮动语音播报栏（sticky bottom） |
| `.bottom-action-bar-marker` | 底部操作栏标记 |
| `.home-scan-area-marker` | 首页扫描区域标记 |
| `.scan-card-marker` | 扫描卡片标记 |
| `.preview-card-marker` | 预览卡片标记 |
| `.health-tag` | 健康标签样式 |
| `.history-card` | 历史卡片样式 |
| `.condition-card-wrapper` | 健康状况选择卡片 |

---

## 9. 安全与合规

### 9.1 安全措施清单

| 措施 | 位置 | 说明 |
|------|------|------|
| API key 环境变量注入 | `get_api_key()` | 不在代码中硬编码 |
| XSS 防护 | `_safe()` / `_js_attr_safe()` | 所有动态文本转义 |
| 文件上传限制 | `config.toml` maxUploadSize=5 | 防止大文件攻击 |
| XSRF 保护 | `config.toml` enableXsrfProtection | 跨站请求伪造防护 |
| CORS 保护 | `config.toml` enableCORS | 跨域资源共享限制 |
| 图片格式验证 | `render_scan_page()` | Image.verify() 验证有效图片 |
| 生产禁用 DEBUG | 多处检查 `os.getenv("DEBUG")` | 避免泄露 key 信息 |
| 图片数据不存储 | `add_history()` | 隐私保护，仅保存文字 |

### 9.2 合规要求

- 服务定位：技术展示 Demo，不构成医疗诊断建议
- 跨境传输：识别服务部署在境外（新加坡集群）
- 数据保护：不保存用户上传图片，健康档案仅会话级
- 强制免责：结果页必须显示「AI识别仅供参考，请以包装原文为准」
- 保健食品：必须展示「保健食品不是药物，不能代替药物治疗疾病」

---

## 10. 测试

### 10.1 测试框架

- 框架：pytest
- 位置：`tests/test_core.py`
- 用例数：17 个

### 10.2 测试覆盖

| 测试类 | 用例数 | 覆盖函数 |
|--------|--------|----------|
| `TestNormalizeAdditive` | 4 | `normalize_additive()` |
| `TestComputeScoreFromAdditives` | 4 | `compute_score_from_additives()` |
| `TestCheckDrugFoodConflicts` | 3 | `check_drug_food_conflicts()` |
| `TestParseResult` | 4 | `parse_result()` |
| `TestDataLoading` | 2 | 数据加载函数 |

### 10.3 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 生成测试报告
pytest tests/ --junitxml=test-report.xml

# 语法检查
python -m py_compile app.py
```

---

## 11. CI/CD

### 11.1 工作流（.github/workflows/ci.yml）

触发条件：push 到 main/develop 分支，或 PR 到 main

4 个 Job 并行/串行：

1. **lint（代码质量检查）**
   - black 格式检查
   - isort 导入排序检查
   - flake8 代码风格检查（max-line-length=120）

2. **test（单元测试）**
   - 安装依赖
   - pytest -v 运行
   - 生成 JUnit XML 报告
   - 上传报告 artifact

3. **security（安全扫描）**
   - safety：依赖漏洞扫描
   - bandit：代码安全扫描

4. **build（构建验证）**
   - py_compile 语法检查
   - 验证关键数据文件存在
   - 依赖 test 和 security

---

## 12. 本地运行

### 12.1 环境要求

- Python 3.10+
- 现代浏览器（支持 SpeechSynthesis API）
- MiMo Vision API Key

### 12.2 运行步骤

```bash
# 1. 克隆仓库
git clone https://github.com/gongyijie85/ai-food-scanner.git
cd ai-food-scanner

# 2. 安装依赖（推荐清华源）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 配置 API 密钥
cp .env.example .env
# 编辑 .env，填入 MIMO_API_KEY=tp-你的密钥

# 4. 启动应用
streamlit run app.py
# 浏览器打开 http://localhost:8501
```

### 12.3 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `MIMO_API_KEY` | 是 | MiMo Token Plan API 密钥 |
| `AGNES_API_KEY` | 否 | Agnes API 密钥（A/B 对比用） |
| `DEBUG` | 否 | 设为 1 开启调试模式（生产环境禁用） |

---

## 13. 部署（Streamlit Cloud）

### 13.1 部署步骤

1. Fork 或 clone 仓库到 GitHub
2. 登录 https://share.streamlit.io/
3. New app → 选择仓库 + `app.py`
4. Advanced settings → Secrets 填入：
   ```toml
   MIMO_API_KEY = "tp-你的密钥"
   ```
5. Deploy，等待 2-3 分钟

### 13.2 公开链接格式

```
https://<你的用户名>-ai-food-scanner.streamlit.app
```

---

## 14. 版本历史

详见 [CHANGELOG.md](file:///d:/GBT/ai-food-scanner/CHANGELOG.md)

### 最近版本

- **v0.4.5（2026-07-06）**：修复扫描页滚动问题、结果页 sticky 样式、顶部导航固定
- **v0.4.4（2026-07-05）**：卡片式扫描页布局，移除全屏遮罩
- **v0.4.3（2026-07-02）**：结果页字体放大、移动端语音修复
- **v0.4.1（2026-07-02）**：历史记录页、产品详情页对齐设计稿

---

## 15. 关键设计决策

### 15.1 为什么用 Streamlit 单文件而不是多页应用？

- 开发速度快，适合快速原型迭代
- 状态管理简单，session_state 全局共享
- 部署方便，Streamlit Cloud 一键部署
- 适老化 Demo 阶段不需要复杂路由

### 15.2 为什么客户端做 GB 2760 权威判定而不是完全信任模型？

- 模型可能幻觉或错误分类添加剂等级
- GB 2760 是国家标准，必须权威准确
- 客户端本地查表速度快，无额外 API 成本
- 评分公式可精确控制，避免模型不一致

### 15.3 为什么历史记录用本地 JSON 而不是数据库？

- Demo 阶段数据量小（最多 50 条）
- 无需用户账号系统，本地存储隐私性好
- 实现简单，无数据库依赖
- 后续升级到 SQLite 成本低

### 15.4 为什么语音播报用浏览器原生而不是 TTS API？

- 零依赖，零成本
- 离线可用（浏览器内置语音）
- 移动端兼容性好（用户手势触发即可播放）
- Microsoft Yaoyao 是 Windows 内置高质量中文女声

---

## 16. 后续优化方向

- [ ] v2.5 公开链接部署优化（性能、CDN）
- [ ] v3.0 SQLite 历史记录（替代 JSON 文件）
- [ ] v3.5 多模态（视频配料表识别）
- [ ] v4.0 微信小程序版
- [ ] 接入更多添加剂数据库（扩展 GB 2760 覆盖）
- [ ] 用户账号系统与云端同步
- [ ] 更多语言支持（粤语、英语等）

---

*本文档自动生成于 2026-07-06，对应版本 v0.4.5*
