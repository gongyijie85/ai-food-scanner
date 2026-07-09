"""评分与添加剂判定工具（客户端权威判定层）。"""

import re

from utils.data import load_gb2760_risk, load_health_data

# 评分公式常量（A=绿/B=黄/C=红）
SCORE_PENALTY = {"A": 0, "B": 8, "C": 25}

# C 级添加剂密度惩罚：当 C 级数量 >=3 时额外扣分
C_LEVEL_DENSITY_PENALTY = 5
C_LEVEL_DENSITY_THRESHOLD = 3

# 不应被识别为食品添加剂的基础配料黑名单（避免 AI 误判导致分数虚低）
ADDITIVE_BLOCKLIST = {
    "水",
    "饮用水",
    "纯净水",
    "蒸馏水",
    "矿泉水",
    "白砂糖",
    "白糖",
    "冰糖",
    "红糖",
    "绵白糖",
    "蔗糖",
    "食用盐",
    "食盐",
    "精盐",
    "海盐",
    "岩盐",
    "食用油",
    "植物油",
    "菜籽油",
    "花生油",
    "大豆油",
    "玉米油",
    "葵花籽油",
    "橄榄油",
    "棕榈油",
    "调和油",
    "面粉",
    "小麦粉",
    "大米",
    "糯米粉",
    "淀粉",
    "小麦淀粉",
    "玉米淀粉",
    "马铃薯淀粉",
    "食品用香精",
    "食用香精",
    "香精",
    "酵母",
    "酵母抽提物",
    "蜂蜜",
    "麦芽糖浆",
    "果葡糖浆",
    "葡萄糖浆",
    "乳糖",
}

# 保健品辅料白名单（不参与扣分）
SUPPLEMENT_EXCIPIENTS = {
    "鱼油",
    "明胶",
    "甘油",
    "蜂蜡",
    "卵磷脂",
    "淀粉",
    "麦芽糊精",
    "羧甲基纤维素钠",
}


def _clean_name(name) -> str:
    """清洗名称：去空白、去首尾标点，返回字符串."""
    if not isinstance(name, str):
        name = str(name)
    return name.strip().strip("，,、.;；")


def _is_blocklisted(name: str) -> bool:
    """判断名称是否为基础配料黑名单（避免误识别为添加剂）."""
    n = _clean_name(name)
    if not n:
        return True
    return n in ADDITIVE_BLOCKLIST


def is_supplement_excipient(name: str) -> bool:
    """判断是否为保健品辅料（不扣分）."""
    n = str(name).strip()
    return n in SUPPLEMENT_EXCIPIENTS or any(k in n for k in ["胶囊壳", "软胶囊"])


def normalize_additive(name):
    """查 GB 2760 风险库返回 (level, ins_no, note)，未匹配默认 B 兜底."""
    if not name:
        return "B", "", ""
    n = str(name).strip()
    # 基础配料黑名单：不应被识别为添加剂，直接判 A
    if _is_blocklisted(n):
        return "A", "", "基础配料，不扣分"
    # 保健品辅料豁免
    if is_supplement_excipient(n):
        return "A", "", "保健品辅料，不扣分"
    risk = load_gb2760_risk()
    # 精确匹配
    if n in risk:
        r = risk[n]
        return r["level"], "", r.get("note", "")
    # 去括号、空格、INS 号后再匹配
    n_clean = re.sub(r"[\s()（）\[\]【】]", "", n)
    n_clean = re.sub(r"[(（][^）)]*[）)]", "", n_clean)
    for k, v in risk.items():
        k_clean = re.sub(r"[\s()（）\[\]【】]", "", k)
        if k_clean == n_clean:
            return v["level"], "", v.get("note", "")
    # 模糊匹配（必须长度相近，避免"山梨糖醇"误匹配"山梨糖醇酐单硬脂酸酯"）
    for k, v in risk.items():
        if abs(len(k) - len(n)) > 2:
            continue
        if k in n or n in k:
            return v["level"], "", f"模糊匹配：{k}"
    # 未匹配：默认 B（保守策略，宁严勿宽）
    return "B", "", "未在 GB 2760 库中，按黄色（注意）兜底"


def compute_score_from_additives(additives, health_groups=None):
    """按添加剂风险等级 + 特殊人群敏感性算分.
    公式: 100 - 红×25 - 黄×8 - 特殊人群命中额外扣 4 - C级密度扣分."""
    if not additives:
        return 100
    score = 100
    health_set = set(health_groups or [])
    risk = load_gb2760_risk()
    c_level_count = 0
    for a in additives:
        if not isinstance(a, dict):
            continue
        name = a.get("name", "")
        level, _, _ = normalize_additive(name)
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
    返回冲突列表: [{drug, food, severity, description, recommendation, source}]."""
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
