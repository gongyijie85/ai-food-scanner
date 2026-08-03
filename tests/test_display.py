"""展示层工具函数测试."""

from utils.display import (
    build_detail_speak,
    family_conclusion_for_result,
    filter_history_entries,
    format_scan_time,
    history_band_for_score,
    history_needs_attention,
    is_attention_additive,
    short_product_name,
    split_additives_by_attention,
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

    def test_all_a_ignores_low_score_number(self):
        """总分不再覆盖添加剂等级：全 A 即使传入低分也非 danger。"""
        label, meaning, cls = status_copy_for_result(
            10, [{"name": "甜菊糖苷", "level": "A"}]
        )
        assert cls == "score-safe"
        assert "高关注" in label or "暂未" in label
        assert "包装" in meaning


class TestBuildDetailSpeak:
    def test_no_score_primary_and_has_disclaimer(self):
        text = build_detail_speak(
            "北田蛋白棒",
            92,
            [{"name": "山梨糖醇", "level": "B"}],
            advice="请适量",
        )
        assert "92" not in text
        assert "参考分" not in text
        assert "山梨糖醇" in text
        assert "参考" in text


class TestFamilyConclusion:
    def test_caution_mentions_additive(self):
        text, tone = family_conclusion_for_result(
            72, [{"name": "阿斯巴甜", "level": "B"}]
        )
        assert tone == "caution"
        assert "阿斯巴甜" in text
        assert text.startswith("给家人")
        assert "能吃" not in text
        assert "偶尔吃" not in text

    def test_danger_prefers_less(self):
        text, tone = family_conclusion_for_result(
            40, [{"name": "胭脂红", "level": "C"}]
        )
        assert tone == "danger"
        assert "少" in text
        assert "胭脂红" in text

    def test_safe_calm_copy(self):
        text, tone = family_conclusion_for_result(
            95, [{"name": "甜菊糖苷", "level": "A"}]
        )
        assert tone == "safe"
        assert "高关注" in text or "对照包装" in text


class TestHistoryBandAndFilter:
    def test_band_copy(self):
        assert history_band_for_score(90)[1] == "较省心"
        assert history_band_for_score(70)[1] == "要注意"
        assert history_band_for_score(40)[1] == "建议少吃"
        assert history_needs_attention(79) is True
        assert history_needs_attention(80) is False

    def test_filter_attention_and_safe(self):
        hist = [
            {"product_name": "A饼干", "score": 90},
            {"product_name": "B薯片", "score": 55},
            {"product_name": "C糖", "score": 72},
        ]
        att = filter_history_entries(hist, band="要注意")
        assert [x[1]["product_name"] for x in att] == ["B薯片", "C糖"]
        safe = filter_history_entries(hist, band="较省心")
        assert [x[1]["product_name"] for x in safe] == ["A饼干"]
        q = filter_history_entries(hist, search="薯", band="全部")
        assert len(q) == 1 and q[0][1]["product_name"] == "B薯片"


class TestSplitAdditives:
    def test_a_is_friendly_b_is_attention(self):
        assert is_attention_additive({"name": "x", "level": "A"}) is False
        assert is_attention_additive({"name": "y", "level": "B"}) is True
        att, fri = split_additives_by_attention(
            [
                {"name": "山梨酸钾", "level": "A"},
                {"name": "阿斯巴甜", "level": "B"},
                {"name": "胭脂红", "level": "C"},
            ]
        )
        names_att = [a["name"] for a in att]
        names_fri = [a["name"] for a in fri]
        assert names_fri == ["山梨酸钾"]
        assert names_att[0] == "胭脂红"
        assert "阿斯巴甜" in names_att
