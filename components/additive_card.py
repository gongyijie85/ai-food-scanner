"""添加剂清单卡片组件."""

import streamlit as st

from utils.security import _safe


def _get_level_info(level: str) -> tuple[str, str, str]:
    """统一返回添加剂等级信息：标签、颜色、形状图标."""
    mapping = {
        "A": ("可食用", "#43A047", "●"),
        "green": ("可食用", "#43A047", "●"),
        "B": ("特定人群注意", "#FF9800", "▲"),
        "yellow": ("特定人群注意", "#FF9800", "▲"),
        "C": ("建议少吃", "#E53935", "■"),
        "red": ("建议少吃", "#E53935", "■"),
    }
    return mapping.get(level, ("未知", "#9E9E9E", "●"))


def _render_additive_card(additives, key="additive_card"):
    """渲染添加剂清单卡片（画布设计稿：图标 + 名称/类别 + 标签 + 色盲图例）.

    超过 5 项时默认折叠，按风险等级排序（高风险优先），并提供展开/收起按钮。
    """
    if not additives:
        st.markdown(
            "<div class='result-card'><div class='result-card-title'>🧪 添加剂清单</div>"
            "<p style='color:#666;'>未识别到需要关注的食品添加剂</p></div>",
            unsafe_allow_html=True,
        )
        return

    # 按风险等级排序：C(红) > B(黄) > A(绿)，让高风险项优先可见
    level_order = {"C": 0, "red": 0, "B": 1, "yellow": 1, "A": 2, "green": 2}
    sorted_additives = sorted(
        additives,
        key=lambda x: level_order.get(x.get("level", "B"), 1),
    )

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
        name = _safe(item.get("name", "未知"))
        level = item.get("level", "B")
        note = _safe(item.get("note", ""))
        label, color, shape = _get_level_info(level)
        label = _safe(label)
        clip = (
            "polygon(50% 0%, 0% 100%, 100% 100%)" if shape == "▲"
            else "polygon(0 0, 100% 0, 100% 100%, 0 100%)" if shape == "■"
            else "circle(50%)"
        )
        note_html = f"<div class='result-additive-note'>{note}</div>" if note else ""
        html += (
            f"<div class='result-additive-item' style='border-left-color:{color};'>"
            f"<span class='result-additive-shape' style='background:{color};clip-path:{clip};'></span>"
            f"<div class='result-additive-body'>"
            f"<div class='result-additive-name'>{name}</div>"
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
        "<div class='legend-item'><span class='legend-shape' style='background:#43A047;clip-path:circle(50%);'></span><span>圆=安全</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#FF9800;clip-path:polygon(50% 0%,0% 100%,100% 100%);'></span><span>三角=中等</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#E53935;clip-path:polygon(0 0,100% 0,100% 100%,0 100%);'></span><span>方块=高风险</span></div>"
        "</div>"
        "</div>"
    )
    st.markdown(legend_html, unsafe_allow_html=True)
