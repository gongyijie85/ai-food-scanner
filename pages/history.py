"""历史记录页与产品详情页渲染."""

import streamlit as st

from components import (
    _ICON_CAMERA,
    _ICON_REFRESH,
    _ICON_SHARE,
    _render_additive_card,
    _render_score_hero,
    render_empty_state,
    render_nutrition_bars,
    render_top_nav,
)
from utils.api import MODEL_NAME
from utils.helpers import switch_page
from utils.history import load_history, load_history_full
from utils.security import _safe


def render_history_page():
    """历史记录页：搜索栏 + 筛选标签 + 竖向列表（对齐设计稿）."""
    render_top_nav("历史记录", back_target="home")

    # 搜索栏
    st.markdown(
        "<div class='history-search-wrap'>"
        "<div class='history-search-box'>"
        "<span class='history-search-icon'>🔍</span>",
        unsafe_allow_html=True,
    )
    search = st.text_input(
        "搜索产品名称",
        key="history_search",
        placeholder="搜索产品名称...",
        label_visibility="collapsed",
    )
    st.markdown("</div></div>", unsafe_allow_html=True)

    # 筛选标签
    filter_options = [
        ("全部", "all", "active"),
        ("安全", "safe", "safe"),
        ("注意", "caution", "caution"),
        ("高风险", "danger", "danger"),
    ]
    current_filter = st.session_state.get("history_filter", "全部")

    st.markdown("<div class='history-filter-row'>", unsafe_allow_html=True)
    filter_col = current_filter
    for label, value, css in filter_options:
        wrapper_cls = f"history-filter-chip-wrapper {css}"
        if current_filter == label:
            wrapper_cls += " active"
        st.markdown(f"<div class='{wrapper_cls}'>", unsafe_allow_html=True)
        if st.button(label, key=f"hist_filter_{value}"):
            st.session_state["history_filter"] = label
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    history = load_history()
    filtered = []
    for idx, item in enumerate(history):
        name = item.get("product_name", "")
        score = item.get("score", 0)
        if search and search.lower() not in name.lower():
            continue
        if filter_col == "安全" and score < 80:
            continue
        if filter_col == "注意" and not (60 <= score < 80):
            continue
        if filter_col == "高风险" and score >= 60:
            continue
        filtered.append((idx, item))

    if not filtered:
        if not history:
            render_empty_state("还没有扫描记录", "去首页拍第一张配料表吧")
            if st.button(f"{_ICON_CAMERA} 开始扫描", type="primary", width="stretch", key="hist_empty_scan"):
                switch_page("scan")
        else:
            st.info("没有匹配的记录")
        return

    st.markdown("<div class='history-list-wrap'>", unsafe_allow_html=True)
    for idx, item in filtered:
        score = item.get("score", 0)
        if score >= 80:
            color, bg, status = "#2E7D32", "#E8F5E9", "安全"
        elif score >= 60:
            color, bg, status = "#F57F17", "#FFF8E1", "需要注意"
        else:
            color, bg, status = "#C62828", "#FFEBEE", "高风险"
        ts = item.get("timestamp", "")[:10]
        name = item.get("product_name", "未知")
        st.markdown(
            f"<div class='history-list-item'>"
            f"<div class='history-list-score' style='background:{bg};color:{color};'>{score}</div>"
            f"<div class='history-list-info'>"
            f"<div class='history-list-name'>{_safe(name)}</div>"
            f"<div class='history-list-status' style='color:{color};'>{_safe(status)}</div>"
            f"<div class='history-list-date'>{_safe(ts)}</div>"
            f"</div>"
            f"<div class='history-list-chevron'>›</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("查看", key=f"hist_btn_{idx}", help="查看详情"):
            st.session_state["selected_history_index"] = idx
            st.session_state["detail_fallback_record"] = item
            switch_page("detail")
    st.markdown("</div>", unsafe_allow_html=True)


def render_detail_page():
    """产品详情页：读取 history_full.json 展示完整识别快照（对齐设计稿）."""
    idx = st.session_state.get("selected_history_index", -1)
    fallback = st.session_state.get("detail_fallback_record", {})
    full_records = load_history_full()
    record = full_records[idx] if 0 <= idx < len(full_records) else None

    if record:
        product_name = record.get("product_name", "未知")
        score = record.get("score", 0)
    else:
        product_name = fallback.get("product_name", "未知")
        score = fallback.get("score", 0)

    render_top_nav("产品详情", back_target=st.session_state.get("prev_page", "home"))

    # 评分英雄区
    _render_score_hero(score, product_name, show_slow_replay=False)

    # 扫描信息卡片
    ts = fallback.get("timestamp", "") or (record.get("timestamp", "") if record else "")
    type_label = "保健食品" if fallback.get("type") == "supplement" else "食品"
    st.markdown(
        "<div class='result-card detail-scan-card'>"
        "<div class='result-card-title'>扫描信息</div>"
        "<div class='detail-scan-meta'>"
        "<div class='detail-image-placeholder'>图片<br>未保存</div>"
        "<div class='detail-scan-info'>"
        f"<div class='detail-scan-row'><span class='detail-scan-label'>扫描时间</span>"
        f"<span class='detail-scan-value'>{_safe(ts)}</span></div>"
        f"<div class='detail-scan-row'><span class='detail-scan-label'>识别引擎</span>"
        f"<span class='detail-scan-value'>{_safe(MODEL_NAME)}</span></div>"
        f"<div class='detail-scan-row'><span class='detail-scan-label'>产品类型</span>"
        f"<span class='detail-scan-value'>{_safe(type_label)}</span></div>"
        "</div></div></div>",
        unsafe_allow_html=True,
    )

    if not record:
        st.info("当时未保存完整配料信息，仅展示摘要。")

    # 添加剂 / 营养 / 建议（复用 result 组件）
    if record:
        _render_additive_card(record.get("additives", []))
        render_nutrition_bars(record)
        advice = record.get("advice", "")
        if advice:
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>健康建议</div>"
                f"<p class='detail-advice-text'>{_safe(advice)}</p></div>",
                unsafe_allow_html=True,
            )
        # 全部配料
        ingredients = record.get("ingredients", [])
        if ingredients:
            st.markdown(
                "<div class='result-card'><div class='result-card-title'>全部配料</div>"
                f"<p class='detail-ingredients-text'>{_safe('、'.join(ingredients))}</p></div>",
                unsafe_allow_html=True,
            )

    # 底部操作栏
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"{_ICON_REFRESH} 重新评分", width="stretch", key="detail_rescore"):
                switch_page("scan")
        with col2:
            if st.button(f"{_ICON_SHARE} 分享给家人", width="stretch", key="detail_share"):
                st.toast("已复制结果摘要，可直接粘贴给家人")
