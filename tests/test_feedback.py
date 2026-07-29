"""utils/feedback.py 纠错反馈持久化测试."""

from utils import feedback


class TestSaveFeedback:
    def test_save_feedback_persists_record(self, tmp_path, monkeypatch):
        """保存的反馈应写入本地 JSON，字段完整."""
        monkeypatch.setattr(feedback, "_DATA_DIR", str(tmp_path))

        ok = feedback.save_feedback("测试牛奶", "少识别了一种添加剂")

        assert ok is True
        records = feedback.load_feedback()
        assert len(records) == 1
        assert records[0]["product_name"] == "测试牛奶"
        assert records[0]["message"] == "少识别了一种添加剂"
        assert "timestamp" in records[0]

    def test_empty_message_is_rejected(self, tmp_path, monkeypatch):
        """空白反馈内容不应被保存."""
        monkeypatch.setattr(feedback, "_DATA_DIR", str(tmp_path))

        ok = feedback.save_feedback("测试牛奶", "   ")

        assert ok is False
        assert feedback.load_feedback() == []
