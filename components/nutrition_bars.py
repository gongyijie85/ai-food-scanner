"""营养成分可视化条组件."""

import streamlit as st

from utils.security import _safe


def render_nutrition_bars(result):
    """营养成分可视化条（钠/糖/脂肪 NRV%，Task 10.3）.

    仅当识别结果中包含 nutrition_nrv 字段时显示，否则跳过。
    字段格式：{"钠": 20, "糖": 35, "脂肪": 10}（数值为 NRV 百分比）
    """
    nrv = result.get("nutrition_nrv") or result.get("nutrition")
    if not nrv or not isinstance(nrv, dict):
        return
    # 三个关键指标：钠/糖/脂肪
    items = []
    for key in ("钠", "糖", "脂肪"):
        val = nrv.get(key)
        if isinstance(val, (int, float)) and val >= 0:
            items.append((key, float(val)))
    if not items:
        return
    st.markdown(
        "<div class='result-card'>"
        "<div class='result-card-title'>📊 营养成分</div>",
        unsafe_allow_html=True,
    )
    for name, pct in items:
        pct_clamped = max(0, min(100, pct))
        # 颜色：<5% 绿 / 5-20% 橙 / >20% 红
        if pct < 5:
            bar_color = "#43A047"
            level_text = "低"
        elif pct <= 20:
            bar_color = "#FF9800"
            level_text = "中"
        else:
            bar_color = "#E53935"
            level_text = "高"
        st.markdown(
            f"<div class='nrv-bar-wrap'>"
            f"<div class='nrv-bar-label'>"
            f"<span class='nrv-bar-name'>{_safe(name)} <small>({level_text})</small></span>"
            f"<span class='nrv-bar-value' style='color:{bar_color};'>{pct:.0f}%</span>"
            f"</div>"
            f"<div class='nrv-bar-track'>"
            f"<div class='nrv-bar-fill' style='width:{pct_clamped:.0f}%;background:{bar_color};'></div>"
            f"</div>"
            f"<div class='nrv-bar-caption'>占每日推荐摄入量 <strong style='color:{bar_color};'>{pct:.0f}%</strong></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
