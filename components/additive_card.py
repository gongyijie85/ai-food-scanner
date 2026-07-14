"""添加剂清单卡片组件."""

import streamlit as st

from services.additive_matcher import MatchStatus
from utils.security import _safe


def _get_level_info(level: str, status) -> tuple[str, str, str]:
    """统一返回添加剂等级信息：标签、颜色、形状图标.

    根据 level 给出基础视觉（A=绿圆，B=黄三角，C=红方块），
    再用 status 覆盖标签：pending=等级待评估，unmatched=名称待核对。
    """
    if level == "A":
        label, color, shape = "较友好", "#43A047", "●"
    elif level == "C":
        label, color, shape = "建议少吃", "#E53935", "■"
    else:
        label, color, shape = "注意", "#FF9800", "▲"
    # status 是 MatchStatus 枚举或带有 value 属性的对象
    if getattr(status, "value", "") == "pending":
        label = "等级待评估"
    elif getattr(status, "value", "") == "unmatched":
        label = "名称待核对"
    return label, color, shape


def _render_additive_card(additives, key="additive_card"):
    """渲染添加剂清单卡片（画布设计稿：图标 + 名称/类别 + 标签 + 色盲图例）.

    展示标准名、INS/CNS、功能、匹配状态、应用等级；图例内置。
    超过 5 项时默认折叠，按风险等级排序（高风险与待核对优先），并提供展开/收起按钮。
    """
    if not additives:
        st.markdown(
            "<div class='result-card'><div class='result-card-title'>🧪 添加剂清单</div>"
            "<p style='color:#666;'>未识别到需要关注的食品添加剂</p></div>",
            unsafe_allow_html=True,
        )
        return

    # 按风险等级排序：C/红=0，unmatched/B/黄=1，A/绿=2，让高风险与待核对项优先可见
    level_order = {
        "C": 0, "red": 0,
        "unmatched": 1, "B": 1, "yellow": 1,
        "A": 2, "green": 2,
    }

    def _sort_key(x):
        # 优先用匹配状态决定排序；没有状态时回退到 level
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
        "<div class='result-card'>"
        "<div class='result-card-title'>🧪 添加剂清单</div>"
        "<div class='result-additive-list'>"
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

        # 元信息：CNS / INS / 功能，用 · 连接
        meta_parts = [
            p for p in [
                f"CNS {cns}" if cns else "",
                f"INS {ins}" if ins else "",
                function,
            ] if p
        ]
        meta = " · ".join(meta_parts)

        # 形状：三角=注意，方块=高风险，圆=较友好
        clip = (
            "polygon(50% 0%, 0% 100%, 100% 100%)"
            if shape == "▲"
            else (
                "polygon(0 0, 100% 0, 100% 100%, 0 100%)"
                if shape == "■"
                else "circle(50%)"
            )
        )
        note_html = f"<div class='result-additive-note'>{note}</div>" if note else ""
        if ai_inferred:
            note_html += "<div class='ai-inferred-tag'>AI 推断，请以包装原文为准</div>"
        meta_html = f"<div class='result-additive-meta'>{meta}</div>" if meta else ""
        html += (
            f"<div class='result-additive-item' style='border-left-color:{color};'>"
            f"<span class='result-additive-shape' style='background:{color};clip-path:{clip};'></span>"
            f"<div class='result-additive-body'>"
            f"<div class='result-additive-name'>{raw_name}</div>"
            f"<div class='result-additive-canonical'>{canonical}</div>"
            f"{meta_html}"
            f"{note_html}"
            f"</div>"
            f"<span class='result-additive-level' style='color:{color};border-color:{color};background:{color}11;'>{label}</span>"
            f"</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    if total > 5:
        btn_label = "收起" if expanded else f"展开全部（共 {total} 项）"
        if st.button(btn_label, use_container_width=True, key=f"{key}_toggle"):
            st.session_state[expand_key] = not expanded
            st.rerun()

    legend_html = (
        "<div class='result-additive-legend'>"
        "<div class='legend-item'><span class='legend-shape' style='background:#43A047;clip-path:circle(50%);'></span><span>圆=较友好</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#FF9800;clip-path:polygon(50% 0%,0% 100%,100% 100%);'></span><span>三角=注意</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#E53935;clip-path:polygon(0 0,100% 0,100% 100%,0 100%);'></span><span>方块=高风险</span></div>"
        "</div>"
        "</div>"
    )
    st.markdown(legend_html, unsafe_allow_html=True)
