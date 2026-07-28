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
