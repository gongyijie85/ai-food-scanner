# 拍了就懂 · DESIGN.md

> Brand contract for agents (Open Design / coding agents) and engineers.
> Product: **拍了就懂** — AI food-ingredient scanner for elders + family caregivers.
> Runtime today: Streamlit + custom HTML/CSS. Prototypes: mobile-first HTML.
> Source of truth for live tokens: `.streamlit/style.css` (keep this file in sync when shipping).

---

## 1. Product essence

| Item | Value |
|------|--------|
| Chinese name | 拍了就懂 |
| One-liner | 拍配料表，马上听懂能不能放心给家人吃 |
| Primary users | 60+ 老人（自用）、带娃家长、子女代操作 |
| Primary device | 手机竖屏 390×844（iPhone 15 框）；平板次之；桌面仅兼容 |
| Core job | 3 秒内给出「一句话结论 + 能否听懂」；细节后置 |
| Non-job | 不装医疗诊断；不吓唬用户；不做信息堆叠的「专业仪表盘」 |

**Voice of UI copy:** 口语、短句、少术语。用「较友好 / 注意 / 建议少吃 / 待确认」，不用「A 级 / C 级 / UNMATCHED」。

---

## 2. Design principles (non-negotiable)

1. **结论优先** — 首屏必须同时看到：产品名、参考分、状态胶囊、一句话含义。语音入口在折叠屏高度内可达。
2. **少层级** — 结果页默认 ≤ 1 次滚动完成「听懂要不要买」；详情折叠，默认展示高风险项。
3. **适老可读** — 正文 ≥ 18px；主标题 ≥ 24px；分数数字 ≥ 48px。行高 1.5–1.75。
4. **大触控** — 主按钮高度 ≥ 48px；列表行 ≥ 56px；关键操作间距 ≥ 12px。
5. **色 + 形双编码** — 风险状态同时用颜色与形状（● 较友好 / ▲ 注意 / ■ 建议少吃），服务色弱用户。
6. **信任克制** — 免责声明始终可见但视觉降权；不出现「保证安全」「治疗」等医疗承诺文案。
7. **暖健康，不诊所** — 米白底 + 叶绿主色；避免冷灰医疗风、霓虹 SaaS 风、暗黑极客风。
8. **动效服务理解** — 分数可 count-up 一次；禁止无限旋转、闪烁、整页视差。尊重 `prefers-reduced-motion`。

---

## 3. Brand personality

| Axis | Position |
|------|----------|
| Tone | 温暖、稳妥、像懂行的家人，不是冷冰冰的检测仪 |
| Density | 宽松、卡片呼吸感；拒绝 bento 拥挤与装饰线 |
| Imagery | 实物包装、柔和植物绿；不用实验室烧瓶作为主 IP |
| Motion | 轻、短、一次；服务「读懂分数」，不是炫技 |

**Do:** 大圆角卡片、清晰分区、一条主 CTA（听结果 / 再扫一个）。  
**Don't:** 玻璃拟态堆叠、紫粉 AI 渐变、细线图标墙、多 Tab 抢结论。

---

## 4. Color

### 4.1 Core palette (shipped)

| Token | Hex | Role |
|-------|-----|------|
| `--color-primary` | `#2E7D32` | 主操作、链接、品牌 |
| `--color-primary-light` | `#E8F5E9` | 轻背景、选中底 |
| `--color-primary-dark` | `#1B5E20` | 按压态、深字 |
| `--color-primary-gradient` | `linear-gradient(135deg, #43A047 0%, #2E7D32 100%)` | 主按钮、安全态强调 |
| `--color-secondary` | `#FF9800` | 次强调、注意态 |
| `--color-secondary-light` | `#FFF3E0` | 注意底 |
| `--color-secondary-dark` | `#E65100` | 注意深色文字 |
| `--color-bg` | `#FAFAF5` | 页面底（暖米白） |
| `--color-bg-card` | `#FFFFFF` | 卡片 |
| `--color-text-primary` | `#212121` | 主文 |
| `--color-text-secondary` | `#616161` | 辅文 |
| `--color-text-tertiary` | `#9E9E9E` | 元信息、免责 |
| `--color-border` | `#E0E0E0` | 描边 |
| `--state-success` | `#43A047` | 较友好 / 安全 |
| `--state-warning` | `#FF9800` | 注意 / 待确认（与 secondary 对齐，UI 上优先橙而非纯黄以保证对比） |
| `--state-error` | `#E53935` | 建议少吃 / 高关注 |
| `--state-info` | `#1E88E5` | 信息提示（少用） |

