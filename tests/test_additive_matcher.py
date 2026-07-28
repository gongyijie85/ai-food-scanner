"""AdditiveMatcher PENDING_RATING 兜底行为与 UI 显示回归测试."""

from components.additive_card import _get_level_info
from repositories.additive_risk import StandardAdditive
from services.additive_matcher import AdditiveMatcher, MatchStatus


class _FakeStandardRepo:
    """伪标准库：只收录一个添加剂，模拟 GB2760 SQLite 已导入该名称."""

    def __init__(self, standard):
        self._standard = standard

    def find_standard(self, name):
        return self._standard if name == self._standard.canonical_name else None

    def find_alias(self, name):
        return None


class _EmptyOverrideRepo:
    """伪覆盖表：永远查不到风险等级，模拟 CSV 未覆盖该添加剂（"山梨酸钾"类场景）."""

    def find(self, name):
        return None


class TestPendingRatingFallback:
    def test_standard_hit_without_override_returns_pending_rating(self):
        """标准库命中但覆盖表无评级时，status 应为 PENDING_RATING 而非静默判定为已评级."""
        standard = StandardAdditive(
            canonical_name="山梨酸钾",
            cns="17.005",
            ins="202",
            functions="防腐剂",
            scopes_summary="",
            page_ref="",
        )
        matcher = AdditiveMatcher(_FakeStandardRepo(standard), _EmptyOverrideRepo())

        result = matcher.match("山梨酸钾")

        assert result.status == MatchStatus.PENDING_RATING
        assert result.canonical_name == "山梨酸钾"
        assert result.level == "B"

    def test_pending_rating_is_distinguishable_from_unmatched(self):
        """PENDING_RATING 与 UNMATCHED 的 status 必须不同（回归"100分虚高"场景）."""
        standard = StandardAdditive(
            canonical_name="山梨酸钾",
            cns="17.005",
            ins="202",
            functions="防腐剂",
            scopes_summary="",
            page_ref="",
        )
        matcher = AdditiveMatcher(_FakeStandardRepo(standard), _EmptyOverrideRepo())

        pending = matcher.match("山梨酸钾")
        unmatched = matcher.match("完全不存在的添加剂名称")

        assert pending.status == MatchStatus.PENDING_RATING
        assert unmatched.status == MatchStatus.UNMATCHED
        assert pending.status != unmatched.status


class TestGetLevelInfoPendingRating:
    def test_pending_rating_status_shows_pending_label_not_generic_caution(self):
        """PENDING_RATING 状态应显示"待确认"，不能与已评级 B 的"注意"混淆（回归 additive_card.py 状态值比较 bug）."""
        label, color, shape = _get_level_info("B", MatchStatus.PENDING_RATING)
        assert label == "待确认"

    def test_rated_b_status_still_shows_caution_label(self):
        """真正已评级为 B 的添加剂应继续显示"注意"，不受本次修复影响."""
        label, color, shape = _get_level_info("B", MatchStatus.RATED)
        assert label == "注意"
