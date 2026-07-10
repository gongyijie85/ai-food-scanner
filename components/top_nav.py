"""顶部导航栏组件."""

import streamlit as st

from utils.helpers import switch_page
from utils.security import _safe


def render_top_nav(
    title: str,
    subtitle: str = "",
    show_back: bool = True,
    back_target: str = "home",
    right_action: str | None = None,
    align: str = "center",
):
    """渲染顶部导航栏（标题居中/居左 + 返回按钮 + 右侧可选入口）.

    right_action 可选值："profile"（心形入口）、None。
    align 可选值："center"（默认）或 "left"（首页设计稿标题居左）。

    注意：用 st.container() 分组，CSS :has(.top-nav-title) 选择器应用 sticky 样式。
    """
    with st.container():
        cols = st.columns([1, 4, 1])
        with cols[0]:
            if show_back:
                if st.button(
                    "⬅️",
                    key=f"tn_back_{title}",
                    help="返回",
                ):
                    target = st.session_state.get("prev_page", back_target)
                    switch_page(target)
        with cols[1]:
            title_style = (
                "text-align:left;" if align == "left" else "text-align:center;"
            )
            title_html = (
                f"<div class='top-nav-title' style='{title_style}'>{_safe(title)}</div>"
            )
            if subtitle:
                title_html += f"<div class='top-nav-subtitle' style='{title_style}'>{_safe(subtitle)}</div>"
            st.markdown(title_html, unsafe_allow_html=True)
        with cols[2]:
            if right_action == "profile":
                if st.button(
                    "❤️",
                    key=f"tn_profile_{title}",
                    help="健康档案",
                ):
                    switch_page("profile")
