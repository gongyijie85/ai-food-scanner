"""扫描上传页渲染（自适应移动端 / 桌面端）."""

import os

import streamlit as st
from PIL import Image

from components import render_empty_state, render_error, render_top_nav
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
from utils.constants import _BASE_DIR
from utils.helpers import switch_page
from utils.history import add_history
from utils.security import _safe


# 取景框 SVG
_CAMERA_FRAME_SVG = """
<div class='scan-frame'>
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
    uploader_key = f"scan_uploader_{st.session_state['scan_upload_key']}"
    return groups, api_key, uploader_key


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
            switch_page("result")
        else:
            status.update(label="识别失败", state="error")
            if raw:
                render_error("返回内容不是合法 JSON", "请重试或更换图片")
            else:
                render_error("识别服务暂时不可用", "请检查网络或 API 密钥后重试")
            if st.button(
                "重新拍摄/选择图片",
                type="primary",
                width="stretch",
                key="scan_retake_on_error",
            ):
                st.session_state["scan_upload_key"] += 1
                st.rerun()


def render_scan_page():
    """扫描上传页：根据设备类型自适应渲染."""
    render_top_nav("扫描识别", back_target="home", right_action="profile")

    groups, api_key, uploader_key = _scan_common_setup()

    st.markdown(
        "<p class='scan-tip' style='text-align:center;color:#616161;font-size:14px;"
        "margin:0 0 16px 0;'>对准包装上的配料表<br>保证光线充足、文字清晰</p>",
        unsafe_allow_html=True,
    )

    uploaded = None
    input_method = "拍照"

    # 取景框展示区
    st.markdown(
        "<div style='background:#1a1a1a;border-radius:16px;min-height:320px;"
        "display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;'>"
        f"{_CAMERA_FRAME_SVG}"
        "<p style='position:absolute;bottom:24px;left:0;right:0;text-align:center;"
        "color:rgba(255,255,255,0.85);font-size:14px;margin:0;'>将配料表放入框内</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # 隐藏的文件上传器，供底部按钮触发
    uploaded = st.file_uploader(
        "选择配料表图片",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        help="支持 jpg/png，大图会自动压缩",
        key=uploader_key,
    )

    camera_key = f"camera_{uploader_key}"
    # 隐藏的相机输入，供底部按钮触发
    st.camera_input(
        "拍照",
        key=camera_key,
        label_visibility="collapsed",
        help="点击快门拍摄配料表",
    )

    # 底部操作按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "📷 拍照",
            type="primary",
            key="scan_take_photo",
            use_container_width=True,
        ):
            # 触发相机输入：Streamlit 无法编程点击，引导用户使用相机组件
            input_method = "拍照"
            st.toast("请点击上方的相机组件进行拍照", icon="📷")
    with col2:
        if st.button(
            "🖼️ 从相册选择",
            key="scan_pick_album",
            use_container_width=True,
        ):
            input_method = "从相册选择"
            st.toast("请点击上方的文件上传区选择图片", icon="🖼️")

    st.markdown(
        "<p class='scan-card-hint' style='text-align:center;color:#9E9E9E;"
        "font-size:13px;margin-top:8px;'>支持 jpg / png，最大 5MB</p>",
        unsafe_allow_html=True,
    )

    if uploaded is not None:
        st.markdown(
            "<div class='preview-card-marker'></div>", unsafe_allow_html=True
        )
        st.markdown(
            "<div class='preview-card-title'>已选择图片</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='preview-file-meta'>{_safe(uploaded.name)} · {uploaded.size / 1024:.0f}KB</div>",
            unsafe_allow_html=True,
        )
        st.image(uploaded, width="stretch")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("重新选择", key="scan_retake", use_container_width=True):
                st.session_state["scan_upload_key"] += 1
                st.rerun()
        with col2:
            if st.button(
                "使用照片", type="primary", key="scan_confirm", use_container_width=True
            ):
                _scan_validate_and_recognize(uploaded, api_key, groups)

    st.markdown(
        "<div class='disclaimer-text'>提示：请尽量正对配料表拍照，保证光线充足</div>",
        unsafe_allow_html=True,
    )
