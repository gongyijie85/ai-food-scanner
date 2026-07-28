"""结果页纠错反馈入口组件测试."""

import contextlib

from components.feedback import render_feedback_entry


class TestFeedbackEntry:
    def test_submit_calls_save_feedback_with_message(self, monkeypatch):
        """点击提交后应调用 save_feedback，传入产品名与用户填写的内容."""
        saved = []
        monkeypatch.setattr(
            "components.feedback.save_feedback",
            lambda product_name, message: saved.append((product_name, message)) or True,
        )
        monkeypatch.setattr(
            "components.feedback.st.expander",
            lambda *a, **kw: contextlib.nullcontext(),
        )
        monkeypatch.setattr(
            "components.feedback.st.text_area", lambda *a, **kw: "少识别了一种添加剂"
        )
        monkeypatch.setattr("components.feedback.st.button", lambda *a, **kw: True)
        success_msgs = []
        monkeypatch.setattr("components.feedback.st.success", success_msgs.append)

        render_feedback_entry("测试产品")

        assert saved == [("测试产品", "少识别了一种添加剂")]
        assert success_msgs
