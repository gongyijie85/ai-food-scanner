"""扫描上传页渲染（摄像头 + 相册双入口）."""

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


def _scan_common_setup():
    """扫描页通用前置：读取档案、API key、组件 key."""
    profile = st.session_state.get("health_profile", {})
    groups = profile.get("diseases", [])
    api_key = get_api_key()

    if "scan_upload_key" not in st.session_state:
        st.session_state["scan_upload_key"] = 0
    key_prefix = st.session_state["scan_upload_key"]
    camera_key = f"scan_camera_{key_prefix}"
    uploader_key = f"scan_uploader_{key_prefix}"
    return groups, api_key, camera_key, uploader_key


def _resolve_uploaded_input(camera_photo, uploaded_file):
    """在 camera_input 和 file_uploader 之间选择有效输入.

    camera_input 优先级高于 file_uploader，二者互斥。
    """
    if camera_photo is not None:
        return camera_photo
    if uploaded_file is not None:
        return uploaded_file
    return None


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
        "<div class='result-card-title' style='margin:20px 0 14px 0;'>"
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
    """扫描上传页：摄像头 + 相册双入口."""
    render_top_nav("扫描识别", back_target="home")

    groups, api_key, camera_key, uploader_key = _scan_common_setup()

    st.markdown(
        "<p class='scan-tip' style='text-align:center;color:#616161;font-size:15px;"
        "font-weight:500;margin:0 0 16px 0;'>对准配料表拍照或从相册选择</p>",
        unsafe_allow_html=True,
    )

    # 摄像头入口
    st.markdown(
        "<div class='scan-camera-wrap'>"
        "<p class='scan-camera-label'>📷 拍照</p></div>",
        unsafe_allow_html=True,
    )
    camera_photo = st.camera_input(
        "拍照识别配料表",
        key=camera_key,
        label_visibility="collapsed",
        help="点击快门拍照，首次使用需要允许浏览器使用摄像头",
    )

    # 相册入口
    st.markdown(
        "<div class='scan-album-label'>或从相册选择</div>",
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "从相册选择配料表图片",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        key=uploader_key,
    )

    # 摄像头权限/不可用提示
    if camera_photo is None and uploaded_file is None:
        st.info(
            "💡 如果摄像头无法使用，请改用下方的“从相册选择”上传图片；"
            "手机端建议在浏览器设置中允许摄像头权限。"
        )

    # 选择有效输入并预览
    selected_input = _resolve_uploaded_input(camera_photo, uploaded_file)

    if selected_input is not None:
        source_label = "相机拍摄" if selected_input is camera_photo else "相册选择"
        st.markdown(
            f"<div class='scan-preview-info'>已选择：{source_label} · "
            f"{_safe(getattr(selected_input, 'name', '未命名'))} · "
            f"{selected_input.size / 1024:.0f}KB</div>",
            unsafe_allow_html=True,
        )
        st.image(selected_input, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("重新拍摄/选择", key="scan_retake", use_container_width=True):
                st.session_state["scan_upload_key"] += 1
                st.rerun()
        with col2:
            if st.button(
                "开始识别", type="primary", key="scan_confirm", use_container_width=True
            ):
                _scan_validate_and_recognize(selected_input, api_key, groups)

    # 最近识别
    _render_recent_scans()
