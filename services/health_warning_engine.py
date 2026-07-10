"""健康风险提示引擎：统一生成药物冲突、过敏原、人群敏感、原料风险警告."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from services.additive_matcher import AdditiveMatcher


@dataclass(frozen=True)
class HealthWarning:
    """单条健康警告.

    Attributes:
        category: 类别，如 drug_conflict / allergen / disease / ingredient_risk
        severity: high / medium / low
        title: 短标题
        description: 详细说明
    """

    category: str
    severity: str
    title: str
    description: str


# 食品原料风险规则配置
# 触发条件：ingredients 列表中匹配关键词（按顺序，前 N 位）
INGREDIENT_RISK_RULES: List[Dict] = [
    {
        "id": "hydrogenated_oil",
        "keywords": ["氢化植物油", "氢化棕榈油", "氢化大豆油", "人造奶油", "植脂末"],
        "position_limit": None,  # 任意位置命中即触发
        "severity": "high",
        "title": "反式脂肪酸风险",
        "description": "含有氢化植物油/植脂末等成分，可能含反式脂肪酸，建议心血管/脑梗人群尽量避免。",
        "groups": ["脑梗/心血管"],
    },
    {
        "id": "high_sugar",
        "keywords": [
            "白砂糖",
            "葡萄糖浆",
            "麦芽糖浆",
            "果葡糖浆",
            "冰糖",
            "红糖",
            "绵白糖",
        ],
        "position_limit": 3,  # 排在前 3 位才触发
        "severity": "medium",
        "title": "糖分较高",
        "description": "配料表中糖排名靠前，糖分较高，糖尿病患者请注意控制摄入量。",
        "groups": ["糖尿病"],
    },
    {
        "id": "high_sodium",
        "keywords": ["食用盐", "食盐", "海盐", "精盐", "岩盐", "氯化钠"],
        "position_limit": 3,
        "severity": "medium",
        "title": "钠含量可能较高",
        "description": "配料表中盐排名靠前，钠含量可能较高，高血压患者建议关注。",
        "groups": ["高血压"],
    },
]


class HealthWarningEngine:
    """统一的健康风险提示引擎.

    输入：识别结果 + 用户健康档案
    输出：按严重级别排序的 HealthWarning 列表
    """

    def __init__(
        self,
        additive_matcher: AdditiveMatcher,
        conflicts: Optional[Sequence[Dict]] = None,
        allergens: Optional[Sequence[Dict]] = None,
    ):
        self.additive_matcher = additive_matcher
        self.conflicts = list(conflicts or [])
        self.allergens = list(allergens or [])

    def analyze(
        self,
        result: Dict,
        health_profile: Optional[Dict] = None,
    ) -> List[HealthWarning]:
        """根据识别结果和健康档案生成全部警告."""
        profile = health_profile or {}
        warnings: List[HealthWarning] = []

        warnings.extend(self._check_drug_conflicts(result, profile))
        warnings.extend(self._check_allergens(result, profile))
        warnings.extend(self._check_disease_warnings(result, profile))
        warnings.extend(self._check_ingredient_risks(result, profile))

        # 按严重级别排序：high > medium > low
        severity_order = {"high": 0, "medium": 1, "low": 2}
        warnings.sort(key=lambda w: severity_order.get(w.severity, 99))
        return warnings

    def _check_drug_conflicts(self, result: Dict, profile: Dict) -> List[HealthWarning]:
        """检查用户用药与配料是否存在冲突."""
        user_drugs = profile.get("drugs", [])
        ingredients = result.get("ingredients", [])
        if not user_drugs or not ingredients:
            return []

        user_drug_ids = {d.get("id") for d in user_drugs if d.get("id")}
        if not user_drug_ids:
            return []

        warnings = []
        for c in self.conflicts:
            if c.get("drug_id") not in user_drug_ids:
                continue
            for ing in ingredients:
                ing_str = str(ing)
                for fk in c.get("food_keywords", []):
                    if fk in ing_str:
                        warnings.append(
                            HealthWarning(
                                category="drug_conflict",
                                severity=c.get("severity", "medium"),
                                title="药物-食物相互作用",
                                description=f"{c.get('drug_name', '')} 与 {fk} "
                                f"可能存在相互作用：{c.get('description', '')} "
                                f"建议：{c.get('recommendation', '请咨询医生或药师')}",
                            )
                        )
                        break  # 每个冲突只算一次
        return warnings

    def _check_allergens(self, result: Dict, profile: Dict) -> List[HealthWarning]:
        """检查配料中是否包含用户过敏原."""
        user_allergens = profile.get("allergens", [])
        if not user_allergens:
            return []

        ingredients = result.get("ingredients", [])
        additives = result.get("additives", [])
        all_text = " ".join(ingredients)
        all_text += " " + " ".join(a.get("name", "") for a in additives)

        matched = []
        for allergen in user_allergens:
            name = allergen.get("name", "")
            if name and name in all_text:
                matched.append(name)
                continue
            for ex in allergen.get("examples", []):
                if ex in all_text:
                    matched.append(name or ex)
                    break

        if not matched:
            return []

        return [
            HealthWarning(
                category="allergen",
                severity="high",
                title="过敏原提示",
                description=f"检测到可能的过敏原：{'、'.join(sorted(set(matched)))}，请谨慎食用。",
            )
        ]

    def _check_disease_warnings(
        self, result: Dict, profile: Dict
    ) -> List[HealthWarning]:
        """基于添加剂风险库中的 warnings 字段，检查特定人群敏感性."""
        groups = set(profile.get("groups", []))
        if not groups:
            return []

        warnings = []
        seen: set = set()
        for additive in result.get("additives", []):
            if not isinstance(additive, dict):
                continue
            name = additive.get("name", "")
            if not name or name in seen:
                continue
            seen.add(name)
            level, _, _ = self.additive_matcher.classify(name)
            # 通过 matcher 拿不到 warnings，需要再查一次 repository
            # 这里复用 repository 的 find 获取 warnings
            risk = self.additive_matcher.repository.find(name)
            if risk and risk.warnings:
                hit_groups = [w for w in risk.warnings.split("/") if w in groups]
                if hit_groups:
                    warnings.append(
                        HealthWarning(
                            category="disease",
                            severity="medium",
                            title="特定人群注意",
                            description=f"{name}（{risk.note or '食品添加剂'}）对 "
                            f"{'、'.join(hit_groups)} 人群需额外注意，建议咨询医生或营养师。",
                        )
                    )
        return warnings

    def _check_ingredient_risks(
        self, result: Dict, profile: Dict
    ) -> List[HealthWarning]:
        """检查食品原料级风险（如氢化植物油、高糖、高钠）."""
        ingredients = result.get("ingredients", [])
        if not ingredients:
            return []

        user_groups = set(profile.get("groups", []))
        warnings = []
        for rule in INGREDIENT_RISK_RULES:
            # 如果规则有关联人群且用户已指定人群，但无交集，则跳过；
            # 用户未指定人群时仍提示（首期即使无人群也提示）
            rule_groups = set(rule.get("groups", []))
            if rule_groups and user_groups and not (rule_groups & user_groups):
                continue

            matched = self._match_ingredient_rule(ingredients, rule)
            if matched:
                warnings.append(
                    HealthWarning(
                        category="ingredient_risk",
                        severity=rule["severity"],
                        title=rule["title"],
                        description=rule["description"],
                    )
                )
        return warnings

    @staticmethod
    def _match_ingredient_rule(ingredients: Sequence[str], rule: Dict) -> bool:
        """判断配料列表是否命中某条原料风险规则."""
        limit = rule.get("position_limit")
        candidates = ingredients if limit is None else ingredients[:limit]
        keywords = rule.get("keywords", [])
        for ing in candidates:
            ing_str = str(ing)
            for kw in keywords:
                if kw in ing_str:
                    return True
        return False