### 4.2 Score / status mapping

| Class | Score band (default) | Pill copy (example) | Visual |
|-------|----------------------|---------------------|--------|
| `score-safe` | ≥ 80 | 暂未发现明显问题 | 绿环 + 绿胶囊 |
| `score-caution` | 60–79 | 有可留意项 | 橙环 + 橙胶囊 |
| `score-danger` | < 60 | 含需关注成分 | 红环 + 红胶囊 |

Additive row labels:

| Level / status | Label | Color | Shape |
|----------------|-------|-------|-------|
| A / rated friendly | 较友好 | `#43A047` | ● |
| B / caution | 注意 | `#FF9800` | ▲ |
| C / high concern | 建议少吃 | `#E53935` | ■ |
| pending_rating | 待确认 | `#FF9800` | ▲ |
| unmatched | 待核对包装 | `#9E9E9E` | — |

**Contrast rule:** 正文与底对比 ≥ 4.5:1；状态色不单独承载语义（必须有文字标签）。

---

## 5. Typography

| Token | Size | Weight | Use |
|-------|------|--------|-----|
| Display / score | 48–56px | 700 | 配料参考分 |
| H1 product name | 24–30px | 700 | 结果页产品名 |
| H2 card title | 20–24px | 600–700 | 区块标题 |
| Body LG | 20px | 400–500 | 一句话结论、主说明 |
| Body | 18px | 400 | 默认正文 |
| Body SM | 16px | 400 | 次要说明 |
| Caption | 14px | 400 | 时间戳、免责、元数据（不可单独承载关键结论） |

**Font stacks**

- CN UI: `"PingFang SC", "Source Han Sans CN", "Noto Sans SC", "Microsoft YaHei", -apple-system, sans-serif`
- Numbers: `"Roboto", "DIN Alternate", "Helvetica Neue", Arial, sans-serif`

**Line height:** body 1.5–1.75；标题 1.25。  
**Max line length on mobile:** 约 18–22 汉字宽感（靠 padding，不强制 `ch`）。

---

## 6. Layout & spacing

| Token | Value |
|-------|-------|
| Page padding | 16–20px |
| Card padding | 16–20px |
| Card gap | 16px |
| Section gap | 16–24px |
| Radius sm/md/lg/xl | 8 / 12 / 16 / 24px |
| Min touch | 48×48px |
| Min list row | 56px |
| Bottom nav + safe area | 预留 ~72px + 34px，内容不被挡 |
| Content max width (desktop) | 480–560px 居中可读；结果页不以宽桌面多栏抢戏 |

**Mobile frame for prototypes:** 390×844, status bar + home indicator optional; bottom tab bar 首页 / 扫描 / 历史 / 我的 when showing app chrome.

---

## 7. Components (result-critical)

### 7.1 Top nav
- 左：返回；中：识别结果；右可空。
- Sticky；底部分割线浅灰；高度约 44–52px。

### 7.2 Score card (`score-hero`)
- 上：左产品名 +「配料表识别于 {date}」；右大分数圆（环 + 数字 +「配料参考分」）。
- 中：状态胶囊（图标 + 文案）+ 副标题一句话。
- 下：免责一行 + 可选「慢速再读一遍」。
- 禁止：高分却写恐吓文案；分数与添加剂等级明显矛盾时以添加剂驱动文案（见产品逻辑）。

### 7.2b Family verdict（一句话）
- 紧接分数卡：左色条 +「一句话」+ 口语结论（`给家人：…`）。
- tone：`safe` / `caution` / `danger`，由 `family_conclusion_for_result` 生成。
- 例：「给家人：可以偶尔吃 · 留意阿斯巴甜」；禁医疗承诺。

### 7.3 Voice CTA
- 主按钮文案：**听结果**；播放中：**正在读… 可点停止**（可橙态）。
- 位置：一句话结论下方、添加剂列表上方（少滚动）。
- 辅文：微信内无声提示；次操作：停止 / 语速。

### 7.5 Additive list（补充）
- **默认只展示需留意项**（B/C/待确认/待核对）；较友好 A 级折叠为「展开较友好的 N 项」。

### 7.4 Personal warnings
- 仅当有档案命中时出现。
- 每条：图标 + 短标题 + 一行说明；高对比警告底，但不使用闪烁。

