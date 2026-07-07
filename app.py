"""AI食品配料表识别工具 - Streamlit Demo 优化版 v0.6.0
用途：上传配料表图片，调用 MiMo Vision API，展示识别结果
特性：适老化样式 + 语音播报 + 历史记录 + 健康档案 + 三端适配
运行环境：Python 3.10+
依赖：pip install streamlit requests pillow
运行命令：streamlit run app.py
"""

import html
import json
import logging
import os
import re
import time
from datetime import datetime

from dotenv import load_dotenv

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from utils.api import (
    AGNES_API_URL,
    AGNES_MODEL_NAME,
    API_URL,
    MODEL_NAME,
    build_system_prompt,
    call_api,
    call_api_with_fallback,
    encode_image_to_base64,
    get_api_key,
    normalize_model_output,
    parse_result,
)
from utils.data import _load_markdown, load_health_data
from utils.helpers import detect_device_type, switch_page
from utils.history import add_history, load_history, load_history_full, save_history, save_history_full, show_history
from utils.score import check_drug_food_conflicts
from utils.security import _safe

from components.icons import (
    _ICON_BACK,
    _ICON_CAMERA,
    _ICON_CHECK,
    _ICON_EMPTY,
    _ICON_FOOD,
    _ICON_HEART,
    _ICON_HISTORY,
    _ICON_HOME,
    _ICON_MUTE_JS,
    _ICON_PROFILE,
    _ICON_REFRESH,
    _ICON_SHARE,
    _ICON_SPEAKER,
    _ICON_SPEAKER_JS,
)
from components.additive_card import _render_additive_card
from components.nutrition_bars import render_nutrition_bars
from components.personal_warnings import render_personal_warnings
from components.score_hero import _render_score_hero
from components.top_nav import render_top_nav
from components.voice_panel import (
    _next_tts_id,
    _preload_tts_voices,
    _render_tts_namespace,
    speak_text,
    voice_control_panel,
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

# 项目根目录，避免多处重复计算
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ========== 配置区 ==========

# 六大人群选项（引导页默认疾病选择）
HEALTH_GROUPS = ["糖尿病", "高血压", "脑梗/心血管", "减脂", "过敏", "孕妇/儿童"]

# 健康档案疾病选项（模块级常量，避免每次渲染重复构造）
CONDITION_ITEMS = [
    ("diabetes", "糖尿病", "糖"),
    ("hypertension", "高血压", "压"),
    ("stroke", "脑梗/心血管", "脑"),
    ("fat-loss", "减脂", "减"),
    ("allergy", "过敏", "敏"),
    ("children", "儿童", "儿"),
    ("pregnant", "孕妇", "孕"),
]
CONDITION_NAME_MAP = {k: v for k, v, _ in CONDITION_ITEMS}


# ========== GB 2760 + 健康档案数据加载 ==========


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


# ========== 结果展示 ==========

def render_food_mobile(result):
    """普通食品结果页：移动端单列布局."""
    score = result.get("score", 0)
    product_name = result.get("product_name", "未知")
    advice = result.get("advice", "")

    render_top_nav("识别结果", back_target="home")
    _render_score_hero(score, product_name)
    st.markdown(
        "<div class='disclaimer-text'>评分仅供参考，AI识别可能存在误差，请以包装原文为准</div>",
        unsafe_allow_html=True,
    )

    speak_content = f"评分{score}分。{advice}本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生/药师/营养师。"

    _render_additive_card(result.get("additives", []))
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

    ingredients = result.get("ingredients", [])
    render_personal_warnings(result, ingredients)

    if ingredients:
        with st.expander("查看全部配料"):
            st.write("、".join(ingredients))

    if os.getenv("DEBUG") == "1":
        with st.expander("查看原始 JSON（调试用）"):
            st.json(result)

    voice_control_panel(
        speak_content,
        key_prefix="tts_food",
        button_text=f"{_ICON_SPEAKER} 一键播报全部结果",
        wrapper_class="voice-float-bar voice-control-wrap",
    )

    with st.container():
        st.markdown("<div class='bottom-action-bar-marker'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"{_ICON_CAMERA} 再扫一个", use_container_width=True, key="food_btn_scan"):
                switch_page("scan")
        with col2:
            if st.button(f"{_ICON_HOME} 返回首页", use_container_width=True, key="food_btn_home"):
                switch_page("home")


def render_food_desktop(result):
    """普通食品结果页：桌面端双栏布局."""
    score = result.get("score", 0)
    product_name = result.get("product_name", "未知")
    advice = result.get("advice", "")
    additives = result.get("additives", [])
    ingredients = result.get("ingredients", [])

    render_top_nav("识别结果", back_target="home")
    st.markdown(
        "<div class='disclaimer-text'>评分仅供参考，AI识别可能存在误差，请以包装原文为准</div>",
        unsafe_allow_html=True,
    )

    speak_content = f"评分{score}分。{advice}本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生/药师/营养师。"

    left, right = st.columns([1, 1])

    with left:
        _render_score_hero(score, product_name, show_slow_replay=True)
        if ingredients:
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>全部配料</div>"
                f"<p class='detail-ingredients-text'>{_safe('、'.join(ingredients))}</p></div>",
                unsafe_allow_html=True,
            )

    with right:
        _render_additive_card(additives)
        render_personal_warnings(result, ingredients)
        render_nutrition_bars(result)
        if advice:
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>健康建议</div>"
                f"<p class='detail-advice-text'>{_safe(advice)}</p></div>",
                unsafe_allow_html=True,
            )
        voice_control_panel(
            speak_content,
            key_prefix="tts_food_desktop",
            button_text=f"{_ICON_SPEAKER} 一键播报全部结果",
            wrapper_class="voice-control-wrap",
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"{_ICON_CAMERA} 再扫一个", use_container_width=True, key="food_btn_scan_desktop"):
            switch_page("scan")
    with col2:
        if st.button(f"{_ICON_HOME} 返回首页", use_container_width=True, key="food_btn_home_desktop"):
            switch_page("home")


