"""首页页面渲染（自适应移动端 / 桌面端）."""

import streamlit as st

from components import render_top_nav
from utils.helpers import switch_page
from utils.security import _safe


def render_home_page():
    """首页：扫描入口 + 健康标签，历史记录统一放到侧边栏/历史页."""
    render_top_nav("食品配料表识别", show_back=False, right_action="profile", align="left")

    profile = st.session_state.get("health_profile", {})
    diseases = profile.get("diseases", [])

    # 扫描入口聚合卡片：健康标签 + 大扫描按钮
    with st.container():
        st.markdown("<div class='home-scan-card-marker'></div>", unsafe_allow_html=True)
        if diseases:
            tags_html = "<div class='health-tags-row'>"
            for d in diseases[:4]:
                tags_html += f"<span class='health-tag'>{_safe(d)}</span>"
            tags_html += "</div>"
            st.markdown(tags_html, unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='health-tags-row'>"
                "<span class='health-tag'>+ 添加健康状况</span></div>",
                unsafe_allow_html=True,
            )

        # 扫描区域：大圆形按钮，使用特定 key 类命中样式，避免影响其他按钮
        with st.container():
            st.markdown(
                "<div class='home-scan-area'>"
                "<div class='home-scan-area-marker'></div>"
                "<div class='hint-bubble'>点击大按钮开始</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button("📷\n扫描配料表", type="primary", key="home_goto_scan"):
                switch_page("scan")