### 7.5 Additive list
- 标题：添加剂清单。
- 默认展示前 5 条高风险优先；「展开全部」。
- 行：名称 + 等级标签（色+形）+ 可选功能一句；CNS/INS 次要。
- 空态：未识别到食品添加剂（正向表述）。

### 7.6 Ingredients
- 标签云为主；与 OCR 重复时不双显。
- 空态：教用户如何重拍（光线、平行、占满画面）。

### 7.7 Bottom actions
- 双主操作：**再扫一个** | **返回首页**，触控高度 ≥ 48px。
- **手机（&lt;768px）：纵向堆叠、全宽**，降低误触、便于拇指操作（与并排双栏相比优先适老）。
- **桌面 / 宽屏：等宽并排** 两列。

---

## 8. Motion

| Effect | Spec |
|--------|------|
| Score count-up | 0 → N，约 600–900ms，ease-out，只播一次 |
| Score ring pulse | 最多 2 次，低幅度 |
| Page enter | 可选 200ms fade |
| Reduced motion | 取消 count-up 与 pulse，瞬时到位 |

禁止：持续旋转 ring、骨架屏无限闪、视差滚动。

---

## 9. Content & compliance

- 默认免责：「结果仅供参考，不能代替医生诊断。身体不适或患有疾病，请先咨询医生。」
- 语音稿结构：产品 + 分数 → 需留意 → 添加剂摘要 → 建议 → 免责。
- 禁止：治愈、保证安全、绝对安全、可代替医嘱。
- 保健食品：单独红色提示条——「保健食品不是药物，不能代替药物治疗疾病」。

---

## 10. Accessibility checklist

- [ ] 触控目标 ≥ 48px
- [ ] 正文 ≥ 18px，对比 ≥ 4.5:1
- [ ] 状态有文字 + 形状，不只靠颜色
- [ ] 焦点可见（Web 原型）
- [ ] 图片/图标有文本等价（按钮 aria-label）
- [ ] 尊重 reduced-motion
- [ ] 关键结论不放在仅图标或仅颜色里

---

## 11. Anti-patterns (reject in review)

- AI 紫粉霓虹渐变、玻璃拟态多层模糊
- 仪表盘式 KPI 墙抢掉「一句话结论」
- 细 12px 脚注当主信息
- 「待确认」刷屏却不解释用户该怎么办
- 配料标签与 OCR 原文双份相同内容
- Streamlit 默认小控件观感直接当最终视觉（原型应做到产品级）

---

## 12. Prototype → product handoff

| Prototype (Open Design HTML) | Product (Streamlit) |
|------------------------------|---------------------|
| `DESIGN.md` tokens | `.streamlit/style.css` `:root` |
| Score card markup | `components/score_hero.py` |
| Additive rows | `components/additive_card.py` |
| Voice CTA | `components/voice_panel.py` |
| Page order | `pages/result.py` `render_food_page` |
| Static previews archive | `design/*_preview.html` |

**Handoff rule:** 先冻结交互顺序与文案，再搬 CSS；不要一次性重写 Streamlit 架构。

---

### 7.0 Home & History
- 首页主 CTA 统一文案 **拍配料表**；副标与扫描一致：对准「配料表」/ 光线够·尽量平·字要大。
- 历史筛选：**全部 | 要注意 | 较省心**（要注意 = 分数 &lt; 80）。
- 列表状态文案：**较省心 / 要注意 / 建议少吃**（不用「良好/高风险」恐吓感）。

### 7.8 Scan page（拍得清）
- 英雄文案：对准「配料表」；取景四角框示意。
- **三步卡片**：光线够 / 尽量平 / 字要大。
- **对比图**：清晰 ✓ vs 模糊 ✗（`design/demo_assets/demo_case_*.png`）。
- **失败态**：禁「JSON」等技术词；复盘三步 + 对比图 +「知道了，我重新拍」。
- 上传前提醒：确认是配料表那一面。

## 13. Open Design usage notes

- Preferred template: **mobile-app** / multi-screen flow, device frame iPhone 15 Pro.
- Design system name in OD: **拍了就懂** (this file).
- Generate **3 directions max** per brief; pick one before engineering.
- Primary screen to iterate first: **识别结果页（普通食品）**.
- Secondary: 扫描页、首页（同一 DESIGN.md）。

When the agent reads this file, treat every section as a hard constraint unless the brief explicitly overrides for A/B exploration — and even then, **适老字号与结论优先**不可推翻。
