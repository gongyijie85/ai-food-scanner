"""AI食品配料表识别工具 - Streamlit Demo 优化版 v0.7.7
用途：上传配料表图片，调用 MiMo Vision API，展示识别结果
特性：适老化样式 + 语音播报 + 历史记录 + 健康档案 + 三端适配 + 评委快速模式
运行环境：Python 3.10+
依赖：pip install streamlit requests pillow
运行命令：streamlit run app.py
"""

import logging
import os
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保 Streamlit Cloud 运行 app.py 时能正确导入 pages/components/utils
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from components import _preload_tts_voices, _render_tts_namespace
from components.navigation import render_navigation
from pages import (
    render_detail_page,
    render_health_profile_page,
    render_history_page,
    render_home_page,
    render_legal_consent,
    render_legal_pp,
    render_legal_ua,
    render_onboarding,
    render_result_page,
    render_scan_page,
)
from utils.api import API_URL, MODEL_NAME, get_api_key
from utils.constants import _BASE_DIR
from utils.helpers import detect_device_type, switch_page
from utils.history import show_history
from utils.security import _safe

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
        render_home_page()
    elif page == "scan":
        render_scan_page()
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


# ========== 评委快速模式 ==========


def _apply_demo_mode():
    """检测 URL 参数 ?demo=1，为评委自动完成法律同意、引导并预填健康档案.

    普通用户访问仍走完整流程；评委模式仅通过 session_state 跳过，不删除任何页面。
    """
    if st.session_state.get("demo_mode"):
        return
    if st.query_params.get("demo") != "1":
        return
    st.session_state["demo_mode"] = True
    st.session_state["legal_agreed"] = True
    st.session_state["onboarded"] = True
    st.session_state["page"] = "home"
    if "health_profile" not in st.session_state:
        st.session_state["health_profile"] = {}
    profile = st.session_state["health_profile"]
    profile.setdefault("name", "")
    profile.setdefault("age", 60)
    profile.setdefault("diseases", ["脑梗/心血管", "高血压"])
    profile.setdefault("allergens", [])
    profile.setdefault("drugs", [])
    # 保持与引导页一致的默认模型
    st.session_state["selected_model"] = "mimo"


# ========== 主程序 ==========


def main():
    """主程序入口：页面配置、CSS、法律同意、引导、页面分发."""
    st.set_page_config(
        page_title="AI食品配料表识别",
        page_icon=":material/scan:",
        layout="wide",
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

    # 评委快速模式：URL ?demo=1 自动完成法律同意与引导
    _apply_demo_mode()

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

    # 根据设备类型渲染导航：移动端底部标签栏 / 桌面端侧边栏
    render_navigation(switch_page, _safe, show_history)

    _dispatch_page(page)

    st.markdown(
        "<div class='disclaimer-text' style='text-align:center;margin-top:24px;'>AI识别仅供参考，请以包装原文为准</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
