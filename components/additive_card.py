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


def _render_additive_card(additives):
    """渲染添加剂清单卡片（画布设计稿：图标 + 名称/类别 + 标签 + 色盲图例）."""
    if not additives:
        st.markdown(
            "<div class='result-card'><div class='result-card-title'>🧪 添加剂清单</div>"
            "<p style='color:#666;'>未识别到需要关注的食品添加剂</p></div>",
            unsafe_allow_html=True,
        )
        return
    html = (
        "<div class='result-card'>"
        "<div class='result-card-title'>🧪 添加剂清单</div>"
        "<div class='result-additive-list'>"
    )
    for item in additives:
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
    html += (
        "</div>"
        "<div class='result-additive-legend'>"
        "<div class='legend-item'><span class='legend-shape' style='background:#43A047;clip-path:circle(50%);'></span><span>圆=安全</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#FF9800;clip-path:polygon(50% 0%,0% 100%,100% 100%);'></span><span>三角=中等</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#E53935;clip-path:polygon(0 0,100% 0,100% 100%,0 100%);'></span><span>方块=高风险</span></div>"
        "</div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)
