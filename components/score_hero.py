"""评分英雄区组件."""

import streamlit as st

from utils.security import _safe


def _render_score_hero(score: int, product_name: str, show_slow_replay: bool = True):
    """渲染评分英雄区（按画布设计稿：纯色卡片 + 装饰圆点 + 慢速重听）."""
    if score >= 80:
        _, label, bg = "#43A047", "可放心食用", "#43A047"
        meaning = "添加剂少，适合日常食用"
    elif score >= 60:
        _, label, bg = "#FF9800", "特定人群注意", "#FF9800"
        meaning = "含少量需注意的成分"
    else:
        _, label, bg = "#E53935", "建议咨询医生", "#E53935"
        meaning = "添加剂较多，请谨慎选择"
    shape = "●" if score >= 80 else ("▲" if score >= 60 else "■")
    clip = (
        "polygon(50% 0%, 0% 100%, 100% 100%)" if shape == "▲"
        else "polygon(0 0, 100% 0, 100% 100%, 0 100%)" if shape == "■"
        else "circle(50%)"
    )
    replay_btn = ""
    if show_slow_replay:
        replay_id = f"slow-replay-{score}"
        replay_btn = (
            f"<button id='{replay_id}' class='score-replay-btn food-scanner-tts-replay-btn' "
            f"data-action='replay' aria-label='慢速重听'>"
            f"<span>🔁</span> 慢速重听</button>"
        )
    st.markdown(
        f"<div class='result-score-hero' style='background:{bg};'>"
        f"<div class='result-score-hero-deco result-score-hero-deco-tl'></div>"
        f"<div class='result-score-hero-deco result-score-hero-deco-br'></div>"
        f"<div class='result-score-hero-product'>{_safe(product_name)}</div>"
        f"<div class='result-score-hero-number'>{score}</div>"
        f"<div class='result-score-hero-label'>"
        f"<span class='result-score-shape' style='background:#FFFFFF;clip-path:{clip};'></span>"
        f"{_safe(label)}</div>"
        f"<div class='result-score-meaning'>{_safe(meaning)}</div>"
        f"{replay_btn}"
        f"</div>",
        unsafe_allow_html=True
    )
