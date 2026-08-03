"""添加剂清单卡片组件（设计稿风格）."""

import streamlit as st

from services.additive_matcher import MatchStatus
from utils.display import split_additives_by_attention
from utils.security import _safe


def _get_level_info(level: str, status) -> tuple[str, str, str]:
    """统一返回添加剂等级信息：标签、颜色、形状图标.

    - rated + A/B/C → 较友好/注意/建议少吃
    - pending_rating → 待确认（标准有、风险级未定）
    - unmatched / 无 level → 待核对包装
    历史数据若未写 status 但有 A/B/C level，按 level 显示（避免全员「待确认」）。
    """
    status_val = ""
    if status is not None:
        status_val = getattr(status, "value", None) or str(status)
    status_val = (status_val or "").lower()
    level = (level or "").upper()

    if status_val == "unmatched":
        return "待核对包装", "#9E9E9E", ""
    if status_val == "pending_rating":
        return "待确认", "#FF9800", "▲"
    if level == "A":
        return "较友好", "#43A047", "●"
    if level == "C":
        return "建议少吃", "#E53935", "■"
    if level == "B":
        return "注意", "#FF9800", "▲"
    if level == "" and status_val in ("", "pending_rating"):
        # 无 status 且无 level：兼容极旧数据
        return "待核对包装", "#9E9E9E", ""
    return "注意", "#FF9800", "▲"


def _additive_row_html(item) -> str:
    """单条添加剂行 HTML."""
    raw_name = _safe(item.get("name", "未知"))
    canonical = _safe(item.get("canonical_name", raw_name))
    level = item.get("level", "B")
    status = item.get("status", MatchStatus.PENDING_RATING)
    cns = _safe(item.get("cns", ""))
    ins = _safe(item.get("ins", ""))
    function = _safe(item.get("function", ""))
    note = _safe(item.get("note", ""))
    ai_inferred = item.get("ai_inferred", False)
    label, color, shape = _get_level_info(level, status)

    meta_parts = [
        p
        for p in [
            f"CNS {cns}" if cns else "",
            f"INS {ins}" if ins else "",
            function,
        ]
        if p
    ]
    meta = " · ".join(meta_parts)

    if shape == "▲":
        clip = "polygon(50% 0%, 0% 100%, 100% 100%)"
    elif shape == "■":
        clip = "polygon(0 0, 100% 0, 100% 100%, 0 100%)"
    elif shape == "●":
        clip = "circle(50%)"
    else:
        clip = ""
    shape_html = (
        f"<span class='result-additive-shape' style='background:{color};"
        f"clip-path:{clip};'></span>"
        if shape
        else ""
    )
    note_html = f"<div class='result-additive-note'>{note}</div>" if note else ""
    if ai_inferred:
        note_html += "<div class='ai-inferred-tag'>自动识别，请以包装为准</div>"
    meta_html = f"<div class='result-additive-meta'>{meta}</div>" if meta else ""
    canonical_html = (
        ""
        if canonical == raw_name
        else f"<div class='result-additive-canonical'>识别为：{canonical}</div>"
    )
    return (
        f"<div class='result-additive-item' style='border-left-color:{color};'>"
        f"{shape_html}"
        f"<div class='result-additive-body'>"
        f"<div class='result-additive-name'>{raw_name}</div>"
        f"{canonical_html}"
        f"{meta_html}"
        f"{note_html}"
        f"</div>"
        f"<span class='result-additive-level' style='color:{color};"
        f"border-color:{color};background:{color}11;'>{label}</span>"
        f"</div>"
    )


def _render_additive_card(additives, key="additive_card"):
    """渲染添加剂清单：默认只展示需留意项，较友好折叠.

    - 空状态：成功提示行
    - 非空：注意力优先 + 色盲图例
    """
    title_icon = (
        "<svg viewBox='0 0 24 24' fill='none' stroke='var(--color-primary)' "
        "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2'/>"
        "<rect x='9' y='3' width='6' height='4' rx='1'/>"
        "<path d='M9 14l2 2 4-4'/></svg>"
    )

    if not additives:
        st.markdown(
            f"<div class='content-card'>"
            f"<h2 class='card-title'>{title_icon}添加剂清单</h2>"
            f"<div class='card-body'>"
            f"<div class='card-success-row'>"
            f"<svg viewBox='0 0 24 24' fill='none' stroke='var(--state-success)' "
            f"stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            f"<circle cx='12' cy='12' r='10'/><polyline points='16 9 10.5 15 8 12.5'/></svg>"
            f"<span>未识别到食品添加剂</span>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )
        return

    attention, friendly = split_additives_by_attention(additives)
    expand_key = f"{key}_show_friendly"
    if expand_key not in st.session_state:
        st.session_state[expand_key] = False
    show_friendly = bool(st.session_state[expand_key])

    # 默认：全部需留意；较友好仅在展开时显示
    display = list(attention)
    if show_friendly:
        display = display + list(friendly)
    # 若没有任何需留意项，默认展示较友好摘要（避免空白）
    if not attention and friendly and not show_friendly:
        display = list(friendly)

    subtitle = ""
    if attention and friendly and not show_friendly:
        subtitle = (
            f"<p class='additive-list-hint'>先看需要留意的 "
            f"{len(attention)} 项；较友好的还有 {len(friendly)} 项可展开</p>"
        )
    elif not attention and friendly:
        subtitle = "<p class='additive-list-hint'>暂无高关注项，下列为较友好添加剂</p>"

    html = (
        f"<div class='content-card'>"
        f"<h2 class='card-title'>{title_icon}添加剂清单</h2>"
        f"<div class='card-body'>"
        f"{subtitle}"
        f"<div class='result-additive-list'>"
    )
    for item in display:
        if isinstance(item, dict):
            html += _additive_row_html(item)
    html += "</div></div></div>"
    st.markdown(html, unsafe_allow_html=True)

    if friendly and attention:
        if show_friendly:
            btn_label = "收起较友好项"
        else:
            btn_label = f"展开较友好的 {len(friendly)} 项"
        if st.button(btn_label, use_container_width=True, key=f"{key}_toggle"):
            st.session_state[expand_key] = not show_friendly
            st.rerun()

    legend_html = (
        "<div class='result-additive-legend'>"
        "<div class='legend-item'><span class='legend-shape' "
        "style='background:#43A047;clip-path:circle(50%);'></span>"
        "<span>绿色圆：较友好</span></div>"
        "<div class='legend-item'><span class='legend-shape' "
        "style='background:#FF9800;clip-path:polygon(50% 0%,0% 100%,100% 100%);'>"
        "</span><span>橙色三角：注意</span></div>"
        "<div class='legend-item'><span class='legend-shape' "
        "style='background:#E53935;clip-path:polygon(0 0,100% 0,100% 100%,0 100%);'>"
        "</span><span>红色方块：建议少吃</span></div>"
        "</div>"
    )
    st.markdown(legend_html, unsafe_allow_html=True)