def render_supplement_mobile(result):
    """保健食品结果页：移动端单列布局."""
    product_name = result.get("product_name", "未知")
    summary = result.get("summary", "")
    score = result.get("score", 0) or 0

    render_top_nav("识别结果", back_target="home")

    st.markdown(
        "<div class='result-card' style='background:#FFEBEE;border:2px solid #E53935;'>"
        "<div style='color:#C62828;font-weight:bold;font-size:18px;'>⚠️ 本产品为保健食品</div>"
        "<p style='color:#C62828;margin:8px 0 0 0;'>保健食品不是药物，不能代替药物治疗疾病</p>"
        "</div>",
        unsafe_allow_html=True
    )

    _render_score_hero(score if score else 100, product_name)

    speak_content = (
        f"保健食品：{product_name}。"
        f"{summary}。"
        f"保健食品不是药物，不能代替药物治疗疾病。"
        f"如需选择，请咨询医生/药师/营养师。"
    )

    if summary:
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>📝 产品摘要</div><p>{_safe(summary)}</p></div>",
            unsafe_allow_html=True
        )

    approval_no = result.get("approval_no", "未显示")
    if approval_no and approval_no != "未显示":
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>📋 批准文号</div>"
            f"<p><code>{_safe(approval_no)}</code></p></div>",
            unsafe_allow_html=True
        )

    functional = result.get("functional_ingredients", [])
    if functional:
        html = "<div class='result-card'><div class='result-card-title'>✨ 标志性成分</div><ul style='margin:0;padding-left:20px;'>"
        for item in functional:
            html += f"<li style='margin:6px 0;'>{_safe(item)}</li>"
        html += "</ul></div>"
        st.markdown(html, unsafe_allow_html=True)

    health_claims = result.get("health_claims", "")
    if health_claims and health_claims != "未显示":
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>💪 保健功能（包装原文）</div><p>{_safe(health_claims)}</p></div>",
            unsafe_allow_html=True
        )

    suitable = result.get("suitable_for", "")
    unsuitable = result.get("unsuitable_for", "")
    if suitable and suitable != "未显示":
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>👥 适宜人群（包装原文）</div><p>{_safe(suitable)}</p></div>",
            unsafe_allow_html=True
        )
    if unsuitable and unsuitable != "未显示":
        st.markdown(
            f"<div class='result-card' style='border-left:4px solid #FF9800;'><div class='result-card-title'>⚠️ 不适宜人群（包装原文）</div><p style='color:#E65100;'>{_safe(unsuitable)}</p></div>",
            unsafe_allow_html=True
        )

    usage = result.get("usage", "")
    if usage and usage != "未显示":
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>💊 食用方法（包装原文）</div><p>{_safe(usage)}</p></div>",
            unsafe_allow_html=True
        )

    ingredients = result.get("ingredients", [])
    if ingredients:
        with st.expander("查看全部原料"):
            st.write("、".join(ingredients))

    if os.getenv("DEBUG") == "1":
        with st.expander("查看原始 JSON（调试用）"):
            st.json(result)

    voice_control_panel(
        speak_content,
        key_prefix="tts_supp",
        button_text=f"{_ICON_SPEAKER} 一键播报全部结果",
        wrapper_class="voice-float-bar voice-control-wrap",
    )

    with st.container():
        st.markdown("<div class='bottom-action-bar-marker'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"{_ICON_CAMERA} 再扫一个", use_container_width=True, key="supp_btn_scan"):
                switch_page("scan")
        with col2:
            if st.button(f"{_ICON_HOME} 返回首页", use_container_width=True, key="supp_btn_home"):
                switch_page("home")


def render_supplement_desktop(result):
    """保健食品结果页：桌面端双栏布局."""
    product_name = result.get("product_name", "未知")
    summary = result.get("summary", "")
    score = result.get("score", 0) or 0

    render_top_nav("识别结果", back_target="home")

    st.markdown(
        "<div class='result-card' style='background:#FFEBEE;border:2px solid #E53935;'>"
        "<div style='color:#C62828;font-weight:bold;font-size:18px;'>⚠️ 本产品为保健食品</div>"
        "<p style='color:#C62828;margin:8px 0 0 0;'>保健食品不是药物，不能代替药物治疗疾病</p>"
        "</div>",
        unsafe_allow_html=True
    )

    _render_score_hero(score if score else 100, product_name)

    speak_content = (
        f"保健食品：{product_name}。"
        f"{summary}。"
        f"保健食品不是药物，不能代替药物治疗疾病。"
        f"如需选择，请咨询医生/药师/营养师。"
    )

    left, right = st.columns([1, 1])

    with left:
        if summary:
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>📝 产品摘要</div><p>{_safe(summary)}</p></div>",
                unsafe_allow_html=True
            )
        approval_no = result.get("approval_no", "未显示")
        if approval_no and approval_no != "未显示":
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>📋 批准文号</div>"
                f"<p><code>{_safe(approval_no)}</code></p></div>",
                unsafe_allow_html=True
            )
        functional = result.get("functional_ingredients", [])
        if functional:
            html = "<div class='result-card'><div class='result-card-title'>✨ 标志性成分</div><ul style='margin:0;padding-left:20px;'>"
            for item in functional:
                html += f"<li style='margin:6px 0;'>{_safe(item)}</li>"
            html += "</ul></div>"
            st.markdown(html, unsafe_allow_html=True)
        ingredients = result.get("ingredients", [])
        if ingredients:
            with st.expander("查看全部原料"):
                st.write("、".join(ingredients))

    with right:
        health_claims = result.get("health_claims", "")
        if health_claims and health_claims != "未显示":
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>💪 保健功能（包装原文）</div><p>{_safe(health_claims)}</p></div>",
                unsafe_allow_html=True
            )
        suitable = result.get("suitable_for", "")
        unsuitable = result.get("unsuitable_for", "")
        if suitable and suitable != "未显示":
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>👥 适宜人群（包装原文）</div><p>{_safe(suitable)}</p></div>",
                unsafe_allow_html=True
            )
        if unsuitable and unsuitable != "未显示":
            st.markdown(
                f"<div class='result-card' style='border-left:4px solid #FF9800;'><div class='result-card-title'>⚠️ 不适宜人群（包装原文）</div><p style='color:#E65100;'>{_safe(unsuitable)}</p></div>",
                unsafe_allow_html=True
            )
        usage = result.get("usage", "")
        if usage and usage != "未显示":
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>💊 食用方法（包装原文）</div><p>{_safe(usage)}</p></div>",
                unsafe_allow_html=True
            )
        voice_control_panel(
            speak_content,
            key_prefix="tts_supp_desktop",
            button_text=f"{_ICON_SPEAKER} 一键播报全部结果",
            wrapper_class="voice-control-wrap",
        )

    if os.getenv("DEBUG") == "1":
        with st.expander("查看原始 JSON（调试用）"):
            st.json(result)

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"{_ICON_CAMERA} 再扫一个", use_container_width=True, key="supp_btn_scan_desktop"):
            switch_page("scan")
    with col2:
        if st.button(f"{_ICON_HOME} 返回首页", use_container_width=True, key="supp_btn_home_desktop"):
            switch_page("home")


