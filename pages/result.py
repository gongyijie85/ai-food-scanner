"""识别结果页渲染（普通食品 / 保健食品 / 分发器）."""

import streamlit as st

from components import (
    _ICON_SPEAKER,
    _render_additive_card,
    _render_score_hero,
    render_empty_state,
    render_feedback_entry,
    render_nutrition_bars,
    render_personal_warnings,
    render_top_nav,
    voice_control_panel,
)
from components.user_guide import render_user_guide
from services.additive_matcher import AdditiveMatcher
from services.health_warning_engine import HealthWarningEngine
from utils.data import (
    get_additive_override_repository,
    get_additive_risk_repository,
    load_health_data,
)
from utils.display import (
    family_conclusion_for_result,
    short_product_name,
    status_copy_for_result,
)
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
    matcher = AdditiveMatcher(
        get_additive_risk_repository(), get_additive_override_repository()
    )
    health_data = load_health_data()
    engine = HealthWarningEngine(
        matcher,
        conflicts=health_data.get("conflicts", []),
        allergens=health_data.get("allergens", []),
    )
    return engine.analyze(result, profile)


def _build_speak_content(result, warnings):
    """组装适老语音文案：分数 + 关注提示 + 配料摘要 + 免责."""
    score = result.get("score", 0)
    product_name = result.get("product_name", "该产品")
    advice = str(result.get("advice", "") or "").strip()
    ingredients = result.get("ingredients") or []
    additives = result.get("additives") or []
    parts = [f"识别结果。{product_name}，配料参考分{score}分。"]

    if warnings:
        titles = [
            getattr(w, "title", None) or (w.get("title") if isinstance(w, dict) else "")
            for w in warnings[:4]
        ]
        titles = [t for t in titles if t]
        if titles:
            parts.append("需要留意：" + "；".join(titles) + "。")

    named = []
    for a in additives[:5]:
        if isinstance(a, dict) and a.get("name"):
            named.append(str(a["name"]))
    if named:
        parts.append("识别到的添加剂包括：" + "、".join(named) + "。")
    elif ingredients:
        preview = [str(x) for x in ingredients[:6] if str(x).strip()]
        if preview:
            parts.append("主要配料：" + "、".join(preview) + "。")
    else:
        ocr = str(result.get("ocr_text", "") or "").strip()
        if ocr:
            parts.append("配料列表不完整，请对照包装原文核对。")
        else:
            parts.append("未能识别配料表文字，请重新对准配料表拍照。")

    if advice:
        parts.append(advice if advice.endswith("。") else advice + "。")
    parts.append(
        "本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生、药师或营养师。"
    )
    return "".join(parts)


def _normalize_ingredient_compare_text(text: str) -> str:
    """去掉配料前缀与标点，用于判断「标签」与「原文」是否实质相同。"""
    import re

    s = str(text or "").strip()
    s = re.sub(r"^(配料表?|原料|成分)\s*[：:]\s*", "", s)
    s = re.sub(r"[\s、,，。；;·:：\(\)（）\[\]【】≥>≤%％\d\.]+", "", s)
    return s


