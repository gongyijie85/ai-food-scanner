# 食品添加剂俗名映射修复计划

## Summary

用户扫描「东方树叶黑乌龙茶饮料」后，识别结果把「维生素 C」标为"未在 GB 2760 库中，按黄色（注意）兜底"。

根因：**GB 2760 风险库中记录的是标准名「抗坏血酸」，而 AI/OCR 输出的是俗名「维生素 C」**，现有匹配逻辑没有同义词/别名映射，导致常见安全添加剂被误标为"未在库中"。

本计划建立一套独立的「俗名 → GB 2760 标准名」映射机制，并批量补充超市常见食品（饮料、调味品、烘焙、冻品、乳制品等）中的高频俗名，让识别结果更准确。

---

## Current State Analysis

### 数据文件

- `data/gb2760_risk.csv`：GB 2760 食品添加剂风险库，主键是 `cn_name`（标准名）。第 6 行已有 `抗坏血酸`，但没有「维生素 C」这个俗名。
- 缺少同义词/别名映射表。

### 匹配逻辑

- `repositories/additive_risk.py` 中的 `CsvAdditiveRiskRepository.find(name)` 依次做：
  1. 精确匹配
  2. 清洗括号/空格/INS 号后匹配
  3. 长度差 ≤2 的模糊包含匹配
- `services/additive_matcher.py` 中的 `AdditiveMatcher.classify(name)` 调用 `repository.find(n)`，未命中则返回 B 级兜底。

### 问题复现

输入 "维生素 C" → 未命中 "抗坏血酸" → 返回 B 级 + "未在 GB 2760 库中"。

---

## Proposed Changes

### 1. 新增独立同义词表 `data/additive_synonyms.csv`

**为什么独立？**

- 不与 `gb2760_risk.csv` 耦合，避免破坏现有库结构和加载逻辑。
- 支持「多对一」映射：多个俗名可以指向同一个标准名。
- 后续维护只需追加行，不需要改动风险等级数据。

**表结构：**

```csv
synonym,canonical_name,note
维生素C,抗坏血酸,抗氧化剂/营养强化剂
维生素 C,抗坏血酸,含空格写法
维他命C,抗坏血酸,别名
小苏打,碳酸氢钠,膨松剂/酸度调节剂
食用碱,碳酸钠,酸度调节剂
泡打粉,碳酸氢钠,复合膨松剂（主要成分）
味精,谷氨酸钠,增味剂
酵母提取物,酵母抽提物,增味剂
...
```

**首批覆盖范围（约 50+ 条）：**

- 维生素/营养强化剂：维生素C、维生素E、维生素D、烟酸、烟酰胺等
- 膨松/酸度调节：小苏打、食用碱、泡打粉、塔塔粉、明矾等
- 增味剂：味精、鸡精（主要标谷氨酸钠/呈味核苷酸二钠）、酵母提取物等
- 抗氧化剂：BHT、BHA、TBHQ、茶多酚等
- 防腐剂：山梨酸、苯甲酸、纳他霉素等
- 乳化/稳定：卡拉胶、黄原胶、瓜尔豆胶、明胶、果胶等
- 甜味剂：阿斯巴甜、木糖醇、赤藓糖醇、甜菊糖、罗汉果甜苷等
- 色素：日落黄、柠檬黄、胭脂红、诱惑红、亮蓝、焦糖色等
- 其他：食用香精（已在黑名单）、叶绿素铜钠盐等

### 2. 修改 `repositories/additive_risk.py`

- `CsvAdditiveRiskRepository.__init__` 新增加载同义词表逻辑。
- 新增 `_synonyms: Dict[str, str]`，把 synonym 映射到 canonical_name。
- 在 `find(name)` 最前面插入一步：
  - 如果输入名命中同义词表，先用 canonical_name 查风险库。
  - 再回退到原有精确/清洗/模糊匹配。

示例：

```python
def find(self, name: str) -> Optional[AdditiveRisk]:
    n = name.strip()
    if not n:
        return None

    # 0) 同义词映射
    canonical = self._synonyms.get(n)
    if canonical and canonical in self._data:
        return self._data[canonical]

    # 1) 精确匹配
    ...
```

### 3. 修改 `services/additive_matcher.py`（可选微调）

- 如果同义词映射在 repository 层实现，matcher 基本无需改动。
- 保持黑名单、保健品辅料白名单逻辑不变。

### 4. 新增/更新测试

- `tests/test_core.py` 新增 `TestAdditiveSynonyms`：
  - 「维生素 C」应映射到「抗坏血酸」并返回 A 级。
  - 「小苏打」应映射到「碳酸氢钠」并返回 A 级。
  - 「味精」应映射到「谷氨酸钠」。
  - 同义词匹配优先级高于模糊匹配（避免"维生素 C"误匹配到别的条目）。

### 5. 数据验证脚本（可选）

- 新增一次性校验：检查 `additive_synonyms.csv` 中的 `canonical_name` 是否都存在于 `gb2760_risk.csv`，避免映射到不存在的标准名。

---

## Assumptions & Decisions

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 同义词表位置 | 独立 `data/additive_synonyms.csv` | 解耦、易维护、支持多对一 |
| 映射时机 | repository.find() 最前端 | 对 matcher 和 score 层透明，改动最小 |
| 首批覆盖数量 | 50+ 常见俗名 | 覆盖饮料、调味品、烘焙、冻品、乳制品 |
| 不匹配策略 | 保持现有 B 级兜底 | 宁严勿宽，只把确认安全的俗名升回 A |
| 空格/大小写 | 同义词表去空格、统一大小写后匹配 | 提高 OCR 输出容错 |

---

## Verification Steps

1. 运行 `python -m pytest tests/ -v`，新增同义词测试通过。
2. 运行 `python -m black --extend-exclude "(__pycache__|\.venv|venv|\.worktrees)" .` 无变更。
3. 运行 `python -m flake8 . --max-line-length=120 --ignore=E501,W503,E402 --exclude=__pycache__,.venv,venv,.worktrees` 无报错。
4. 本地用测试脚本验证：
   - `normalize_additive("维生素 C")` 返回 `("A", "", "维生素C/抗氧化剂")` 类似结果。
   - `normalize_additive("小苏打")` 返回 A 级。
5. 部署后重新扫描茶饮料截图，"维生素 C" 应显示为 A 级绿色/可食用，不再提示"未在 GB 2760 库中"。

---

## Out of Scope

- 不修改 GB 2760 风险等级本身（只加映射，不改 A/B/C 判定）。
- 不新增药物-食物冲突数据。
- 不改 AI 提示词/OCR 识别流程（在匹配层做容错）。
