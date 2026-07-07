"""
核心函数单元测试
覆盖：normalize_additive, compute_score_from_additives, check_drug_food_conflicts, parse_result
"""

import sys
import os
import json
import pytest
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import (
    normalize_additive,
    compute_score_from_additives,
    check_drug_food_conflicts,
    parse_result,
    load_gb2760_risk,
    normalize_model_output,
    detect_device_type,
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


class TestNormalizeModelOutput:
    """测试 normalize_model_output 函数"""

    def test_strip_markdown_code_block(self):
        """应去掉 Markdown 代码块标记"""
        raw = '```json\n{"type": "food", "product_name": "测试", "additives": []}\n```'
        out = normalize_model_output(raw, "mimo")
        data = json.loads(out)
        assert data["type"] == "food"
        assert data["product_name"] == "测试"

    def test_ensure_additives_is_list(self):
        """additives 非 list 时应强制为空 list"""
        raw = '{"type": "food", "product_name": "测试", "additives": "无"}'
        out = normalize_model_output(raw, "mimo")
        data = json.loads(out)
        assert data["additives"] == []

    def test_english_product_name_fallback(self):
        """纯英文 product_name 应替换为「该产品」"""
        raw = '{"type": "food", "product_name": "Pure English", "additives": []}'
        out = normalize_model_output(raw, "mimo")
        data = json.loads(out)
        assert data["product_name"] == "该产品"

    def test_agnes_field_alias_mapping(self):
        """Agnes 别名字段应映射为标准名"""
        raw = json.dumps({
            "type": "food",
            "product_name": "测试",
            "additive": [{"name": "山梨酸钾"}],
        })
        out = normalize_model_output(raw, "agnes")
        data = json.loads(out)
        assert "additives" in data
        assert data["additives"] == [{"name": "山梨酸钾"}]
        assert "additive" not in data

    def test_model_score_is_removed(self):
        """模型自带 score / level 应被删除"""
        raw = json.dumps({
            "type": "food",
            "product_name": "测试",
            "score": 95,
            "additives": [{"name": "山梨酸钾", "level": "A", "score": 95}],
        })
        out = normalize_model_output(raw, "agnes")
        data = json.loads(out)
        assert "score" not in data
        assert "level" not in data["additives"][0]

    def test_invalid_json_returns_raw(self):
        """非法 JSON 应原样返回"""
        raw = "这不是 JSON"
        out = normalize_model_output(raw, "mimo")
        assert out == raw


class TestDetectDeviceType:
    """测试 detect_device_type 函数（通过 monkeypatch 模拟请求上下文）"""

    def test_url_param_forces_desktop(self, monkeypatch):
        """URL 参数 device=desktop 应返回 desktop"""
        monkeypatch.setattr(st, "query_params", {"device": "desktop"})
        monkeypatch.setattr(st, "session_state", {})
        assert detect_device_type() == "desktop"

    def test_url_param_forces_mobile(self, monkeypatch):
        """URL 参数 device=mobile 应返回 mobile"""
        monkeypatch.setattr(st, "query_params", {"device": "mobile"})
        monkeypatch.setattr(st, "session_state", {})
        assert detect_device_type() == "mobile"

    def test_session_state_cache(self, monkeypatch):
        """session_state 缓存应优先于 User-Agent"""
        monkeypatch.setattr(st, "query_params", {})
        monkeypatch.setattr(st, "session_state", {"device_type": "desktop"})
        assert detect_device_type() == "desktop"

    def test_mobile_user_agent(self, monkeypatch):
        """手机 User-Agent 应返回 mobile"""
        monkeypatch.setattr(st, "query_params", {})
        monkeypatch.setattr(st, "session_state", {})
        monkeypatch.setattr(
            st, "context",
            type("Ctx", (), {"headers": {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}})()
        )
        assert detect_device_type() == "mobile"

    def test_desktop_user_agent(self, monkeypatch):
        """桌面 User-Agent 应返回 desktop"""
        monkeypatch.setattr(st, "query_params", {})
        monkeypatch.setattr(st, "session_state", {})
        monkeypatch.setattr(
            st, "context",
            type("Ctx", (), {"headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}})()
        )
        assert detect_device_type() == "desktop"

    def test_default_is_mobile(self, monkeypatch):
        """无任何信息时默认返回 mobile"""
        monkeypatch.setattr(st, "query_params", {})
        monkeypatch.setattr(st, "session_state", {})
        assert detect_device_type() == "mobile"

    def test_invalid_url_param_falls_through(self, monkeypatch):
        """非法 URL 参数应继续按 User-Agent 判断"""
        monkeypatch.setattr(st, "query_params", {"device": "tablet"})
        monkeypatch.setattr(st, "session_state", {})
        monkeypatch.setattr(
            st, "context",
            type("Ctx", (), {"headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}})()
        )
        assert detect_device_type() == "desktop"


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
