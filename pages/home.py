"""首页页面渲染（历史记录 + 底部双按钮）."""

import streamlit as st

from components import render_top_nav
from components.user_guide import render_user_guide
from utils.display import history_band_for_score
from utils.helpers import switch_page
from utils.history import load_history
from utils.security import _safe


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


def _render_home_hero() -> None:
    """首页主视觉：与扫描页同一套「拍配料表」话术."""
    st.markdown(
        "<div class='home-hero'>"
        "<p class='home-hero-kicker'>拍了就懂</p>"
        "<h1 class='home-hero-title'>对准「配料表」拍照</h1>"
        "<p class='home-hero-sub'>"
        "马上听懂能不能放心给家人吃 · 光线够、尽量平、字要大"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_home_empty() -> None:
    """无历史：强化主 CTA 路径，复用扫描三步话术."""
    st.markdown(
        "<div class='home-empty'>"
        "<div class='home-empty-icon' aria-hidden='true'>📷</div>"
        "<p class='home-empty-title'>还没有识别记录</p>"
        "<p class='home-empty-desc'>拍包装上的配料小字，不是商品名那一面</p>"
        "<div class='home-empty-steps'>"
        "<div class='home-empty-step'><span>1</span>光线够</div>"
        "<div class='home-empty-step'><span>2</span>尽量平</div>"
        "<div class='home-empty-step'><span>3</span>字要大</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button(
        "拍配料表",
        type="primary",
        key="home_empty_scan",
        width="stretch",
    ):
        switch_page("scan")


def render_home_page():
    """首页：主 CTA + 最近识别 + 底部导航动作."""
    render_top_nav(
        "拍了就懂",
        subtitle="对准配料表，马上听懂",
        show_back=False,
    )
    render_user_guide("home")
    _render_home_hero()

    history = load_history()

    st.markdown(
        "<div class='result-card-title home-section-title'>" "🕐 最近识别</div>",
        unsafe_allow_html=True,
    )

    if not history:
        _render_home_empty()
    else:
        # 有历史时仍突出「再扫一个」入口
        if st.button(
            "拍配料表 · 再扫一个",
            type="primary",
            key="home_again_scan",
            width="stretch",
        ):
            switch_page("scan")

        for idx, item in enumerate(history[:3]):
            score = item.get("score", 0)
            status_class, status_text, bar_color = history_band_for_score(score)
            ts = item.get("timestamp", "")[:10]
            name = item.get("product_name", "未知")
            additives_count = item.get("additives_count", 0)

            label = _history_button_label(
                item, score, status_text, bar_color, name, additives_count, ts
            )
            st.markdown(
                f"<div class='home-history-row-marker {status_class}'></div>",
                unsafe_allow_html=True,
            )
            if st.button(
                label,
                key=f"home_hist_{idx}",
                width="stretch",
            ):
                st.session_state["selected_history_index"] = idx
                st.session_state["detail_fallback_record"] = item
                switch_page("detail")

        if len(history) > 3:
            if st.button(
                "查看全部历史 · 可筛选要注意的",
                key="home_view_all_history",
                width="stretch",
            ):
                switch_page("history")

    # 底部固定双按钮（与底栏导航互补：主行动拍配料表）
    with st.container():
        st.markdown(
            "<div class='home-action-bar-marker'></div>", unsafe_allow_html=True
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "📷 拍配料表",
                type="primary",
                key="home_btn_scan",
                width="stretch",
            ):
                switch_page("scan")
        with col2:
            if st.button(
                "❤️ 健康档案",
                key="home_btn_profile",
                width="stretch",
            ):
                switch_page("profile")

    st.markdown(
        "<p class='disclaimer-text'>识别结果仅供参考，请以包装上的配料表为准</p>",
        unsafe_allow_html=True,
    )
