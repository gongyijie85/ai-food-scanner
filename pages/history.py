"""历史记录页与产品详情页渲染."""

import streamlit as st

from components import (
    _ICON_SPEAKER,
    _render_additive_card,
    _render_score_hero,
    render_empty_state,
    render_nutrition_bars,
    render_top_nav,
    voice_control_panel,
)
from utils.api import MODEL_NAME
from utils.display import (
    build_detail_speak,
    family_conclusion_for_result,
    filter_history_entries,
    format_scan_time,
    history_band_for_score,
    short_product_name,
    status_copy_for_result,
)
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
    safe_name = _safe(short_product_name(name, max_len=18))
    return (
        f"{status_emoji} {safe_name}\n"
        f"{score} 分 · {status_text} · {additives_count}种添加剂 · {ts}"
    )


def render_history_page():
    """历史记录页：搜索 +「要注意」筛选 + 整行可点击列表."""
    render_top_nav("历史记录", back_target="home")

    st.markdown(
        "<p class='history-page-hint'>筛选「要注意」可快速复盘少买/留意的商品</p>",
        unsafe_allow_html=True,
    )

    # 搜索栏（原生 st.text_input）
    search = st.text_input(
        "搜索产品名称",
        key="history_search",
        placeholder="搜索产品名称...",
        label_visibility="collapsed",
    )

    # 档位筛选：全部 / 要注意（&lt;80）/ 较省心（≥80）
    # 新 key 避免旧 segmented 会话态残留「良好/高风险」
    filter_options = ["全部", "要注意", "较省心"]
    current_filter = (
        st.segmented_control(
            "记录筛选",
            options=filter_options,
            default="全部",
            key="history_filter_band_v2",
            label_visibility="collapsed",
        )
        or "全部"
    )

    history = load_history()
    filtered = filter_history_entries(history, search=search or "", band=current_filter)

    if not filtered:
        if not history:
            render_empty_state("还没有扫描记录", "去首页拍第一张配料表吧")
            if st.button(
                "拍配料表",
                type="primary",
                width="stretch",
                key="hist_empty_scan",
            ):
                switch_page("scan")
        elif current_filter == "要注意":
            st.success("当前没有「要注意」的记录，挺好的")
            if st.button("查看全部记录", key="hist_show_all", width="stretch"):
                st.session_state["history_filter_band_v2"] = "全部"
                st.rerun()
        elif current_filter == "较省心":
            st.info("还没有较省心的记录，去拍一张配料表试试")
        else:
            st.info("没有匹配的记录")
        return

    # 历史列表：整行可点击按钮
    for idx, item in filtered:
        score = item.get("score", 0)
        status_class, status_text, bar_color = history_band_for_score(score)
        ts = format_scan_time(item.get("timestamp", ""))
        # 列表只显示日期部分更短
        if "日" in ts:
            ts_short = ts.split("日")[0] + "日"
        else:
            ts_short = ts[:10]
        name = item.get("product_name", "未知")
        additives_count = item.get("additives_count", 0)

        label = _history_row_label(
            score, status_text, bar_color, name, additives_count, ts_short
        )
        # marker 供 CSS :has 定位，给相邻按钮加左侧状态色条
        st.markdown(
            f"<div class='history-row-btn-marker {status_class}'></div>",
            unsafe_allow_html=True,
        )
        if st.button(
            label,
            key=f"hist_btn_{idx}",
            width="stretch",
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
        additives = record.get("additives", []) or []
        ingredients = record.get("ingredients", []) or []
        advice = record.get("advice", "") or ""
    else:
        product_name = fallback.get("product_name", "未知")
        score = fallback.get("score", 0)
        additives = fallback.get("additives", []) or []
        ingredients = fallback.get("ingredients", []) or []
        advice = fallback.get("advice", "") or ""

    display_name = short_product_name(product_name)
    label, meaning, score_class = status_copy_for_result(score, additives)
    family_line, family_tone = family_conclusion_for_result(score, additives)

    render_top_nav("产品详情", back_target=st.session_state.get("prev_page", "home"))

    ts_raw = fallback.get("timestamp", "") or (
        record.get("timestamp", "") if record else ""
    )
    ts_friendly = format_scan_time(ts_raw)

    # 评分英雄区：短名 + 与添加剂一致的状态
    _render_score_hero(
        score,
        display_name,
        show_slow_replay=False,
        scan_date=ts_friendly,
        status_label=label,
        status_meaning=meaning,
        score_class=score_class,
    )
    if display_name != (product_name or "").strip() and product_name:
        st.caption(f"全称：{_safe(product_name)}")

    st.markdown(
        f"<div class='family-verdict family-verdict-{_safe(family_tone)}' role='status'>"
        f"<span class='family-verdict-kicker'>一句话</span>"
        f"<p class='family-verdict-text'>{_safe(family_line)}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # 语音（子女回看历史时也能听）
    speak = build_detail_speak(
        product_name, score, additives, advice=advice, ingredients=ingredients
    )
    if family_line and not speak.startswith("给家人"):
        speak = family_line + "。" + speak
    voice_control_panel(
        speak,
        key_prefix="tts_detail",
        button_text=f"{_ICON_SPEAKER} 听结果",
        wrapper_class="voice-controls voice-controls-primary",
    )

    # 扫描信息卡片
    type_label = "保健食品" if fallback.get("type") == "supplement" else "食品"
    if record and record.get("type") == "supplement":
        type_label = "保健食品"
    st.markdown(
        "<div class='result-card detail-scan-card'>"
        "<div class='result-card-title'>扫描信息</div>"
        "<div class='detail-scan-meta'>"
        "<div class='detail-image-placeholder'>本次未保留<br>包装照片</div>"
        "<div class='detail-scan-info'>"
        f"<div class='detail-scan-row'><span class='detail-scan-label'>扫描时间</span>"
        f"<span class='detail-scan-value'>{_safe(ts_friendly)}</span></div>"
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
    if record or additives:
        _render_additive_card(additives)
    if record:
        render_nutrition_bars(record)
        if advice:
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>健康建议</div>"
                f"<p class='detail-advice-text'>{_safe(advice)}</p></div>",
                unsafe_allow_html=True,
            )
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
            if st.button("重新扫描", key="detail_rescore", width="stretch"):
                switch_page("scan")
        with col2:
            if st.button("分享给家人", key="detail_share", width="stretch"):
                summary = (
                    f"{display_name}，配料参考分{score}分，{label}。"
                    f"结果仅供参考，不构成医疗建议。"
                )
                st.session_state["last_share_summary"] = summary
                st.toast("已生成摘要，可复制后发给家人：" + summary[:40] + "…")
