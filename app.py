"""AI食品配料表识别工具 - Streamlit Demo 优化版 v0.6.0
用途：上传配料表图片，调用 MiMo Vision API，展示识别结果
特性：适老化样式 + 语音播报 + 历史记录 + 健康档案 + 三端适配
运行环境：Python 3.10+
依赖：pip install streamlit requests pillow
运行命令：streamlit run app.py
"""

import logging
import os

from dotenv import load_dotenv

import streamlit as st
import streamlit.components.v1 as components

from utils.api import API_URL, MODEL_NAME, get_api_key
from utils.helpers import detect_device_type, switch_page
from utils.history import show_history
from utils.security import _safe
from utils.constants import _BASE_DIR

from components import (
    _ICON_HISTORY,
    _ICON_HOME,
    _ICON_PROFILE,
    _preload_tts_voices,
    _render_tts_namespace,
)

from pages import (
    render_detail_page,
    render_health_profile_page,
    render_history_page,
    render_home_desktop,
    render_home_mobile,
    render_legal_consent,
    render_legal_pp,
    render_legal_ua,
    render_onboarding,
    render_result_page,
    render_scan_desktop,
    render_scan_mobile,
)

# ========== 日志配置 ==========
# 生产环境 INFO，本地 DEBUG=1 时 DEBUG
_log_level = logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai-food-scanner")

# 加载本地 .env（如果存在），便于本地测试；Streamlit Cloud 仍使用 Secrets
load_dotenv()


# ========== 适老化样式 ==========

def inject_css():
    """注入 .streamlit/style.css 到页面."""
    css_path = os.path.join(_BASE_DIR, ".streamlit", "style.css")
    try:
        with open(css_path, encoding="utf-8") as f:
            css_content = f.read()
    except FileNotFoundError:
        css_content = ""
    if css_content:
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


# ========== 页面分发 ==========

def _dispatch_page(page: str):
    """根据当前页面名称分发到对应渲染函数."""
    if page == "home":
        if detect_device_type() == "mobile":
            render_home_mobile()
        else:
            render_home_desktop()
    elif page == "scan":
        if detect_device_type() == "mobile":
            render_scan_mobile()
        else:
            render_scan_desktop()
    elif page == "result":
        render_result_page()
    elif page == "history":
        render_history_page()
    elif page == "detail":
        render_detail_page()
    elif page == "profile":
        render_health_profile_page()
    elif page == "legal_ua":
        render_legal_ua()
    elif page == "legal_pp":
        render_legal_pp()
    else:
        st.session_state["page"] = "home"
        st.rerun()


# ========== 主程序 ==========

def main():
    """主程序入口：页面配置、CSS、法律同意、引导、页面分发."""
    st.set_page_config(
        page_title="AI食品配料表识别",
        page_icon=":material/scan:",
        layout="centered",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": None,
        },
    )
    # 移动端适配：声明 viewport，禁止缩放，适配手机浏览器
    st.markdown(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">',
        unsafe_allow_html=True,
    )
    inject_css()
    _preload_tts_voices()
    # 提前注入全局 TTS 命名空间，避免页面刚加载时点击播报提示"组件加载中"
    _render_tts_namespace()

    # 检测设备类型并注入 CSS class，供 .device-mobile / .device-desktop 样式规则使用
    device_type = detect_device_type()
    st.session_state["device_type"] = device_type
    components.html(
        f"""
        <script>
        (function() {{
            try {{
                var d = window.parent.document;
                d.body.classList.remove('device-mobile', 'device-desktop');
                d.body.classList.add('device-{device_type}');
            }} catch(e) {{}}
        }})();
        </script>
        """,
        height=0,
    )

    # DEBUG 信息块：仅当环境变量 DEBUG=1 时显示，用于本地排查 API 配置
    # 生产环境（Streamlit Cloud）严禁设置 DEBUG=1，避免泄露 API key 信息
    if os.getenv("DEBUG") == "1":
        with st.expander("🔧 调试信息（DEBUG=1）", expanded=True):
            mimo_key = get_api_key()
            st.markdown(f"- **MiMo API URL**: `{API_URL}`")
            st.markdown(f"- **MiMo Model**: `{MODEL_NAME}`")
            st.markdown(f"- **MiMo API Key 已配置**: {'是' if mimo_key else '否'}")
            st.markdown("- **Auth Header 类型**: `api-key`")

    # 默认模型选择
    if "selected_model" not in st.session_state:
        st.session_state["selected_model"] = "mimo"

    # 首次访问：先法律同意，再触发 4 步引导
    if "legal_agreed" not in st.session_state:
        st.session_state["legal_agreed"] = False
    if not st.session_state["legal_agreed"]:
        render_legal_consent()
        return

    if "onboarded" not in st.session_state:
        st.session_state["onboarded"] = False
    if not st.session_state["onboarded"]:
        render_onboarding()
        return

    # 默认首页
    if "page" not in st.session_state:
        st.session_state["page"] = "home"
    page = st.session_state["page"]

    # 侧边栏：弱化导航 + 模型选择 + 历史 + 法律文件入口
    with st.sidebar:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"{_ICON_HOME} 首页", use_container_width=True, key="sb_home"):
                switch_page("home")
        with c2:
            if st.button(f"{_ICON_HISTORY} 历史", use_container_width=True, key="sb_history"):
                switch_page("history")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button(f"{_ICON_PROFILE} 健康档案", use_container_width=True, key="sb_profile"):
            switch_page("profile")
        st.divider()

        with st.expander("高级设置"):
            model_choice = st.radio(
                "选择识别模型",
                options=["mimo", "agnes"],
                format_func=lambda x: {
                    "mimo": "MiMo（推荐）：识别更准确",
                    "agnes": "Agnes（更快）：速度优先",
                }[x],
                key="selected_model_radio",
                index=0 if st.session_state.get("selected_model", "mimo") == "mimo" else 1,
            )
            st.session_state["selected_model"] = model_choice
            if os.getenv("DEBUG") == "1":
                if st.button("重新查看引导", use_container_width=True, key="replay_ob"):
                    st.session_state["onboarded"] = False
                    st.session_state["onboarding_step"] = 1
                    st.rerun()
        with st.expander("📄 法律声明"):
            st.caption("AI识别仅供参考，不构成医疗建议")
            if st.button("查看用户协议", use_container_width=True, key="sb_ua"):
                st.session_state["page"] = "legal_ua"
                st.rerun()
            if st.button("查看隐私政策", use_container_width=True, key="sb_pp"):
                st.session_state["page"] = "legal_pp"
                st.rerun()
        st.divider()
        show_history(switch_page, _safe)

    _dispatch_page(page)

    st.markdown(
        "<div class='disclaimer-text' style='text-align:center;margin-top:24px;'>AI识别仅供参考，请以包装原文为准</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
