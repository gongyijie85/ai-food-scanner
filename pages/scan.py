"""扫描上传页渲染（相机优先模式）."""

import os

import streamlit as st
from PIL import Image

from components import render_error, render_top_nav
from utils.api import (
    AGNES_API_URL,
    AGNES_MODEL_NAME,
    MODEL_NAME,
    build_system_prompt,
    call_api,
    call_api_with_fallback,
    encode_image_to_base64,
    get_api_key,
    normalize_model_output,
    parse_result,
)
from utils.helpers import switch_page
from utils.history import add_history, load_history
from utils.security import _safe

# 取景框覆盖层 HTML
_CAMERA_OVERLAY = """
<div class='scan-frame-overlay'>
    <div class='corner corner-tl'></div>
    <div class='corner corner-tr'></div>
    <div class='corner corner-bl'></div>
    <div class='corner corner-br'></div>
    <div class='scan-line'></div>
</div>
"""


def _scan_common_setup():
    """扫描页通用前置：读取档案、API key、上传 key."""
    profile = st.session_state.get("health_profile", {})
    groups = profile.get("diseases", [])
    api_key = get_api_key()

    if "scan_upload_key" not in st.session_state:
        st.session_state["scan_upload_key"] = 0
    if "scan_camera_key" not in st.session_state:
        st.session_state["scan_camera_key"] = 0
    uploader_key = f"scan_uploader_{st.session_state['scan_upload_key']}"
    camera_key = f"scan_camera_{st.session_state['scan_camera_key']}"
    return groups, api_key, uploader_key, camera_key


def _scan_validate_and_recognize(uploaded, api_key, groups):
    """校验图片并调用 API 识别，成功后跳转结果页."""
    if not api_key:
        st.error("API 密钥未配置，请联系管理员")
        st.stop()
    if uploaded.size > 5 * 1024 * 1024:
        st.error("图片超过 5MB，请选择更小的图片或截图后重试")
        st.stop()
    try:
        uploaded.seek(0)
        Image.open(uploaded).verify()
        uploaded.seek(0)
    except Exception:
        st.error("文件格式似乎不是有效图片，请重新上传 jpg/png")
        st.stop()
    with st.status("正在识别配料表...", expanded=True) as status:
        status.write("① 正在上传图片...")
        img_b64 = encode_image_to_base64(uploaded)
        orig_kb = uploaded.size / 1024
        b64_kb = len(img_b64) * 0.75 / 1024
        status.update(
            label=f"上传完成：{orig_kb:.0f}KB → {b64_kb:.0f}KB",
            state="running",
        )
        status.write("② 正在分析配料表...")
        sys_prompt = build_system_prompt(groups)
        agnes_key = os.getenv("AGNES_API_KEY", "")
        selected_model = st.session_state.get("selected_model", "mimo")
        if selected_model == "agnes" and agnes_key:
            raw = call_api(
                agnes_key,
                img_b64,
                sys_prompt,
                url=AGNES_API_URL,
                model=AGNES_MODEL_NAME,
            )
        else:
            raw = call_api_with_fallback(
                api_key, img_b64, sys_prompt, agnes_key=agnes_key
            )
        result = None
        if raw:
            status.update(label="③ 正在计算评分...", state="running")
            normalized = normalize_model_output(raw)
            result = parse_result(normalized, health_groups=groups)

        if result:
            status.update(label="识别完成", state="complete")
            st.session_state["last_result"] = result
            add_history(result, default_engine=MODEL_NAME)
            st.session_state["scan_camera_key"] += 1
            st.session_state["scan_upload_key"] += 1
            switch_page("result")
        else:
            status.update(label="识别失败", state="error")
            if raw:
                render_error("返回内容不是合法 JSON", "请重试或更换图片")
            else:
                render_error("识别服务暂时不可用", "请检查网络或 API 密钥后重试")


def _render_recent_scans():
    """渲染最近识别的小卡片列表."""
    history = load_history()
    if not history:
        return

    st.markdown(
        "<div class='result-card-title' style='margin:8px 0 14px 0;'>"
        "📷 最近拍过的商品</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='scan-recent-list'>", unsafe_allow_html=True)
    cols = st.columns(min(len(history[:3]), 3))
    for idx, item in enumerate(history[:3]):
        score = item.get("score", 0)
        name = _safe(item.get("product_name", "未知"))
        emoji = "🥛" if "牛奶" in name else ("🍪" if "饼干" in name else "🍜")
        short_name = name[:6] + "..." if len(name) > 6 else name
        with cols[idx]:
            if st.button(
                f"{emoji}\n{short_name}\n{score}分",
                key=f"scan_recent_{idx}",
                use_container_width=True,
            ):
                st.session_state["selected_history_index"] = idx
                st.session_state["detail_fallback_record"] = item
                switch_page("detail")
    st.markdown("</div>", unsafe_allow_html=True)


def render_scan_page():
    """扫描上传页：相机优先，拍照后自动识别."""
    render_top_nav("扫描识别", back_target="home")

    groups, api_key, uploader_key, camera_key = _scan_common_setup()

    st.markdown(
        "<p class='scan-tip' style='text-align:center;color:#616161;font-size:15px;"
        "font-weight:500;margin:0 0 16px 0;'>对准商品自动识别</p>",
        unsafe_allow_html=True,
    )

    # 相机取景框区域：视觉取景框 + 实际 camera_input
    st.markdown(
        "<div style='background:#1a1a1a;border-radius:16px;position:relative;"
        "overflow:hidden;padding:20px 16px 16px;text-align:center;'>"
        f"{_CAMERA_OVERLAY}"
        "<p style='color:rgba(255,255,255,0.85);font-size:14px;margin:12px 0 0;'>"
        "将配料表放入框内，点击快门拍照</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    captured_image = st.camera_input(
        "拍照",
        key=camera_key,
        label_visibility="collapsed",
        help="对准配料表，点击快门拍照，拍完后自动识别",
    )

    if captured_image is not None:
        _scan_validate_and_recognize(captured_image, api_key, groups)
        return

    # 相册入口
    st.markdown(
        "<p style='text-align:center;color:#616161;font-size:14px;margin:8px 0 4px;'>"
        "或从相册选择已有照片</p>",
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "选择配料表图片",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        help="支持 jpg/png，大图会自动压缩",
        key=uploader_key,
    )

    if uploaded is not None:
        st.markdown(
            f"<div style='text-align:center;color:#616161;font-size:14px;padding:10px;'>"
            f"已选择：{_safe(uploaded.name)} · {uploaded.size / 1024:.0f}KB</div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("重新选择", key="scan_retake", use_container_width=True):
                st.session_state["scan_upload_key"] += 1
                st.rerun()
        with col2:
            if st.button(
                "开始识别", type="primary", key="scan_confirm", use_container_width=True
            ):
                _scan_validate_and_recognize(uploaded, api_key, groups)

    # 最近识别
    _render_recent_scans()

    st.markdown(
        "<div class='disclaimer-text'>提示：请尽量正对配料表拍照，保证光线充足</div>",
        unsafe_allow_html=True,
    )
