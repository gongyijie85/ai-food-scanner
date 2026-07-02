"""
核心函数单元测试
覆盖：normalize_additive, compute_score_from_additives, check_drug_food_conflicts, parse_result
"""

import sys
import os
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import (
    normalize_additive,
    compute_score_from_additives,
    check_drug_food_conflicts,
    parse_result,
    load_gb2760_risk,
)


class TestNormalizeAdditive:
    """测试 normalize_additive 函数"""

    def test_empty_name(self):
        """空名称应返回 level='B'（默认）"""
        level, ins, note = normalize_additive("")
        assert level == "B"

    def test_none_name(self):
        """None 名称应返回 level='B'（默认）"""
        level, ins, note = normalize_additive(None)
        assert level == "B"

    def test_supplement_excipient(self):
        """保健品辅料应返回 level='A'"""
        level, ins, note = normalize_additive("鱼油")
        assert level == "A"
        assert "不扣分" in note

    def test_unknown_additive(self):
        """未匹配的添加剂应返回 level='B'（默认）"""
        level, ins, note = normalize_additive("某种未知物质")
        assert level == "B"
        assert "未在 GB 2760" in note


class TestComputeScoreFromAdditives:
    """测试 compute_score_from_additives 函数"""

    def test_empty_list(self):
        """空列表应返回 100 分"""
        score = compute_score_from_additives([])
        assert score == 100

    def test_all_a_level(self):
        """全部 A 等级应不扣分"""
        additives = [
            {"name": "鱼油"},  # 保健品辅料，level=A
            {"name": "明胶"},  # 保健品辅料，level=A
        ]
        score = compute_score_from_additives(additives)
        assert score == 100

    def test_b_level_penalty(self):
        """B 等级应扣 8 分"""
        additives = [{"name": "某种未知物质"}]  # 未匹配默认 B
        score = compute_score_from_additives(additives)
        assert score == 92  # 100 - 8

    def test_mixed_levels(self):
        """混合等级应累加扣分"""
        additives = [
            {"name": "鱼油"},  # A，不扣分
            {"name": "某种未知物质"},  # B，扣 8 分
        ]
        score = compute_score_from_additives(additives)
        assert score == 92  # 100 - 8


class TestCheckDrugFoodConflicts:
    """测试 check_drug_food_conflicts 函数"""

    def test_no_drugs(self):
        """无药物应返回空列表"""
        ingredients = ["维生素C", "柠檬酸"]
        user_drugs = []
        result = check_drug_food_conflicts(ingredients, user_drugs)
        assert result == []

    def test_no_ingredients(self):
        """无配料应返回空列表"""
        ingredients = []
        user_drugs = [{"id": "drug_001", "name": "阿司匹林"}]
        result = check_drug_food_conflicts(ingredients, user_drugs)
        assert result == []

    def test_empty_inputs(self):
        """空输入应返回空列表"""
        result = check_drug_food_conflicts([], [])
        assert result == []


class TestParseResult:
    """测试 parse_result 函数"""

    def test_valid_json(self):
        """合法 JSON 应正确解析"""
        raw = '{"product_name": "测试产品", "score": 85, "additives": []}'
        result = parse_result(raw)
        assert result is not None
        assert result["product_name"] == "测试产品"
        assert result["score"] == 85

    def test_json_with_markdown_code_block(self):
        """带 markdown code block 的 JSON 应正确解析"""
        raw = '```json\n{"product_name": "测试", "score": 90}\n```'
        result = parse_result(raw)
        assert result is not None
        assert result["product_name"] == "测试"

    def test_english_product_name_translation(self):
        """纯英文 product_name 应翻译为'该产品'"""
        raw = '{"product_name": "Test Product", "score": 80}'
        result = parse_result(raw)
        assert result is not None
        assert result["product_name"] == "该产品"

    def test_invalid_json_returns_none(self):
        """JSON 解析失败应返回 None"""
        raw = "这不是 JSON"
        result = parse_result(raw)
        assert result is None


class TestDataLoading:
    """测试数据加载函数"""

    def test_load_gb2760_risk(self):
        """应成功加载 GB 2760 风险数据"""
        risk_map = load_gb2760_risk()
        assert isinstance(risk_map, dict)
        # 应该包含一些常见添加剂
        assert len(risk_map) > 0

    def test_load_drug_food_conflicts(self):
        """应成功加载药物-食物冲突数据"""
        from app import _load_json, _CONFLICTS_PATH
        conflicts = _load_json(_CONFLICTS_PATH).get("conflicts", [])
        assert isinstance(conflicts, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
