"""添加剂分类服务：把模型识别的添加剂名称映射为风险等级."""

import re
from typing import Tuple

from repositories.additive_risk import AdditiveRiskRepository

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
    """清洗名称：去空白、去首尾标点."""
    if not isinstance(name, str):
        name = str(name)
    return name.strip().strip("，,、.;；")


def _is_blocklisted(name: str) -> bool:
    """判断名称是否为基础配料黑名单."""
    n = _clean_name(name)
    if not n:
        return True
    return n in ADDITIVE_BLOCKLIST


def is_supplement_excipient(name: str) -> bool:
    """判断是否为保健品辅料."""
    n = str(name).strip()
    return n in SUPPLEMENT_EXCIPIENTS or any(k in n for k in ["胶囊壳", "软胶囊"])


class AdditiveMatcher:
    """添加剂分类器：结合业务规则和风险库判定单一添加剂等级."""

    def __init__(self, repository: AdditiveRiskRepository):
        self.repository = repository

    def classify(self, name) -> Tuple[str, str, str]:
        """返回 (level, ins_no, note).

        判定顺序：
        1. 空/黑名单基础配料 -> A 级
        2. 保健品辅料 -> A 级
        3. 查询 GB 2760 风险库
        4. 未命中 -> B 级兜底
        """
        if not name:
            return "B", "", ""

        n = _clean_name(name)
        if not n:
            return "B", "", ""

        # 基础配料黑名单：不应被识别为添加剂
        if _is_blocklisted(n):
            return "A", "", "基础配料，不扣分"

        # 保健品辅料豁免
        if is_supplement_excipient(n):
            return "A", "", "保健品辅料，不扣分"

        # GB 2760 风险库查询
        risk = self.repository.find(n)
        if risk:
            return risk.level, "", risk.note

        # 未匹配：默认 B（保守策略，宁严勿宽）
        return "B", "", "未在 GB 2760 库中，按黄色（注意）兜底"
