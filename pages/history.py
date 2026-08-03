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
    filter_history_entries,
    format_scan_time,
    history_band_for_item,
    short_product_name,
)
from utils.helpers import switch_page
from utils.history import load_history, load_history_full
from utils.result_presentation import build_result_presentation
from utils.security import _safe


def _history_row_label(score, status_text, bar_color, name, additives_count, ts):
    """构造历史页整行可点击按钮的纯文本标签（无分数主叙事）.

    score / bar_color 保留签名兼容；状态色由 status_text 对应 emoji。
    """
    _ = score
    _ = bar_color
    if status_text in ("较省心", "暂无高关注"):
        status_emoji = "🟢"
    elif status_text in ("建议少吃", "需重点看"):
        status_emoji = "🔴"
    else:
        status_emoji = "🟠"
    safe_name = _safe(short_product_name(name, max_len=18))
    return (
        f"{status_emoji} {safe_name}\n"
        f"{status_text} · {additives_count}种添加剂 · {ts}"
    )


def render_history_page():
    """历史记录页：搜索 +「要注意」筛选 + 整行可点击列表."""
    render_top_nav("历史记录", back_target="home")

    st.markdown(
        "<p class='history-page-hint'>筛选「有关注项」可快速复盘需核对的商品</p>",
        unsafe_allow_html=True,
    )

    # 搜索栏（原生 st.text_input）
    search = st.text_input(
        "搜索产品名称",
        key="history_search",
        placeholder="搜索产品名称...",
        label_visibility="collapsed",
    )

    # 档位：全部 / 有关注项 / 暂无高关注（不再用分数分档）
    filter_options = ["全部", "要注意", "较省心"]
    current_filter = (
        st.segmented_control(
            "记录筛选",
            options=filter_options,
            default="全部",
            key="history_filter_band_v3",
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
            st.success("当前没有「有关注项」的记录")
            if st.button("查看全部记录", key="hist_show_all", width="stretch"):
                st.session_state["history_filter_band_v3"] = "全部"
                st.rerun()
        elif current_filter == "较省心":
            st.info("还没有「暂无高关注」的记录，去拍一张配料表试试")
        else:
            st.info("没有匹配的记录")
        return

    # 历史列表：整行可点击按钮
    for idx, item in filtered:
        status_class, status_text, bar_color = history_band_for_item(item)
        ts = format_scan_time(item.get("timestamp", ""))
        # 列表只显示日期部分更短
        if "日" in ts:
            ts_short = ts.split("日")[0] + "日"
        else:
            ts_short = ts[:10]
        name = item.get("product_name", "未知")
        additives_count = item.get("additives_count", 0)

        label = _history_row_label(
            item.get("score", 0),
            status_text,
            bar_color,
            name,
            additives_count,
            ts_short,
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
        additives = record.get("additives", []) or []
        ingredients = record.get("ingredients", []) or []
        advice = record.get("advice", "") or ""
    else:
        product_name = fallback.get("product_name", "未知")
        additives = fallback.get("additives", []) or []
        ingredients = fallback.get("ingredients", []) or []
        advice = fallback.get("advice", "") or ""

    display_name = short_product_name(product_name)
    detail_payload = {
        "type": (record or fallback or {}).get("type", "food"),
        "product_name": product_name,
        "additives": additives,
        "ingredients": ingredients,
        "ocr_text": (record or {}).get("ocr_text", "") if record else "",
        "advice": advice,
    }
    if record:
        detail_payload = {**record, **detail_payload}
    pres = build_result_presentation(detail_payload)

    render_top_nav("产品详情", back_target=st.session_state.get("prev_page", "home"))

    ts_raw = fallback.get("timestamp", "") or (
        record.get("timestamp", "") if record else ""
    )
    ts_friendly = format_scan_time(ts_raw)

    # 与结果页同一呈现契约
    _render_score_hero(
        0,
        pres.product_display_name,
        show_slow_replay=False,
        scan_date=ts_friendly,
        status_label=pres.status_label,
        status_meaning=pres.status_meaning,
        score_class=pres.status_class,
        recognition_label=pres.recognition_label,
        recognition_meaning=pres.recognition_meaning,
        action_line=pres.action_line,
        show_score=False,
    )
    if display_name != (product_name or "").strip() and product_name:
        st.caption(f"全称：{_safe(product_name)}")

    voice_control_panel(
        pres.voice_script,
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
                    f"{pres.product_display_name}，{pres.status_label}。"
                    f"{pres.action_line}"
                    f"结果仅供参考，不构成医疗建议。"
                )
                st.session_state["last_share_summary"] = summary
                st.toast("已生成摘要，可复制后发给家人：" + summary[:40] + "…")
