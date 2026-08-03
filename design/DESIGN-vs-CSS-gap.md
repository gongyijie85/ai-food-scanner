# DESIGN.md ↔ 线上样式对照清单

> **范围：** `design/DESIGN.md` vs 实际注入的 `.streamlit/style.css`（`app.py` 唯一注入）及结果页相关组件。  
> **不改代码** — 仅对照与优先级建议。  
> **日期：** 2026-08-03  

**对照源**

| 契约 | 线上主路径 |
|------|------------|
| `design/DESIGN.md` | `.streamlit/style.css` |
| 组件语义 | `components/score_hero.py`, `additive_card.py`, `voice_panel.py`, `pages/result.py` |
| 旁路文件（**未注入**） | `colors_and_type.css` — 易误导 agent，勿当线上 token |

---

## 总览

| 维度 | 对齐度 | 说明 |
|------|--------|------|
| 主色 / 背景 / 中性色 | **高** | primary `#2E7D32`、bg `#FAFAF5`、正文色一致 |
| 间距 / 圆角 / 触控变量 | **高** | `:root` 已声明 min-touch 48、card-gap 16 等 |
| 结果页信息顺序 | **高** | `render_food_page` 与 DESIGN §7 一致 |
| 适老动效策略 | **高** | pulse×2、无旋转 ring、`prefers-reduced-motion` |
| 注意态色 / 对比 | **高（已修）** | `--state-warning` → `#FF9800` |
| 分数卡字号层级 | **高（已修）** | 品名 24 / 分数 48 |
| 次要控件触控 | **高（已修）** | btn-replay ≥48 |
| 桌面结果栏宽 | **中** | 900px 宽于「可读栏 480–560」建议 |
| Token 单一事实源 | **中** | 双 CSS 文件 + 组件内硬编码色 |

---

## A. 已对齐（无需为对齐而改）

| DESIGN 要求 | 线上证据 |
|-------------|---------|
| primary `#2E7D32` + light/dark/gradient | `style.css` L8–11 |
| secondary 橙系 `#FF9800` | L12–14 |
| bg `#FAFAF5`、卡片白、正文 `#212121` | L23–31 |
| body 18 / body-lg 20 / caption 14 | L45–52；手机 body 提到 19–21 |
| radius 8/12/16/24 | L75–78 |
| min-touch 48、list 56 | L100–101 |
| 移动端底栏预留 | L108–109 |
| score-safe / caution / danger 背景分流 | L3467–3505 |
| score 入场 + pulse 2 次 + reduced-motion | L3557–3744 |
| ring **不**持续旋转 | `.score-ring` 静态虚线 L3572–3579 |
| 听结果：手机全宽 ≥56px、叶绿渐变 | L1904–1928 |
| 添加剂色+形（●▲■）+ 中文标签 | `additive_card.py` 内联色与 shape |
| 结果页顺序：分数→警告→语音→添加剂→建议→配料→底栏 | `result.py` `render_food_page` |
| 免责在分数卡底部 | `score_hero.py` |

---

## B. 缺口清单（按优先级）

### P0 — 影响可读 / 语义对比（建议优先修）

| ID | DESIGN | 线上现状 | 影响 | 建议落点 |
|----|--------|----------|------|----------|
| **G1** | 注意态 / warning 用 **`#FF9800`**（与 secondary 对齐，保证对比） | `--state-warning: **#FDD835**`（亮黄） | `score-caution` 分数环 `color: var(--state-warning)` → 黄环在白底上偏弱；legend-b / 部分左边框也偏「黄」而非「橙」 | `style.css` L18：改为 `#FF9800`（或新增 `--state-caution` 并替换 score-caution 引用） |
| **G2** | 分数数字 **≥ 48px**（display 可用 52–56） | `.score-number { font-size: **40px** }` | 首屏「一眼读分」弱于契约 | L3593–3598 → `48px` 或 `var(--font-size-display)` 缩放；圆可略大于 110px |
| **G3** | 产品名 **H1 24–30px** | `.product-name` 用 **`--font-size-h3`（20px）** | 结论层级被压过状态副文 | L3521–3523 → `h2`（24）或 `h1`（30） |

### P1 — 体验与适老触控

| ID | DESIGN | 线上现状 | 影响 | 建议落点 |
|----|--------|----------|------|----------|
| **G4** | 主结论/胶囊偏 **body-lg（20）** | `.status-pill` 为 **body-sm（16）** | 状态胶囊偏「标签」不像「结论」 | L3625 → body / body-lg；padding 略增 |
| **G5** | 触控 ≥ **48×48** | `.btn-replay` padding `6px 12px`、字 caption **14**、svg 14px | 「慢速再读」难点，尤其老人 | 增高 min-height 48、字号 ≥16 |
| **G6** | 一句话结论 body **≥18** 且足够醒目 | `.score-card-subtitle` 已是 body 18，但 caution/danger 用深橙/红 **整句染色** | 长说明可读性尚可，但「说明」与「警告色」绑死，弱视时刺眼 | 可保持标签染色、副文用 secondary 灰 + 加粗首句（可选） |
| **G7** | 底栏双按钮 **等宽并排** | 手机 `@media max 767` 强制 **纵向堆叠**（L2002–2008） | 与 DESIGN 示意不一致；**实际更适老** | **契约可修订为「手机堆叠、桌面并排」**，避免按错 brief 改坏 |

### P2 — 布局 / 信息密度

