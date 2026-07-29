"""个性化健康警告组件未确认徽标测试."""

from components.personal_warnings import render_personal_warnings
from services.health_warning_engine import HealthWarning


class TestUnconfirmedBadge:
    def test_unconfirmed_warning_shows_badge(self, monkeypatch):
        """unconfirmed=True 的警告应带上『未确认』徽标"""
        markdown_calls = []
        monkeypatch.setattr(
            "components.personal_warnings.st.markdown",
            lambda html, **kw: markdown_calls.append(html),
        )

        render_personal_warnings(
            [
                HealthWarning(
                    category="allergen",
                    severity="high",
                    title="过敏原提示",
                    description="可能含有您过敏的配料：西柚",
                    unconfirmed=True,
                )
            ]
        )

        html = "".join(markdown_calls)
        assert "ai-inferred-tag" in html

    def test_confirmed_warning_has_no_badge(self, monkeypatch):
        """unconfirmed=False 的警告不应带徽标"""
        markdown_calls = []
        monkeypatch.setattr(
            "components.personal_warnings.st.markdown",
            lambda html, **kw: markdown_calls.append(html),
        )

        render_personal_warnings(
            [
                HealthWarning(
                    category="allergen",
                    severity="high",
                    title="过敏原提示",
                    description="可能含有您过敏的配料：西柚",
                    unconfirmed=False,
                )
            ]
        )

        html = "".join(markdown_calls)
        assert "ai-inferred-tag" not in html
