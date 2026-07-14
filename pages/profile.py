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
    """健康档案：基本信息 + 个性化风险 + 当前用药."""
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

    # 个性化风险（疾病 + 过敏原）
    st.markdown(
        "<div class='result-card-title' style='margin:20px 0 6px 0;'>🩺 个性化风险</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#616161;font-size:13px;margin-bottom:14px;'>"
        "多选后，识别结果会据此给出个性化提醒</p>",
        unsafe_allow_html=True,
    )

    # 疾病：原生 pills，自动换行
    disease_labels = [f"{emoji} {name}" for key, name, emoji in CONDITION_ITEMS]
    disease_label_to_name = {
        f"{emoji} {name}": name for key, name, emoji in CONDITION_ITEMS
    }
    selected_disease_names = set(profile.get("diseases", []))
    default_disease_labels = [
        lbl for lbl, name in disease_label_to_name.items() if name in selected_disease_names
    ]
    selected_disease_labels = st.pills(
        "基础疾病",
        options=disease_labels,
        default=default_disease_labels,
        selection_mode="multi",
        key="hp_diseases_pills",
        label_visibility="collapsed",
    )
    profile["diseases"] = [
        disease_label_to_name[lbl] for lbl in selected_disease_labels or []
    ]

    # 过敏原：原生 pills，自动换行
    allergen_options = [
        "花生", "牛奶", "鸡蛋", "鱼类", "甲壳类", "坚果", "小麦", "大豆"
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
    default_allergen_labels = [
        f"{ALLERGEN_ICONS.get(opt, '🏷️')} {opt}"
        for opt in allergen_options
        if allergen_structured_map.get(opt, {}).get("name", "") in current_names
    ]
    allergen_labels = [f"{ALLERGEN_ICONS.get(opt, '🏷️')} {opt}" for opt in allergen_options]
    allergen_label_to_name = {
        f"{ALLERGEN_ICONS.get(opt, '🏷️')} {opt}": opt for opt in allergen_options
    }
    selected_allergen_labels = st.pills(
        "过敏原",
        options=allergen_labels,
        default=default_allergen_labels,
        selection_mode="multi",
        key="hp_allergens_pills",
        label_visibility="collapsed",
    )
    profile["allergens"] = [
        allergen_structured_map[allergen_label_to_name[lbl]]
        for lbl in selected_allergen_labels or []
    ]

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

        # 控件创建前执行清空，避免实例化 hp_drugs 后再次赋值
        if st.session_state.pop("_hp_clear_trigger", False):
            st.session_state["hp_drugs"] = []
            profile["drugs"] = []
            default_labels = []

        selected_drug_labels = st.multiselect(
            "搜索并选择当前用药",
            options=all_drug_options,
            default=default_labels,
            key="hp_drugs",
            placeholder="输入药品名搜索，如：氨氯地平",
            label_visibility="collapsed",
        )
        profile["drugs"] = [drug_id_map[label] for label in selected_drug_labels]

        # 有选择时才显示清空按钮
        if selected_drug_labels:
            if st.button("清空用药", key="hp_clear_drugs", use_container_width=True):
                st.session_state["_hp_clear_trigger"] = True
                st.rerun()

    # 补充说明默认折叠
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

    # 保存按钮保持在内容末尾
    if st.button(
        "💾 保存档案", type="primary", key="hp_save_btn", use_container_width=True
    ):
        st.session_state["user_profile"] = {
            "drugs": profile.get("drugs", []),
            "allergens": profile.get("allergens", []),
        }
        st.session_state["health_profile"] = profile
        st.success("✅ 档案已保存")


def render_health_profile_page():
    """健康档案页入口."""
    render_top_nav("健康档案", back_target="home")
    render_health_profile()
