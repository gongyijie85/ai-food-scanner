"""展示层工具函数测试."""

from utils.display import (
    build_detail_speak,
    format_scan_time,
    short_product_name,
    status_copy_for_result,
)


class TestShortProductName:
    def test_strip_english_brand_and_category(self):
        raw = "PEI TIEN北田99+能量蛋白棒无糖黑芝麻口味(膨化食品)"
        short = short_product_name(raw, max_len=22)
        assert "PEI" not in short.upper() or short.startswith("北")
        assert "膨化" not in short
        assert "北田" in short or "蛋白" in short

    def test_empty(self):
        assert short_product_name("") == "未知产品"


class TestFormatScanTime:
    def test_iso(self):
        assert format_scan_time("2026-07-27T01:27:46") == "2026年7月27日 01:27"

    def test_empty(self):
        assert "未知" in format_scan_time("")


class TestStatusCopy:
    def test_b_level_not_all_clear(self):
        label, meaning, cls = status_copy_for_result(
            92, [{"name": "山梨糖醇", "level": "B"}]
        )
        assert label == "有可留意项"
        assert cls == "score-caution"
        assert "留意" in meaning

    def test_all_a_high_score(self):
        label, meaning, cls = status_copy_for_result(
            95, [{"name": "甜菊糖苷", "level": "A"}]
        )
        assert label == "暂未发现明显问题"
        assert cls == "score-safe"


class TestBuildDetailSpeak:
    def test_includes_score_and_disclaimer(self):
        text = build_detail_speak(
            "北田蛋白棒",
            92,
            [{"name": "山梨糖醇", "level": "B"}],
            advice="请适量",
        )
        assert "92" in text
        assert "山梨糖醇" in text
        assert "参考" in text