def show_result(result):
    """分发到食品/保健食品渲染器."""
    if not result:
        return
    ptype = str(result.get("type", "food")).lower()
    if ptype == "supplement":
        if detect_device_type() == "mobile":
            render_supplement_mobile(result)
        else:
            render_supplement_desktop(result)
    else:
        if detect_device_type() == "mobile":
            render_food_mobile(result)
        else:
            render_food_desktop(result)


# ========== 首次访问法律同意弹窗 ==========

def render_legal_consent():
    """首次访问：阅读并同意用户协议及隐私政策."""
    st.markdown("## 用户协议及隐私政策")
    st.markdown(
        "使用本工具前请阅读并同意《用户协议及免责声明》和《隐私政策》。"
    )

    # 使用模块级 _BASE_DIR，避免重复计算
    user_agreement = _load_markdown(os.path.join(_BASE_DIR, "USER_AGREEMENT.md"))
    privacy_policy = _load_markdown(os.path.join(_BASE_DIR, "PRIVACY_POLICY.md"))

    with st.expander("查看《用户协议及免责声明》", expanded=False):
        st.markdown(user_agreement)
    with st.expander("查看《隐私政策》", expanded=False):
        st.markdown(privacy_policy)

    agree_terms = st.checkbox(
        "我已阅读并同意《用户协议及隐私政策》",
        key="legal_agree_terms"
    )
    agree_sensitive = st.checkbox(
        "我同意收集我的敏感健康信息（疾病、过敏原、用药）用于个性化科普提示，并知悉数据可能传输至境外 AI 服务",
        key="legal_agree_sensitive"
    )

    start_disabled = not (agree_terms and agree_sensitive)
    if start_disabled:
        st.info("请勾选上方两项同意后，再点击「开始使用」按钮")

    if st.button(
        "开始使用",
        type="primary",
        use_container_width=True,
        disabled=start_disabled,
        key="legal_start_btn"
    ):
        if agree_terms and agree_sensitive:
            st.session_state["legal_agreed"] = True
            st.rerun()
        else:
            st.warning("请先勾选同意用户协议及隐私政策")


# ========== 首次引导页（4 步）==========