| ID | DESIGN | 线上现状 | 影响 | 建议落点 |
|----|--------|----------|------|----------|
| **G8** | 桌面结果 **可读宽 480–560** 居中 | `.device-desktop .stMainBlockContainer { max-width: **900px** }` | 结果页在大屏过宽、行过长 | 结果页专用 class 或 560–640 max-width；扫描/历史可保持更宽 |
| **G9** | 配料标签可读 | 手机 `.ingredient-tag` **16px**（&lt; body 18） | 次要信息可接受；若当主读路径则偏小 | 可选 17–18px |
| **G10** | 首屏「听结果」在折叠高度内 | 顺序已对；Streamlit chrome + user_guide 仍可能挤出首屏 | 设备相关 | 原型验证后考虑折叠指引 / 减 caption |

### P3 — 工程卫生（不直接影响一帧 UI）

| ID | DESIGN | 线上现状 | 影响 | 建议落点 |
|----|--------|----------|------|----------|
| **G11** | 单一 token 源 | `colors_and_type.css` 另一套：base **15**、xs **11**、bg `#f8faf8`、绿阶 Tailwind 风 | Agent/新人可能改错文件；**app 不注入** | README 标明废弃或删/改指向 `style.css`；或与 DESIGN 合并后删除 |
| **G12** | 状态色走 token | `additive_card.py` 硬编码 `#43A047` / `#FF9800` / `#E53935` / `#9E9E9E` | 与 DESIGN 标签色一致，但改 CSS 变量不会生效 | 长期：CSS class + token；短期可接受 |
| **G13** | 图例文案「橙色三角」 | 图例写 **「黄色三角：适量注意」** 而色是 `#FF9800` | 文案与色不一致 | `additive_card.py` legend 改为「橙色三角：注意」 |
| **G14** | score-danger 背景 token | 硬编码 `#FFEBEE` / 字 `#C62828` | 功能正确，未进 `:root` | 可选 `--state-error-bg` / `--state-error-text` |

---

## C. 组件级核对（结果页）

| 组件 | DESIGN § | 对齐 | 备注 |
|------|----------|------|------|
| Top nav | 7.1 | 基本 | 高度 44 变量在；实现依赖 Streamlit 结构 |
| Score card | 7.2 | **部分** | G2/G3/G4/G1 |
| Voice CTA | 7.3 | **好** | 手机强化已做 |
| Personal warnings | 7.4 | 基本 | 未逐条对照字号 |
| Additive list | 7.5 | **好**（语义） | G12/G13 文案与 token |
| Ingredients | 7.6 | 好 | 去重逻辑在 Python；G9 字号 |
| Bottom actions | 7.7 | 手机堆叠 | G7 建议改契约而非强行并排 |

---

## D. Token 速查表（契约 vs `:root`）

| Token / 角色 | DESIGN.md | `style.css` | 判定 |
|--------------|-----------|-------------|------|
| primary | `#2E7D32` | `#2E7D32` | OK |
| primary-light | `#E8F5E9` | `#E8F5E9` | OK |
| secondary | `#FF9800` | `#FF9800` | OK |
| bg | `#FAFAF5` | `#FAFAF5` | OK |
| text-primary | `#212121` | `#212121` | OK |
| success | `#43A047` | `#43A047` | OK |
| warning / 注意 | **`#FF9800`** | **`#FDD835`** | **GAP G1** |
| error | `#E53935` | `#E53935` | OK |
| body | 18px | 18px（手机 19） | OK |
| score number | ≥48 | **40** | **GAP G2** |
| product name | 24–30 | **20 (h3)** | **GAP G3** |
| min-touch | 48 | 变量 48；replay 未用满 | **GAP G5** |
| desktop content max | 480–560 结果 | 容器 **900** | **GAP G8** |

`colors_and_type.css`（未注入）对照：

| 项 | colors_and_type | 与 DESIGN/线上 |
|----|-----------------|---------------|
| bg | `#f8faf8` | 不一致 |
| base font | 15px | 小于适老 18 |
| xs | 11px | 禁止用于结论 |

---

## E. 建议实施顺序（仍不动代码，仅排期）

1. **G1** 注意色黄→橙（改一行 token，连带 score-caution 环对比）  
2. **G2 + G3** 分数与产品名字号（结果页首屏）  
3. **G5 + G4** 慢速重听触控 + 状态胶囊字号  
4. **G13** 图例「黄→橙」文案（零风险）  
5. **G7** 回写 DESIGN：手机底栏堆叠为合法  
6. **G11** 处理 `colors_and_type.css` 歧义  
7. **G8** 桌面结果栏宽（可等 OD 原型冻结后）  

**明确不做（验证前）：** 全站 React 重写、为对齐 OD 像素而推翻 Streamlit 布局。

---

## F. 与 Open Design 的关系

- 出原型时以 **`DESIGN.md` 为准**（橙注意态、48px 分、24px 品名）。  
- 回灌 Streamlit 时按 **E 顺序** 改 `style.css` / 组件，本表当验收 checklist。  
- 若 OD 原型故意试「更冷静 B 方向」，冻结前 **不要** 把实验色写进 `style.css`。

---

## G. 验收勾选（工程回灌后）

- [x] `--state-warning` 对比满足注意环可见（或 score-caution 不再用亮黄） — **2026-08-03：改为 #FF9800**
- [x] 手机结果页：产品名 ≥24、分数 ≥48 — **h2 24px / score-number 48px**
- [x] 慢速再读 min-height ≥48 — **btn-replay min-height + body-sm**
- [x] 图例文案与色一致（橙/绿/红） — **橙色三角：注意**
- [x] `colors_and_type.css` 不再被误用为 source of truth — **文件头已标注 NOT INJECTED（G11 轻量）**
- [x] `prefers-reduced-motion` 仍生效 — **未改动该块**
- [x] G4 状态胶囊 body-lg — **已做**
- [x] G7 契约修订手机底栏堆叠 — **DESIGN.md §7.7**
