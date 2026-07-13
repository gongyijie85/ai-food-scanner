"""健康档案页回归测试

覆盖：默认渲染、用药清空触发器（预填药品）、连续二次渲染（捕获原 StreamlitAPIException 回归）。
"""

import os
import sys

import pytest
import streamlit as st

# 添加项目根目录到路径，与 tests/test_core.py 约定一致
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pages.profile import render_health_profile
from utils.data import load_health_data


def _seed_profile(age=60, drugs=None):
    """预填健康档案 session_state，供测试复用。"""
    st.session_state["health_profile"] = {
        "name": "",
        "age": age,
        "diseases": [],
        "allergens": [],
        "drugs": drugs or [],
    }
    st.session_state["user_profile"] = {"drugs": [], "allergens": []}


class TestProfileRegression:
    """最小页面回归测试：验证 render_health_profile 在常见交互下不抛异常."""

    def test_initial_render(self):
        """初始渲染不应抛异常."""
        _seed_profile()
        render_health_profile()

    def test_default_age_render(self):
        """渲染后默认 age 应保持初始值（验证 number_input 不破坏既有值）."""
        _seed_profile(age=60)
        render_health_profile()
        assert st.session_state["health_profile"]["age"] == 60

    def test_drug_clear_trigger_clears_populated_drugs(self):
        """预填药品后触发清空，渲染后 drugs 应为空且不抛异常."""
        drug_categories = load_health_data().get("drugs", [])
        if not drug_categories or not drug_categories[0].get("drugs"):
            pytest.skip("数据文件无药品可供测试")
        cat = drug_categories[0]
        d = cat["drugs"][0]
        label = f"{d['name']}（{cat['name']}）"
        _seed_profile(
            drugs=[{"id": d["id"], "name": d["name"], "category": cat["name"]}]
        )
        st.session_state["hp_drugs"] = [label]
        st.session_state["_hp_clear_trigger"] = True
        render_health_profile()
        assert st.session_state["health_profile"]["drugs"] == []

    def test_consecutive_renders_no_exception(self):
        """连续二次渲染不应抛 StreamlitAPIException（原 hp_age_slider 状态冲突回归）."""
        _seed_profile()
        render_health_profile()
        render_health_profile()
