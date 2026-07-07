"""通用页面/设备辅助函数。"""
import streamlit as st


def switch_page(page: str, **kwargs):
    """切换页面，跳转前保存当前页到 prev_page."""
    if "page" in st.session_state:
        st.session_state["prev_page"] = st.session_state["page"]
    st.session_state["page"] = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def detect_device_type() -> str:
    """检测设备类型：mobile 或 desktop.

    判断优先级：
    1. URL 查询参数 ?device=mobile / ?device=desktop（用于测试）
    2. session_state 中已缓存的值
    3. User-Agent 中的 Mobi/Android/iPhone 关键字 -> mobile
    4. User-Agent 中的 Windows/Mac/Linux/X11 关键字 -> desktop
    5. 默认返回 mobile（比赛主场景是手机）
    """
    # 1) URL 参数（最高优先级，便于 Playwright 测试和调试）
    query_device = st.query_params.get("device")
    if query_device in ("mobile", "desktop"):
        return query_device

    # 2) session_state 缓存
    cached = st.session_state.get("device_type")
    if cached in ("mobile", "desktop"):
        return cached

    # 3) 从 Streamlit 上下文读取 User-Agent
    try:
        ua = st.context.headers.get("User-Agent", "") if hasattr(st, "context") else ""
    except Exception:
        ua = ""

    mobile_keywords = ["Mobi", "Android", "iPhone", "iPod", "BlackBerry", "IEMobile"]
    if any(k in ua for k in mobile_keywords):
        return "mobile"

    desktop_keywords = ["Windows NT", "Macintosh", "X11", "Linux"]
    if any(k in ua for k in desktop_keywords):
        return "desktop"

    # 5) 默认 mobile，优先保证手机体验
    return "mobile"