def _ocr_duplicates_ingredients(ocr_text: str, ingredients: list) -> bool:
    """原文与标签列表实质相同时视为重复展示。"""
    if not ocr_text or not ingredients:
        return False
    o = _normalize_ingredient_compare_text(ocr_text)
    j = _normalize_ingredient_compare_text("".join(str(x) for x in ingredients))
    if not o or not j:
        return False
    if o == j:
        return True
    # 仅当长度几乎一致且一方包含另一方（标点差异），避免「标签是子集」误判为重复
    if abs(len(o) - len(j)) <= max(2, min(len(o), len(j)) // 20):
        shorter, longer = (o, j) if len(o) <= len(j) else (j, o)
        if shorter in longer:
            return True
    return False


def _render_ingredients_section(result):
    """配料列表：标签为主；原文仅在与标签有差异或兜底恢复时展示，避免重复。

    说明：标签 = 结构化 ingredients；原文 = 模型 OCR。
    两者逻辑不同，但内容相同时只保留标签，减少老人阅读负担。
    整块用一次 markdown 输出，保证卡片包住内容（避免标题空壳、正文掉到卡外）。
    """
    ingredients = result.get("ingredients") or []
    ocr_text = str(result.get("ocr_text", "") or "").strip()
    recovered = bool(result.get("ingredients_recovered_from_ocr"))
    show_ocr = bool(ocr_text) and (
        not ingredients
        or recovered
        or not _ocr_duplicates_ingredients(ocr_text, ingredients)
    )

    parts = [
        "<div class='content-card ingredients-card'>",
        "<h2 class='card-title'>全部配料</h2>",
        "<div class='card-body'>",
    ]

    if ingredients:
        if recovered:
            parts.append(
                "<div class='advice-block advice-block-general'>"
                "<div class='advice-block-icon'>⚠️</div>"
                "<div class='advice-block-body'>"
                "<div class='advice-block-title'>配料为自动整理，请与包装核对</div>"
                "<p class='advice-block-text'>"
                "未能直接识别出配料表，已根据拍到的文字自动整理，可能与包装原文有出入，"
                "请核对包装后再参考本页提示。"
                "</p></div></div>"
            )
        tags_html = "".join(
            f"<span class='ingredient-tag'>{_safe(item)}</span>" for item in ingredients
        )
        parts.append(f"<div class='ingredient-tags'>{tags_html}</div>")
    else:
        parts.append(
            "<div class='ingredients-empty'>"
            "<p class='ingredients-empty-title'>暂时没看清配料列表</p>"
            "<p class='ingredients-empty-tip'>"
            "请重新对准包装上的「配料表」文字拍照：光线充足、尽量平行、配料小字占满画面。"
            "</p></div>"
        )

    if show_ocr:
        label = (
            "包装原文（供核对，与上方标签有差异）"
            if ingredients and not recovered
            else "包装原文（供核对）"
        )
        parts.append(
            f"<div class='ocr-text-box'>"
            f"<div class='ocr-text-label'>{_safe(label)}</div>"
            f"<p class='ocr-text-body'>{_safe(ocr_text)}</p>"
            f"</div>"
        )

    parts.append("</div></div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_food_page(result):
    """普通食品结果页：根据设备类型自适应渲染."""
    score = result.get("score", 0)
    product_name = result.get("product_name", "未知")
    advice = result.get("advice", "")
    additives = result.get("additives", [])
    display_name = short_product_name(product_name)
    status_label, status_meaning, score_class = status_copy_for_result(score, additives)
    family_line, family_tone = family_conclusion_for_result(score, additives)

    render_top_nav("识别结果", back_target="home")
    # 结果页指引默认收起，避免挤占「一句话结论」首屏
    render_user_guide("result")

    # 1) 配料参考分摘要（短名 + 与添加剂一致的状态）
    _render_score_hero(
        score,
        display_name,
        status_label=status_label,
        status_meaning=status_meaning,
        score_class=score_class,
    )
    if display_name != (product_name or "").strip() and product_name:
        st.caption(f"全称：{_safe(product_name)}")

    # 1b) 家人一句话结论（结论优先）
    st.markdown(
        f"<div class='family-verdict family-verdict-{_safe(family_tone)}' role='status'>"
        f"<span class='family-verdict-kicker'>一句话</span>"
        f"<p class='family-verdict-text'>{_safe(family_line)}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # 2) 个性化警告
    warnings = _analyze_warnings(result)
    if warnings:
        render_personal_warnings(warnings)

    # 3) 语音提前到中部，手机端少滚动（手势路径更稳）
    speak_content = _build_speak_content(result, warnings)
    # 语音稿开头带上家庭结论，听感与屏幕一致
    if family_line and not speak_content.startswith("给家人"):
        speak_content = family_line + "。" + speak_content
    voice_control_panel(
        speak_content,
        key_prefix="tts_food",
        button_text=f"{_ICON_SPEAKER} 听结果",
        wrapper_class="voice-controls voice-controls-primary",
    )
    st.markdown(
        "<p class='voice-hint-line'>点上方绿色大按钮，可听完整结果"
        "（微信内若无声，请用系统浏览器打开）</p>",
        unsafe_allow_html=True,
    )

    # 4) 添加剂匹配（默认只展开需留意项）
    _render_additive_card(additives)

    # 5) 一般饮食建议
    if advice:
        st.markdown(
            "<div class='content-card'>"
            "<h2 class='card-title'>"
            "<svg viewBox='0 0 24 24' fill='none' stroke='var(--state-warning)' "
            "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
            "<circle cx='12' cy='12' r='10'/><path d='M12 16v-4'/><path d='M12 8h.01'/>"
            "</svg>一般饮食建议</h2>"
            "<div class='card-body'>"
            "<div class='advice-box'>"
            "<span class='advice-icon'>&#x2139;&#xFE0F;</span>"
            f"<p class='advice-text'>{_safe(advice)}</p>"
            "</div></div></div>",
            unsafe_allow_html=True,
        )

    # 6) 全部配料（始终展示区域，空状态给重拍提示）
    _render_ingredients_section(result)

    # 营养成分（可选，有数据时显示）
    render_nutrition_bars(result)

    # 纠错反馈入口
    render_feedback_entry(product_name)

    with st.container():
        st.markdown(
            "<div class='bottom-action-bar-marker'></div>", unsafe_allow_html=True
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("再扫一个", key="food_btn_scan", width="stretch"):
                switch_page("scan")
        with col2:
            if st.button("返回首页", key="food_btn_home", width="stretch"):
                switch_page("home")


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

            # 桌面端底部操作
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "再扫一个", use_container_width=True, key="supp_btn_scan_desktop"
                ):
                    switch_page("scan")
            with col2:
                if st.button(
                    "返回首页", use_container_width=True, key="supp_btn_home_desktop"
                ):
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
            wrapper_class="voice-control-wrap",
        )

        with st.container():
            st.markdown(
                "<div class='bottom-action-bar-marker'></div>", unsafe_allow_html=True
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("再扫一个", use_container_width=True, key="supp_btn_scan"):
                    switch_page("scan")
            with col2:
                if st.button("返回首页", use_container_width=True, key="supp_btn_home"):
                    switch_page("home")


def render_result_page():
    """结果页：分发食品/保健食品."""
    result = st.session_state.get("last_result")
    if not result:
        render_empty_state(
            "暂无识别结果",
            "请先扫描配料表；本地预览样式可加载示例结果。",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(
                "查看示例结果", use_container_width=True, key="result_empty_sample"
            ):
                from utils.sample_result import build_sample_food_result

                st.session_state["last_result"] = build_sample_food_result()
                st.rerun()
        with col_b:
            if st.button("去扫描", use_container_width=True, key="result_empty_scan"):
                switch_page("scan")
        if st.button("返回首页", use_container_width=True, key="result_empty_home"):
            switch_page("home")
        return
    if result.get("_offline") or result.get("_sample_preview"):
        note = result.get("_offline_note") or (
            "当前为本地示例/离线配料解析（未调用识别 API），仅供预览。"
        )
        st.caption(str(note))
    if result.get("type") == "supplement":
        render_supplement_page(result)
    else:
        render_food_page(result)
