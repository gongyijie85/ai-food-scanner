"""个性化健康档案警告组件."""

import streamlit as st

from utils.security import _safe


def render_personal_warnings(warnings):
    """渲染 HealthWarning 列表.

    警告统一由 HealthWarningEngine 生成，本组件只负责展示。
    """
    if not warnings:
        return

    warning_items = "".join(
        f"<div class='advice-block {_severity_class(w.severity)}'>"
        f"<div class='advice-block-icon'>{_severity_icon(w.severity)}</div>"
        f"<div class='advice-block-body'>"
        f"<div class='advice-block-title'>{_safe(w.title)}</div>"
        f"<p class='advice-block-text'>{_safe(w.description)}</p>"
        f"</div></div>"
        for w in warnings
    )

    st.markdown(
        "<div class='result-card'>"
        "<div class='result-card-title'>💗 根据您的健康情况</div>"
        + warning_items
        + "<p class='result-card-footnote'>本工具不能代替医生，有疑问请咨询医生或药师</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def _severity_icon(severity: str) -> str:
    """根据严重级别返回图标."""
    return {"high": "⚠️", "medium": "⚡", "low": "ℹ️"}.get(severity, "ℹ️")


def _severity_class(severity: str) -> str:
    """根据严重级别返回 CSS 类名.

    复用 style.css 中已有的样式块：
    - high  -> 红色警告块
    - medium -> 黄色注意块
    - low   -> 绿色提示块
    """
    return {
        "high": "advice-block-warning",
        "medium": "advice-block-general",
        "low": "advice-block-safe",
    }.get(severity, "advice-block-general")
