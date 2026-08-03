"""pages/result.py 配料展示区域测试."""

import pages.result as result_page


class TestIngredientsSectionLowConfidenceNotice:
    def test_recovered_ingredients_shows_prominent_warning_not_caption(
        self, monkeypatch
    ):
        """兜底恢复的配料列表应展示醒目警示块，而非小字 caption."""
        markdown_calls = []
        monkeypatch.setattr(
            "pages.result.st.markdown", lambda html, **kw: markdown_calls.append(html)
        )
        caption_calls = []
        monkeypatch.setattr(
            "pages.result.st.caption", lambda text, **kw: caption_calls.append(text)
        )

        result_page._render_ingredients_section(
            {
                "ingredients": ["山楂", "低聚果糖"],
                "ingredients_recovered_from_ocr": True,
                "ocr_text": "山楂、低聚果糖",
            }
        )

        notice_html = "".join(markdown_calls)
        assert "advice-block-general" in notice_html
        assert "核对包装" in notice_html
        assert "content-card" in notice_html
        assert not any("已根据识别到的原文自动整理配料" in c for c in caption_calls)

    def test_non_recovered_ingredients_shows_no_notice(self, monkeypatch):
        """未走兜底恢复路径时不应出现该警示块."""
        markdown_calls = []
        monkeypatch.setattr(
            "pages.result.st.markdown", lambda html, **kw: markdown_calls.append(html)
        )

        result_page._render_ingredients_section(
            {"ingredients": ["山楂", "低聚果糖"], "ocr_text": "山楂、低聚果糖"}
        )

        notice_html = "".join(markdown_calls)
        assert "advice-block-general" not in notice_html


class TestIngredientsOcrDedup:
    def test_identical_ocr_hidden_when_tags_present(self, monkeypatch):
        """标签与原文实质相同时不重复展示原文块."""
        markdown_calls = []
        monkeypatch.setattr(
            "pages.result.st.markdown", lambda html, **kw: markdown_calls.append(html)
        )
        ocr = (
            "配料：米谷粉(糙米、大米)、棕榈油、麦芽糊精、玉米、黑芝麻粉、"
            "山梨糖醇、豌豆蛋白、荞麦、燕麦片、绿豆、莲子、薏苡仁、豌豆、"
            "红豆、芸豆、黑豆、黑米、食用盐、甜菊糖苷。"
        )
        ings = [
            "米谷粉(糙米、大米)",
            "棕榈油",
            "麦芽糊精",
            "玉米",
            "黑芝麻粉",
            "山梨糖醇",
            "豌豆蛋白",
            "荞麦",
            "燕麦片",
            "绿豆",
            "莲子",
            "薏苡仁",
            "豌豆",
            "红豆",
            "芸豆",
            "黑豆",
            "黑米",
            "食用盐",
            "甜菊糖苷",
        ]
        result_page._render_ingredients_section(
            {
                "ingredients": ings,
                "ocr_text": ocr,
                "ingredients_recovered_from_ocr": False,
            }
        )
        html = "".join(markdown_calls)
        assert "ingredient-tag" in html
        assert "ocr-text-box" not in html
        assert "全部配料" in html

    def test_different_ocr_still_shown(self, monkeypatch):
        """原文与标签有实质差异时保留原文供核对."""
        markdown_calls = []
        monkeypatch.setattr(
            "pages.result.st.markdown", lambda html, **kw: markdown_calls.append(html)
        )
        result_page._render_ingredients_section(
            {
                "ingredients": ["小麦粉", "白砂糖"],
                "ocr_text": "配料：小麦粉、白砂糖、食用盐、山梨酸钾。",
                "ingredients_recovered_from_ocr": False,
            }
        )
        html = "".join(markdown_calls)
        assert "ocr-text-box" in html
        assert "包装原文" in html
        assert "山梨酸钾" in html

    def test_ocr_duplicate_helper(self):
        assert result_page._ocr_duplicates_ingredients(
            "配料：山楂、低聚果糖。", ["山楂", "低聚果糖"]
        )
        assert not result_page._ocr_duplicates_ingredients(
            "配料：山楂、低聚果糖、白砂糖。", ["山楂", "低聚果糖"]
        )
