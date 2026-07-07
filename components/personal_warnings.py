"""个性化健康档案警告组件."""

import streamlit as st

from utils.score import check_drug_food_conflicts
from utils.security import _safe


def render_personal_warnings(result, ingredients):
    """根据用户健康档案个性化警告（药物-食物冲突 + 过敏原匹配）."""
    user_profile = st.session_state.get("user_profile", {})
    user_drugs = user_profile.get("drugs", [])
    user_allergens = user_profile.get("allergens", [])

    if not user_drugs and not user_allergens:
        return

    warnings = []

    if user_drugs:
        conflicts = check_drug_food_conflicts(ingredients, user_drugs)
        if conflicts:
            grouped = {}
            for c in conflicts:
                grouped.setdefault(c["drug"], []).append(c)
            for drug, items in grouped.items():
                food_names = "、".join(sorted({c["matched_keyword"] for c in items}))
                warnings.append(f"⚠️ {drug} 与 {food_names} 可能存在相互作用，建议咨询医生或药师")

    if user_allergens:
        allergen_warnings = []
        all_ingredient_text = " ".join(ingredients) + " " + " ".join(
            a.get("name", "") for a in result.get("additives", [])
        )
        for allergen in user_allergens:
            if allergen.get("name") in all_ingredient_text:
                allergen_warnings.append(allergen.get("name"))
                continue
            for ex in allergen.get("examples", []):
                if ex in all_ingredient_text:
                    allergen_warnings.append(allergen.get("name"))
                    break
        if allergen_warnings:
            warnings.append(f"⚠️ 检测到可能的过敏原：{'、'.join(allergen_warnings)}，请谨慎食用")

    if warnings:
        warning_items = "".join(
            f"<div class='advice-block advice-block-warning'>"
            f"<div class='advice-block-icon'>⚠️</div>"
            f"<div class='advice-block-body'>"
            f"<div class='advice-block-title'>特定人群注意</div>"
            f"<p class='advice-block-text'>{_safe(w)}</p>"
            f"</div></div>"
            for w in warnings
        )
        st.markdown(
            "<div class='result-card'>"
            "<div class='result-card-title'>💗 针对您的健康档案</div>"
            + warning_items
            + "<p class='result-card-footnote'>本工具不提供医疗建议，如有疑问请咨询专业人士</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    elif user_drugs or user_allergens:
        st.markdown(
            "<div class='result-card'>"
            "<div class='result-card-title'>💗 针对您的健康档案</div>"
            "<div class='advice-block advice-block-safe'>"
            "<div class='advice-block-icon'>✅</div>"
            "<div class='advice-block-body'>"
            "<div class='advice-block-title'>暂未发现冲突</div>"
            "<p class='advice-block-text'>根据您的健康档案，未发现需要特别注意的成分</p>"
            "</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )
