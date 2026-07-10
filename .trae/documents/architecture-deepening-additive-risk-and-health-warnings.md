# 架构深化计划：GB 2760 适配器 + 健康风险提示引擎

## 摘要

当前 `utils/score.py` 同时承担「添加剂名称匹配」「GB 2760 风险库查询」「评分计算」「药物-食物冲突检查」四项职责，且结果页缺少对食品原料（如氢化植物油、高糖）的健康风险提示。

本计划将：
1. 把 GB 2760 CSV 加载封装成 `AdditiveRiskRepository` 接口（候选 2）
2. 建立 `HealthWarningEngine` 模块，统一输出健康警告（候选 6）
3. 让 `utils/score.py` 只保留评分公式，调用新的深度模块

## 当前状态分析

### 已确认的关键代码

- `utils/data.py`：
  - `load_gb2760_risk()` 直接读取 `data/gb2760_risk.csv`，返回 `dict[中文名, {level, adi, warnings, note}]`
  - 使用 `@st.cache_resource` 装饰，与 Streamlit 运行时耦合
- `utils/score.py`：
  - `normalize_additive()`：清洗名称、黑名单过滤、GB 2760 精确/模糊匹配，未匹配默认 B 级
  - `compute_score_from_additives()`：基于风险等级和人群敏感性计算 0-100 分
  - `check_drug_food_conflicts()`：遍历配料检查药物冲突
  - 硬编码 `ADDITIVE_BLOCKLIST` 和 `SUPPLEMENT_EXCIPIENTS`
- `pages/result.py`：
  - 调用 `utils.score.compute_score_from_additives()` 和 `check_drug_food_conflicts()`
  - 健康建议只展示 `advice` 文本，没有针对高糖/高钠/反式脂肪的原料级警告
- `components/personal_warnings.py`：
  - 负责渲染个人警告（疾病、过敏、药物冲突），但逻辑不在统一引擎中

### 当前摩擦点

1. **CSV 风险库的 seam 是隐式的**：`score.py` 直接依赖 `load_gb2760_risk()`，CSV 路径、列名、缓存策略泄露到业务层。
2. **匹配逻辑与评分逻辑混在一起**：修改「大豆磷脂」的匹配规则需要改 `score.py` 中的 `normalize_additive()`；修改评分公式需要改 `compute_score_from_additives()`。
3. **健康警告缺少统一的领域模块**：药物冲突、过敏原、人群建议分散在不同位置；食品原料风险（氢化植物油、高糖）完全没有判定逻辑。
4. **测试依赖 Streamlit 缓存**：`load_gb2760_risk()` 被 `@st.cache_resource` 装饰，单元测试需要 mock Streamlit。

## 拟议变更

### 变更 1：创建 GB 2760 适配器层

**新增文件：**

- `repositories/__init__.py`
- `repositories/additive_risk.py`

**内容：**

```python
# repositories/additive_risk.py
from abc import ABC, abstractmethod
from typing import Dict, Optional

class AdditiveRisk:
    def __init__(self, level: str, adi: str, warnings: str, note: str):
        self.level = level
        self.adi = adi
        self.warnings = warnings
        self.note = note

class AdditiveRiskRepository(ABC):
    @abstractmethod
    def find(self, name: str) -> Optional[AdditiveRisk]:
        ...

class CsvAdditiveRiskRepository(AdditiveRiskRepository):
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._data: Dict[str, AdditiveRisk] = {}
        self._load()

    def _load(self):
        # 原 load_gb2760_risk 的 CSV 解析逻辑迁移到这里
        # 不依赖 @st.cache_resource
        ...

    def find(self, name: str) -> Optional[AdditiveRisk]:
        # 原 normalize_additive 中的精确匹配和清洗后匹配迁移到这里
        ...
```

**修改文件：**

- `utils/data.py`：保留原始加载函数 `_load_gb2760_risk_raw()`（无缓存），新增带缓存的包装函数 `load_gb2760_risk()` 调用 `CsvAdditiveRiskRepository`
- `utils/score.py`：
  - 删除 `load_gb2760_risk` 的直接使用
  - `normalize_additive()` 改为接收 `AdditiveRiskRepository` 实例
  - `compute_score_from_additives()` 通过 repository 查询风险等级

### 变更 2：拆分添加剂匹配器

**新增文件：**

- `services/__init__.py`
- `services/additive_matcher.py`

**内容：**

```python
# services/additive_matcher.py
class AdditiveMatcher:
    def __init__(self, repository: AdditiveRiskRepository):
        self.repository = repository

    def classify(self, name: str) -> AdditiveMatchResult:
        # 1. 清洗名称
        # 2. 黑名单检查 -> A 级
        # 3. 保健品辅料白名单 -> A 级
        # 4. repository.find 精确匹配
        # 5. 模糊匹配兜底
        ...
```

**修改文件：**

- `utils/score.py`：
  - 删除 `_clean_name`、`_is_blocklisted`、`is_supplement_excipient`、`normalize_additive`
  - 引入 `AdditiveMatcher`

### 变更 3：建立健康风险提示引擎

**新增文件：**

- `services/health_warning_engine.py`

**内容：**

