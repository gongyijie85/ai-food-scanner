"""通用状态组件：空态、错误态.

将页面中分散的空状态/错误状态统一为可复用组件，
避免重复 HTML 拼接，保证视觉与交互一致。
"""

import streamlit as st

from components.icons import _ICON_ALERT, _ICON_EMPTY
from utils.security import _safe


def render_empty_state(
    title: str, description: str | None = None, icon: str = _ICON_EMPTY
):
    """渲染统一空状态.

    参数:
        title: 主标题，如"还没有扫描记录"。
        description: 辅助说明，可选。
        icon: 图标 HTML，默认使用空盒子 SVG。
    """
    desc_html = (
        f"<p class='empty-state-desc'>{_safe(description)}</p>" if description else ""
    )
    st.markdown(
        f"<div class='empty-state'>"
        f"<div class='empty-state-icon'>{icon}</div>"
        f"<p class='empty-state-text'>{_safe(title)}</p>"
        f"{desc_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_error(title: str, description: str | None = None):
    """渲染统一错误状态（红色主题，带警告图标）.

    参数:
        title: 错误主标题。
        description: 错误说明或修复建议，可选。
    """
    desc_html = (
        f"<p class='empty-state-desc'>{_safe(description)}</p>" if description else ""
    )
    st.markdown(
        f"<div class='empty-state empty-state-error'>"
        f"<div class='empty-state-icon'>{_ICON_ALERT}</div>"
        f"<p class='empty-state-text'>{_safe(title)}</p>"
        f"{desc_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
