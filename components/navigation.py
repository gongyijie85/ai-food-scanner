"""全局导航组件：移动端底部标签栏 + 桌面端侧边栏."""

import os

import streamlit as st

from components.icons import (
    _ICON_CAMERA,
    _ICON_HISTORY,
    _ICON_HOME,
    _ICON_PROFILE,
)
from utils.helpers import detect_device_type


def render_mobile_bottom_nav(switch_page_func):
    """渲染移动端底部固定标签栏.

    共 4 个 tab：首页 / 扫描 / 历史 / 我的，根据当前 page 高亮激活项。
    """
    current_page = st.session_state.get("page", "home")

    tabs = [
        ("home", _ICON_HOME, "首页"),
        ("scan", _ICON_CAMERA, "扫描"),
        ("history", _ICON_HISTORY, "历史"),
        ("profile", _ICON_PROFILE, "我的"),
    ]

    with st.container():
        st.markdown(
            "<div class='mobile-bottom-nav-marker'></div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(4)
        for col, (page, icon, label) in zip(cols, tabs):
            active = current_page == page
            item_class = "mobile-bottom-nav-item"
            if active:
                item_class += " active"
            with col:
                with st.container():
                    st.markdown(
                        f"<div class='{item_class}'></div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"{icon}\n{label}",
                        use_container_width=True,
                        key=f"mobile_nav_{page}",
                    ):
                        switch_page_func(page)


def render_desktop_sidebar(switch_page_func, safe_func, show_history_func):
    """渲染桌面端侧边栏导航.

    包含：首页 / 扫描 / 历史 / 健康档案、模型选择、法律声明、最近历史。
    """
    with st.sidebar:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                f"{_ICON_HOME} 首页", use_container_width=True, key="sidebar_home"
            ):
                switch_page_func("home")
        with c2:
            if st.button(
                f"{_ICON_HISTORY} 历史",
                use_container_width=True,
                key="sidebar_history",
            ):
                switch_page_func("history")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        if st.button(
            f"{_ICON_CAMERA} 扫描", use_container_width=True, key="sidebar_scan"
        ):
            switch_page_func("scan")

        if st.button(
            f"{_ICON_PROFILE} 健康档案",
            use_container_width=True,
            key="sidebar_profile",
        ):
            switch_page_func("profile")

        st.divider()

        with st.expander("高级设置"):
            model_choice = st.radio(
                "选择识别模型",
                options=["mimo", "agnes"],
                format_func=lambda x: {
                    "mimo": "MiMo（推荐）：识别更准确",
                    "agnes": "Agnes（更快）：速度优先",
                }[x],
                key="selected_model_radio",
                index=0
                if st.session_state.get("selected_model", "mimo") == "mimo"
                else 1,
            )
            st.session_state["selected_model"] = model_choice
            if os.getenv("DEBUG") == "1":
                if st.button("重新查看引导", use_container_width=True, key="replay_ob"):
                    st.session_state["onboarded"] = False
                    st.session_state["onboarding_step"] = 1
                    st.rerun()

        with st.expander("📄 法律声明"):
            st.caption("AI识别仅供参考，不构成医疗建议")
            if st.button("查看用户协议", use_container_width=True, key="sidebar_ua"):
                switch_page_func("legal_ua")
            if st.button("查看隐私政策", use_container_width=True, key="sidebar_pp"):
                switch_page_func("legal_pp")

        st.divider()
        show_history_func(switch_page_func, safe_func)


def render_navigation(switch_page_func, safe_func, show_history_func):
    """根据设备类型渲染对应导航."""
    if detect_device_type() == "mobile":
        render_mobile_bottom_nav(switch_page_func)
    else:
        render_desktop_sidebar(switch_page_func, safe_func, show_history_func)
