"""扫描上传页渲染（自适应移动端 / 桌面端）."""

import os

import streamlit as st
from PIL import Image

from components import _ICON_CAMERA, render_empty_state, render_error, render_top_nav
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
from utils.helpers import detect_device_type, switch_page
from utils.history import add_history
from utils.security import _safe


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
                render_error("返回内容不是合法 JSON", "请重试或更换图片")
                if os.getenv("DEBUG") == "1":
                    with st.expander("查看原始返回（调试用）"):
                        st.text(raw)
        else:
            status.update(label="识别失败", state="error")
            render_error("识别服务暂时不可用", "请检查网络或 API 密钥后重试")


def render_scan_page():
    """扫描上传页：根据设备类型自适应渲染."""
    render_top_nav("扫描识别", back_target="home", right_action="profile")

    groups, api_key, uploader_key = _scan_common_setup()

    if not api_key and os.getenv("DEBUG") == "1":
        # 仅本地开发允许手动输入密钥：通过 Host 头判断，避免 Streamlit Cloud 误配 DEBUG=1 后被任意访客滥用
        try:
            host = st.context.headers.get("Host", "") if hasattr(st, "context") else ""
        except Exception:
            host = ""
        is_local = any(h in host for h in ("localhost", "127.0.0.1", "0.0.0.0"))
        if is_local:
            st.warning("未检测到 MIMO_API_KEY，请在 .env 或 Secrets 中配置")
            api_key = st.text_input("API 密钥", type="password")
        else:
            st.error("API 密钥未配置，请联系管理员")

    is_desktop = detect_device_type() == "desktop"

    if is_desktop:
        left, right = st.columns([1, 1])
    else:
        left = right = st.container()

    uploaded = None

    with left:
        # 桌面端显示示例图；移动端首屏空间有限，改用一行提示，避免挤占拍照区域
        if is_desktop:
            example_path = os.path.join(_BASE_DIR, "test_images", "example_label.jpg")
            if os.path.exists(example_path):
                st.image(
                    example_path,
                    caption="像这样正对配料表拍照，识别率更高",
                    width="stretch",
                )
            else:
                st.info("📷 像这样正对配料表拍照，识别率更高")

        input_method_key = (
            f"scan_input_method_desktop_{uploader_key}"
            if is_desktop
            else f"scan_input_method_{uploader_key}"
        )
        # 评委快速模式下自动选择输入方式，减少一次无意义点击
        if st.session_state.get("demo_mode"):
            input_method = "从相册选择" if is_desktop else "拍照"
        else:
            input_method = st.radio(
                "输入方式",
                ["拍照", "从相册选择"],
                horizontal=True,
                label_visibility="collapsed",
                key=input_method_key,
            )

        with st.container():
            if is_desktop:
                scan_card_desc = "<div class='scan-card-desc'>对准包装上的配料表，保证光线充足、文字清晰</div>"
                scan_card_hint = (
                    "<div class='scan-card-hint'>支持 jpg / png，最大 5MB</div>"
                )
            else:
                scan_card_desc = ""
                scan_card_hint = (
                    "<div class='scan-card-hint'>对准配料表，光线充足更清晰</div>"
                )
            st.markdown(
                "<div class='scan-card-marker'></div>"
                "<div class='scan-card-header'>"
                f"<div class='scan-card-title'>{_ICON_CAMERA} 拍照识别</div>"
                f"{scan_card_desc}"
                "</div>"
                f"{scan_card_hint}",
                unsafe_allow_html=True,
            )
            if input_method == "拍照":
                camera_key = (
                    f"camera_desktop_{uploader_key}"
                    if is_desktop
                    else f"camera_{uploader_key}"
                )
                uploaded = st.camera_input(
                    "对准配料表拍照",
                    key=camera_key,
                    help="点击快门拍摄配料表",
                )
            else:
                uploaded = st.file_uploader(
                    "点击选择或拍照上传配料表图片",
                    type=["jpg", "jpeg", "png"],
                    accept_multiple_files=False,
                    label_visibility="collapsed",
                    help="支持 jpg/png，大图会自动压缩",
                    key=uploader_key,
                )

    with right:
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
                retake_key = "scan_retake_desktop" if is_desktop else "scan_retake"
                if st.button("重新选择", width="stretch", key=retake_key):
                    st.session_state["scan_upload_key"] += 1
                    st.rerun()
            with col2:
                confirm_key = "scan_confirm_desktop" if is_desktop else "scan_confirm"
                if st.button(
                    "使用照片", type="primary", width="stretch", key=confirm_key
                ):
                    _scan_validate_and_recognize(uploaded, api_key, groups)
        elif is_desktop:
            render_empty_state("在左侧上传配料表图片后，这里会显示预览")

    st.markdown(
        "<div class='disclaimer-text'>提示：请尽量正对配料表拍照，保证光线充足</div>",
        unsafe_allow_html=True,
    )
