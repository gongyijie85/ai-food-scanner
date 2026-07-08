"""健康档案页渲染."""

import streamlit as st

from components import render_top_nav
from utils.constants import CONDITION_ITEMS, CONDITION_NAME_MAP
from utils.data import load_health_data


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
            st.markdown(f"<div class='{wrapper_cls}'></div>", unsafe_allow_html=True)
            label = f"✓ {icon} {name}" if is_selected else f"{icon} {name}"
            if st.button(
                label,
                key=f"cond_{key}",
                width="stretch",
                type="primary" if is_selected else "secondary",
            ):
                if is_selected:
                    selected.discard(CONDITION_NAME_MAP[key])
                else:
                    selected.add(CONDITION_NAME_MAP[key])
                profile["diseases"] = list(selected)
                st.rerun()

    st.markdown("<div class='profile-section-title'>过敏原</div>", unsafe_allow_html=True)
    st.markdown("<div class='profile-section-desc'>如有过敏请点击选择</div>", unsafe_allow_html=True)
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
            is_selected = name in selected_alg
            wrapper_cls = "condition-card-wrapper allergen-card selected" if is_selected else "condition-card-wrapper allergen-card"
            st.markdown(f"<div class='{wrapper_cls}'></div>", unsafe_allow_html=True)
            label = f"✓ {name}" if is_selected else name
            if st.button(
                label,
                key=f"alg_{name}",
                width="stretch",
                type="primary" if is_selected else "secondary",
            ):
                if is_selected:
                    selected_alg.discard(name)
                else:
                    selected_alg.add(name)
                profile["allergens"] = [allergen_structured_map[n] for n in selected_alg]
                st.rerun()
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
        width="stretch",
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


def render_health_profile_page():
    """健康档案页入口."""
    render_top_nav("健康档案", back_target="home")
    render_health_profile()
