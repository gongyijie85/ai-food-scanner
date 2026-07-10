"""评分与添加剂判定工具（客户端权威判定层）。"""

from services.additive_matcher import (
    _is_blocklisted,
    is_supplement_excipient,
)
from services.additive_matcher import AdditiveMatcher
from utils.data import get_additive_risk_repository, load_gb2760_risk, load_health_data

# 评分公式常量（A=绿/B=黄/C=红）
SCORE_PENALTY = {"A": 0, "B": 8, "C": 25}

# C 级添加剂密度惩罚：当 C 级数量 >=3 时额外扣分
C_LEVEL_DENSITY_PENALTY = 5
C_LEVEL_DENSITY_THRESHOLD = 3


def _get_matcher() -> AdditiveMatcher:
    """获取默认的添加剂分类器（基于本地 GB 2760 CSV 仓库）."""
    return AdditiveMatcher(get_additive_risk_repository())


def normalize_additive(name):
    """查 GB 2760 风险库返回 (level, ins_no, note)，未匹配默认 B 兜底.

    此函数保留为兼容接口，实际逻辑委托给 AdditiveMatcher。
    """
    return _get_matcher().classify(name)


def compute_score_from_additives(additives, health_groups=None):
    """按添加剂风险等级 + 特殊人群敏感性算分.
    公式: 100 - 红×25 - 黄×8 - 特殊人群命中额外扣 4 - C级密度扣分.
    """
    if not additives:
        return 100
    score = 100
    health_set = set(health_groups or [])
    matcher = _get_matcher()
    risk = load_gb2760_risk()
    c_level_count = 0
    for a in additives:
        if not isinstance(a, dict):
            continue
        name = a.get("name", "")
        level, _, _ = matcher.classify(name)
        score -= SCORE_PENALTY.get(level, 0)
        if level == "C":
            c_level_count += 1
        # 特殊人群敏感性（如糖尿病/高血压 + 命中 warnings）
        if name in risk:
            warnings = risk[name].get("warnings", "")
            if warnings and any(w in health_set for w in warnings.split("/")):
                score -= 4
    # C 级密度惩罚：高风险添加剂过多时额外扣分
    if c_level_count >= C_LEVEL_DENSITY_THRESHOLD:
        score -= C_LEVEL_DENSITY_PENALTY
    return max(0, min(100, score))


def check_drug_food_conflicts(ingredients_list, user_drugs):
    """根据用户当前用药和识别到的配料，检测药物-食物冲突.

    user_drugs: 用户在健康档案中选择的药物列表，每项为 dict 含 id 和 name.
    返回冲突列表: [{drug, food, severity, description, recommendation, source}].

    注意：此函数保留为兼容接口，新代码建议直接使用 HealthWarningEngine。
    """
    if not user_drugs or not ingredients_list:
        return []
    user_drug_ids = {d.get("id") for d in user_drugs if d.get("id")}
    if not user_drug_ids:
        return []

    conflicts = []
    health_data = load_health_data()
    for c in health_data.get("conflicts", []):
        if c.get("drug_id") not in user_drug_ids:
            continue
        # 检查配料中是否包含冲突食物关键词
        for ing in ingredients_list:
            ing_str = str(ing)
            for fk in c.get("food_keywords", []):
                if fk in ing_str:
                    conflicts.append(
                        {
                            "drug": c.get("drug_name", ""),
                            "food": ing_str,
                            "matched_keyword": fk,
                            "severity": c.get("severity", "medium"),
                            "description": c.get("description", ""),
                            "recommendation": c.get("recommendation", ""),
                            "mechanism": c.get("mechanism", ""),
                            "source": c.get("source", ""),
                        }
                    )
                    break  # 每个冲突只算一次
    return conflicts


# 保留从 services.additive_matcher 导入的别名，兼容现有测试和调用方
__all__ = [
    "compute_score_from_additives",
    "check_drug_food_conflicts",
    "normalize_additive",
    "_is_blocklisted",
    "is_supplement_excipient",
    "SCORE_PENALTY",
    "C_LEVEL_DENSITY_PENALTY",
    "C_LEVEL_DENSITY_THRESHOLD",
]
