"""首页页面渲染（历史记录 + 底部双按钮）."""

import streamlit as st

from components import render_top_nav
from utils.helpers import switch_page
from utils.history import load_history
from utils.security import _safe


def _status_style(score: int):
    """根据评分返回状态样式."""
    if score >= 80:
        return "safe", "#43A047"
    if score >= 60:
        return "caution", "#F57F17"
    return "danger", "#E53935"


def _history_button_label(
    item, score, status_text, bar_color, name, additives_count, ts
):
    """构造首页历史记录整行按钮的纯文本标签.

    注意：st.button 会对 label 进行 HTML 转义，因此不能再传入 HTML。
    使用 emoji 状态圆 + 两行纯文本，保留产品名、分数、状态、添加剂数量和日期。
    产品名在函数内部做 HTML 转义，避免外部忘记转义时把源码暴露给用户。
    """
    status_emoji = "🟢" if score >= 80 else ("🟠" if score >= 60 else "🔴")
    safe_name = _safe(name)
    return (
        f"{status_emoji} {safe_name}\n"
        f"{score} 分 · {status_text} · {additives_count}种添加剂 · {ts}"
    )


def render_home_page():
    """首页：最近识别记录 + 底部拍照/健康档案双按钮."""
    render_top_nav(
        "食品配料表识别",
        subtitle="拍照即懂，吃得更安心",
        show_back=False,
    )

    history = load_history()

    st.markdown(
        "<div class='result-card-title' style='margin:8px 0 14px 0;'>"
        "🕐 最近识别</div>",
        unsafe_allow_html=True,
    )

    if not history:
        st.markdown(
            "<div style='text-align:center;padding:40px 20px;color:#616161;'>"
            "<div style='font-size:48px;margin-bottom:12px;'>📷</div>"
            "<p>还没有识别记录</p>"
            "<p style='font-size:13px;margin-top:4px;'>点击下方拍照按钮开始</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        # 整行可点击的历史记录按钮列表
        for idx, item in enumerate(history[:3]):
            score = item.get("score", 0)
            status_class, bar_color = _status_style(score)
            status_text = (
                "良好" if score >= 80 else ("注意" if score >= 60 else "高风险")
            )
            ts = item.get("timestamp", "")[:10]
            name = item.get("product_name", "未知")
            additives_count = item.get("additives_count", 0)

            label = _history_button_label(
                item, score, status_text, bar_color, name, additives_count, ts
            )
            # marker 供 CSS :has 定位，给相邻按钮加左侧状态色条
            st.markdown(
                f"<div class='home-history-row-marker {status_class}'></div>",
                unsafe_allow_html=True,
            )
            if st.button(
                label,
                key=f"home_hist_{idx}",
                use_container_width=True,
            ):
                st.session_state["selected_history_index"] = idx
                st.session_state["detail_fallback_record"] = item
                switch_page("detail")

        if len(history) > 3:
            if st.button(
                "查看全部历史记录",
                key="home_view_all_history",
                use_container_width=True,
            ):
                switch_page("history")

    # 底部固定双按钮
    with st.container():
        st.markdown(
            "<div class='home-action-bar-marker'></div>", unsafe_allow_html=True
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "📷 拍照识别",
                type="primary",
                key="home_btn_scan",
                use_container_width=True,
            ):
                switch_page("scan")
        with col2:
            if st.button(
                "❤️ 健康档案",
                key="home_btn_profile",
                use_container_width=True,
            ):
                switch_page("profile")

    st.markdown(
        "<p class='disclaimer-text'>AI识别仅供参考，请以包装原文为准</p>",
        unsafe_allow_html=True,
    )
