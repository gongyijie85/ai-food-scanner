"""识别结果页渲染（普通食品 / 保健食品 / 分发器）."""

import streamlit as st

from components import (
    _ICON_SPEAKER,
    _render_additive_card,
    _render_score_hero,
    render_empty_state,
    render_nutrition_bars,
    render_personal_warnings,
    render_top_nav,
    voice_control_panel,
)
from services.additive_matcher import AdditiveMatcher
from services.health_warning_engine import HealthWarningEngine
from utils.data import get_additive_risk_repository, load_health_data
from utils.helpers import detect_device_type, switch_page
from utils.security import _safe


def _build_health_profile():
    """从 session_state 组装 HealthWarningEngine 需要的健康档案."""
    health_profile = st.session_state.get("health_profile", {})
    user_profile = st.session_state.get("user_profile", {})
    profile = {
        "groups": health_profile.get("diseases", []),
        "drugs": user_profile.get("drugs") or health_profile.get("drugs", []),
        "allergens": user_profile.get("allergens")
        or health_profile.get("allergens", []),
    }
    # 过滤空值，减少引擎无效计算
    return {k: v for k, v in profile.items() if v}


def _analyze_warnings(result):
    """根据识别结果和当前用户档案生成健康警告列表."""
    profile = _build_health_profile()
    if not profile:
        return []
    matcher = AdditiveMatcher(get_additive_risk_repository())
    health_data = load_health_data()
    engine = HealthWarningEngine(
        matcher,
        conflicts=health_data.get("conflicts", []),
        allergens=health_data.get("allergens", []),
    )
    return engine.analyze(result, profile)


