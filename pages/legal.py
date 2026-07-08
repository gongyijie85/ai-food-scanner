"""法律同意页与静态法律文件页渲染."""

import os

import streamlit as st

from components import render_top_nav
from utils.constants import _BASE_DIR
from utils.data import _load_markdown


def render_legal_consent():
    """首次访问：阅读并同意用户协议及隐私政策."""
    st.markdown("## 用户协议及隐私政策")
    st.markdown(
        "使用本工具前请阅读并同意《用户协议及免责声明》和《隐私政策》。"
    )

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
        width="stretch",
        disabled=start_disabled,
        key="legal_start_btn"
    ):
        if agree_terms and agree_sensitive:
            st.session_state["legal_agreed"] = True
            st.rerun()
        else:
            st.warning("请先勾选同意用户协议及隐私政策")


def render_legal_ua():
    """用户协议静态页."""
    render_top_nav("用户协议", back_target="home")
    st.markdown(_load_markdown(os.path.join(_BASE_DIR, "USER_AGREEMENT.md")))


def render_legal_pp():
    """隐私政策静态页."""
    render_top_nav("隐私政策", back_target="home")
    st.markdown(_load_markdown(os.path.join(_BASE_DIR, "PRIVACY_POLICY.md")))
