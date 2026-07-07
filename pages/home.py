"""首页页面渲染（自适应移动端 / 桌面端）."""

import streamlit as st

from components import _ICON_CAMERA, render_empty_state, render_top_nav
from utils.helpers import detect_device_type, switch_page
from utils.history import load_history
from utils.security import _safe


def render_home_page():
    """首页：根据设备类型自适应渲染."""
    render_top_nav("食品配料表识别", show_back=False, right_action="profile", align="left")

    profile = st.session_state.get("health_profile", {})
    diseases = profile.get("diseases", [])

    if detect_device_type() == "desktop":
        left, right = st.columns([1, 1])
    else:
        left = right = st.container()

    with left:
        if diseases:
            tags_html = "<div class='health-tags-row'>"
            for d in diseases[:4]:
                tags_html += f"<span class='health-tag'>{_safe(d)}</span>"
            tags_html += "</div>"
            st.markdown(tags_html, unsafe_allow_html=True)
        else:
            if detect_device_type() == "desktop":
                st.markdown(
                    "<div class='health-tags-row'>"
                    "<span class='health-tag'>+ 添加健康状况</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='health-tags-row'>"
                    "<span class='health-tag' onclick=\"window.parent.postMessage({action:'goto_profile'},'*')\">"
                    "+ 添加健康状况</span></div>",
                    unsafe_allow_html=True,
                )

        with st.container():
            st.markdown(
                "<div class='home-scan-area-marker'></div>"
                "<div class='hint-bubble'>点击大按钮开始</div>",
                unsafe_allow_html=True,
            )
            scan_key = "home_goto_scan" if detect_device_type() == "mobile" else "home_goto_scan_desktop"
            if st.button(f"{_ICON_CAMERA}\n扫描配料表", type="primary", key=scan_key):
                switch_page("scan")

    with right:
        st.markdown(
            "<div class='home-history-heading'><span class='home-history-title'>最近扫描</span></div>",
            unsafe_allow_html=True,
        )
        history = load_history()[:6]
        if history:
            if detect_device_type() == "desktop":
                for i, item in enumerate(history[:6]):
                    score = item.get("score", 0)
                    score_class = "score-safe" if score >= 80 else ("score-caution" if score >= 60 else "score-danger")
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.markdown(
                            f"<div class='history-list-name'>{_safe(item.get('product_name', '未知'))}</div>",
                            unsafe_allow_html=True,
                        )
                    with cols[1]:
                        st.markdown(
                            f"<div class='history-list-score {score_class}'>{score}</div>",
                            unsafe_allow_html=True,
                        )
                    if st.button("查看", key=f"home_card_desktop_{i}"):
                        st.session_state["selected_history_index"] = i
                        st.session_state["detail_fallback_record"] = item
                        switch_page("detail")
            else:
                st.markdown(
                    "<div class='home-history-section'>"
                    "<div class='home-history-heading'>"
                    "<span class='home-history-title'>最近扫描</span>"
                    "</div>"
                    "<div class='history-cards-row'>",
                    unsafe_allow_html=True,
                )
                for i, item in enumerate(history[:3]):
                    score = item.get("score", 0)
                    score_class = "score-safe" if score >= 80 else ("score-caution" if score >= 60 else "score-danger")
                    status_text = "安全" if score >= 80 else ("注意" if score >= 60 else "高风险")
                    st.markdown(
                        f"<div class='history-card'>"
                        f"<div class='history-card-name'>{_safe(item.get('product_name', '未知'))}</div>"
                        f"<div class='history-card-score {score_class}'>"
                        f"{status_text} {score}分</div>"
                        f"<div class='history-card-date'>{_safe(item.get('timestamp', '')[:10])}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("查看", key=f"home_card_{i}", help="查看详情"):
                        st.session_state["selected_history_index"] = i
                        st.session_state["detail_fallback_record"] = item
                        switch_page("detail")
                st.markdown(
                    "</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button("查看全部历史记录", use_container_width=True, key="home_goto_history"):
                    switch_page("history")
        else:
            empty_text = (
                "点击左侧大按钮开始扫描配料表"
                if detect_device_type() == "desktop"
                else "点击大按钮开始扫描配料表"
            )
            render_empty_state(empty_text)


# 兼容旧版调用入口
render_home_mobile = render_home_page
render_home_desktop = render_home_page
