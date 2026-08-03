"""结果呈现契约外部行为测试（Ticket A / Spec #47）."""

from utils.result_presentation import (
    apply_result_corrections,
    assert_primary_copy_safe,
    build_result_presentation,
    infer_recognition_state,
)


def _food_complete(**kwargs):
    base = {
        "type": "food",
        "product_name": "测试饼干",
        "ocr_text": "配料：小麦粉、白砂糖、山梨糖醇。",
        "ingredients": ["小麦粉", "白砂糖", "山梨糖醇"],
        "additives": [{"name": "山梨糖醇", "level": "B"}],
        "advice": "普通人群可适量食用，建议保持均衡饮食。",
        "score": 72,
    }
    base.update(kwargs)
    return base


class TestInferRecognitionState:
    def test_complete(self):
        assert infer_recognition_state(_food_complete()) == "complete"

    def test_unconfirmed(self):
        assert (
            infer_recognition_state(
                {"type": "food", "product_name": "x", "ingredients": [], "additives": []}
            )
            == "unconfirmed"
        )

    def test_partial_recovered(self):
        assert (
            infer_recognition_state(
                _food_complete(ingredients_recovered_from_ocr=True)
            )
            == "partial"
        )


class TestBuildResultPresentation:
    def test_no_score_primary_in_voice_or_action(self):
        p = build_result_presentation(_food_complete())
        assert "参考分" not in p.voice_script
        assert "72" not in p.voice_script
        assert "参考分" not in p.action_line
        hits = assert_primary_copy_safe(
            p.action_line, p.voice_script, p.status_label, p.recognition_label
        )
        assert hits == []

    def test_attention_in_action(self):
        p = build_result_presentation(_food_complete())
        assert p.recognition_state == "complete"
        assert "山梨糖醇" in p.action_line or "山梨糖醇" in p.voice_script
        assert p.tone in ("caution", "danger", "safe")
        assert p.status_class.startswith("score-")

    def test_partial_not_soft_all_clear(self):
        p = build_result_presentation(
            _food_complete(
                ingredients_recovered_from_ocr=True,
                additives=[{"name": "甜菊糖苷", "level": "A"}],
            )
        )
        assert p.recognition_state == "partial"
        assert p.tone != "safe" or "不完整" in p.action_line
        assert "省心" not in p.action_line

    def test_unconfirmed_action_asks_rescan(self):
        p = build_result_presentation(
            {
                "type": "food",
                "product_name": "未知",
                "ocr_text": "",
                "ingredients": [],
                "additives": [],
            }
        )
        assert p.recognition_state == "unconfirmed"
        assert "重" in p.action_line or "拍" in p.action_line

    def test_supplement_no_score_and_non_drug(self):
        p = build_result_presentation(
            {
                "type": "supplement",
                "product_name": "某牌维生素",
                "summary": "成人补充多种维生素",
                "approval_no": "国食健注G20251234",
                "ingredients": ["维生素C"],
            }
        )
        assert "参考分" not in p.voice_script
        assert "药物" in p.action_line or "药物" in p.voice_script
        assert assert_primary_copy_safe(p.action_line, p.voice_script) == []

    def test_forbidden_eat_phrases_absent(self):
        p = build_result_presentation(_food_complete())
        for bad in ("能吃", "不能吃", "放心吃"):
            assert bad not in p.action_line
            assert bad not in p.voice_script

    def test_inferred_not_in_decisive_action(self):
        p = build_result_presentation(
            _food_complete(
                additives=[
                    {
                        "name": "胭脂红",
                        "level": "C",
                        "ai_inferred": True,
                    }
                ]
            )
        )
        assert "胭脂红" not in p.attention_names
        assert "胭脂红" not in p.action_line or "包装" in p.action_line
        # 不得写成确定「含需关注」却无包装依据的决断句
        assert p.tone in ("caution", "danger")
        assert "自动识别" in p.voice_script or "包装" in p.action_line

    def test_correction_removes_additive_and_softens(self):
        raw = _food_complete(
            additives=[
                {"name": "胭脂红", "level": "C"},
                {"name": "甜菊糖苷", "level": "A"},
            ]
        )
        before = build_result_presentation(raw)
        assert before.tone == "danger"
        fixed = apply_result_corrections(raw, remove_additive_names=["胭脂红"])
        after = build_result_presentation(fixed)
        assert all(a.get("name") != "胭脂红" for a in fixed["additives"])
        assert after.tone != "danger"
        assert fixed.get("corrections_applied") is True
