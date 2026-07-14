"""UI 回归测试.

覆盖：
- 首页/历史页整行可点击按钮标签不再包含 HTML，且保留关键信息.
- 结果页评分卡按分数区间输出正确的状态类.
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from components.score_hero import _render_score_hero
from pages.home import _history_button_label
from pages.history import _history_row_label


class TestHistoryButtonLabel:
    """测试首页历史按钮纯文本标签."""

    def test_label_contains_key_info(self):
        """标签应包含产品名、分数、状态、添加剂数量、日期."""
        label = _history_button_label(
            item={},
            score=100,
            status_text="良好",
            bar_color="#43A047",
            name="测试产品",
            additives_count=2,
            ts="2026-07-14",
        )
        assert "测试产品" in label
        assert "100" in label
        assert "良好" in label
        assert "2种添加剂" in label
        assert "2026-07-14" in label

    def test_label_does_not_contain_html(self):
        """标签不能包含 HTML 标签，避免 st.button 转义后源码外露."""
        label = _history_button_label(
            item={},
            score=85,
            status_text="良好",
            bar_color="#43A047",
            name="<b>测试</b>",
            additives_count=0,
            ts="2026-07-14",
        )
        assert "<" not in label
        assert ">" not in label

    def test_label_status_emoji_safe_caution_danger(self):
        """不同分数区间应使用对应状态 emoji."""
        safe = _history_button_label(
            item={},
            score=80,
            status_text="良好",
            bar_color="#43A047",
            name="A",
            additives_count=0,
            ts="2026-07-14",
        )
        caution = _history_button_label(
            item={},
            score=60,
            status_text="注意",
            bar_color="#F57F17",
            name="B",
            additives_count=0,
            ts="2026-07-14",
        )
        danger = _history_button_label(
            item={},
            score=59,
            status_text="高风险",
            bar_color="#E53935",
            name="C",
            additives_count=0,
            ts="2026-07-14",
        )
        assert "🟢" in safe
        assert "🟠" in caution
        assert "🔴" in danger


class TestHistoryRowLabel:
    """测试历史页整行按钮纯文本标签."""

    def test_label_contains_key_info(self):
        """标签应包含产品名、分数、状态、添加剂数量、日期."""
        label = _history_row_label(
            score=92,
            status_text="良好",
            bar_color="#43A047",
            name="历史产品",
            additives_count=1,
            ts="2026-07-13",
        )
        assert "历史产品" in label
        assert "92" in label
        assert "良好" in label
        assert "1种添加剂" in label
        assert "2026-07-13" in label

    def test_label_does_not_contain_html(self):
        """标签不能包含 HTML 标签."""
        label = _history_row_label(
            score=55,
            status_text="高风险",
            bar_color="#E53935",
            name="<script>alert(1)</script>",
            additives_count=3,
            ts="2026-07-12",
        )
        assert "<" not in label
        assert ">" not in label


class TestScoreHeroColorClass:
    """测试评分卡按分数输出正确状态类."""

    @pytest.mark.parametrize(
        "score, expected_class",
        [
            (100, "score-safe"),
            (80, "score-safe"),
            (79, "score-caution"),
            (60, "score-caution"),
            (59, "score-danger"),
            (0, "score-danger"),
        ],
    )
    def test_score_class(self, score, expected_class):
        """不同分数区间应渲染对应状态类."""
        with patch("components.score_hero.st.markdown") as mock_markdown:
            _render_score_hero(score, "测试产品", show_slow_replay=False)
            mock_markdown.assert_called_once()
            rendered_html = mock_markdown.call_args[0][0]
            assert expected_class in rendered_html
            assert "result-score-hero-compact" in rendered_html
