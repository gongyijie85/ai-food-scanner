"""评分英雄区组件."""

import streamlit as st

from utils.security import _safe


def _render_score_hero(score: int, product_name: str, show_slow_replay: bool = True):
    """渲染压缩后的配料参考分摘要（按分数显示绿/橙/红状态色）.

    使用浅色状态背景、同色边框和深色文字，在保持适老化高对比度的同时，
    让用户一眼区分风险等级。
    """
    if score >= 80:
        label = "暂未发现已知高风险提示"
        meaning = "按当前档案暂未发现高风险配料"
        score_class = "score-safe"
    elif score >= 60:
        label = "特定人群注意"
        meaning = "含少量需注意的成分"
        score_class = "score-caution"
    else:
        label = "建议咨询医生"
        meaning = "添加剂较多，请谨慎选择"
        score_class = "score-danger"

    replay_btn = ""
    if show_slow_replay:
        replay_id = f"slow-replay-{score}"
        replay_btn = (
            f"<button id='{replay_id}' class='score-replay-btn food-scanner-tts-replay-btn' "
            f"data-action='replay' aria-label='慢速重听'>"
            f"<span>🔁</span> 慢速重听</button>"
        )

    st.markdown(
        f"<div class='result-score-hero result-score-hero-compact {score_class}'>"
        f"<div class='result-score-hero-product'>{_safe(product_name)}</div>"
        f"<div class='result-score-hero-row'>"
        f"<div class='result-score-hero-number'>{score}</div>"
        f"<div class='result-score-hero-text'>"
        f"<div class='result-score-hero-label'>{_safe(label)}</div>"
        f"<div class='result-score-meaning'>{_safe(meaning)}</div>"
        f"</div></div>"
        f"<div class='result-score-hero-disclaimer'>评分反映本地添加剂分类，不代表适合所有人。</div>"
        f"{replay_btn}"
        f"</div>",
        unsafe_allow_html=True,
    )
