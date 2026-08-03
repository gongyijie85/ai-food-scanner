"""结果摘要英雄区：识别状态 + 行动导向状态，不以总分为主结论."""

import streamlit as st

from utils.security import _safe


def _render_score_hero(
    score: int = 0,
    product_name: str = "",
    show_slow_replay: bool = True,
    scan_date: str = "",
    status_label: str = "",
    status_meaning: str = "",
    score_class: str = "",
    *,
    recognition_label: str = "",
    recognition_meaning: str = "",
    action_line: str = "",
    show_score: bool = False,
):
    """渲染结果摘要卡片（默认不展示数字总分）.

    Ticket A：主结论为识别状态 + 状态标签 + 行动句；
    show_score=True 仅兼容旧调用/测试，验证期 UI 应保持 False。
    score 参数保留签名兼容，默认不参与主叙事。
    """
    _ = score  # 保留参数；主路径不展示

    if not score_class:
        score_class = "score-caution"
    if not status_label:
        status_label = "请对照包装查看"
    if not status_meaning:
        status_meaning = "结果仅供参考，请以包装与医嘱为准。"

    label = status_label
    meaning = status_meaning

    if score_class == "score-safe":
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<polyline points='20 6 9 17 4 12'/></svg>"
        )
    elif score_class == "score-caution":
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<path d='M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'/>"
            "<line x1='12' y1='9' x2='12' y2='13'/><line x1='12' y1='17' x2='12.01' y2='17'/></svg>"
        )
    else:
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<circle cx='12' cy='12' r='10'/><line x1='12' y1='8' x2='12' y2='12'/>"
            "<line x1='12' y1='16' x2='12.01' y2='16'/></svg>"
        )

    meta_html = ""
    if scan_date:
        meta_html = f"<p class='product-meta'>配料表识别于 {_safe(scan_date)}</p>"

    rec_html = ""
    if recognition_label:
        rec_html = (
            f"<div class='recognition-state' role='status'>"
            f"<span class='recognition-state-kicker'>识别状态</span>"
            f"<span class='recognition-state-label'>{_safe(recognition_label)}</span>"
            f"<p class='recognition-state-meaning'>{_safe(recognition_meaning or '')}</p>"
            f"</div>"
        )

    action_html = ""
    if action_line:
        action_html = (
            f"<div class='family-verdict family-verdict-action' role='status'>"
            f"<span class='family-verdict-kicker'>建议下一步</span>"
            f"<p class='family-verdict-text'>{_safe(action_line)}</p>"
            f"</div>"
        )

    score_block = ""
    if show_score:
        # 兼容旧测试/调试；生产路径默认关闭
        score_block = (
            f"<div class='score-circle'>"
            f"<div class='score-ring'></div>"
            f"<span class='score-number'>{int(score)}</span>"
            f"<span class='score-label'>内部参考</span>"
            f"</div>"
        )

    replay_btn = ""
    if show_slow_replay:
        replay_btn = (
            "<button class='btn-replay food-scanner-tts-replay-btn' "
            "data-action='replay' aria-label='慢速再读一遍'>"
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
            "<path d='M1 4v6h6'/><path d='M3.51 15a9 9 0 1 0 2.13-9.36L1 10'/></svg>"
            "<span>慢速再读一遍</span></button>"
        )

    st.markdown(
        f"<div class='score-card {score_class} score-card-no-total'>"
        f"<div class='score-card-top'>"
        f"<div class='product-info'>"
        f"<h1 class='product-name'>{_safe(product_name)}</h1>"
        f"{meta_html}"
        f"</div>"
        f"{score_block}"
        f"</div>"
        f"{rec_html}"
        f"<div class='status-pill'>{pill_icon}<span>{_safe(label)}</span></div>"
        f"<p class='score-card-subtitle'>{_safe(meaning)}</p>"
        f"{action_html}"
        f"<div class='score-card-footer'>"
        f"<p class='disclaimer'>结果仅供参考，不能代替医生诊断。"
        f"身体不适或患有疾病，请先咨询医生。</p>"
        f"{replay_btn}"
        f"</div></div>",
        unsafe_allow_html=True,
    )
