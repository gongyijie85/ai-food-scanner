"""HealthWarningEngine 未确认配料标记测试."""

from services.health_warning_engine import HealthWarningEngine, HealthWarning
from services.additive_matcher import AdditiveMatcher


class _EmptyStandardRepo:
    def find_standard(self, name):
        return None

    def find_alias(self, name):
        return None


class _EmptyOverrideRepo:
    def find(self, name):
        return None


def _engine(conflicts=None, allergens=None):
    matcher = AdditiveMatcher(_EmptyStandardRepo(), _EmptyOverrideRepo())
    return HealthWarningEngine(matcher, conflicts=conflicts or [], allergens=allergens or [])


class TestDrugConflictUnconfirmedFlag:
    def test_conflict_from_unconfirmed_ingredient_is_flagged(self):
        """命中的配料若在 ingredients_unconfirmed 中，警告应标记 unconfirmed=True"""
        engine = _engine(
            conflicts=[
                {
                    "drug_id": "D001",
                    "drug_name": "华法林",
                    "food_keywords": ["西柚"],
                    "severity": "high",
                    "description": "可能增强药效",
                    "recommendation": "避免同服",
                }
            ]
        )
        result = {"ingredients": ["西柚"], "ingredients_unconfirmed": ["西柚"]}
        profile = {"drugs": [{"id": "D001", "name": "华法林"}]}

        warnings = engine._check_drug_conflicts(result, profile)

        assert len(warnings) == 1
        assert warnings[0].unconfirmed is True

    def test_conflict_from_confirmed_ingredient_is_not_flagged(self):
        """命中的配料若不在 ingredients_unconfirmed 中，警告应为 unconfirmed=False"""
        engine = _engine(
            conflicts=[
                {
                    "drug_id": "D001",
                    "drug_name": "华法林",
                    "food_keywords": ["西柚"],
                    "severity": "high",
                    "description": "可能增强药效",
                    "recommendation": "避免同服",
                }
            ]
        )
        result = {"ingredients": ["西柚"], "ingredients_unconfirmed": []}
        profile = {"drugs": [{"id": "D001", "name": "华法林"}]}

        warnings = engine._check_drug_conflicts(result, profile)

        assert len(warnings) == 1
        assert warnings[0].unconfirmed is False


class TestAllergenUnconfirmedFlag:
    def test_allergen_from_unconfirmed_ingredient_is_flagged(self):
        """过敏原命中若来自未确认配料，警告应标记 unconfirmed=True"""
        engine = _engine(allergens=[])
        result = {
            "ingredients": ["花生酱"],
            "additives": [],
            "ingredients_unconfirmed": ["花生酱"],
        }
        profile = {"allergens": [{"name": "花生", "examples": ["花生酱"]}]}

        warnings = engine._check_allergens(result, profile)

        assert len(warnings) == 1
        assert warnings[0].unconfirmed is True

    def test_allergen_from_confirmed_ingredient_is_not_flagged(self):
        """过敏原命中若来自已确认配料，警告应为 unconfirmed=False"""
        engine = _engine(allergens=[])
        result = {
            "ingredients": ["花生酱"],
            "additives": [],
            "ingredients_unconfirmed": [],
        }
        profile = {"allergens": [{"name": "花生", "examples": ["花生酱"]}]}

        warnings = engine._check_allergens(result, profile)

        assert len(warnings) == 1
        assert warnings[0].unconfirmed is False

    def test_one_confirmed_one_unconfirmed_allergen_is_not_flagged(self):
        """两个过敏原均命中，其中一个已确认、一个未确认：
        整体 unconfirmed 应为 False（存在确认匹配时不应被未确认匹配拖累可信度）"""
        engine = _engine(allergens=[])
        result = {
            "ingredients": ["花生酱", "牛奶"],
            "additives": [],
            "ingredients_unconfirmed": ["牛奶"],
        }
        profile = {
            "allergens": [
                {"name": "花生", "examples": ["花生酱"]},
                {"name": "牛奶", "examples": ["牛奶"]},
            ]
        }

        warnings = engine._check_allergens(result, profile)

        assert len(warnings) == 1
        assert warnings[0].unconfirmed is False

    def test_both_allergens_unconfirmed_is_flagged(self):
        """两个过敏原均命中，且均来自未确认配料：整体 unconfirmed 应为 True"""
        engine = _engine(allergens=[])
        result = {
            "ingredients": ["花生酱", "牛奶"],
            "additives": [],
            "ingredients_unconfirmed": ["花生酱", "牛奶"],
        }
        profile = {
            "allergens": [
                {"name": "花生", "examples": ["花生酱"]},
                {"name": "牛奶", "examples": ["牛奶"]},
            ]
        }

        warnings = engine._check_allergens(result, profile)

        assert len(warnings) == 1
        assert warnings[0].unconfirmed is True


def test_health_warning_unconfirmed_defaults_to_false():
    """不显式传入 unconfirmed 时应默认为 False，保持旧调用方兼容"""
    w = HealthWarning(category="disease", severity="medium", title="t", description="d")
    assert w.unconfirmed is False
