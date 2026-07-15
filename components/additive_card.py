"""添加剂清单卡片组件（设计稿风格）."""

import streamlit as st

from services.additive_matcher import MatchStatus
from utils.security import _safe


def _get_level_info(level: str, status) -> tuple[str, str, str]:
    """统一返回添加剂等级信息：标签、颜色、形状图标."""
    # 未匹配项：中性灰色，不参与评分
    if getattr(status, "value", "") == "unmatched" or level == "":
        return "未识别", "#9E9E9E", "?"
    if level == "A":
        label, color, shape = "较友好", "#43A047", "●"
    elif level == "C":
        label, color, shape = "建议少吃", "#E53935", "■"
    else:
        label, color, shape = "注意", "#FF9800", "▲"
    # status 是 MatchStatus 枚举或带有 value 属性的对象
    if getattr(status, "value", "") == "pending":
        label = "待确认"
    return label, color, shape


def _render_additive_card(additives, key="additive_card"):
    """渲染添加剂清单卡片.

    - 空状态：成功提示行
    - 非空：按风险排序的列表项 + 色盲图例
    """
    # 添加剂卡片标题图标（实验瓶/清单）
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

    # 按风险等级排序：C/红=0，unmatched/B/黄=1，A/绿=2
    level_order = {
        "C": 0,
        "red": 0,
        "unmatched": 1,
        "B": 1,
        "yellow": 1,
        "A": 2,
        "green": 2,
    }

    def _sort_key(x):
        status = x.get("status")
        if hasattr(status, "value"):
            return level_order.get(status.value, 1)
        return level_order.get(status, level_order.get(x.get("level", "B"), 1))

    sorted_additives = sorted(additives, key=_sort_key)

    expand_key = f"{key}_expanded"
    if expand_key not in st.session_state:
        st.session_state[expand_key] = False

    total = len(sorted_additives)
    expanded = st.session_state[expand_key]
    display = sorted_additives if expanded or total <= 5 else sorted_additives[:5]

    html = (
        f"<div class='content-card'>"
        f"<h2 class='card-title'>{title_icon}添加剂清单</h2>"
        f"<div class='card-body'>"
        f"<div class='result-additive-list'>"
    )
    for item in display:
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

        if shape == "?":
            clip = "none"
        elif shape == "▲":
            clip = "polygon(50% 0%, 0% 100%, 100% 100%)"
        elif shape == "■":
            clip = "polygon(0 0, 100% 0, 100% 100%, 0 100%)"
        else:
            clip = "circle(50%)"
        note_html = f"<div class='result-additive-note'>{note}</div>" if note else ""
        if ai_inferred:
            note_html += "<div class='ai-inferred-tag'>自动识别，请以包装为准</div>"
        meta_html = f"<div class='result-additive-meta'>{meta}</div>" if meta else ""
        # 名称相同时只显示一次，避免重复；不同时显示识别对应关系
        canonical_html = (
            ""
            if canonical == raw_name
            else f"<div class='result-additive-canonical'>识别为：{canonical}</div>"
        )
        html += (
            f"<div class='result-additive-item' style='border-left-color:{color};'>"
            f"<span class='result-additive-shape' style='background:{color};clip-path:{clip};'></span>"
            f"<div class='result-additive-body'>"
            f"<div class='result-additive-name'>{raw_name}</div>"
            f"{canonical_html}"
            f"{meta_html}"
            f"{note_html}"
            f"</div>"
            f"<span class='result-additive-level' style='color:{color};border-color:{color};background:{color}11;'>{label}</span>"
            f"</div>"
        )
    html += "</div></div></div>"
    st.markdown(html, unsafe_allow_html=True)

    if total > 5:
        btn_label = "收起" if expanded else f"展开全部（共 {total} 项）"
        if st.button(btn_label, use_container_width=True, key=f"{key}_toggle"):
            st.session_state[expand_key] = not expanded
            st.rerun()

    legend_html = (
        "<div class='result-additive-legend'>"
        "<div class='legend-item'><span class='legend-shape' style='background:#43A047;clip-path:circle(50%);'></span><span>绿色圆：较友好</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#FF9800;clip-path:polygon(50% 0%,0% 100%,100% 100%);'></span><span>黄色三角：适量注意</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#E53935;clip-path:polygon(0 0,100% 0,100% 100%,0 100%);'></span><span>红色方块：建议少吃</span></div>"
        "</div>"
    )
    st.markdown(legend_html, unsafe_allow_html=True)