def render_food_page(result):
    """普通食品结果页：根据设备类型自适应渲染."""
    score = result.get("score", 0)
    product_name = result.get("product_name", "未知")
    advice = result.get("advice", "")
    additives = result.get("additives", [])
    ingredients = result.get("ingredients", [])

    render_top_nav("识别结果", back_target="home")

    speak_content = f"评分{score}分。{advice}本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生/药师/营养师。"

    _render_score_hero(score, product_name)
    warnings = _analyze_warnings(result)
    if warnings:
        render_personal_warnings(warnings)
    _render_additive_card(additives)
    render_nutrition_bars(result)

    if advice:
        st.markdown(
            "<div class='result-card'>"
            "<div class='result-card-title'>💡 健康建议</div>"
            "<div class='advice-block advice-block-general'>"
            "<div class='advice-block-icon'>ℹ️</div>"
            "<div class='advice-block-body'>"
            "<div class='advice-block-title'>普通人群</div>"
            f"<p class='advice-block-text'>{_safe(advice)}</p>"
            "</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )

    if ingredients:
        with st.expander("查看全部配料"):
            st.write("、".join(ingredients))
            ocr_text = result.get("ocr_text", "")
            if ocr_text:
                st.caption(f"识别到的配料表原文：{_safe(ocr_text)}")

    voice_control_panel(
        speak_content,
        key_prefix="tts_food",
        button_text=f"{_ICON_SPEAKER} 一键播报全部结果",
        wrapper_class="voice-float-bar voice-control-wrap",
    )

    with st.container():
        st.markdown(
            "<div class='bottom-action-bar-marker'></div>", unsafe_allow_html=True
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("再扫一个", key="food_btn_scan", use_container_width=True):
                switch_page("scan")
        with col2:
            if st.button("返回首页", key="food_btn_home", use_container_width=True):
                switch_page("home")

    st.markdown(
        "<p class='disclaimer-text'>评分仅供参考，AI识别可能存在误差，请以包装原文为准。本工具不构成医疗建议。</p>",
        unsafe_allow_html=True,
    )


def render_supplement_page(result):
    """保健食品结果页：根据设备类型自适应渲染."""
    product_name = result.get("product_name", "未知")
    summary = result.get("summary", "")
    score = result.get("score", 0) or 0
    ingredients = result.get("ingredients", [])
    approval_no = result.get("approval_no", "未显示")
    functional = result.get("functional_ingredients", [])
    health_claims = result.get("health_claims", "")
    suitable = result.get("suitable_for", "")
    unsuitable = result.get("unsuitable_for", "")
    usage = result.get("usage", "")
    is_desktop = detect_device_type() == "desktop"

    render_top_nav("识别结果", back_target="home")

    st.markdown(
        "<div class='result-card' style='background:#FFEBEE;border:2px solid #E53935;'>"
        "<div style='color:#C62828;font-weight:bold;font-size:18px;'>⚠️ 本产品为保健食品</div>"
        "<p style='color:#C62828;margin:8px 0 0 0;'>保健食品不是药物，不能代替药物治疗疾病</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    _render_score_hero(score if score else 100, product_name)

    speak_content = (
        f"保健食品：{product_name}。"
        f"{summary}。"
        f"保健食品不是药物，不能代替药物治疗疾病。"
        f"如需选择，请咨询医生/药师/营养师。"
    )

    if is_desktop:
        left, right = st.columns([1, 1])

        with left:
            if summary:
                st.markdown(
                    f"<div class='result-card'><div class='result-card-title'>📝 产品摘要</div><p>{_safe(summary)}</p></div>",
                    unsafe_allow_html=True,
                )
            if approval_no and approval_no != "未显示":
                st.markdown(
                    f"<div class='result-card'><div class='result-card-title'>📋 批准文号</div>"
                    f"<p><code>{_safe(approval_no)}</code></p></div>",
                    unsafe_allow_html=True,
                )
            if functional:
                html = "<div class='result-card'><div class='result-card-title'>✨ 标志性成分</div><ul style='margin:0;padding-left:20px;'>"
                for item in functional:
                    html += f"<li style='margin:6px 0;'>{_safe(item)}</li>"
                html += "</ul></div>"
                st.markdown(html, unsafe_allow_html=True)
            if ingredients:
                with st.expander("查看全部原料"):
                    st.write("、".join(ingredients))

        with right:
            if health_claims and health_claims != "未显示":
                st.markdown(
                    f"<div class='result-card'><div class='result-card-title'>💪 保健功能（包装原文）</div><p>{_safe(health_claims)}</p></div>",
                    unsafe_allow_html=True,
                )
            if suitable and suitable != "未显示":
                st.markdown(
                    f"<div class='result-card'><div class='result-card-title'>👥 适宜人群（包装原文）</div><p>{_safe(suitable)}</p></div>",
                    unsafe_allow_html=True,
                )
            if unsuitable and unsuitable != "未显示":
                st.markdown(
                    f"<div class='result-card' style='border-left:4px solid #FF9800;'><div class='result-card-title'>⚠️ 不适宜人群（包装原文）</div><p style='color:#E65100;'>{_safe(unsuitable)}</p></div>",
                    unsafe_allow_html=True,
                )
            warnings = _analyze_warnings(result)
            render_personal_warnings(warnings)
            if usage and usage != "未显示":
                st.markdown(
                    f"<div class='result-card'><div class='result-card-title'>💊 食用方法（包装原文）</div><p>{_safe(usage)}</p></div>",
                    unsafe_allow_html=True,
                )
            voice_control_panel(
                speak_content,
                key_prefix="tts_supp_desktop",
                button_text=f"{_ICON_SPEAKER} 一键播报全部结果",
                wrapper_class="voice-control-wrap",
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("再扫一个", width="stretch", key="supp_btn_scan_desktop"):
                switch_page("scan")
        with col2:
            if st.button("返回首页", width="stretch", key="supp_btn_home_desktop"):
                switch_page("home")
    else:
        if summary:
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>📝 产品摘要</div><p>{_safe(summary)}</p></div>",
                unsafe_allow_html=True,
            )

        if approval_no and approval_no != "未显示":
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>📋 批准文号</div>"
                f"<p><code>{_safe(approval_no)}</code></p></div>",
                unsafe_allow_html=True,
            )

        if functional:
            html = "<div class='result-card'><div class='result-card-title'>✨ 标志性成分</div><ul style='margin:0;padding-left:20px;'>"
            for item in functional:
                html += f"<li style='margin:6px 0;'>{_safe(item)}</li>"
            html += "</ul></div>"
            st.markdown(html, unsafe_allow_html=True)

        if health_claims and health_claims != "未显示":
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>💪 保健功能（包装原文）</div><p>{_safe(health_claims)}</p></div>",
                unsafe_allow_html=True,
            )

        if suitable and suitable != "未显示":
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>👥 适宜人群（包装原文）</div><p>{_safe(suitable)}</p></div>",
                unsafe_allow_html=True,
            )
        if unsuitable and unsuitable != "未显示":
            st.markdown(
                f"<div class='result-card' style='border-left:4px solid #FF9800;'><div class='result-card-title'>⚠️ 不适宜人群（包装原文）</div><p style='color:#E65100;'>{_safe(unsuitable)}</p></div>",
                unsafe_allow_html=True,
            )

        warnings = _analyze_warnings(result)
        render_personal_warnings(warnings)

        if usage and usage != "未显示":
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>💊 食用方法（包装原文）</div><p>{_safe(usage)}</p></div>",
                unsafe_allow_html=True,
            )

        if ingredients:
            with st.expander("查看全部原料"):
                st.write("、".join(ingredients))

        voice_control_panel(
            speak_content,
            key_prefix="tts_supp",
            button_text=f"{_ICON_SPEAKER} 一键播报全部结果",
            wrapper_class="voice-float-bar voice-control-wrap",
        )

        with st.container():
            st.markdown(
                "<div class='bottom-action-bar-marker'></div>", unsafe_allow_html=True
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("再扫一个", width="stretch", key="supp_btn_scan"):
                    switch_page("scan")
            with col2:
                if st.button("返回首页", width="stretch", key="supp_btn_home"):
                    switch_page("home")


def render_result_page():
    """结果页：分发食品/保健食品."""
    result = st.session_state.get("last_result")
    if not result:
        render_empty_state("暂无识别结果", "请返回首页扫描")
        if st.button("返回首页", width="stretch", key="result_empty_home"):
            switch_page("home")
        return
    if result.get("type") == "supplement":
        render_supplement_page(result)
    else:
        render_food_page(result)
