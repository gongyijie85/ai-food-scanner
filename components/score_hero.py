"""评分英雄区组件（设计稿：产品名+分数横向排布）."""

import streamlit as st

from utils.security import _safe


def _render_score_hero(
    score: int, product_name: str, show_slow_replay: bool = True, scan_date: str = ""
):
    """渲染新版评分摘要卡片.

    布局参考 result_optimized_v2.html：
    - 顶部横向：左侧产品名+识别时间，右侧放大分数圆形
    - 中部：圆角胶囊状态标签 + 状态含义
    - 底部：免责声明 + 慢速重听按钮
    - 分数圈带 popIn / pulseRing / rotateRing 动画
    根据分数使用绿/橙/红三色状态，保持适老化高对比度。
    """
    if score >= 80:
        label = "暂未发现明显问题"
        meaning = "根据您的健康情况，暂未发现需要特别注意的配料"
        score_class = "score-safe"
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<polyline points='20 6 9 17 4 12'/></svg>"
        )
    elif score >= 60:
        label = "特定人群注意"
        meaning = "含少量需注意的成分"
        score_class = "score-caution"
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<path d='M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'/>"
            "<line x1='12' y1='9' x2='12' y2='13'/><line x1='12' y1='17' x2='12.01' y2='17'/></svg>"
        )
    else:
        label = "含多项需关注成分"
        meaning = "该食品含多种高关注配料，建议查看详情后再选择"
        score_class = "score-danger"
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<circle cx='12' cy='12' r='10'/><line x1='12' y1='8' x2='12' y2='12'/>"
            "<line x1='12' y1='16' x2='12.01' y2='16'/></svg>"
        )

    meta_html = ""
    if scan_date:
        meta_html = f"<p class='product-meta'>配料表识别于 {_safe(scan_date)}</p>"

    replay_btn = ""
    if show_slow_replay:
        replay_id = f"slow-replay-{score}"
        replay_btn = (
            f"<button id='{replay_id}' class='btn-replay food-scanner-tts-replay-btn' "
            f"data-action='replay' aria-label='慢速再读一遍'>"
            f"<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            f"stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
            f"<path d='M1 4v6h6'/><path d='M3.51 15a9 9 0 1 0 2.13-9.36L1 10'/></svg>"
            f"<span>慢速再读一遍</span></button>"
        )

    st.markdown(
        f"<div class='score-card {score_class}'>"
        f"<div class='score-card-top'>"
        f"<div class='product-info'>"
        f"<h1 class='product-name'>{_safe(product_name)}</h1>"
        f"{meta_html}"
        f"</div>"
        f"<div class='score-circle'>"
        f"<div class='score-ring'></div>"
        f"<span class='score-number'>{score}</span>"
        f"<span class='score-label'>安全分</span>"
        f"</div></div>"
        f"<div class='status-pill'>{pill_icon}<span>{_safe(label)}</span></div>"
        f"<p class='score-card-subtitle'>{_safe(meaning)}</p>"
        f"<div class='score-card-footer'>"
        f"<p class='disclaimer'>结果仅供参考，不能代替医生诊断。"
        f"身体不适或患有疾病，请先咨询医生。</p>"
        f"{replay_btn}"
        f"</div></div>",
        unsafe_allow_html=True,
        key=f"score-hero-{_safe(product_name)}-{score}",
    )