```python
# services/health_warning_engine.py
from dataclasses import dataclass
from typing import List

@dataclass
class HealthWarning:
    category: str  # "drug_conflict", "allergen", "disease", "ingredient_risk"
    severity: str  # "high", "medium", "low"
    title: str
    description: str

class HealthWarningEngine:
    def __init__(
        self,
        additive_matcher: AdditiveMatcher,
        conflict_repository,  # 未来可替换
        allergen_data,
    ):
        self.additive_matcher = additive_matcher
        self.conflict_repository = conflict_repository
        self.allergen_data = allergen_data

    def analyze(
        self,
        result: dict,
        health_profile: dict,
    ) -> List[HealthWarning]:
        warnings = []
        warnings.extend(self._check_drug_conflicts(result, health_profile))
        warnings.extend(self._check_allergens(result, health_profile))
        warnings.extend(self._check_disease_warnings(result, health_profile))
        warnings.extend(self._check_ingredient_risks(result, health_profile))
        return warnings

    def _check_ingredient_risks(self, result, health_profile):
        # 新增：针对氢化植物油、高糖、高钠等原料的警告
        ...
```

**食品原料风险规则（首期）：**

| 原料关键词 | 触发条件 | 警告文案示例 | 关联人群 |
|---|---|---|---|
| 氢化植物油 | ingredients 中含「氢化植物油」 | 含有氢化植物油，可能含反式脂肪酸，心血管/脑梗人群建议避免 | 脑梗/心血管 |
| 白砂糖/葡萄糖浆/麦芽糖浆/果葡糖浆 | 排在前三位 | 糖分较高，糖尿病患者请注意控制摄入量 | 糖尿病 |
| 食用盐/食盐/海盐 | 排在前三位 | 钠含量可能较高，高血压患者请关注 | 高血压 |

**修改文件：**

- `utils/score.py`：把 `check_drug_food_conflicts()` 逻辑迁移到 `HealthWarningEngine._check_drug_conflicts()`；保留一个兼容函数作为薄封装，避免一次性改太多调用方。
- `components/personal_warnings.py`：改为接收 `List[HealthWarning]` 并渲染。
- `pages/result.py`：
  - 实例化 `HealthWarningEngine`
  - 调用 `engine.analyze(result, profile)` 得到警告列表
  - 把警告列表传给 `personal_warnings.render()`
  - 原有的 `check_drug_food_conflicts()` 调用替换为 engine 调用

### 变更 4：调整缓存策略

**修改文件：**

- `utils/data.py`：
  - 把 CSV 解析逻辑迁移到 `repositories/additive_risk.py`
  - 保留一个轻量包装：
    ```python
    @st.cache_resource
    def get_additive_risk_repository():
        return CsvAdditiveRiskRepository(_GB2760_RISK_PATH)
    ```
  - 其他模块通过 `get_additive_risk_repository()` 获取 repository

## 文件变更清单

### 新增
- `repositories/__init__.py`
- `repositories/additive_risk.py`
- `services/__init__.py`
- `services/additive_matcher.py`
- `services/health_warning_engine.py`

### 修改
- `utils/data.py`
- `utils/score.py`
- `utils/helpers.py`（如有需要，新增 `get_additive_risk_repository` 辅助函数）
- `components/personal_warnings.py`
- `pages/result.py`
- `tests/test_core.py`（更新测试）

### 可能新增测试
- `tests/repositories/test_additive_risk.py`
- `tests/services/test_additive_matcher.py`
- `tests/services/test_health_warning_engine.py`

## 假设与决策

1. **不改变外部行为**：评分公式、黑名单、白名单内容保持不变；只是移动代码位置。
2. **Streamlit 缓存仍然保留**：但只保留在 `utils/data.py` 的薄包装层，业务模块不感知。
3. **健康警告首期只加原料级风险提示**：不改动 AI prompt，只基于已有 `ingredients` 列表做关键词匹配。
4. **向后兼容**：`utils.score.check_drug_food_conflicts()` 在迁移期间保留为薄封装，避免一次性改太多文件。
5. **数据文件路径不变**：仍然使用 `data/gb2760_risk.csv`。

## 验证步骤

1. **单元测试**
   - `pytest` 51 项原有测试全部通过
   - 新增 `AdditiveRiskRepository` 测试：精确匹配、清洗后匹配、模糊匹配
   - 新增 `AdditiveMatcher` 测试：黑名单、辅料白名单、未匹配兜底
   - 新增 `HealthWarningEngine` 测试：药物冲突、过敏原、原料风险（氢化植物油）

2. **静态检查**
   - `python -m py_compile` 全文件通过
   - `python -m black --check --diff` 通过

3. **功能验证**
   - 用阿尔卑斯巧克力截图测试：
     - 大豆磷脂/乳酸/乳酸钠识别正确（GB 2760 库问题需同步更新数据文件，超出本计划范围）
     - 出现「氢化植物油含反式脂肪酸」警告
   - 用山楂糕测试：评分保持 100

## 风险

- 迁移期间 `utils/score.py` 接口变化可能导致页面调用失败。通过保留兼容函数降低风险。
- 新增模块目录 `repositories/`、`services/` 可能需要在 `app.py` 中调整 `sys.path` 以确保 Streamlit Cloud 能正确导入。
