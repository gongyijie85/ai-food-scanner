"""深链与示例结果纯函数测试."""

from utils.sample_result import (
    apply_deep_link,
    build_sample_food_result,
    resolve_deep_link,
)


class TestBuildSampleFoodResult:
    def test_has_food_type_and_additives(self):
        r = build_sample_food_result()
        assert r["type"] == "food"
        assert r["score"] == 72
        assert len(r["additives"]) >= 3
        assert r.get("_sample_preview") is True
        levels = {a.get("level") for a in r["additives"] if a.get("level")}
        assert "A" in levels and "B" in levels and "C" in levels


class TestResolveDeepLink:
    def test_page_result_sample(self):
        intent = resolve_deep_link({"page": "result", "sample": "1"})
        assert intent["page"] == "result"
        assert intent["seed_sample"] is True
        assert intent["skip_gates"] is True

    def test_preview_alias(self):
        intent = resolve_deep_link({"page": "result", "preview": "1"})
        assert intent["seed_sample"] is True

    def test_demo_with_result_page(self):
        intent = resolve_deep_link({"demo": "1", "page": "result"})
        assert intent["page"] == "result"
        assert intent["seed_sample"] is True
        assert intent["skip_gates"] is True

    def test_invalid_page_ignored(self):
        intent = resolve_deep_link({"page": "admin"})
        assert intent["page"] is None
        assert intent["seed_sample"] is False

    def test_page_only_no_sample(self):
        intent = resolve_deep_link({"page": "scan"})
        assert intent["page"] == "scan"
        assert intent["seed_sample"] is False
        assert intent["skip_gates"] is False


class TestApplyDeepLink:
    def test_seeds_result_once(self):
        ss = {}
        page = apply_deep_link(ss, {"page": "result", "sample": "1"})
        assert page == "result"
        assert ss["page"] == "result"
        assert ss["legal_agreed"] is True
        assert ss["onboarded"] is True
        assert ss["last_result"]["score"] == 72
        # 第二次不覆盖（会话内只应用一次）
        ss["page"] = "home"
        assert apply_deep_link(ss, {"page": "result", "sample": "1"}) is None
        assert ss["page"] == "home"

    def test_does_not_overwrite_existing_result(self):
        ss = {"last_result": {"product_name": "真实扫描", "score": 90, "type": "food"}}
        apply_deep_link(ss, {"page": "result", "sample": "1"})
        assert ss["last_result"]["product_name"] == "真实扫描"

    def test_offline_ymgs_alias(self):
        intent = resolve_deep_link({"page": "result", "sample": "ymgs"})
        assert intent["seed_offline"] is True
        assert intent["offline_name"] == "ymgs"
        assert intent["skip_gates"] is True
        ss = {}
        apply_deep_link(ss, {"page": "result", "sample": "ymgs"})
        assert ss.get("last_result", {}).get("product_name", "").find("山楂") >= 0
        assert ss["last_result"].get("score") == 100
