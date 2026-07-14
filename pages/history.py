"""历史记录页与产品详情页渲染."""

import streamlit as st

from components import (
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


def _history_row_label(score, status_text, bar_color, name, additives_count, ts):
    """构造历史页整行可点击按钮的纯文本标签.

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


def render_history_page():
    """历史记录页：搜索栏 + 分段控制器 + 整行可点击列表."""
    render_top_nav("历史记录", back_target="home")

    # 搜索栏（原生 st.text_input）
    search = st.text_input(
        "搜索产品名称",
        key="history_search",
        placeholder="搜索产品名称...",
        label_visibility="collapsed",
    )

    # 风险筛选：原生 segmented_control，无需手动 rerun
    filter_options = ["全部", "良好", "注意", "高风险"]
    current_filter = (
        st.segmented_control(
            "风险筛选",
            options=filter_options,
            default="全部",
            key="history_filter_segmented",
            label_visibility="collapsed",
        )
        or "全部"
    )

    history = load_history()
    filtered = []
    for idx, item in enumerate(history):
        name = item.get("product_name", "")
        score = item.get("score", 0)
        if search and search.lower() not in name.lower():
            continue
        if current_filter == "良好" and score < 80:
            continue
        if current_filter == "注意" and not (60 <= score < 80):
            continue
        if current_filter == "高风险" and score >= 60:
            continue
        filtered.append((idx, item))

    if not filtered:
        if not history:
            render_empty_state("还没有扫描记录", "去首页拍第一张配料表吧")
            if st.button(
                "开始扫描",
                type="primary",
                use_container_width=True,
                key="hist_empty_scan",
            ):
                switch_page("scan")
        else:
            st.info("没有匹配的记录")
        return

    # 历史列表：整行可点击按钮
    for idx, item in filtered:
        score = item.get("score", 0)
        if score >= 80:
            status_class, status_text, bar_color = "safe", "良好", "#43A047"
        elif score >= 60:
            status_class, status_text, bar_color = "caution", "注意", "#F57F17"
        else:
            status_class, status_text, bar_color = "danger", "高风险", "#C62828"
        ts = item.get("timestamp", "")[:10]
        name = item.get("product_name", "未知")
        additives_count = item.get("additives_count", 0)

        label = _history_row_label(
            score, status_text, bar_color, name, additives_count, ts
        )
        # marker 供 CSS :has 定位，给相邻按钮加左侧状态色条
        st.markdown(
            f"<div class='history-row-btn-marker {status_class}'></div>",
            unsafe_allow_html=True,
        )
        if st.button(
            label,
            key=f"hist_btn_{idx}",
            use_container_width=True,
        ):
            st.session_state["selected_history_index"] = idx
            st.session_state["detail_fallback_record"] = item
            switch_page("detail")


def render_detail_page():
    """产品详情页：读取 history_full.json 展示完整识别快照."""
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
    ts = fallback.get("timestamp", "") or (
        record.get("timestamp", "") if record else ""
    )
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
            if st.button("重新评分", key="detail_rescore", use_container_width=True):
                switch_page("scan")
        with col2:
            if st.button("分享给家人", key="detail_share", use_container_width=True):
                st.toast("已复制结果摘要，可直接粘贴给家人")