def render_onboarding():
    """首次访问的 4 步引导：欢迎 → 选人群 → 使用说明 → 开始."""
    if "onboarding_step" not in st.session_state:
        st.session_state["onboarding_step"] = 1
    if "onboarded" not in st.session_state:
        st.session_state["onboarded"] = False
    # 默认档案：脑梗/心血管 + 高血压（Task 9.3，减少首次配置成本）
    if "onboarding_groups" not in st.session_state:
        st.session_state["onboarding_groups"] = ["脑梗/心血管", "高血压"]

    step = st.session_state["onboarding_step"]

    # 顶部进度条
    progress = (step - 1) / 4
    st.progress(progress, text=f"第 {step} 步 / 共 4 步")

    if step == 1:
        # 第 1 步：欢迎
        st.markdown(
            "<div style='text-align:center;padding:32px 16px;'>"
            "<div style='font-size:96px;'>🥫</div>"
            "<h1 style='font-size:36px;margin:16px 0 8px;'>欢迎使用</h1>"
            "<h2 style='font-size:28px;color:#43A047;margin:0;'>AI 食品配料表识别工具</h2>"
            "<p style='font-size:20px;color:#666;margin-top:16px;'>拍照配料表，3 秒读懂添加剂风险</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("### 🎯 这个工具能做什么？")
        st.markdown("✅ **拍照**食品包装，自动识别**配料表**\n\n✅ 用**红黄绿三色**告诉您添加剂风险\n\n✅ **大字体**、**语音播报**，老人也能轻松用")

    elif step == 2:
        # 第 2 步：选人群（默认已勾选「脑梗/心血管 + 高血压」，可跳过）
        st.markdown("## 👴 第 2 步：请选择您的健康状况")
        st.caption("我们会根据您的情况给个性化建议（可多选；已为您预选常见选项）")
        selected = st.multiselect(
            "您有以下情况吗？（可多选）",
            HEALTH_GROUPS,
            default=st.session_state.get("onboarding_groups", []),
            key="onboarding_groups_widget",
        )
        st.session_state["onboarding_groups"] = selected
        if selected:
            st.info(f"已选：{'、'.join(selected)}")
        # 一键跳过：保留默认档案，直接进入下一步
        if st.button(
            "⏭️ 跳过，稍后设置",
            use_container_width=True,
            key="ob_skip_health",
            help="保留默认档案（脑梗/心血管 + 高血压），稍后可在健康档案页修改"
        ):
            if not st.session_state.get("onboarding_groups"):
                st.session_state["onboarding_groups"] = ["脑梗/心血管", "高血压"]
            st.session_state["onboarding_step"] = 3
            st.rerun()

    elif step == 3:
        # 第 3 步：使用说明
        st.markdown("## 📖 第 3 步：使用说明（3 步搞定）")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                "<div style='text-align:center;padding:20px;background:#E3F2FD;"
                "border-radius:12px;height:200px;'>"
                "<div style='font-size:64px;'>📷</div>"
                "<h3>1. 拍照</h3>"
                "<p style='font-size:18px;'>拍配料表</p>"
                "</div>",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                "<div style='text-align:center;padding:20px;background:#FFF3E0;"
                "border-radius:12px;height:200px;'>"
                "<div style='font-size:64px;'>🤖</div>"
                "<h3>2. 识别</h3>"
                "<p style='font-size:18px;'>AI 自动分析</p>"
                "</div>",
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                "<div style='text-align:center;padding:20px;background:#E8F5E9;"
                "border-radius:12px;height:200px;'>"
                "<div style='font-size:64px;'>📊</div>"
                "<h3>3. 看结果</h3>"
                "<p style='font-size:18px;'>红黄绿三色评分</p>"
                "</div>",
                unsafe_allow_html=True,
            )

    elif step == 4:
        # 第 4 步：开始
        st.markdown(
            "<div style='text-align:center;padding:48px 16px;'>"
            "<div style='font-size:96px;'>🎉</div>"
            "<h1 style='font-size:36px;color:#43A047;'>准备好了！</h1>"
            "<p style='font-size:20px;color:#666;margin:16px 0;'>现在可以开始识别配料表了</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # 导航按钮
    col_back, col_next = st.columns(2)
    with col_back:
        if step > 1:
            if st.button("⬅️ 上一步", use_container_width=True, key=f"ob_back_{step}"):
                st.session_state["onboarding_step"] = step - 1
                st.rerun()
    with col_next:
        if step < 4:
            if st.button("下一步 ➡️", type="primary", use_container_width=True, key=f"ob_next_{step}"):
                st.session_state["onboarding_step"] = step + 1
                st.rerun()
        else:
            if st.button("🚀 开始使用", type="primary", use_container_width=True, key="ob_start"):
                # 完成引导，把人群保存到 health_profile
                if "health_profile" not in st.session_state:
                    st.session_state["health_profile"] = {}
                # 引导时用的是 6 大类 HEALH_GROUPS 简化选项，存到 diseases 列表
                st.session_state["health_profile"]["diseases"] = st.session_state.get("onboarding_groups", [])
                st.session_state["health_profile"].setdefault("name", "")
                st.session_state["health_profile"].setdefault("age", 60)
                st.session_state["health_profile"].setdefault("allergens", [])
                st.session_state["health_profile"].setdefault("drugs", [])
                st.session_state["onboarded"] = True
                st.session_state["onboarding_step"] = 1
                st.rerun()


# ========== 健康档案页 ==========

def render_health_profile():
    """健康档案：基本信息 + 基础疾病 + 过敏原 + 当前用药."""
    st.markdown("## 👤 我的健康档案")
    st.caption("填写档案后，识别结果会根据您的健康情况给出个性化建议")

    if "health_profile" not in st.session_state:
        st.session_state["health_profile"] = {
            "name": "",
            "age": 60,
            "diseases": [],
            "allergens": [],
            "drugs": [],
        }
    if "user_profile" not in st.session_state:
        st.session_state["user_profile"] = {
            "drugs": [],
            "allergens": [],
        }
    profile = st.session_state["health_profile"]
    health_data = load_health_data()
    allergens = health_data.get("allergens", [])
    drug_categories = health_data.get("drugs", [])

    st.markdown("### 📝 基本信息")
    col1, col2 = st.columns(2)
    with col1:
        profile["name"] = st.text_input(
            "称呼（可选）",
            value=profile.get("name", ""),
            placeholder="如：张奶奶"
        )
    with col2:
        profile["age"] = st.number_input(
            "年龄", min_value=1, max_value=120,
            value=profile.get("age", 60), step=1
        )

    st.markdown("<div class='profile-section-title'>我的健康状况</div>", unsafe_allow_html=True)
    st.markdown("<div class='profile-section-desc'>可多选，帮助我们提供更准确的建议</div>", unsafe_allow_html=True)
    selected = set(profile.get("diseases", []))
    cols = st.columns(2)
    for i, (key, name, icon) in enumerate(CONDITION_ITEMS):
        with cols[i % 2]:
            is_selected = CONDITION_NAME_MAP[key] in selected
            wrapper_cls = "condition-card-wrapper selected" if is_selected else "condition-card-wrapper"
            st.markdown(f"<div class='{wrapper_cls}'>", unsafe_allow_html=True)
            if st.button(f"{icon}\n{name}", key=f"cond_{key}", use_container_width=True):
                if is_selected:
                    selected.discard(CONDITION_NAME_MAP[key])
                else:
                    selected.add(CONDITION_NAME_MAP[key])
                profile["diseases"] = list(selected)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='profile-section-title'>过敏原</div>", unsafe_allow_html=True)
    st.markdown("<div class='profile-section-desc'>如有过敏请勾选</div>", unsafe_allow_html=True)
    allergen_options = ["花生", "牛奶", "鸡蛋", "鱼类", "甲壳类", "坚果", "小麦", "大豆"]
    allergen_structured_map = {}
    for a in allergens:
        name = a.get("name", "")
        for opt in allergen_options:
            if opt in name:
                allergen_structured_map[opt] = a
                break
    for opt in allergen_options:
        if opt not in allergen_structured_map:
            allergen_structured_map[opt] = {"name": opt, "examples": [opt]}

    current_names = {a.get("name", "") for a in profile.get("allergens", []) if isinstance(a, dict)}
    selected_alg = set()
    for opt in allergen_options:
        struct = allergen_structured_map[opt]
        if struct.get("name", "") in current_names:
            selected_alg.add(opt)

    st.markdown("<div class='allergen-grid'>", unsafe_allow_html=True)
    cols = st.columns(2)
    for i, name in enumerate(allergen_options):
        with cols[i % 2]:
            checked = name in selected_alg
            if st.checkbox(name, value=checked, key=f"alg_{name}"):
                selected_alg.add(name)
            else:
                selected_alg.discard(name)
    st.markdown("</div>", unsafe_allow_html=True)

    profile["allergens"] = [allergen_structured_map[name] for name in selected_alg]

    st.markdown("<div class='profile-section-title'>💊 当前用药</div>", unsafe_allow_html=True)
    st.markdown("<div class='profile-section-desc'>选填，用于配料交互提醒</div>", unsafe_allow_html=True)
    if drug_categories:
        all_drug_options = []
        drug_id_map = {}
        for cat in drug_categories:
            for d in cat.get("drugs", []):
                label = f"{d['name']}（{cat['name']}）"
                all_drug_options.append(label)
                drug_id_map[label] = {"id": d["id"], "name": d["name"], "category": cat["name"]}
        selected_drug_labels = st.multiselect(
            "您目前在吃什么药？",
            options=all_drug_options,
            default=[
                f"{d['name']}（{d['category']}）"
                for d in profile.get("drugs", []) if isinstance(d, dict) and "category" in d
            ],
            key="hp_drugs",
        )
        profile["drugs"] = [drug_id_map[label] for label in selected_drug_labels]

    with st.expander("📝 补充说明（可选）"):
        profile["medications_free"] = st.text_area(
            "其他用药",
            value=profile.get("medications_free", ""),
            placeholder="如：自购保健品、中药等",
            height=60,
        )
        profile["allergies_free"] = st.text_input(
            "其他过敏",
            value=profile.get("allergies_free", ""),
            placeholder="如：特定添加剂、特殊食物",
        )

    st.markdown("<div class='profile-save-bottom-btn'>", unsafe_allow_html=True)
    if st.button(
        "💾 保存档案",
        type="primary",
        use_container_width=True,
        key="hp_save_btn"
    ):
        st.session_state["user_profile"] = {
            "drugs": profile.get("drugs", []),
            "allergens": profile.get("allergens", []),
        }
        st.session_state["health_profile"] = profile
        st.success("✅ 档案已保存")
    st.markdown("</div>", unsafe_allow_html=True)

    if profile.get("diseases") or profile.get("allergens") or profile.get("drugs"):
        st.divider()
        st.markdown("### 📋 当前档案")
        if profile.get("name"):
            st.markdown(f"- **称呼**：{profile['name']}")
        st.markdown(f"- **年龄**：{profile.get('age', 60)} 岁")
        if profile.get("diseases"):
            st.markdown(f"- **健康状况**：{'、'.join(profile['diseases'])}")
        if profile.get("allergens"):
            st.markdown(f"- **过敏原**：{'、'.join(a['name'] for a in profile['allergens'] if isinstance(a, dict))}")
        if profile.get("drugs"):
            st.markdown(f"- **用药**：{'、'.join(d['name'] for d in profile['drugs'] if isinstance(d, dict))}")


# ========== 页面渲染函数 ==========

def render_home_mobile():
    """首页：移动端布局（单列堆叠 + 大按钮 + 最近扫描卡片）."""
    render_top_nav("食品配料表识别", show_back=False, right_action="profile", align="left")

    profile = st.session_state.get("health_profile", {})
    diseases = profile.get("diseases", [])
    if diseases:
        tags_html = "<div class='health-tags-row'>"
        for d in diseases[:4]:
            tags_html += f"<span class='health-tag'>{_safe(d)}</span>"
        tags_html += "</div>"
        st.markdown(tags_html, unsafe_allow_html=True)
    else:
        # 未设置档案时显示引导标签
        st.markdown(
            "<div class='health-tags-row'>"
            "<span class='health-tag' onclick=\"window.parent.postMessage({action:'goto_profile'},'*')\">"
            "+ 添加健康状况</span></div>",
            unsafe_allow_html=True,
        )

    # 大圆形扫描按钮区（改用 st.container 分组，CSS 通过 marker 定位）
    with st.container():
        st.markdown(
            "<div class='home-scan-area-marker'></div>"
            "<div class='hint-bubble'>点击大按钮开始</div>",
            unsafe_allow_html=True,
        )
        if st.button(f"{_ICON_CAMERA}\n扫描配料表", type="primary", key="home_goto_scan"):
            switch_page("scan")

    # 最近扫描
    history = load_history()[:6]
    if history:
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
            # 卡片整体可点击，使用透明覆盖按钮
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
        st.markdown(
            "<div class='empty-state'>"
            "<div class='empty-state-icon'>🥫</div>"
            "<p class='empty-state-text'>点击大按钮开始扫描配料表</p>"
            "</div>",
            unsafe_allow_html=True,
        )


def render_home_desktop():
    """首页：桌面端布局，左右分栏 + 最近扫描列表."""
    render_top_nav("食品配料表识别", show_back=False, right_action="profile", align="left")

    profile = st.session_state.get("health_profile", {})
    diseases = profile.get("diseases", [])

    # 桌面端：左侧健康档案 + 扫描按钮，右侧最近扫描
    left, right = st.columns([1, 1])

    with left:
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

        with st.container():
            st.markdown(
                "<div class='home-scan-area-marker'></div>"
                "<div class='hint-bubble'>点击大按钮开始</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"{_ICON_CAMERA}\n扫描配料表", type="primary", key="home_goto_scan_desktop"):
                switch_page("scan")

    with right:
        st.markdown(
            "<div class='home-history-heading'><span class='home-history-title'>最近扫描</span></div>",
            unsafe_allow_html=True,
        )
        history = load_history()[:6]
        if history:
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
                "<div class='empty-state'>"
                "<div class='empty-state-icon'>🥫</div>"
                "<p class='empty-state-text'>点击左侧大按钮开始扫描配料表</p>"
                "</div>",
                unsafe_allow_html=True,
            )


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
            raw = call_api(agnes_key, img_b64, sys_prompt, url=AGNES_API_URL, model=AGNES_MODEL_NAME)
        else:
            raw = call_api_with_fallback(api_key, img_b64, sys_prompt, agnes_key=agnes_key)
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
                st.error("返回内容不是合法 JSON，请重试或更换图片")
                if os.getenv("DEBUG") == "1":
                    with st.expander("查看原始返回（调试用）"):
                        st.text(raw)
        else:
            status.update(label="识别失败", state="error")
            st.error("识别服务暂时不可用，请检查网络或 API 密钥后重试。")


def render_scan_mobile():
    """扫描上传页：移动端布局（单列堆叠）."""
    render_top_nav("扫描识别", back_target="home", right_action="profile")

    groups, api_key, uploader_key = _scan_common_setup()

    if not api_key and os.getenv("DEBUG") == "1":
        st.warning("未检测到 MIMO_API_KEY，请在 .env 或 Secrets 中配置")
        api_key = st.text_input("API 密钥", type="password")

    # 拍照示例
    st.image(
        os.path.join(_BASE_DIR, "test_images", "example_label.jpg"),
        caption="像这样正对配料表拍照，识别率更高",
        use_container_width=True,
    )

    # 输入方式选择
    input_method = st.radio(
        "输入方式",
        ["拍照", "从相册选择"],
        horizontal=True,
        label_visibility="collapsed",
        key=f"scan_input_method_{uploader_key}",
    )

    # 上传卡片
    with st.container():
        st.markdown(
            "<div class='scan-card-marker'></div>"
            "<div class='scan-card-header'>"
            f"<div class='scan-card-title'>{_ICON_CAMERA} 拍照或上传配料表</div>"
            "<div class='scan-card-desc'>对准包装上的配料表，保证光线充足、文字清晰</div>"
            "</div>"
            "<div class='scan-card-hint'>支持 jpg / png，最大 5MB</div>",
            unsafe_allow_html=True,
        )
        uploaded = None
        if input_method == "拍照":
            uploaded = st.camera_input(
                "对准配料表拍照",
                key=f"camera_{uploader_key}",
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

    # 预览与识别流程
    if uploaded is not None:
        with st.container():
            st.markdown("<div class='preview-card-marker'></div>", unsafe_allow_html=True)
            st.markdown("<div class='preview-card-title'>已选择图片</div>", unsafe_allow_html=True)
            st.image(uploaded, use_container_width=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"{_ICON_REFRESH} 重新选择", use_container_width=True, key="scan_retake"):
                    st.session_state["scan_upload_key"] += 1
                    st.rerun()
            with col2:
                if st.button(f"{_ICON_CHECK} 使用照片", type="primary", use_container_width=True, key="scan_confirm"):
                    _scan_validate_and_recognize(uploaded, api_key, groups)

    st.markdown(
        "<div class='disclaimer-text'>提示：请尽量正对配料表拍照，保证光线充足</div>",
        unsafe_allow_html=True,
    )


def render_scan_desktop():
    """扫描上传页：桌面端布局，上传与预览左右并排."""
    render_top_nav("扫描识别", back_target="home", right_action="profile")

    groups, api_key, uploader_key = _scan_common_setup()

    if not api_key and os.getenv("DEBUG") == "1":
        st.warning("未检测到 MIMO_API_KEY，请在 .env 或 Secrets 中配置")
        api_key = st.text_input("API 密钥", type="password")

    left, right = st.columns([1, 1])

    with left:
        # 拍照示例
        st.image(
            os.path.join(_BASE_DIR, "test_images", "example_label.jpg"),
            caption="像这样正对配料表拍照，识别率更高",
            use_container_width=True,
        )

        # 输入方式选择
        input_method = st.radio(
            "输入方式",
            ["拍照", "从相册选择"],
            horizontal=True,
            label_visibility="collapsed",
            key=f"scan_input_method_desktop_{uploader_key}",
        )

        st.markdown(
            "<div class='scan-card-marker'></div>"
            "<div class='scan-card-header'>"
            f"<div class='scan-card-title'>{_ICON_CAMERA} 拍照或上传配料表</div>"
            "<div class='scan-card-desc'>对准包装上的配料表，保证光线充足、文字清晰</div>"
            "</div>"
            "<div class='scan-card-hint'>支持 jpg / png，最大 5MB</div>",
            unsafe_allow_html=True,
        )
        uploaded = None
        if input_method == "拍照":
            uploaded = st.camera_input(
                "对准配料表拍照",
                key=f"camera_desktop_{uploader_key}",
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
            st.markdown("<div class='preview-card-marker'></div>", unsafe_allow_html=True)
            st.markdown("<div class='preview-card-title'>已选择图片</div>", unsafe_allow_html=True)
            st.image(uploaded, use_container_width=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"{_ICON_REFRESH} 重新选择", use_container_width=True, key="scan_retake_desktop"):
                    st.session_state["scan_upload_key"] += 1
                    st.rerun()
            with col2:
                if st.button(f"{_ICON_CHECK} 使用照片", type="primary", use_container_width=True, key="scan_confirm_desktop"):
                    _scan_validate_and_recognize(uploaded, api_key, groups)
        else:
            st.markdown(
                "<div class='empty-state'>"
                "<div class='empty-state-icon'>📷</div>"
                "<p class='empty-state-text'>在左侧上传配料表图片后，这里会显示预览</p>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<div class='disclaimer-text'>提示：请尽量正对配料表拍照，保证光线充足</div>",
        unsafe_allow_html=True,
    )


def render_result_page():
    """结果页：分发食品/保健食品."""
    result = st.session_state.get("last_result")
    if not result:
        st.warning("暂无识别结果，请返回首页扫描。")
        if st.button("返回首页"):
            switch_page("home")
        return
    if result.get("type") == "supplement":
        if detect_device_type() == "mobile":
            render_supplement_mobile(result)
        else:
            render_supplement_desktop(result)
    else:
        if detect_device_type() == "mobile":
            render_food_mobile(result)
        else:
            render_food_desktop(result)


def render_history_page():
    """历史记录页：搜索栏 + 筛选标签 + 竖向列表（对齐设计稿）."""
    render_top_nav("历史记录", back_target="home")

    # 搜索栏
    st.markdown(
        "<div class='history-search-wrap'>"
        "<div class='history-search-box'>"
        "<span class='history-search-icon'>🔍</span>",
        unsafe_allow_html=True,
    )
    search = st.text_input(
        "搜索产品名称",
        key="history_search",
        placeholder="搜索产品名称...",
        label_visibility="collapsed",
    )
    st.markdown("</div></div>", unsafe_allow_html=True)

    # 筛选标签
    filter_options = [
        ("全部", "all", "active"),
        ("安全", "safe", "safe"),
        ("注意", "caution", "caution"),
        ("高风险", "danger", "danger"),
    ]
    current_filter = st.session_state.get("history_filter", "全部")
    st.markdown("<div class='history-filter-row'>", unsafe_allow_html=True)
    filter_col = current_filter
    for label, value, css in filter_options:
        wrapper_cls = f"history-filter-chip-wrapper {css}"
        if current_filter == label:
            wrapper_cls += " active"
        st.markdown(f"<div class='{wrapper_cls}'>", unsafe_allow_html=True)
        if st.button(label, key=f"hist_filter_{value}"):
            st.session_state["history_filter"] = label
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    history = load_history()
    filtered = []
    for idx, item in enumerate(history):
        name = item.get("product_name", "")
        score = item.get("score", 0)
        if search and search.lower() not in name.lower():
            continue
        if filter_col == "安全" and score < 80:
            continue
        if filter_col == "注意" and not (60 <= score < 80):
            continue
        if filter_col == "高风险" and score >= 60:
            continue
        filtered.append((idx, item))

    if not filtered:
        if not history:
            st.markdown(
                "<div class='empty-state'>"
                "<div class='empty-state-icon'>📭</div>"
                "<p class='empty-state-text'>还没有扫描记录</p>"
                "<p style='font-size:var(--font-size-body);color:var(--color-text-secondary);'>"
                "去首页拍第一张配料表吧</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"{_ICON_CAMERA} 开始扫描", type="primary", use_container_width=True, key="hist_empty_scan"):
                switch_page("scan")
        else:
            st.info("没有匹配的记录")
        return

    st.markdown("<div class='history-list-wrap'>", unsafe_allow_html=True)
    for idx, item in filtered:
        score = item.get("score", 0)
        if score >= 80:
            color, bg, status = "#2E7D32", "#E8F5E9", "安全"
        elif score >= 60:
            color, bg, status = "#F57F17", "#FFF8E1", "需要注意"
        else:
            color, bg, status = "#C62828", "#FFEBEE", "高风险"
        ts = item.get("timestamp", "")[:10]
        name = item.get("product_name", "未知")
        st.markdown(
            f"<div class='history-list-item'>"
            f"<div class='history-list-score' style='background:{bg};color:{color};'>{score}</div>"
            f"<div class='history-list-info'>"
            f"<div class='history-list-name'>{_safe(name)}</div>"
            f"<div class='history-list-status' style='color:{color};'>{_safe(status)}</div>"
            f"<div class='history-list-date'>{_safe(ts)}</div>"
            f"</div>"
            f"<div class='history-list-chevron'>›</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("查看", key=f"hist_btn_{idx}", help="查看详情"):
            st.session_state["selected_history_index"] = idx
            st.session_state["detail_fallback_record"] = item
            switch_page("detail")
    st.markdown("</div>", unsafe_allow_html=True)


def render_detail_page():
    """产品详情页：读取 history_full.json 展示完整识别快照（对齐设计稿）."""
    idx = st.session_state.get("selected_history_index", -1)
    fallback = st.session_state.get("detail_fallback_record", {})
    full_records = load_history_full()
    record = full_records[idx] if 0 <= idx < len(full_records) else None

    if record:
        product_name = record.get("product_name", "未知")
        score = record.get("score", 0)
    else:
        product_name = fallback.get("product_name", "未知")
        score = fallback.get("score", 0)

    render_top_nav("产品详情", back_target=st.session_state.get("prev_page", "home"))

    # 评分英雄区
    _render_score_hero(score, product_name, show_slow_replay=False)

    # 扫描信息卡片
    ts = fallback.get("timestamp", "") or (record.get("timestamp", "") if record else "")
    type_label = "保健食品" if fallback.get("type") == "supplement" else "食品"
    st.markdown(
        "<div class='result-card detail-scan-card'>"
        "<div class='result-card-title'>扫描信息</div>"
        "<div class='detail-scan-meta'>"
        "<div class='detail-image-placeholder'>图片<br>未保存</div>"
        "<div class='detail-scan-info'>"
        f"<div class='detail-scan-row'><span class='detail-scan-label'>扫描时间</span>"
        f"<span class='detail-scan-value'>{_safe(ts)}</span></div>"
        f"<div class='detail-scan-row'><span class='detail-scan-label'>识别引擎</span>"
        f"<span class='detail-scan-value'>{_safe(MODEL_NAME)}</span></div>"
        f"<div class='detail-scan-row'><span class='detail-scan-label'>产品类型</span>"
        f"<span class='detail-scan-value'>{_safe(type_label)}</span></div>"
        "</div></div></div>",
        unsafe_allow_html=True,
    )

    if not record:
        st.info("当时未保存完整配料信息，仅展示摘要。")

    # 添加剂 / 营养 / 建议（复用 result 组件）
    if record:
        _render_additive_card(record.get("additives", []))
        render_nutrition_bars(record)
        advice = record.get("advice", "")
        if advice:
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>健康建议</div>"
                f"<p class='detail-advice-text'>{_safe(advice)}</p></div>",
                unsafe_allow_html=True,
            )
        # 全部配料
        ingredients = record.get("ingredients", [])
        if ingredients:
            st.markdown(
                "<div class='result-card'><div class='result-card-title'>全部配料</div>"
                f"<p class='detail-ingredients-text'>{_safe('、'.join(ingredients))}</p></div>",
                unsafe_allow_html=True,
            )

    # 底部操作栏
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"{_ICON_REFRESH} 重新评分", use_container_width=True, key="detail_rescore"):
                switch_page("scan")
        with col2:
            if st.button(f"{_ICON_SHARE} 分享给家人", use_container_width=True, key="detail_share"):
                st.toast("已复制结果摘要，可直接粘贴给家人")


def render_health_profile_page():
    """健康档案页入口."""
    render_top_nav("健康档案", back_target="home")
    render_health_profile()


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
    # ⚠️ 生产环境（Streamlit Cloud）严禁设置 DEBUG=1，避免泄露 API key 信息
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
            # 使用模块级 _BASE_DIR，避免重复计算
            if st.button("查看用户协议", use_container_width=True, key="sb_ua"):
                st.session_state["page"] = "legal_ua"
                st.rerun()
            if st.button("查看隐私政策", use_container_width=True, key="sb_pp"):
                st.session_state["page"] = "legal_pp"
                st.rerun()
        st.divider()
        show_history(switch_page, _safe)

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
        render_top_nav("用户协议", back_target="home")
        # 使用模块级 _BASE_DIR，避免重复计算
        st.markdown(_load_markdown(os.path.join(_BASE_DIR, "USER_AGREEMENT.md")))
    elif page == "legal_pp":
        render_top_nav("隐私政策", back_target="home")
        # 使用模块级 _BASE_DIR，避免重复计算
        st.markdown(_load_markdown(os.path.join(_BASE_DIR, "PRIVACY_POLICY.md")))
    else:
        st.session_state["page"] = "home"
        st.rerun()

    st.markdown(
        "<div class='disclaimer-text' style='text-align:center;margin-top:24px;'>AI识别仅供参考，请以包装原文为准</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
