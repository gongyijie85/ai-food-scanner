"""首次访问引导页渲染."""

import streamlit as st

from utils.constants import CONDITION_ITEMS, CONDITION_NAME_MAP
from utils.helpers import switch_page


def render_onboarding():
    """首次访问的 4 步引导：欢迎 → 选人群 → 使用说明 → 开始."""
    if "onboarding_step" not in st.session_state:
        st.session_state["onboarding_step"] = 1
    if "onboarded" not in st.session_state:
        st.session_state["onboarded"] = False
    # 默认档案：脑梗/心血管 + 高血压（减少首次配置成本）
    if "onboarding_groups" not in st.session_state:
        st.session_state["onboarding_groups"] = ["脑梗/心血管", "高血压"]

    step = st.session_state["onboarding_step"]

    # 跳过按钮
    if st.button(
        "跳过",
        key="ob_skip",
        help="跳过引导，使用默认档案",
    ):
        _finish_onboarding()
        return

    # 顶部进度条
    progress = (step - 1) / 4
    st.progress(progress, text=f"第 {step} 步 / 共 4 步")

    if step == 1:
        # 第 1 步：欢迎
        st.markdown(
            "<div style='text-align:center;padding:48px 16px 32px;'>"
            "<div style='width:140px;height:140px;border-radius:50%;"
            "background:linear-gradient(135deg,#43A047 0%,#2E7D32 100%);"
            "margin:0 auto 24px;display:flex;align-items:center;justify-content:center;"
            "font-size:72px;box-shadow:0 12px 32px rgba(46,125,50,0.25);'>🥫</div>"
            "<h1 style='font-size:28px;margin:0 0 8px;'>AI 食品配料表识别</h1>"
            "<p style='font-size:16px;color:#616161;line-height:1.6;'>"
            "拍照即懂，让老人和孩子吃得更安心</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='display:flex;flex-direction:column;gap:12px;padding:0 8px;'>"
            "<div style='display:flex;align-items:center;gap:14px;padding:16px;"
            "background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);'>"
            "<div style='width:36px;height:36px;border-radius:50%;background:#E8F5E9;"
            "color:#2E7D32;display:flex;align-items:center;justify-content:center;"
            "font-weight:700;flex-shrink:0;'>1</div>"
            "<div><div style='font-weight:700;'>拍照</div>"
            "<div style='font-size:14px;color:#616161;'>对准包装上的配料表拍照</div></div></div>"
            "<div style='display:flex;align-items:center;gap:14px;padding:16px;"
            "background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);'>"
            "<div style='width:36px;height:36px;border-radius:50%;background:#E8F5E9;"
            "color:#2E7D32;display:flex;align-items:center;justify-content:center;"
            "font-weight:700;flex-shrink:0;'>2</div>"
            "<div><div style='font-weight:700;'>识别</div>"
            "<div style='font-size:14px;color:#616161;'>AI 自动识别配料并分析风险</div></div></div>"
            "<div style='display:flex;align-items:center;gap:14px;padding:16px;"
            "background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);'>"
            "<div style='width:36px;height:36px;border-radius:50%;background:#E8F5E9;"
            "color:#2E7D32;display:flex;align-items:center;justify-content:center;"
            "font-weight:700;flex-shrink:0;'>3</div>"
            "<div><div style='font-weight:700;'>看结果</div>"
            "<div style='font-size:14px;color:#616161;'>红黄绿三色评分 + 语音播报</div></div></div>"
            "</div>",
            unsafe_allow_html=True,
        )

    elif step == 2:
        # 第 2 步：选人群（默认已勾选「脑梗/心血管 + 高血压」，可跳过）
        st.markdown(
            "<h2 style='font-size:22px;margin-bottom:6px;'>您属于哪类人群？</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color:#616161;font-size:14px;margin-bottom:20px;'>"
            "已为您预选常见选项，可多选</p>",
            unsafe_allow_html=True,
        )

        selected = set(st.session_state.get("onboarding_groups", []))
        cols = st.columns(2)
        for i, (key, name, emoji) in enumerate(CONDITION_ITEMS):
            with cols[i % 2]:
                disease_name = CONDITION_NAME_MAP[key]
                is_selected = disease_name in selected
                wrapper_cls = (
                    "condition-card-wrapper selected"
                    if is_selected
                    else "condition-card-wrapper"
                )
                st.markdown(
                    f"<div class='{wrapper_cls}'></div>", unsafe_allow_html=True
                )
                label = f"{emoji}\n{name}"
                if st.button(
                    label,
                    key=f"ob_cond_{key}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    if is_selected:
                        selected.discard(disease_name)
                    else:
                        selected.add(disease_name)
                    st.session_state["onboarding_groups"] = list(selected)
                    st.rerun()

        if selected:
            st.info(f"已选：{'、'.join(sorted(selected))}")

    elif step == 3:
        # 第 3 步：使用说明
        st.markdown(
            "<h2 style='font-size:22px;margin-bottom:6px;'>使用说明</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color:#616161;font-size:14px;margin-bottom:20px;'>3 步搞定</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='display:flex;flex-direction:column;gap:12px;padding:0 8px;'>"
            "<div style='text-align:center;padding:20px 12px;background:#E3F2FD;"
            "border-radius:12px;'><div style='font-size:48px;margin-bottom:8px;'>📷</div>"
            "<div style='font-weight:700;font-size:18px;'>1. 拍照</div>"
            "<div style='font-size:14px;color:#616161;'>拍配料表</div></div>"
            "<div style='text-align:center;padding:20px 12px;background:#FFF3E0;"
            "border-radius:12px;'><div style='font-size:48px;margin-bottom:8px;'>🤖</div>"
            "<div style='font-weight:700;font-size:18px;'>2. 识别</div>"
            "<div style='font-size:14px;color:#616161;'>AI 自动分析</div></div>"
            "<div style='text-align:center;padding:20px 12px;background:#E8F5E9;"
            "border-radius:12px;'><div style='font-size:48px;margin-bottom:8px;'>📊</div>"
            "<div style='font-weight:700;font-size:18px;'>3. 看结果</div>"
            "<div style='font-size:14px;color:#616161;'>红黄绿三色评分</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )

    elif step == 4:
        # 第 4 步：开始
        st.markdown(
            "<div style='text-align:center;padding:64px 16px;'>"
            "<div style='font-size:80px;margin-bottom:16px;'>🎉</div>"
            "<h1 style='font-size:28px;color:#2E7D32;margin:0 0 12px;'>准备好了！</h1>"
            "<p style='font-size:16px;color:#616161;'>现在可以开始识别配料表了</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # 底部导航按钮
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    col_back, col_next = st.columns(2)
    with col_back:
        if step > 1:
            if st.button("⬅️ 上一步", use_container_width=True, key=f"ob_back_{step}"):
                st.session_state["onboarding_step"] = step - 1
                st.rerun()
    with col_next:
        if step < 4:
            if st.button(
                "下一步 ➡️",
                type="primary",
                use_container_width=True,
                key=f"ob_next_{step}",
            ):
                st.session_state["onboarding_step"] = step + 1
                st.rerun()
        else:
            if st.button(
                "🚀 开始使用", type="primary", use_container_width=True, key="ob_start"
            ):
                _finish_onboarding()


def _finish_onboarding():
    """完成引导，保存默认档案并跳转首页."""
    if "health_profile" not in st.session_state:
        st.session_state["health_profile"] = {}
    # 引导时用的是疾病卡片网格选择的选项，存到 diseases 列表
    st.session_state["health_profile"]["diseases"] = st.session_state.get(
        "onboarding_groups", ["脑梗/心血管", "高血压"]
    )
    st.session_state["health_profile"].setdefault("name", "")
    st.session_state["health_profile"].setdefault("age", 60)
    st.session_state["health_profile"].setdefault("allergens", [])
    st.session_state["health_profile"].setdefault("drugs", [])
    # 同步初始化 user_profile
    st.session_state.setdefault("user_profile", {"drugs": [], "allergens": []})
    st.session_state["onboarded"] = True
    st.session_state["onboarding_step"] = 1
    switch_page("home")
