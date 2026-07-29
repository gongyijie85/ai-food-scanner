"""结果页纠错反馈入口组件."""

import streamlit as st

from utils.feedback import save_feedback


def render_feedback_entry(product_name: str, key: str = "feedback") -> None:
    """在结果页渲染一个可展开的纠错反馈入口."""
    with st.expander("结果不对？点此反馈"):
        message = st.text_area(
            "请描述哪里不对（例如：漏识别了某个配料、添加剂判定有误）",
            key=f"{key}_message",
        )
        if st.button("提交反馈", key=f"{key}_submit"):
            if save_feedback(product_name, message):
                st.success("感谢反馈，我们会尽快核对。")
            else:
                st.warning("请先填写反馈内容再提交。")
