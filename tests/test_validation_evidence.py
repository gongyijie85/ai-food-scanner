"""验证证据账本接缝测试（Spec #53）."""

from utils.validation_evidence import (
    compute_pay_signal,
    compute_reuse_count,
    default_wechat_invite,
    is_gate_blocking_incident,
    outreach_forbidden_hits,
    summarize_valid_children,
    validate_evidence_row,
)


class TestOutreachCopy:
    def test_default_invite_has_no_forbidden(self):
        text = default_wechat_invite(public_url="https://example.com/app")
        assert outreach_forbidden_hits(text) == []
        assert "参考" in text or "科普" in text
        assert "example.com" in text

    def test_forbidden_detection(self):
        assert "能吃" in outreach_forbidden_hits("告诉爸妈这能吃")


class TestValidateRow:
    def test_good_child_valid(self):
        row = {
            "id": "S02",
            "date": "2026-08-04",
            "channel": "微信熟人",
            "role": "子女",
            "path_complete": "是",
            "reuse_verbal": "是",
            "pay_tier": "2",
            "valid_sample": "是",
            "recognition_honesty": "完整",
            "gate_incident": "否",
            "soft_fail_notes": "",
            "blocker_notes": "",
            "quote": "关注项还挺清楚",
        }
        assert validate_evidence_row(row) == []

    def test_valid_requires_path(self):
        row = {
            "id": "S03",
            "date": "2026-08-04",
            "channel": "微信",
            "role": "子女",
            "path_complete": "否",
            "reuse_verbal": "否",
            "pay_tier": "1",
            "valid_sample": "是",
            "recognition_honesty": "部分",
            "gate_incident": "否",
        }
        errs = validate_evidence_row(row)
        assert "valid_requires_path_complete" in errs

    def test_incident_blocks_valid(self):
        row = {
            "id": "S04",
            "date": "2026-08-04",
            "channel": "微信",
            "role": "子女",
            "path_complete": "是",
            "reuse_verbal": "是",
            "pay_tier": "2",
            "valid_sample": "是",
            "recognition_honesty": "完整",
            "gate_incident": "是",
        }
        assert "valid_forbids_gate_incident" in validate_evidence_row(row)
        assert is_gate_blocking_incident(row) is True


class TestSummary:
    def test_reuse_and_pay(self):
        rows = [
            {
                "id": "S1",
                "date": "2026-08-01",
                "channel": "微信",
                "role": "子女",
                "path_complete": "是",
                "reuse_verbal": "是",
                "reuse_rescan_7d": "否",
                "pay_tier": "2",
                "valid_sample": "是",
                "recognition_honesty": "完整",
                "gate_incident": "否",
            },
            {
                "id": "S2",
                "date": "2026-08-01",
                "channel": "微信",
                "role": "子女",
                "path_complete": "是",
                "reuse_verbal": "否",
                "reuse_rescan_7d": "否",
                "pay_tier": "1",
                "valid_sample": "是",
                "recognition_honesty": "部分",
                "gate_incident": "否",
            },
            {
                "id": "E1",
                "date": "2026-08-01",
                "channel": "微信",
                "role": "老人",
                "path_complete": "是",
                "reuse_verbal": "是",
                "pay_tier": "3",
                "valid_sample": "是",
                "recognition_honesty": "完整",
                "gate_incident": "否",
            },
        ]
        for r in rows:
            assert validate_evidence_row(r) == []
        s = summarize_valid_children(rows)
        assert s["valid_children_n"] == 2
        assert s["reuse_n"] == 1
        assert s["pay_signal_n"] == 1
        assert s["enough_for_gate"] is False
        assert compute_reuse_count(rows[0]) == 1
        assert compute_pay_signal(rows[0]) is True
