"""
核心函数单元测试
覆盖：normalize_additive, compute_score_from_additives, check_drug_food_conflicts, parse_result
"""

import json
import os
import sys

import pytest
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repositories.additive_risk import CsvAdditiveRiskRepository
from services.additive_matcher import AdditiveMatcher
from services.health_warning_engine import HealthWarningEngine
from utils.api import (
    _generate_advice,
    encode_image_to_base64,
    normalize_model_output,
    parse_result,
)
from utils.data import load_gb2760_risk
from utils.helpers import detect_device_type
from utils.score import (
    C_LEVEL_DENSITY_PENALTY,
    _is_blocklisted,
    check_drug_food_conflicts,
    compute_score_from_additives,
    normalize_additive,
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

    def test_blocklisted_basic_ingredient(self):
        """黑名单基础配料应返回 level='A'，避免误扣分"""
        level, ins, note = normalize_additive("白砂糖")
        assert level == "A"
        assert "基础配料" in note

    def test_blocklisted_water(self):
        """水应返回 level='A'"""
        level, ins, note = normalize_additive("水")
        assert level == "A"

    def test_synonym_vitamin_c(self):
        """维生素C 俗名应映射到 抗坏血酸 并返回 A 级"""
        level, ins, note = normalize_additive("维生素 C")
        assert level == "A"
        assert "未在 GB 2760" not in note
        assert "维生素C" in note or "抗坏血酸" in note

    def test_synonym_baking_soda(self):
        """小苏打 俗名应映射到 碳酸氢钠 并返回 A 级"""
        level, ins, note = normalize_additive("小苏打")
        assert level == "A"
        assert "未在 GB 2760" not in note

    def test_synonym_msg(self):
        """味精 俗名应映射到 谷氨酸钠"""
        level, ins, note = normalize_additive("味精")
        assert level == "A"
        assert "未在 GB 2760" not in note


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

    def test_c_level_density_penalty(self):
        """C 级添加剂超过阈值应额外扣分"""
        # 构造 3 个 C 级添加剂（利用已知的 TBHQ/特丁基对苯二酚）
        additives = [
            {"name": "TBHQ"},
            {"name": "特丁基对苯二酚"},
            {"name": "亚硝酸钠"},
        ]
        score = compute_score_from_additives(additives)
        expected = 100 - 25 * 3 - C_LEVEL_DENSITY_PENALTY
        assert score == max(0, expected)

    def test_blocklisted_not_penalized(self):
        """黑名单基础配料不应扣分"""
        additives = [
            {"name": "水"},
            {"name": "食用盐"},
            {"name": "白砂糖"},
        ]
        score = compute_score_from_additives(additives)
        assert score == 100


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

    def test_advice_template_fallback(self):
        """advice 为空或含禁用词时应使用本地模板兜底"""
        raw = '{"type": "food", "product_name": "测试", "additives": [], "advice": ""}'
        result = parse_result(raw, health_groups=["糖尿病"])
        assert "糖尿病" in result["advice"]
        assert "请咨询" in result["advice"]

    def test_advice_template_forbidden_words(self):
        """advice 含医学疗效词时应被模板替换"""
        raw = '{"type": "food", "product_name": "测试", "additives": [], "advice": "本品可降三高"}'
        result = parse_result(raw, health_groups=["高血压"])
        assert "降三高" not in result["advice"]
        assert "高血压" in result["advice"]


class TestNormalizeModelOutput:
    """测试 normalize_model_output 函数"""

    def test_strip_markdown_code_block(self):
        """应去掉 Markdown 代码块标记"""
        raw = '```json\n{"type": "food", "product_name": "测试", "additives": []}\n```'
        out = normalize_model_output(raw)
        data = json.loads(out)
        assert data["type"] == "food"
        assert data["product_name"] == "测试"

    def test_ensure_additives_is_list(self):
        """additives 非 list 时应强制为空 list"""
        raw = '{"type": "food", "product_name": "测试", "additives": "无"}'
        out = normalize_model_output(raw)
        data = json.loads(out)
        assert data["additives"] == []

    def test_english_product_name_fallback(self):
        """纯英文 product_name 应替换为「该产品」"""
        raw = '{"type": "food", "product_name": "Pure English", "additives": []}'
        out = normalize_model_output(raw)
        data = json.loads(out)
        assert data["product_name"] == "该产品"

    def test_model_score_is_removed(self):
        """模型自带 score / level 应被删除"""
        raw = json.dumps(
            {
                "type": "food",
                "product_name": "测试",
                "score": 95,
                "additives": [{"name": "山梨酸钾", "level": "A", "score": 95}],
            }
        )
        out = normalize_model_output(raw)
        data = json.loads(out)
        assert "score" not in data
        assert "level" not in data["additives"][0]

    def test_invalid_json_returns_raw(self):
        """非法 JSON 应原样返回"""
        raw = "这不是 JSON"
        out = normalize_model_output(raw)
        assert out == raw

    def test_blocklisted_additive_filtered(self):
        """黑名单基础配料应从 additives 中过滤"""
        raw = json.dumps(
            {
                "type": "food",
                "product_name": "测试",
                "additives": [
                    {"name": "水"},
                    {"name": "白砂糖"},
                    {"name": "山梨酸钾"},
                ],
            }
        )
        out = normalize_model_output(raw)
        data = json.loads(out)
        assert len(data["additives"]) == 1
        assert data["additives"][0]["name"] == "山梨酸钾"

    def test_empty_and_abnormal_additive_filtered(self):
        """空名称、过短、过长条目应被过滤"""
        raw = json.dumps(
            {
                "type": "food",
                "product_name": "测试",
                "additives": [
                    {"name": ""},
                    {"name": "a"},
                    {"name": "x" * 35},
                    {"name": "山梨酸钾"},
                ],
            }
        )
        out = normalize_model_output(raw)
        data = json.loads(out)
        assert len(data["additives"]) == 1
        assert data["additives"][0]["name"] == "山梨酸钾"

    def test_ai_inferred_additive_not_in_ocr(self):
        """additives 中未在 ocr_text 出现的项应被标记 ai_inferred=True"""
        raw = json.dumps(
            {
                "type": "food",
                "product_name": "测试",
                "ocr_text": "配料：山楂、低聚果糖、浓缩苹果汁。",
                "additives": [
                    {"name": "山梨糖醇"},
                    {"name": "低聚果糖"},
                ],
            }
        )
        out = normalize_model_output(raw)
        data = json.loads(out)
        assert data["additives"][0].get("ai_inferred") is True
        assert data["additives"][1].get("ai_inferred") is False

    def test_ai_inferred_ignores_parentheses(self):
        """ocr_text 校验时应忽略添加剂名称中的括号补充说明"""
        raw = json.dumps(
            {
                "type": "food",
                "product_name": "测试",
                "ocr_text": "配料：山梨酸钾、柠檬酸。",
                "additives": [{"name": "山梨酸钾（E202）"}],
            }
        )
        out = normalize_model_output(raw)
        data = json.loads(out)
        assert data["additives"][0].get("ai_inferred") is False


class TestIsBlocklisted:
    """测试 _is_blocklisted 辅助函数"""

    def test_water_is_blocklisted(self):
        assert _is_blocklisted("水") is True

    def test_sugar_is_blocklisted(self):
        assert _is_blocklisted("白砂糖") is True

    def test_additive_not_blocklisted(self):
        assert _is_blocklisted("山梨酸钾") is False


class TestGenerateAdvice:
    """测试 _generate_advice 辅助函数"""

    def test_default_advice(self):
        advice = _generate_advice([])
        assert advice == "普通人群可适量食用，建议保持均衡饮食。"

    def test_diabetes_advice(self):
        advice = _generate_advice(["糖尿病"])
        assert "糖尿病" in advice

    def test_multiple_groups(self):
        advice = _generate_advice(["糖尿病", "高血压"])
        assert "糖尿病" in advice
        assert "高血压" in advice


class TestImageEncoding:
    """测试图片压缩与 base64 编码"""

    def test_encode_image_keeps_under_2mb(self):
        """压缩后 base64 应不超过 2MB"""
        test_path = os.path.join(os.path.dirname(__file__), "..", "test_label.jpg")
        if not os.path.exists(test_path):
            pytest.skip("test_label.jpg 不存在，跳过图片压缩测试")
        with open(test_path, "rb") as f:
            b64 = encode_image_to_base64(f)
        assert b64
        assert len(b64) <= 2 * 1024 * 1024


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
            st,
            "context",
            type(
                "Ctx",
                (),
                {
                    "headers": {
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
                    }
                },
            )(),
        )
        assert detect_device_type() == "mobile"

    def test_desktop_user_agent(self, monkeypatch):
        """桌面 User-Agent 应返回 desktop"""
        monkeypatch.setattr(st, "query_params", {})
        monkeypatch.setattr(st, "session_state", {})
        monkeypatch.setattr(
            st,
            "context",
            type(
                "Ctx",
                (),
                {
                    "headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    }
                },
            )(),
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
            st,
            "context",
            type(
                "Ctx",
                (),
                {
                    "headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    }
                },
            )(),
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
        from utils.data import _CONFLICTS_PATH, _load_json

        conflicts = _load_json(_CONFLICTS_PATH).get("conflicts", [])
        assert isinstance(conflicts, list)


class TestBuildSystemPrompt:
    """測試 build_system_prompt 的關鍵約束是否穩定存在"""

    def test_prompt_requires_json_only(self):
        """提示詞應要求純 JSON 輸出"""
        from utils.api import build_system_prompt

        prompt = build_system_prompt([])
        assert "純 JSON" in prompt or "不要 Markdown" in prompt

    def test_prompt_forbids_basic_ingredients_in_additives(self):
        """提示詞應禁止把基礎配料列入 additives"""
        from utils.api import build_system_prompt

        prompt = build_system_prompt([])
        assert "白砂糖" in prompt
        assert "食用盐" in prompt

    def test_prompt_has_output_examples(self):
        """提示詞應包含輸出示例"""
        from utils.api import build_system_prompt

        prompt = build_system_prompt([])
        assert '"type":"food"' in prompt
        assert '"type":"supplement"' in prompt

    def test_prompt_requires_no_model_level_or_score(self):
        """提示詞應要求模型不要輸出 level/score"""
        from utils.api import build_system_prompt

        prompt = build_system_prompt([])
        assert "不要输出 level" in prompt
        assert "不要给 score" in prompt


class TestCallApiWithFallback:
    """測試 call_api_with_fallback 的降級邏輯"""

    def test_mimo_success_no_fallback(self, monkeypatch):
        """MiMo 成功時不應調用 Agnes"""
        from utils.api import call_api_with_fallback

        call_count = {"mimo": 0, "agnes": 0}

        def mock_call_api(api_key, image_b64, system_prompt, url=None, model=None):
            if url and "agnes" in url:
                call_count["agnes"] += 1
                return "agnes_result"
            call_count["mimo"] += 1
            return "mimo_result"

        monkeypatch.setattr("utils.api.call_api", mock_call_api)
        result = call_api_with_fallback(
            "mimo_key", "img", "prompt", agnes_key="agnes_key"
        )
        assert result == "mimo_result"
        assert call_count["mimo"] == 1
        assert call_count["agnes"] == 0

    def test_mimo_fail_fallback_to_agnes(self, monkeypatch):
        """MiMo 失敗時應降級到 Agnes"""
        from utils.api import call_api_with_fallback

        call_count = {"mimo": 0, "agnes": 0}

        def mock_call_api(api_key, image_b64, system_prompt, url=None, model=None):
            if url and "agnes" in url:
                call_count["agnes"] += 1
                return "agnes_result"
            call_count["mimo"] += 1
            return None  # MiMo 失敗

        monkeypatch.setattr("utils.api.call_api", mock_call_api)
        monkeypatch.setattr("streamlit.toast", lambda *a, **kw: None)
        result = call_api_with_fallback(
            "mimo_key", "img", "prompt", agnes_key="agnes_key"
        )
        assert result == "agnes_result"
        assert call_count["mimo"] == 1
        assert call_count["agnes"] == 1

    def test_mimo_fail_no_agnes_key_returns_none(self, monkeypatch):
        """MiMo 失敗且無 Agnes key 時應返回 None"""
        from utils.api import call_api_with_fallback

        def mock_call_api(api_key, image_b64, system_prompt, url=None, model=None):
            return None

        monkeypatch.setattr("utils.api.call_api", mock_call_api)
        result = call_api_with_fallback("mimo_key", "img", "prompt", agnes_key="")
        assert result is None

    def test_mimo_fail_agnes_also_fail_returns_none(self, monkeypatch):
        """MiMo 和 Agnes 都失敗時應返回 None"""
        from utils.api import call_api_with_fallback

        def mock_call_api(api_key, image_b64, system_prompt, url=None, model=None):
            return None

        monkeypatch.setattr("utils.api.call_api", mock_call_api)
        monkeypatch.setattr("streamlit.toast", lambda *a, **kw: None)
        result = call_api_with_fallback(
            "mimo_key", "img", "prompt", agnes_key="agnes_key"
        )
        assert result is None


class TestAdditiveRiskRepository:
    """测试 GB 2760 CSV 仓库适配器"""

    def _repo(self):
        from utils.data import _GB2760_RISK_PATH

        return CsvAdditiveRiskRepository(_GB2760_RISK_PATH)

    def test_exact_match(self):
        """精确匹配应返回风险信息"""
        repo = self._repo()
        risk = repo.find("山梨酸钾")
        assert risk is not None
        assert risk.level in {"A", "B", "C"}

    def test_cleaned_match_with_parentheses(self):
        """带括号残留的名称清洗后应命中"""
        repo = self._repo()
        risk = repo.find("山梨酸钾（E202）")
        assert risk is not None

    def test_fuzzy_match_short_alias(self):
        """TBHQ 等短别名应模糊命中"""
        repo = self._repo()
        risk = repo.find("TBHQ")
        assert risk is not None
        assert risk.level == "C"

    def test_missing_additive_returns_none(self):
        """不存在的添加剂应返回 None"""
        repo = self._repo()
        assert repo.find("根本不存在的添加剂名字") is None


class TestAdditiveMatcher:
    """测试添加剂分类器"""

    def _matcher(self):
        from utils.data import get_additive_risk_repository

        return AdditiveMatcher(get_additive_risk_repository())

    def test_blocklisted_basic_ingredient(self):
        """黑名单基础配料应返回 A 级"""
        level, _, note = self._matcher().classify("白砂糖")
        assert level == "A"
        assert "基础配料" in note

    def test_supplement_excipient(self):
        """保健品辅料应返回 A 级"""
        level, _, note = self._matcher().classify("鱼油")
        assert level == "A"
        assert "辅料" in note

    def test_known_c_level_additive(self):
        """已知 C 级添加剂应返回 C 级"""
        level, _, _ = self._matcher().classify("特丁基对苯二酚")
        assert level == "C"

    def test_unknown_returns_b(self):
        """未匹配名称默认 B 级"""
        level, _, _ = self._matcher().classify("某种未知合成物")
        assert level == "B"


class TestHealthWarningEngine:
    """测试健康风险提示引擎"""

    def _engine(self):
        from utils.data import get_additive_risk_repository, load_health_data

        matcher = AdditiveMatcher(get_additive_risk_repository())
        health_data = load_health_data()
        return HealthWarningEngine(
            matcher,
            conflicts=health_data.get("conflicts", []),
            allergens=health_data.get("allergens", []),
        )

    def test_drug_conflict_aspirin_alcohol(self):
        """阿司匹林 + 酒精应产生药物冲突警告"""
        engine = self._engine()
        result = {
            "ingredients": ["白酒", "水", "食用香精"],
            "additives": [],
        }
        profile = {
            "drugs": [{"id": "D051", "name": "阿司匹林"}],
        }
        warnings = engine.analyze(result, profile)
        assert any(w.category == "drug_conflict" for w in warnings)

    def test_allergen_milk(self):
        """牛奶过敏 + 配料含牛奶应产生过敏原警告"""
        engine = self._engine()
        result = {
            "ingredients": ["牛奶", "白砂糖"],
            "additives": [],
        }
        profile = {
            "allergens": [{"name": "乳及乳制品", "examples": ["牛奶"]}],
        }
        warnings = engine.analyze(result, profile)
        assert any(w.category == "allergen" for w in warnings)

    def test_ingredient_risk_hydrogenated_oil(self):
        """氢化植物油应产生原料风险警告"""
        engine = self._engine()
        result = {
            "ingredients": ["氢化植物油", "白砂糖"],
            "additives": [],
        }
        warnings = engine.analyze(result, {})
        assert any(
            w.category == "ingredient_risk" and w.severity == "high" for w in warnings
        )

    def test_no_profile_no_warnings(self):
        """无健康档案且无风险配料时应返回空列表"""
        engine = self._engine()
        result = {
            "ingredients": ["水", "小麦粉"],
            "additives": [],
        }
        warnings = engine.analyze(result, {})
        assert warnings == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
