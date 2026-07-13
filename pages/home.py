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
        st.markdown("<div class='home-history-list'>", unsafe_allow_html=True)
        for idx, item in enumerate(history[:3]):
            score = item.get("score", 0)
            status_class, bar_color = _status_style(score)
            status_text = (
                "良好" if score >= 80 else ("注意" if score >= 60 else "高风险")
            )
            ts = item.get("timestamp", "")[:10]
            name = _safe(item.get("product_name", "未知"))
            additives_count = item.get("additives_count", 0)

            card_html = (
                f"<div class='home-history-card {status_class}' style='"
                f"display:flex;align-items:center;gap:14px;padding:14px;"
                f"background:#fff;border-radius:16px;box-shadow:0 2px 8px rgba(0,0,0,0.08);"
                f"border-left:5px solid {bar_color};margin-bottom:12px;cursor:pointer;'>"
                f"<div style='width:50px;height:50px;border-radius:50%;background:{bar_color};"
                f"color:#fff;display:flex;flex-direction:column;align-items:center;"
                f"justify-content:center;flex-shrink:0;font-weight:700;'>"
                f"<div style='font-size:20px;line-height:1;'>{score}</div>"
                f"<div style='font-size:10px;'>{status_text}</div>"
                f"</div>"
                f"<div style='flex:1;min-width:0;display:flex;flex-direction:column;gap:4px;'>"
                f"<div style='font-size:16px;font-weight:600;white-space:nowrap;"
                f"overflow:hidden;text-overflow:ellipsis;'>{name}</div>"
                f"<div style='font-size:13px;color:#616161;'>"
                f"{additives_count}种添加剂 · {ts}</div>"
                f"</div>"
                f"<div style='color:#9E9E9E;flex-shrink:0;'>➡️</div>"
                f"</div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button(
                "查看详情",
                key=f"home_hist_{idx}",
                help="查看详情",
                use_container_width=True,
            ):
                st.session_state["selected_history_index"] = idx
                st.session_state["detail_fallback_record"] = item
                switch_page("detail")
        st.markdown("</div>", unsafe_allow_html=True)

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
