"""评分英雄区组件."""

import math

import streamlit as st

from utils.security import _safe


def _render_score_hero(score: int, product_name: str, show_slow_replay: bool = True):
    """渲染评分英雄区（环形进度 + 产品名 + 评级 + 含义）."""
    if score >= 80:
        label, bg = "可放心食用", "#43A047"
        meaning = "添加剂少，适合日常食用"
    elif score >= 60:
        label, bg = "特定人群注意", "#FF9800"
        meaning = "含少量需注意的成分"
    else:
        label, bg = "建议咨询医生", "#E53935"
        meaning = "添加剂较多，请谨慎选择"

    # 环形进度条：周长 ≈ 2π*52 ≈ 327
    circumference = 2 * math.pi * 52
    offset = circumference * (1 - score / 100)
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
        f"<div style='position:relative;width:160px;height:160px;margin:0 auto 12px;'>"
        f"<svg viewBox='0 0 120 120' style='transform:rotate(-90deg);width:100%;height:100%;'>"
        f"<circle cx='60' cy='60' r='52' fill='none' stroke='rgba(255,255,255,0.25)' stroke-width='8' />"
        f"<circle cx='60' cy='60' r='52' fill='none' stroke='#FFFFFF' stroke-width='8' "
        f"stroke-linecap='round' stroke-dasharray='{circumference}' stroke-dashoffset='{offset}' />"
        f"</svg>"
        f"<div class='result-score-hero-number' style='position:absolute;top:50%;left:50%;"
        f"transform:translate(-50%,-50%);font-size:56px;'>{score}</div>"
        f"</div>"
        f"<div class='result-score-hero-label'>⚠️ {_safe(label)}</div>"
        f"<div class='result-score-meaning'>{_safe(meaning)}</div>"
        f"{replay_btn}"
        f"</div>",
        unsafe_allow_html=True,
    )
