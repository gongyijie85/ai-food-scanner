"""健康档案页渲染."""

import streamlit as st

from components import render_top_nav
from utils.constants import CONDITION_ITEMS, CONDITION_NAME_MAP
from utils.data import load_health_data

# 过敏原到图标的映射
ALLERGEN_ICONS = {
    "花生": "🥜",
    "牛奶": "🥛",
    "鸡蛋": "🥚",
    "鱼类": "🐟",
    "甲壳类": "🦐",
    "坚果": "🌰",
    "小麦": "🌾",
    "大豆": "🫘",
}


def render_health_profile():
    """健康档案：基本信息 + 基础疾病 + 过敏原 + 当前用药."""
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

    # 页面标题卡片
    st.markdown(
        "<div class='page-header'>"
        "<div class='page-title'>❤️ 我的健康档案</div>"
        "<p class='page-desc'>填写后，识别结果会根据您的健康情况给出个性化建议</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # 基本信息
    with st.container():
        st.markdown(
            "<div class='result-card-title' style='margin-bottom:14px;'>📝 基本信息</div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            profile["name"] = st.text_input(
                "称呼（可选）", value=profile.get("name", ""), placeholder="如：张奶奶"
            )
        with col2:
            profile["age"] = st.number_input(
                "年龄", min_value=1, max_value=120, value=profile.get("age", 60), step=1
            )

    # 健康状况
    st.markdown(
        "<div class='result-card-title' style='margin:20px 0 6px 0;'>我的健康状况</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#616161;font-size:13px;margin-bottom:14px;'>"
        "可多选，帮助我们提供更准确的建议</p>",
        unsafe_allow_html=True,
    )
    selected = set(profile.get("diseases", []))
    cols = st.columns(2)
    for i, (key, name, emoji) in enumerate(CONDITION_ITEMS):
        with cols[i % 2]:
            is_selected = CONDITION_NAME_MAP[key] in selected
            wrapper_cls = (
                "condition-card-wrapper selected"
                if is_selected
                else "condition-card-wrapper"
            )
            st.markdown(f"<div class='{wrapper_cls}'></div>", unsafe_allow_html=True)
            label = f"{emoji}\n{name}"
            if st.button(
                label,
                key=f"cond_{key}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                if is_selected:
                    selected.discard(CONDITION_NAME_MAP[key])
                else:
                    selected.add(CONDITION_NAME_MAP[key])
                profile["diseases"] = list(selected)
                st.rerun()

    # 过敏原
    st.markdown(
        "<div class='result-card-title' style='margin:20px 0 6px 0;'>过敏原</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#616161;font-size:13px;margin-bottom:14px;'>如有过敏请点击选择</p>",
        unsafe_allow_html=True,
    )
    allergen_options = [
        "花生",
        "牛奶",
        "鸡蛋",
        "鱼类",
        "甲壳类",
        "坚果",
        "小麦",
        "大豆",
    ]
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

    current_names = {
        a.get("name", "") for a in profile.get("allergens", []) if isinstance(a, dict)
    }
    selected_alg = set()
    for opt in allergen_options:
        struct = allergen_structured_map[opt]
        if struct.get("name", "") in current_names:
            selected_alg.add(opt)

    cols = st.columns(2)
    for i, name in enumerate(allergen_options):
        with cols[i % 2]:
            is_selected = name in selected_alg
            icon = ALLERGEN_ICONS.get(name, "🏷️")
            wrapper_cls = (
                "condition-card-wrapper allergen-card selected"
                if is_selected
                else "condition-card-wrapper allergen-card"
            )
            st.markdown(f"<div class='{wrapper_cls}'></div>", unsafe_allow_html=True)
            label = f"{icon}\n{name}"
            if st.button(
                label,
                key=f"alg_{name}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                if is_selected:
                    selected_alg.discard(name)
                else:
                    selected_alg.add(name)
                profile["allergens"] = [
                    allergen_structured_map[n] for n in selected_alg
                ]
                st.rerun()

    profile["allergens"] = [allergen_structured_map[name] for name in selected_alg]

    # 当前用药
    st.markdown(
        "<div class='result-card-title' style='margin:20px 0 6px 0;'>💊 当前用药</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#616161;font-size:13px;margin-bottom:14px;'>"
        "选填，用于配料交互提醒</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='drug-section-marker'></div>", unsafe_allow_html=True)

    if drug_categories:
        all_drug_options = []
        drug_id_map = {}
        for cat in drug_categories:
            for d in cat.get("drugs", []):
                label = f"{d['name']}（{cat['name']}）"
                all_drug_options.append(label)
                drug_id_map[label] = {
                    "id": d["id"],
                    "name": d["name"],
                    "category": cat["name"],
                }

        default_labels = [
            f"{d['name']}（{d['category']}）"
            for d in profile.get("drugs", [])
            if isinstance(d, dict) and "category" in d
        ]

        selected_drug_labels = st.multiselect(
            "搜索并选择当前用药",
            options=all_drug_options,
            default=default_labels,
            key="hp_drugs",
            placeholder="输入药品名搜索，如：氨氯地平",
            label_visibility="collapsed",
        )
        profile["drugs"] = [drug_id_map[label] for label in selected_drug_labels]

        # 已选药品 Chip 展示 + 快捷清空
        if selected_drug_labels:
            cols = st.columns([1, 0.3])
            with cols[1]:
                if st.button("清空", key="hp_clear_drugs", use_container_width=True):
                    st.session_state["hp_drugs"] = []
                    profile["drugs"] = []
                    st.rerun()

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

    # 保存按钮吸底
    st.markdown("<div class='voice-float-bar'>", unsafe_allow_html=True)
    if st.button(
        "💾 保存档案", type="primary", key="hp_save_btn", use_container_width=True
    ):
        st.session_state["user_profile"] = {
            "drugs": profile.get("drugs", []),
            "allergens": profile.get("allergens", []),
        }
        st.session_state["health_profile"] = profile
        st.success("✅ 档案已保存")
    st.markdown("</div>", unsafe_allow_html=True)


def render_health_profile_page():
    """健康档案页入口."""
    render_top_nav("健康档案", back_target="home")
    render_health_profile()
