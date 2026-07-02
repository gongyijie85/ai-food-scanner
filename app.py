"""
AI食品配料表识别工具 - Streamlit Demo 优化版 v0.3.4
用途：上传配料表图片，调用 MiMo Vision API，展示识别结果
特性：适老化样式 + 语音播报 + 历史记录 + 健康档案
运行环境：Python 3.10+
依赖：pip install streamlit requests pillow
运行命令：streamlit run app.py
"""

import base64
import csv
import io
import json
import os
import re
import time
from datetime import datetime

from dotenv import load_dotenv

import requests
import streamlit as st
from PIL import Image

# 加载本地 .env（如果存在），便于本地测试；Streamlit Cloud 仍使用 Secrets
load_dotenv()


# ========== 配置区 ==========

# MiMo Token Plan - 新加坡集群
API_URL = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions"
MODEL_NAME = "mimo-v2.5"

# Agnes-2.0-Flash 配置（A/B 对比用）
AGNES_API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
AGNES_MODEL_NAME = "agnes-2.0-flash"

# 六大人群选项（保留向后兼容）
HEALTH_GROUPS = ["糖尿病", "高血压", "脑梗/心血管", "减脂", "过敏", "孕妇/儿童"]


# ========== GB 2760 + 健康档案数据加载 ==========

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_GB2760_RISK_PATH = os.path.join(_DATA_DIR, "gb2760_risk.csv")
_DISEASES_PATH = os.path.join(_DATA_DIR, "common_diseases.json")
_ALLERGENS_PATH = os.path.join(_DATA_DIR, "allergens.json")
_DRUGS_PATH = os.path.join(_DATA_DIR, "common_drugs.json")
_CONFLICTS_PATH = os.path.join(_DATA_DIR, "drug_food_conflicts.json")

# 评分公式常量（A=绿/B=黄/C=红）
SCORE_PENALTY = {"A": 0, "B": 8, "C": 25}

# 保健品辅料白名单（不参与扣分）
SUPPLEMENT_EXCIPIENTS = {"鱼油", "明胶", "甘油", "蜂蜡", "卵磷脂", "淀粉", "麦芽糊精", "羧甲基纤维素钠"}

# 页面名称映射
PAGE_NAMES = {
    "home": "首页",
    "scan": "扫描",
    "result": "识别结果",
    "history": "历史记录",
    "detail": "产品详情",
    "profile": "健康档案",
}

# 完整历史快照路径与上限
_HISTORY_FULL_PATH = os.path.join(_DATA_DIR, "history_full.json")
_HISTORY_FULL_MAX = 20


def _load_json(path):
    """读取 JSON 文件，失败返回空 dict/list."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if path.endswith(("diseases.json", "allergens.json", "common_drugs.json", "drug_food_conflicts.json")) else {}


def _load_markdown(path):
    """读取 Markdown 文件，失败返回提示文本."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "文件暂未找到，请稍后刷新页面重试。"


@st.cache_resource
def load_health_data():
    """加载所有健康档案数据（疾病/过敏原/药物/冲突），缓存一次."""
    return {
        "diseases": _load_json(_DISEASES_PATH).get("categories", []),
        "allergens": _load_json(_ALLERGENS_PATH).get("categories", []),
        "drugs": _load_json(_DRUGS_PATH).get("categories", []),
        "conflicts": _load_json(_CONFLICTS_PATH).get("conflicts", []),
    }


@st.cache_resource
def load_gb2760_risk():
    """加载 GB 2760 添加剂风险分级表，返回 dict[中文名] -> {level, adi, warnings, note}."""
    risk_map = {}
    try:
        with open(_GB2760_RISK_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row["cn_name"].strip()
                if key:
                    risk_map[key] = {
                        "level": row.get("risk_level", "B").strip(),
                        "adi": row.get("adi_value", "").strip(),
                        "warnings": row.get("health_warnings", "").strip(),
                        "note": row.get("note", "").strip(),
                    }
    except FileNotFoundError:
        pass
    return risk_map


# ========== 数据文件启动校验（Phase 4 / Task 12）==========

# 数据文件 → 必需键/列 的对照表（用于启动时结构校验）
_DATA_FILE_SPEC = [
    # (路径常量, 文件显示名, 校验类型, 必需键/列列表)
    (_GB2760_RISK_PATH, "gb2760_risk.csv", "csv", ["cn_name", "risk_level"]),
    (_DISEASES_PATH, "common_diseases.json", "json", ["categories"]),
    (_ALLERGENS_PATH, "allergens.json", "json", ["categories"]),
    (_DRUGS_PATH, "common_drugs.json", "json", ["categories"]),
    (_CONFLICTS_PATH, "drug_food_conflicts.json", "json", ["conflicts"]),
]


def validate_data_files():
    """启动时校验关键数据文件存在性与结构，返回问题列表.

    校验对象：gb2760_risk.csv / common_diseases.json / allergens.json /
    common_drugs.json / drug_food_conflicts.json
    校验内容：文件是否存在 + 必需列/键是否存在
    返回值：list[str]，每个元素是一条用户可读的问题描述；空列表表示全部通过。
    注意：本函数不阻断运行，仅返回问题清单由调用方决定如何展示。
    """
    issues = []
    for path, display_name, kind, required_keys in _DATA_FILE_SPEC:
        # 1. 文件存在性
        if not os.path.exists(path):
            issues.append(f"缺失文件：data/{display_name}（相关功能将不可用）")
            continue

        # 2. 结构校验
        if kind == "csv":
            try:
                with open(path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    cols = reader.fieldnames or []
                    missing = [k for k in required_keys if k not in cols]
                    if missing:
                        issues.append(
                            f"data/{display_name} 缺少必要列：{', '.join(missing)}"
                        )
            except Exception as e:
                issues.append(f"data/{display_name} 读取失败：{e}")
        elif kind == "json":
            data = _load_json(path)
            if not isinstance(data, dict):
                issues.append(f"data/{display_name} 不是合法 JSON 对象")
                continue
            missing = [k for k in required_keys if k not in data]
            if missing:
                issues.append(
                    f"data/{display_name} 缺少键：{', '.join(missing)}"
                )
    return issues


# ========== 页面路由工具 ==========

def switch_page(page: str, **kwargs):
    """切换页面，跳转前保存当前页到 prev_page."""
    if "page" in st.session_state:
        st.session_state["prev_page"] = st.session_state["page"]
    st.session_state["page"] = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def render_top_nav(title: str, show_back: bool = True, back_target: str = "home", right_action: str | None = None):
    """渲染顶部导航栏（标题 + 返回按钮 + 右侧可选入口）.

    right_action 可选值："profile"（心形入口）、None。
    """
    cols = st.columns([1, 4, 1])
    with cols[0]:
        if show_back:
            if st.button("← 返回", key=f"tn_back_{title}", help="返回"):
                target = st.session_state.get("prev_page", back_target)
                switch_page(target)
    with cols[1]:
        st.markdown(f"<div style='text-align:center;font-size:22px;font-weight:bold;'>{title}</div>", unsafe_allow_html=True)
    with cols[2]:
        if right_action == "profile":
            if st.button("👤 档案", key=f"tn_profile_{title}", help="健康档案"):
                switch_page("profile")


# ========== 适老化样式 ==========

def inject_elder_css():
    """注入适老化 CSS：大字体、大按钮、高对比度，并按设计稿统一主题."""
    st.markdown(
        """
        <style>
        /* ── 设计稿变量 ── */
        :root {
          --color-primary: #2E7D32;
          --color-primary-light: #E8F5E9;
          --color-primary-dark: #1B5E20;
          --color-secondary: #FF9800;
          --color-secondary-light: #FFF3E0;
          --state-success: #43A047;
          --state-warning: #FDD835;
          --state-error: #E53935;
          --color-bg: #FAFAF5;
          --color-card: #FFFFFF;
          --color-text-primary: #212121;
          --color-text-secondary: #616161;
          --color-text-tertiary: #9E9E9E;
          --radius-md: 12px;
          --radius-lg: 16px;
          --radius-xl: 24px;
          --shadow-subtle: 0 1px 3px rgba(0,0,0,0.05);
          --shadow-card: 0 2px 8px rgba(0,0,0,0.08);
          --shadow-button: 0 4px 12px rgba(46,125,50,0.3);
        }

        /* 全局字体放大 + 背景 */
        .stApp { font-size: 18px; background: var(--color-bg) !important; }
        h1 { font-size: 28px !important; }
        h2 { font-size: 24px !important; }
        h3 { font-size: 20px !important; }

        /* 按钮放大 */
        .stButton > button {
            font-size: 20px !important;
            height: 56px !important;
            border-radius: 12px !important;
            font-weight: bold !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 8px !important;
        }

        /* 输入框放大 */
        .stTextInput input, .stTextArea textarea {
            font-size: 18px !important;
        }

        /* 通用白色卡片 */
        .card-white {
            background: var(--color-card);
            border-radius: var(--radius-lg);
            padding: 16px;
            margin: 12px 0;
            box-shadow: var(--shadow-card);
        }

        /* 顶部导航栏 */
        .top-nav {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 16px; background: var(--color-card);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin: -1rem -1rem 1rem -1rem;
        }
        .top-nav-title { font-size: 22px; font-weight: bold; color: var(--color-text-primary); }
        .top-nav-btn {
            width: 48px; height: 48px; border-radius: 50%;
            background: var(--color-primary-light); color: var(--color-primary);
            border: none; cursor: pointer; display: inline-flex;
            align-items: center; justify-content: center; font-size: 24px;
        }

        /* 语音按钮统一样式 */
        .voice-btn {
            display: inline-flex; align-items: center; justify-content: center;
            gap: 8px; font-size: 20px; height: 56px; padding: 0 24px;
            border-radius: 9999px; border: 2px solid #2E7D32;
            background: #E8F5E9; color: #1B5E20; font-weight: bold;
            cursor: pointer; min-width: 180px;
        }
        .voice-btn-sm {
            display: inline-flex; align-items: center; justify-content: center;
            gap: 6px; font-size: 18px; height: 48px; padding: 0 16px;
            border-radius: 12px; border: 2px solid #2E7D32;
            background: #E8F5E9; color: #1B5E20; font-weight: bold;
            cursor: pointer;
        }
        .voice-btn-icon { font-size: 24px; line-height: 1; }

        /* 健康标签行 */
        .health-tags-row {
            display: flex; gap: 8px; padding: 8px 0;
            overflow-x: auto; -webkit-overflow-scrolling: touch;
        }
        .health-tags-row::-webkit-scrollbar { display: none; }
        .health-tag {
            flex-shrink: 0; display: inline-flex; align-items: center; gap: 4px;
            padding: 8px 16px; border-radius: 9999px;
            font-size: 16px; font-weight: 500;
            background: var(--color-secondary-light); color: #E65100;
            cursor: pointer; border: none;
        }

        /* 评分色块 */
        .score-box {
            padding: 20px; border-radius: var(--radius-lg); text-align: center;
            color: #333333; margin: 12px 0;
            display: flex; align-items: center; justify-content: center; gap: 16px;
        }
        .score-num { font-size: 48px; font-weight: bold; }
        .score-label { font-size: 20px; }
        .score-shape {
            font-size: 48px; line-height: 1; font-weight: bold;
            display: inline-block; min-width: 56px;
        }

        /* 评分英雄区（结果页顶部大卡） */
        .score-hero {
            border-radius: var(--radius-lg); padding: 24px 20px;
            text-align: center; position: relative; overflow: hidden;
            margin: 12px 0;
        }
        .score-hero-product { font-size: 20px; font-weight: bold; color: var(--color-text-primary); margin-bottom: 8px; }
        .score-hero-number { font-size: 56px; font-weight: bold; line-height: 1.1; }
        .score-hero-label {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 8px 16px; border-radius: 9999px;
            font-size: 16px; font-weight: 500; margin-top: 12px;
        }

        /* 添加剂卡片：色盲友好三重编码 */
        .additive-row {
            display: flex; justify-content: space-between;
            align-items: center; padding: 14px 16px;
            border-radius: 10px; margin: 6px 0;
            background: var(--color-bg); font-size: 18px;
        }
        .additive-shape {
            display: inline-flex; align-items: center; justify-content: center;
            width: 24px; height: 24px; font-size: 16px;
            margin-right: 12px; flex-shrink: 0;
        }
        .additive-level {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 6px 12px; border-radius: 8px; font-weight: bold;
            font-size: 16px;
        }

        /* 添加剂清单项 */
        .additive-list-item {
            display: flex; align-items: center; gap: 12px;
            padding: 12px; border-radius: 12px;
            background: var(--color-bg); margin: 8px 0;
        }
        .additive-list-name { font-size: 18px; font-weight: 500; color: var(--color-text-primary); flex: 1; }
        .additive-list-note { font-size: 14px; color: var(--color-text-tertiary); }

        /* 健康档案：大复选框 */
        .stCheckbox {
            padding: 8px 0;
        }
        .stCheckbox > label {
            font-size: 20px !important;
        }
        .stCheckbox > label > div {
            min-width: 32px !important; min-height: 32px !important;
        }

        /* 健康档案疾病卡片 */
        .condition-card {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            gap: 8px; min-height: 110px; border-radius: var(--radius-md);
            border: 2px solid #E0E0E0; background: var(--color-card);
            cursor: pointer; transition: all 0.2s; padding: 12px;
        }
        .condition-card.selected {
            background: var(--color-primary-light); border-color: var(--color-primary);
        }
        .condition-card .condition-icon {
            width: 44px; height: 44px; border-radius: 50%;
            background: #E0E0E0; color: var(--color-text-secondary);
            display: flex; align-items: center; justify-content: center;
            font-size: 22px;
        }
        .condition-card.selected .condition-icon {
            background: var(--color-primary); color: #fff;
        }
        .condition-card .condition-name {
            font-size: 18px; font-weight: 500; color: var(--color-text-primary);
        }
        .condition-card.selected .condition-name {
            color: var(--color-primary); font-weight: bold;
        }

        /* 首页扫描按钮 */
        .home-main-scan-btn {
            display: flex; align-items: center; justify-content: center;
            gap: 12px; width: 100%;
        }
        .home-main-scan-btn-icon { font-size: 28px; }

        /* 历史记录卡片 */
        .history-cards-row {
            display: flex; gap: 12px; overflow-x: auto;
            -webkit-overflow-scrolling: touch; padding-bottom: 8px;
        }
        .history-cards-row::-webkit-scrollbar { display: none; }
        .history-card-mini {
            flex-shrink: 0; width: 150px; background: var(--color-card);
            border-radius: var(--radius-md); padding: 14px;
            box-shadow: var(--shadow-card); cursor: pointer;
        }
        .history-card-mini-name { font-size: 17px; font-weight: bold; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .history-card-mini-score { display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; border-radius: 9999px; font-size: 15px; font-weight: bold; margin-bottom: 8px; }
        .history-card-mini-date { font-size: 13px; color: var(--color-text-tertiary); }

        /* 历史记录列表项 */
        .history-list-item {
            display: flex; align-items: center; gap: 16px;
            background: var(--color-card); border-radius: var(--radius-lg);
            padding: 16px; margin-bottom: 12px; box-shadow: var(--shadow-card);
            cursor: pointer;
        }
        .history-list-score {
            width: 52px; height: 52px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px; font-weight: bold; flex-shrink: 0;
        }
        .history-list-info { flex: 1; }
        .history-list-name { font-size: 18px; font-weight: bold; color: var(--color-text-primary); }
        .history-list-status { font-size: 15px; font-weight: 500; margin-top: 2px; }
        .history-list-date { font-size: 13px; color: var(--color-text-tertiary); margin-top: 2px; }

        /* 营养成分可视化条 */
        .nrv-bar-wrap {
            margin: 10px 0; padding: 8px 0;
        }
        .nrv-bar-label {
            display: flex; justify-content: space-between;
            font-size: 18px; margin-bottom: 6px; color: #333;
        }
        .nrv-bar-track {
            width: 100%; height: 24px; background: #E0E0E0;
            border-radius: 12px; overflow: hidden;
        }
        .nrv-bar-fill {
            height: 100%; border-radius: 12px;
            transition: width 0.3s;
        }

        /* 底部语音控制条 */
        .voice-control-bar {
            position: sticky; bottom: 0; left: 0; right: 0;
            background: #fff; padding: 12px 16px;
            border-top: 2px solid #43A047; z-index: 100;
            box-shadow: 0 -4px 12px rgba(0,0,0,0.08);
            margin-bottom: 20px;
        }

        /* 结果页样式 */
        .result-score-hero {
            border-radius: 16px; padding: 24px 20px; text-align: center;
            position: relative; overflow: hidden; margin: 12px 0; min-height: 160px;
        }
        .result-score-hero-product { font-size: 20px; font-weight: bold; margin-bottom: 8px; }
        .result-score-hero-number { font-size: 56px; font-weight: bold; line-height: 1.1; }
        .result-score-hero-label {
            display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px;
            border-radius: 9999px; font-size: 16px; font-weight: 500; margin-top: 12px;
        }
        .result-score-shape {
            display: inline-block; width: 16px; height: 16px; flex-shrink: 0;
        }
        .result-card {
            background:#FFFFFF; border-radius:16px; padding:16px;
            margin:12px 0; box-shadow:0 2px 8px rgba(0,0,0,0.08);
        }
        .result-card-title {
            font-size:20px; font-weight:bold; margin-bottom:12px;
            display:flex; align-items:center; gap:8px;
        }
        .result-additive-item {
            display:flex; align-items:center; gap:12px; padding:12px;
            border-radius:12px; background:#FAFAF5; border-left:4px solid; margin:8px 0;
        }
        .result-additive-shape {
            width:20px; height:20px; flex-shrink:0;
            display:inline-flex; align-items:center; justify-content:center;
        }
        .result-additive-name { flex:1; font-size:18px; font-weight:500; }
        .result-additive-level {
            flex-shrink:0; padding:4px 12px; border-radius:9999px;
            border:1px solid; font-size:14px; font-weight:500;
        }
        .detail-image-placeholder {
            width:100%; aspect-ratio:1; background:#F0F0EC;
            border-radius:12px; display:flex; align-items:center;
            justify-content:center; color:#9E9E9E; font-size:16px;
        }
        /* 健康档案页 */
        .profile-condition-grid {
            display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px;
        }
        .profile-condition-card {
            min-height:110px; background:#FFFFFF; border:2px solid #F0F0F0;
            border-radius:16px; padding:16px; display:flex; flex-direction:column;
            align-items:center; justify-content:center; gap:8px;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);
        }
        .profile-condition-selected {
            background:var(--color-primary-light); border-color:var(--color-primary);
        }
        .profile-condition-icon {
            width:44px; height:44px; border-radius:50%;
            background:var(--color-primary); color:#fff;
            display:flex; align-items:center; justify-content:center; font-size:22px;
        }
        .profile-condition-name {
            font-size:18px; font-weight:500; color:var(--color-text-primary);
        }
        .profile-allergen-card {
            background:#FFFFFF; border-radius:16px; padding:16px;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);
        }
        .profile-save-bottom-btn {
            position:sticky; bottom:0; left:0; right:0;
            padding:12px 16px; background:#fff; border-top:1px solid #E0E0E0;
            margin-top:20px; z-index:50;
        }
        .profile-save-bottom-btn button {
            height:56px !important; border-radius:9999px !important;
        }
        /* 小字免责提示 */
        .disclaimer-text {
            font-size:14px; color:#9E9E9E; text-align:center;
            padding:8px 0; margin-top:8px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# ========== 语音播报（浏览器原生，零依赖）==========

def speak_text(text: str, rate: float = 1.0):
    """用浏览器原生 SpeechSynthesis API 播报中文语音.

    参数：
        text: 要播报的文本
        rate: 语速，0.7 慢速 / 1.0 正常 / 1.3 快速 / 0.75 慢速重播

    注意：手机浏览器要求语音播报必须由用户手势同步触发。
    此函数注入一个纯 HTML 按钮 + 内联 JS，点击时直接在浏览器端
    调用 speechSynthesis.speak()，不经过 Python rerun，确保
    用户手势上下文不丢失。
    """
    rate = max(0.5, min(2.0, float(rate)))
    safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace('"', '\\"')
    # 用纯 HTML 按钮 + 内联 onclick，确保移动端用户手势同步触发播报
    js = f"""
    <div style="text-align:center;margin:12px 0;">
        <button onclick="
            var txt = '{safe}';
            speechSynthesis.cancel();
            var u = new SpeechSynthesisUtterance(txt);
            u.lang = 'zh-CN';
            u.rate = {rate};
            u.pitch = 1.0;
            u.volume = 1.0;
            var voices = speechSynthesis.getVoices();
            var v = null;
            for (var i = 0; i &lt; voices.length; i++) {{
                if (voices[i].name &amp;&amp; voices[i].name.indexOf('Yaoyao') >= 0) {{ v = voices[i]; break; }}
                if (!v &amp;&amp; voices[i].lang === 'zh-CN') v = voices[i];
            }}
            if (v) u.voice = v;
            speechSynthesis.speak(u);
        " style="
            font-size:20px; height:56px; padding:0 28px;
            border-radius:12px; border:2px solid #2E7D32;
            background:#E8F5E9; color:#1B5E20; font-weight:bold;
            cursor:pointer; min-width:200px;
        ">🔊 点击播报</button>
    </div>
    """
    st.markdown(js, unsafe_allow_html=True)


def _js_speech_control(action: str):
    """通过 JS 控制 speechSynthesis：pause / resume / cancel.

    参数：
        action: 'pause' / 'resume' / 'cancel' 之一
    """
    action = action if action in ("pause", "resume", "cancel") else "cancel"
    js = f"""
    <script>
    (function() {{
        try {{ speechSynthesis.{action}(); }} catch(e) {{ console.warn('[tts {action}]', e); }}
    }})();
    </script>
    """
    st.markdown(js, unsafe_allow_html=True)


def voice_control_panel(speak_content: str, key_prefix: str = "tts"):
    """语音播报控制面板：简洁版，主按钮+折叠的语速控制."""
    if "tts_rate" not in st.session_state:
        st.session_state["tts_rate"] = 1.0

    rate = st.session_state["tts_rate"]
    safe = speak_content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace('"', '\\"')

    st.markdown(
        f"""
        <div style="display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap;">
            <button onclick="
                speechSynthesis.cancel();
                var u = new SpeechSynthesisUtterance('{safe}');
                u.lang='zh-CN'; u.rate={rate}; u.pitch=1.0; u.volume=1.0;
                var voices = speechSynthesis.getVoices();
                for (var i=0; i&lt;voices.length; i++) {{
                    if (voices[i].name &amp;&amp; voices[i].name.indexOf('Yaoyao')>=0) {{ u.voice=voices[i]; break; }}
                    if (voices[i].lang==='zh-CN' &amp;&amp; !u.voice) u.voice=voices[i];
                }}
                speechSynthesis.speak(u);
            " class="voice-btn">
                <span class="voice-btn-icon">🔊</span> 点击播报
            </button>
            <button onclick="try{{speechSynthesis.cancel();}}catch(e){{}}" class="voice-btn-sm" style="border-color:#9E9E9E;background:#F5F5F5;color:#616161;">
                ⏹ 停止
            </button>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("语速调整"):
        rate_options = ["0.7x 慢速", "1.0x 正常", "1.3x 快速"]
        rate_values = [0.7, 1.0, 1.3]
        cur_idx = 1
        try:
            cur_idx = rate_values.index(st.session_state["tts_rate"])
        except ValueError:
            cur_idx = 1
        chosen = st.radio(
            "选择语速",
            rate_options,
            index=cur_idx,
            horizontal=True,
            key=f"{key_prefix}_rate_radio",
            label_visibility="collapsed",
        )
        st.session_state["tts_rate"] = rate_values[rate_options.index(chosen)]


# ========== 核心函数（API 调用）==========

def get_api_key(model="mimo"):
    """从环境变量或 secrets 读取 API 密钥，按模型选不同变量名.

    安全说明：
    - 本地开发使用 .env（已被 .gitignore 排除，禁止提交）；
    - 生产环境（Streamlit Cloud）必须使用 Settings → Secrets 配置，禁止在源码中写死 key；
    - 不要把真实 key 写入 README、issue、commit message 或聊天记录。
    """
    var = "AGNES_API_KEY" if model == "agnes" else "MIMO_API_KEY"
    key = os.getenv(var, "")
    if key:
        return key
    try:
        return st.secrets[var]
    except (KeyError, FileNotFoundError):
        return ""


def encode_image_to_base64(image_file, max_size=1024):
    """压缩图片并转 base64."""
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def build_system_prompt(groups):
    """构建 system 提示词：自动判断食品/保健品，单次 API 返回双模式 JSON."""
    group_str = "、".join(groups) if groups else "普通人群"
    return (
        "你是食品/保健食品标签解读助手，专门为老年人解析中国境内销售的预包装食品和保健食品标签。"
        "用户会上传一张标签图片（可能是普通食品配料表，也可能是保健食品标签）。"
        "**第一步判断产品类型**：(1) 看到'蓝帽子'标志、'国食健字'/'国食健注'/'食健备'备案号、'保健食品'字样、'本品不能代替药物'等表述 → **supplement**（保健食品）"
        "(2) 否则 → **food**（普通预包装食品）。"
        "**第二步按类型返回 JSON**。必须返回合法 JSON，不要 Markdown 代码块，不要任何解释。\n\n"
        "## type=supplement（保健食品）必填字段\n"
        "- type: \"supplement\"\n"
        "- product_name: 产品名称（**必须中文**），英文产品名翻译成中文或填'该产品'\n"
        "- approval_no: 批准文号/备案号（如'国食健注 G20170479'、'食健备 G202537000369'），**未显示则填'未显示'**\n"
        "- ingredients: 全部原料/配料成分（按包装原文顺序）\n"
        "- functional_ingredients: 标志性成分/功效成分及含量（如'每100g含辅酶Q10 24g'、'每片含钙 150mg'）\n"
        "- health_claims: 包装上写的保健功能（**严格按包装原文引用，不评价**），如'补充多种维生素和矿物质'、'有助于增强免疫力和抗氧化'\n"
        "- suitable_for: 包装上的适宜人群（**严格按包装原文引用**），如'需要补充多种维生素和矿物质的成人'、'成人'\n"
        "- unsuitable_for: 包装上的不适宜人群（**严格按包装原文引用**），如'17岁以下人群、孕妇、乳母'\n"
        "- usage: 食用方法及食用量（**严格按包装原文引用**），如'每日1次，每次2片，口服'、'每日1次，每次1粒，口服'\n"
        "- storage: 贮藏方法（按包装原文）\n"
        "- shelf_life: 保质期\n"
        "- summary: **30字以内**的事实摘要（如'成人多种维生素补充剂，每日2片'），**禁止评价、禁止推荐**\n\n"
        "## type=food（普通预包装食品）必填字段\n"
        "- type: \"food\"\n"
        "- product_name: 产品名称（**必须中文**），英文产品名翻译成中文或填'该产品'，图片未显示则填'未知'\n"
        "- ingredients: 所有配料成分列表，按原文顺序\n"
        "- additives: 只含 GB 2760 具体食品添加剂。**不要**把食品用香精、食用盐、水、糖、油、面粉等基础配料列入。"
        "每个添加剂含 name、code(INS/E号，没有留空)。**不要输出 level 字段，不要给 score 评分，风险等级由系统判定。**\n"
        "- advice: 针对以下人群的一句话建议：" + group_str + "\n\n"
        "## 强制规则（两类产品都适用）\n"
        "- product_name **必须中文**，英文产品名翻译成中文或填'该产品'\n"
        "- 所有引用包装的内容（health_claims/suitable_for/usage）**严格按包装原文**，不评价、不推荐、不补全\n"
        "- 禁止任何医学疗效措辞：'治疗/疗效/降三高/防癌/增强免疫力+治愈'等\n"
        "- 所有健康相关结论以'请咨询医生/药师/营养师'收尾"
    )


def _show_friendly_error(friendly_msg, debug_detail=""):
    """显示用户友好的错误提示；DEBUG=1 时附带原始详情折叠区（不直接展示给普通用户）."""
    st.error(friendly_msg)
    if os.getenv("DEBUG") == "1" and debug_detail:
        with st.expander("调试：错误详情"):
            st.code(debug_detail)


def call_api(api_key, image_b64, system_prompt, model="mimo"):
    """统一调用 MiMo 或 Agnes Vision API，返回模型回复文本.

    Phase 4 (v0.2.5) 健壮性增强：
    - 最多 2 次指数退避重试（第1次等2秒，第2次等4秒）
    - 仅网络错误或 5xx 状态码才重试，4xx 直接返回不重试
    - 错误提示使用用户友好文案，不直接展示 resp.text
    - 原始错误信息仅在 DEBUG=1 时通过折叠区展示
    """
    if model == "agnes":
        url, model_name = AGNES_API_URL, AGNES_MODEL_NAME
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    else:
        url, model_name = API_URL, MODEL_NAME
        headers = {"api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": "请分析这张配料表图片，按规则返回 JSON。"}
            ]}
        ],
        "temperature": 0.2,
        "max_tokens": 4096
    }

    # 指数退避重试：1 次初始 + 最多 2 次重试 = 共 3 次
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        # ===== 发起请求 =====
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
        except requests.exceptions.Timeout:
            # 超时属于网络错误，可重试
            if attempt < max_attempts:
                time.sleep(2 ** attempt)  # attempt=1→2秒，attempt=2→4秒
                continue
            _show_friendly_error(
                "识别服务暂时不可用，请稍后重试。",
                f"Timeout after 90s, attempts={attempt}"
            )
            return None
        except requests.exceptions.RequestException as e:
            # 连接错误/网络异常，可重试
            if attempt < max_attempts:
                time.sleep(2 ** attempt)
                continue
            _show_friendly_error(
                "网络连接失败，请检查网络后重试。",
                str(e)[:1000]
            )
            return None

        # ===== 收到 HTTP 响应 =====
        if resp.status_code == 200:
            try:
                return resp.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                # 响应内容解析失败：不重试（重试也不会变好）
                _show_friendly_error(
                    "识别结果解析失败，请重试。",
                    f"Parse error: {e}\n{resp.text[:1000]}"
                )
                return None

        # 4xx 客户端错误：不重试（API Key 无效、请求格式错误等）
        if 400 <= resp.status_code < 500:
            _show_friendly_error(
                "API 密钥无效或请求被拒绝，请检查密钥后重试。",
                f"HTTP {resp.status_code}\n{resp.text[:1000]}"
            )
            return None

        # 5xx 服务端错误：可重试
        if attempt < max_attempts:
            time.sleep(2 ** attempt)
            continue
        # 最后一次仍失败
        _show_friendly_error(
            "识别服务暂时不可用，请稍后重试。",
            f"HTTP {resp.status_code}\n{resp.text[:1000]}"
        )
        return None

    return None


def parse_result(raw, health_groups=None):
    """解析模型返回的 JSON 文本，并对 type=food 强制按 GB 2760 库覆盖 level 和 score."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        result = json.loads(s)
    except json.JSONDecodeError as e:
        st.error(f"返回内容不是合法 JSON：{e}")
        st.text(raw)
        return None
    # 兜底：纯英文 product_name 强制改成"该产品"（适老化）
    name = str(result.get("product_name", ""))
    if name and re.fullmatch(r"[A-Za-z\s\-\.\&]+", name):
        result["product_name"] = "该产品"
    # 仅对普通食品做客户端权威判定
    if result.get("type") == "food":
        additives = result.get("additives", [])
        if isinstance(additives, list):
            for a in additives:
                if isinstance(a, dict) and a.get("name"):
                    level, ins, note = normalize_additive(a["name"])
                    a["level"] = level
                    if ins and not a.get("code"):
                        a["code"] = ins
                    if note and not a.get("note"):
                        a["note"] = note
            result["additives"] = additives
            result["score"] = compute_score_from_additives(
                additives, health_groups or []
            )
    return result


# ========== 客户端权威判定（GB 2760 库 + 药物冲突）==========

def normalize_additive(name):
    """查 GB 2760 风险库返回 (level, ins_no, note)，未匹配默认 yellow 兜底."""
    if not name:
        return "yellow", "", ""
    n = str(name).strip()
    # 保健品辅料豁免
    if n in SUPPLEMENT_EXCIPIENTS or any(k in n for k in ["胶囊壳", "软胶囊"]):
        return "A", "", "保健品辅料，不扣分"
    risk = load_gb2760_risk()
    # 精确匹配
    if n in risk:
        r = risk[n]
        return r["level"], "", r.get("note", "")
    # 去括号、空格、INS 号后再匹配
    n_clean = re.sub(r"[\s()（）\[\]【】]", "", n)
    n_clean = re.sub(r"[(（][^）)]*[）)]", "", n_clean)
    for k, v in risk.items():
        k_clean = re.sub(r"[\s()（）\[\]【】]", "", k)
        if k_clean == n_clean:
            return v["level"], "", v.get("note", "")
    # 模糊匹配（必须长度相近，避免"山梨糖醇"误匹配"山梨糖醇酐单硬脂酸酯"）
    for k, v in risk.items():
        if abs(len(k) - len(n)) > 2:
            continue
        if k in n or n in k:
            return v["level"], "", f"模糊匹配：{k}"
    # 未匹配：默认 B（保守策略，宁严勿宽）
    return "B", "", "未在 GB 2760 库中，按黄色（注意）兜底"


def compute_score_from_additives(additives, health_groups=None):
    """按添加剂风险等级 + 特殊人群敏感性算分.
    公式: 100 - 红×25 - 黄×8 + 特殊人群命中额外扣 4."""
    if not additives:
        return 100
    score = 100
    health_set = set(health_groups or [])
    risk = load_gb2760_risk()
    for a in additives:
        if not isinstance(a, dict):
            continue
        name = a.get("name", "")
        level, _, _ = normalize_additive(name)
        score -= SCORE_PENALTY.get(level, 0)
        # 特殊人群敏感性（如糖尿病/高血压 + 命中 warnings）
        if name in risk:
            warnings = risk[name].get("warnings", "")
            if warnings and any(w in health_set for w in warnings.split("/")):
                score -= 4
    return max(0, min(100, score))


def check_drug_food_conflicts(ingredients_list, user_drugs):
    """根据用户当前用药和识别到的配料，检测药物-食物冲突.
    user_drugs: 用户在健康档案中选择的药物列表，每项为 dict 含 id 和 name.
    返回冲突列表: [{drug, food, severity, description, recommendation, source}]."""
    if not user_drugs or not ingredients_list:
        return []
    user_drug_ids = {d.get("id") for d in user_drugs if d.get("id")}
    if not user_drug_ids:
        return []
    conflicts = []
    health_data = load_health_data()
    for c in health_data.get("conflicts", []):
        if c.get("drug_id") not in user_drug_ids:
            continue
        # 检查配料中是否包含冲突食物关键词
        for ing in ingredients_list:
            ing_str = str(ing)
            for fk in c.get("food_keywords", []):
                if fk in ing_str:
                    conflicts.append({
                        "drug": c.get("drug_name", ""),
                        "food": ing_str,
                        "matched_keyword": fk,
                        "severity": c.get("severity", "medium"),
                        "description": c.get("description", ""),
                        "recommendation": c.get("recommendation", ""),
                        "mechanism": c.get("mechanism", ""),
                        "source": c.get("source", ""),
                    })
                    break  # 每个冲突只算一次
    return conflicts


# ========== 历史记录（本地 JSON 持久化，Phase 4 / Task 13）==========

# 历史记录本地文件路径
_HISTORY_PATH = os.path.join(_DATA_DIR, "history.json")
# 最多保留最近 50 条（超出自动删除最旧的）
_HISTORY_MAX = 50


def load_history():
    """读取本地历史记录 JSON，返回 list[dict].

    文件不存在或损坏时返回空列表，不抛异常（初赛版本：刷新不丢失）。
    每条记录字段：timestamp, product_name, score, type(food/supplement), additives_count。
    """
    try:
        with open(_HISTORY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_history(record):
    """追加一条历史记录到本地 JSON 文件，并保留最近 50 条.

    record: dict，至少包含 timestamp/product_name/score/type/additives_count。
    异常时静默忽略（写入失败不阻断识别主流程）。
    """
    try:
        history = load_history()
        history.insert(0, record)
        history = history[:_HISTORY_MAX]  # 截断到最近 50 条
        os.makedirs(_DATA_DIR, exist_ok=True)  # 兜底确保 data 目录存在
        with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError:
        # 写入失败不阻断主流程
        pass


def load_history_full():
    """读取完整历史快照."""
    try:
        with open(_HISTORY_FULL_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_history_full(result):
    """保存完整识别结果快照，最多 _HISTORY_FULL_MAX 条."""
    try:
        history = load_history_full()
        history.insert(0, result)
        history = history[:_HISTORY_FULL_MAX]
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_HISTORY_FULL_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def add_history(result):
    """识别成功后保存一条历史记录（Phase 4 起改为本地 JSON 持久化，刷新不丢失）.

    不保存图片数据（隐私保护，已在 Phase 0 确认）。
    """
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "product_name": result.get("product_name", "未知"),
        "score": result.get("score", 0),
        "type": str(result.get("type", "food")),
        "additives_count": len(result.get("additives", [])),
    }
    save_history(record)
    # 同步写入 session_state，便于其他逻辑即时读取（可选）
    if "history" not in st.session_state:
        st.session_state["history"] = []
    st.session_state["history"].insert(0, record)
    st.session_state["history"] = st.session_state["history"][:_HISTORY_MAX]

    # 保存完整识别快照供详情页使用
    save_history_full(result)


def show_history():
    """在侧边栏展示历史记录（调用时需已在 sidebar 上下文内）.

    Phase 4 起改为从本地 JSON 加载，刷新页面不丢失。
    """
    st.header("历史记录")
    st.caption(f"最近 {_HISTORY_MAX} 条记录保存在本地，不存储图片。")
    history = load_history()
    if not history:
        st.caption("暂无记录")
        return
    for item in history:
        score = item.get("score", 0)
        color = "green" if score >= 80 else ("orange" if score >= 60 else "red")
        # 简短时间显示（YYYY-MM-DD HH:MM），适老化不显示秒
        ts = item.get("timestamp", "")
        time_str = ts[:16].replace("T", " ") if ts else ""
        # 类型标签：保健食品 / 食品
        type_tag = "保健食品" if item.get("type") == "supplement" else "食品"
        st.markdown(
            f"<div style='border-left:4px solid {color};padding:8px 12px;margin:6px 0;background:#FAFAF5;border-radius:6px;'>"
            f"<b>{item.get('product_name', '未知')}</b>"
            f"<span style='color:#888;font-size:14px;'> [{type_tag}]</span><br>"
            f"<span style='color:{color};font-size:20px;font-weight:bold;'>{score}分</span> "
            f"<span style='color:#888;'>{item.get('additives_count', 0)}种添加剂</span>"
            f"<br><span style='color:#aaa;font-size:13px;'>{time_str}</span>"
            f"</div>",
            unsafe_allow_html=True
        )


# ========== 结果页通用组件 ==========

from typing import Tuple


def _get_level_info(level: str) -> Tuple[str, str, str]:
    """统一返回添加剂等级信息：标签、颜色、形状图标."""
    mapping = {
        "A": ("可食用", "#43A047", "●"),
        "green": ("可食用", "#43A047", "●"),
        "B": ("注意", "#FF9800", "▲"),
        "yellow": ("注意", "#FF9800", "▲"),
        "C": ("少吃", "#E53935", "■"),
        "red": ("少吃", "#E53935", "■"),
    }
    return mapping.get(level, ("未知", "#9E9E9E", "●"))


def _clip_path(shape: str) -> str:
    """返回形状对应的 CSS clip-path."""
    if shape == "▲":
        return "polygon(50% 0%, 0% 100%, 100% 100%)"
    if shape == "■":
        return "polygon(0 0, 100% 0, 100% 100%, 0 100%)"
    return "circle(50%)"


def _render_score_hero(score: int, product_name: str, show_slow_replay: bool = True):
    """渲染评分英雄区（result/detail 复用）."""
    if score >= 80:
        color, label, bg_gradient = "#43A047", "可放心食用", "linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%)"
    elif score >= 60:
        color, label, bg_gradient = "#FF9800", "特定人群注意", "linear-gradient(135deg, #FFF8E1 0%, #FFECB3 100%)"
    else:
        color, label, bg_gradient = "#E53935", "建议咨询医生", "linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%)"
    text_color = "#333333" if score >= 60 else "#333333"
    shape = "●" if score >= 80 else ("▲" if score >= 60 else "■")
    shape_bg = color
    st.markdown(
        f"<div class='result-score-hero' style='background:{bg_gradient};border:2px solid {color}44;'>"
        f"<div class='result-score-hero-product' style='color:{color};'>{product_name}</div>"
        f"<div class='result-score-hero-number' style='color:{color};'>{score}</div>"
        f"<div class='result-score-hero-label' style='background:{color}22;color:{color};'>"
        f"<span class='result-score-shape' style='background:{shape_bg};clip-path:{_clip_path(shape)};'></span>"
        f"{label}</div></div>",
        unsafe_allow_html=True
    )


def _render_additive_card(additives):
    """渲染添加剂清单卡片（result/detail 复用）."""
    if not additives:
        st.markdown("<div class='result-card'><div class='result-card-title'>📋 添加剂清单</div><p style='color:#666;'>未识别到需要关注的食品添加剂</p></div>", unsafe_allow_html=True)
        return
    html = "<div class='result-card'><div class='result-card-title'>📋 添加剂清单</div>"
    for item in additives:
        name = item.get("name", "未知")
        level = item.get("level", "B")
        label, color, shape = _get_level_info(level)
        html += (
            f"<div class='result-additive-item' style='border-left-color:{color};'>"
            f"<span class='result-additive-shape' style='background:{color};clip-path:{_clip_path(shape)};'></span>"
            f"<div class='result-additive-name'>{name}</div>"
            f"<span class='result-additive-level' style='color:{color};border-color:{color};background:{color}11;'>{label}</span>"
            f"</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ========== 结果展示 ==========

def render_food(result):
    """展示普通食品结果（设计稿卡片化）."""
    score = result.get("score", 0)
    product_name = result.get("product_name", "未知")
    advice = result.get("advice", "")

    render_top_nav("识别结果", back_target="home")

    _render_score_hero(score, product_name)

    st.markdown(
        "<div class='disclaimer-text'>评分仅供参考，AI识别可能存在误差，请以包装原文为准</div>",
        unsafe_allow_html=True
    )

    speak_content = f"评分{score}分。{advice}本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生/药师/营养师。"
    st.session_state["last_speak_content"] = speak_content

    _render_additive_card(result.get("additives", []))

    render_nutrition_bars(result)

    if advice:
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>💡 健康建议</div><p>{advice}</p></div>",
            unsafe_allow_html=True
        )

    ingredients = result.get("ingredients", [])
    render_personal_warnings(result, ingredients)

    if ingredients:
        with st.expander("查看全部配料"):
            st.write("、".join(ingredients))

    if os.getenv("DEBUG") == "1":
        with st.expander("查看原始 JSON（调试用）"):
            st.json(result)

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='voice-control-bar'>", unsafe_allow_html=True)
    last_speak = st.session_state.get("last_speak_content", "")
    if last_speak:
        voice_control_panel(last_speak, key_prefix="tts_food")
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📷 再扫一个", use_container_width=True):
            switch_page("scan")
    with col2:
        if st.button("🏠 返回首页", use_container_width=True):
            switch_page("home")


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
        health_data = load_health_data()
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
        st.markdown(
            "<div class='result-card' style='border-left:4px solid #E53935;'>"
            "<div class='result-card-title'>⚠️ 个性化提醒</div>"
            + "".join(f"<p style='margin:8px 0;'>{w}</p>" for w in warnings)
            + "<p style='font-size:14px;color:#9E9E9E;margin-top:8px;'>本工具不提供医疗建议，如有疑问请咨询专业人士</p>"
            "</div>",
            unsafe_allow_html=True
        )
    elif user_drugs or user_allergens:
        st.markdown(
            "<div class='result-card' style='border-left:4px solid #43A047;'>"
            "<div class='result-card-title'>✅ 健康档案匹配</div>"
            "<p>根据您的健康档案，未发现需要特别注意的成分</p>"
            "</div>",
            unsafe_allow_html=True
        )


def render_nutrition_bars(result):
    """营养成分可视化条（钠/糖/脂肪 NRV%，Task 10.3）.

    仅当识别结果中包含 nutrition_nrv 字段时显示，否则跳过。
    字段格式：{"钠": 20, "糖": 35, "脂肪": 10}（数值为 NRV 百分比）
    """
    nrv = result.get("nutrition_nrv") or result.get("nutrition")
    if not nrv or not isinstance(nrv, dict):
        return
    # 三个关键指标：钠/糖/脂肪
    items = []
    for key in ("钠", "糖", "脂肪"):
        val = nrv.get(key)
        if isinstance(val, (int, float)) and val >= 0:
            items.append((key, float(val)))
    if not items:
        return
    st.markdown("### 📊 营养成分（NRV% 占比）")
    st.caption("NRV% = 营养素参考值百分比，每日推荐摄入量占比。数据来自包装原文。")
    for name, pct in items:
        pct_clamped = max(0, min(100, pct))
        # 颜色：<5% 绿 / 5-20% 橙 / >20% 红
        if pct < 5:
            bar_color = "#43A047"
            level_text = "低"
        elif pct <= 20:
            bar_color = "#FF9800"
            level_text = "中"
        else:
            bar_color = "#E53935"
            level_text = "高"
        st.markdown(
            f"<div class='nrv-bar-wrap'>"
            f"<div class='nrv-bar-label'>"
            f"<span><b>{name}</b> <small style='color:#888;'>({level_text})</small></span>"
            f"<span style='color:{bar_color};font-weight:bold;'>{pct:.0f}%</span>"
            f"</div>"
            f"<div class='nrv-bar-track'>"
            f"<div class='nrv-bar-fill' style='width:{pct_clamped:.0f}%;background:{bar_color};'></div>"
            f"</div></div>",
            unsafe_allow_html=True
        )


def render_supplement(result):
    """展示保健食品结果（卡片化包装，强制免责声明）."""
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
    st.session_state["last_speak_content"] = speak_content

    if summary:
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>📝 产品摘要</div><p>{summary}</p></div>",
            unsafe_allow_html=True
        )

    approval_no = result.get("approval_no", "未显示")
    if approval_no and approval_no != "未显示":
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>📋 批准文号</div>"
            f"<p><code>{approval_no}</code></p></div>",
            unsafe_allow_html=True
        )

    functional = result.get("functional_ingredients", [])
    if functional:
        html = "<div class='result-card'><div class='result-card-title'>✨ 标志性成分</div><ul style='margin:0;padding-left:20px;'>"
        for item in functional:
            html += f"<li style='margin:6px 0;'>{item}</li>"
        html += "</ul></div>"
        st.markdown(html, unsafe_allow_html=True)

    health_claims = result.get("health_claims", "")
    if health_claims and health_claims != "未显示":
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>💪 保健功能（包装原文）</div><p>{health_claims}</p></div>",
            unsafe_allow_html=True
        )

    suitable = result.get("suitable_for", "")
    unsuitable = result.get("unsuitable_for", "")
    if suitable and suitable != "未显示":
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>👥 适宜人群（包装原文）</div><p>{suitable}</p></div>",
            unsafe_allow_html=True
        )
    if unsuitable and unsuitable != "未显示":
        st.markdown(
            f"<div class='result-card' style='border-left:4px solid #FF9800;'><div class='result-card-title'>⚠️ 不适宜人群（包装原文）</div><p style='color:#E65100;'>{unsuitable}</p></div>",
            unsafe_allow_html=True
        )

    usage = result.get("usage", "")
    if usage and usage != "未显示":
        st.markdown(
            f"<div class='result-card'><div class='result-card-title'>💊 食用方法（包装原文）</div><p>{usage}</p></div>",
            unsafe_allow_html=True
        )

    ingredients = result.get("ingredients", [])
    if ingredients:
        with st.expander("查看全部原料"):
            st.write("、".join(ingredients))

    if os.getenv("DEBUG") == "1":
        with st.expander("查看原始 JSON（调试用）"):
            st.json(result)

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='voice-control-bar'>", unsafe_allow_html=True)
    last_speak = st.session_state.get("last_speak_content", "")
    if last_speak:
        voice_control_panel(last_speak, key_prefix="tts_supp")
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📷 再扫一个", use_container_width=True):
            switch_page("scan")
    with col2:
        if st.button("🏠 返回首页", use_container_width=True):
            switch_page("home")


def show_result(result):
    """分发到食品/保健食品渲染器."""
    if not result:
        return
    ptype = str(result.get("type", "food")).lower()
    if ptype == "supplement":
        render_supplement(result)
    else:
        render_food(result)


# ========== 首次访问法律同意弹窗 ==========

def render_legal_consent():
    """首次访问：阅读并同意用户协议及隐私政策."""
    st.markdown("## 用户协议及隐私政策")
    st.markdown(
        "使用本工具前请阅读并同意《用户协议及免责声明》和《隐私政策》。"
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_agreement = _load_markdown(os.path.join(base_dir, "USER_AGREEMENT.md"))
    privacy_policy = _load_markdown(os.path.join(base_dir, "PRIVACY_POLICY.md"))

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
    if st.button(
        "开始使用",
        type="primary",
        use_container_width=True,
        disabled=start_disabled,
        key="legal_start_btn"
    ):
        st.session_state["legal_agreed"] = True
        st.rerun()


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
    diseases = health_data.get("diseases", [])
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

    CONDITION_ITEMS = [
        ("diabetes", "糖尿病", "糖"),
        ("hypertension", "高血压", "压"),
        ("fat-loss", "减脂", "减"),
        ("allergy", "过敏", "敏"),
        ("children", "儿童", "儿"),
        ("pregnant", "孕妇", "孕"),
    ]
    CONDITION_NAME_MAP = {
        "diabetes": "糖尿病",
        "hypertension": "高血压",
        "fat-loss": "减脂",
        "allergy": "过敏",
        "children": "儿童",
        "pregnant": "孕妇",
    }

    st.markdown("### 我的健康状况")
    selected = set(profile.get("diseases", []))
    cols = st.columns(2)
    for i, (key, name, icon) in enumerate(CONDITION_ITEMS):
        with cols[i % 2]:
            is_selected = CONDITION_NAME_MAP[key] in selected
            cls = "profile-condition-card profile-condition-selected" if is_selected else "profile-condition-card"
            if st.button(f"{icon} {name}", key=f"cond_{key}", use_container_width=True):
                if is_selected:
                    selected.discard(CONDITION_NAME_MAP[key])
                else:
                    selected.add(CONDITION_NAME_MAP[key])
                profile["diseases"] = list(selected)
                st.rerun()
            st.markdown(
                f"<div class='{cls}'><span class='profile-condition-icon'>{icon}</span>"
                f"<span class='profile-condition-name'>{name}</span></div>",
                unsafe_allow_html=True
            )

    st.markdown("### 过敏原")
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

    cols = st.columns(2)
    for i, name in enumerate(allergen_options):
        with cols[i % 2]:
            checked = name in selected_alg
            if st.checkbox(name, value=checked, key=f"alg_{name}"):
                selected_alg.add(name)
            else:
                selected_alg.discard(name)

    profile["allergens"] = [allergen_structured_map[name] for name in selected_alg]

    st.markdown("### 💊 当前用药")
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

    st.divider()
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

def render_home_page():
    """首页：顶部导航 + 健康标签 + 扫描按钮 + 最近扫描."""
    render_top_nav("食品配料表识别", show_back=False, right_action="profile")

    profile = st.session_state.get("health_profile", {})
    diseases = profile.get("diseases", [])
    if diseases:
        tags_html = "<div class='health-tags-row'>"
        for d in diseases[:4]:
            tags_html += f"<span class='health-tag'>{d}</span>"
        tags_html += "</div>"
        st.markdown(tags_html, unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    if st.button("📷 拍照 / 上传配料表", type="primary", use_container_width=True, key="home_goto_scan"):
        switch_page("scan")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    history = load_history()[:6]
    if history:
        st.markdown(
            "<div style='display:flex;justify-content:space-between;align-items:center;padding:12px 0;'>"
            "<span style='font-size:20px;font-weight:bold;'>最近扫描</span>"
            "</div>",
            unsafe_allow_html=True
        )
        cols = st.columns(min(len(history), 3))
        for i, item in enumerate(history[:3]):
            with cols[i]:
                score = item.get("score", 0)
                if score >= 80:
                    bg, text_c = "#E8F5E9", "#2E7D32"
                elif score >= 60:
                    bg, text_c = "#FFF8E1", "#F57F17"
                else:
                    bg, text_c = "#FFEBEE", "#C62828"
                st.markdown(
                    f"<div style='background:#fff;border-radius:12px;padding:14px;box-shadow:0 2px 8px rgba(0,0,0,0.08);cursor:pointer;'>"
                    f"<div style='font-size:17px;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{item.get('product_name', '未知')}</div>"
                    f"<div style='display:inline-block;margin-top:8px;padding:4px 12px;border-radius:9999px;font-size:15px;font-weight:bold;background:{bg};color:{text_c};'>{score}分</div>"
                    f"<div style='font-size:13px;color:#9E9E9E;margin-top:8px;'>{item.get('timestamp', '')[:10]}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button(f"查看", key=f"home_card_{i}", use_container_width=True):
                    st.session_state["selected_history_index"] = i
                    st.session_state["detail_fallback_record"] = item
                    switch_page("detail")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("查看全部历史记录", use_container_width=True, key="home_goto_history"):
            switch_page("history")
    else:
        st.markdown(
            "<div style='text-align:center;padding:40px 20px;color:#9E9E9E;'>"
            "<div style='font-size:64px;margin-bottom:12px;'>🥫</div>"
            "<p style='font-size:18px;'>点击上方按钮开始扫描配料表</p>"
            "</div>",
            unsafe_allow_html=True
        )

    st.markdown(
        "<div class='disclaimer-text'>AI识别仅供参考，请以包装原文为准</div>",
        unsafe_allow_html=True
    )


def render_scan_page():
    """扫描上传页：文件上传 + 识别 + 跳转结果页."""
    render_top_nav("扫描识别", back_target="home", right_action="profile")

    profile = st.session_state.get("health_profile", {})
    groups = profile.get("diseases", [])

    model = "mimo"
    model_choice = "MiMo (mimo-v2.5)"
    st.session_state["model_choice"] = model_choice

    api_key = get_api_key(model)

    if not api_key and os.getenv("DEBUG") == "1":
        var_name = "MIMO_API_KEY"
        st.warning(f"未检测到 {var_name}，请在 .env 或 Secrets 中配置")
        api_key = st.text_input("API 密钥", type="password")

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<div style='text-align:center;padding:20px;'>"
        "<div style='font-size:72px;margin-bottom:12px;'>📷</div>"
        "<p style='font-size:20px;color:#333;font-weight:500;'>请选择配料表图片</p>"
        "<p style='font-size:16px;color:#9E9E9E;'>支持拍照或从相册选择</p>"
        "</div>",
        unsafe_allow_html=True
    )

    uploaded = st.file_uploader("上传配料表图片", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded is not None:
        st.image(uploaded, use_container_width=True)
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        if st.button("🔍 开始识别", type="primary", use_container_width=True):
            if not api_key:
                st.error("API 密钥未配置，请联系管理员")
                return
            with st.spinner("正在识别配料表..."):
                img_b64 = encode_image_to_base64(uploaded)
                sys_prompt = build_system_prompt(groups)
                raw = call_api(api_key, img_b64, sys_prompt, model)
                if raw:
                    result = parse_result(raw, health_groups=groups)
                    if result:
                        st.session_state["last_result"] = result
                        add_history(result)
                        switch_page("result")

    st.markdown(
        "<div class='disclaimer-text'>提示：请尽量正对配料表拍照，保证光线充足</div>",
        unsafe_allow_html=True
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
        render_supplement(result)
    else:
        render_food(result)


def render_history_page():
    """历史记录页：搜索 + 筛选 + 竖向列表."""
    render_top_nav("📋 历史记录", back_target="home")

    search = st.text_input("搜索产品", key="history_search", placeholder="输入产品名搜索")

    filter_col = st.segmented_control(
        "筛选",
        ["全部", "食品", "保健食品"],
        default="全部",
        key="history_filter",
        label_visibility="collapsed"
    ) or "全部"

    history = load_history()
    filtered = []
    for idx, item in enumerate(history):
        name = item.get("product_name", "")
        if search and search.lower() not in name.lower():
            continue
        if filter_col == "食品" and item.get("type") != "food":
            continue
        if filter_col == "保健食品" and item.get("type") != "supplement":
            continue
        filtered.append((idx, item))

    if not filtered:
        if not history:
            st.markdown(
                "<div style='text-align:center;padding:40px 20px;color:#9E9E9E;'>"
                "<div style='font-size:48px;margin-bottom:12px;'>📭</div>"
                "<p style='font-size:18px;'>还没有扫描记录</p>"
                "<p style='font-size:16px;'>去首页拍第一张配料表吧</p>"
                "</div>",
                unsafe_allow_html=True
            )
            if st.button("📷 开始扫描", type="primary", use_container_width=True):
                switch_page("scan")
        else:
            st.info("没有匹配的记录")
        return

    for idx, item in filtered:
        score = item.get("score", 0)
        color = "#43A047" if score >= 80 else ("#FF9800" if score >= 60 else "#E53935")
        label = "可食用" if score >= 80 else ("注意" if score >= 60 else "少吃")
        type_label = "保健食品" if item.get("type") == "supplement" else "食品"
        with st.container():
            cols = st.columns([1, 4, 1])
            with cols[0]:
                st.markdown(
                    f"<div class='history-list-score' style='background:{color}22;color:{color};'>{score}</div>",
                    unsafe_allow_html=True
                )
            with cols[1]:
                st.markdown(f"**{item.get('product_name', '未知')}**")
                st.caption(f"{label} · {type_label} · {item.get('timestamp', '')[:10]}")
            with cols[2]:
                if st.button("查看", key=f"hist_btn_{idx}"):
                    st.session_state["selected_history_index"] = idx
                    st.session_state["detail_fallback_record"] = item
                    switch_page("detail")
            st.markdown("<hr style='margin:8px 0;border:none;border-top:1px solid #f0f0f0;'>", unsafe_allow_html=True)


def render_detail_page():
    """产品详情页：读取 history_full.json 展示完整识别快照."""
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
        st.info("当时未保存完整配料信息，仅展示摘要。")

    render_top_nav("产品详情", back_target=st.session_state.get("prev_page", "home"))

    # 评分英雄区
    _render_score_hero(score, product_name, show_slow_replay=False)

    # 扫描信息卡片
    ts = fallback.get("timestamp", "") or record.get("timestamp", "")
    type_label = "保健食品" if fallback.get("type") == "supplement" else "食品"
    st.markdown(
        f"<div class='result-card'>"
        f"<div class='result-card-title'>扫描信息</div>"
        f"<div style='display:flex;gap:16px;'>"
        f"<div class='detail-image-placeholder' style='flex:1;'>图片未保存</div>"
        f"<div style='flex:2;display:flex;flex-direction:column;justify-content:center;'>"
        f"<p><b>扫描时间</b>：{ts}</p>"
        f"<p><b>识别引擎</b>：{MODEL_NAME}</p>"
        f"<p><b>产品类型</b>：{type_label}</p>"
        f"</div></div></div>",
        unsafe_allow_html=True
    )

    # 添加剂 / 营养 / 建议（复用 result 组件）
    if record:
        _render_additive_card(record.get("additives", []))
        render_nutrition_bars(record)
        advice = record.get("advice", "")
        if advice:
            st.markdown(f"<div class='result-card'><div class='result-card-title'>健康建议</div><p>{advice}</p></div>", unsafe_allow_html=True)
        # 全部配料
        ingredients = record.get("ingredients", [])
        if ingredients:
            st.markdown(
                f"<div class='result-card'><div class='result-card-title'>全部配料</div>"
                f"<p>{'、'.join(ingredients)}</p></div>",
                unsafe_allow_html=True
            )

    # 底部操作栏：仅保留已完成的「重新评分」
    if st.button("重新评分", use_container_width=True, key="detail_rescore"):
        switch_page("scan")


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
    inject_elder_css()

    # DEBUG 信息块：仅当环境变量 DEBUG=1 时显示，用于本地排查 API 配置
    # ⚠️ 生产环境（Streamlit Cloud）严禁设置 DEBUG=1，避免泄露 API key 信息
    if os.getenv("DEBUG") == "1":
        with st.expander("🔧 调试信息（DEBUG=1）", expanded=True):
            mimo_key = get_api_key("mimo")
            agnes_key = get_api_key("agnes")
            st.markdown(f"- **MiMo API URL**: `{API_URL}`")
            st.markdown(f"- **MiMo Model**: `{MODEL_NAME}`")
            st.markdown(f"- **MiMo API Key 长度**: {len(mimo_key)} / 末4位: `{mimo_key[-4:] if len(mimo_key) >= 4 else 'N/A'}`")
            st.markdown(f"- **Agnes API URL**: `{AGNES_API_URL}`")
            st.markdown(f"- **Agnes Model**: `{AGNES_MODEL_NAME}`")
            st.markdown(f"- **Agnes API Key 长度**: {len(agnes_key)} / 末4位: `{agnes_key[-4:] if len(agnes_key) >= 4 else 'N/A'}`")
            st.markdown("- **Auth Header 类型**: MiMo=`api-key`, Agnes=`Bearer`")

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
            if st.button("🏠 首页", use_container_width=True, key="sb_home"):
                switch_page("home")
        with c2:
            if st.button("📋 历史", use_container_width=True, key="sb_history"):
                switch_page("history")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("👤 健康档案", use_container_width=True, key="sb_profile"):
            switch_page("profile")
        st.divider()
        if os.getenv("DEBUG") == "1":
            with st.expander("高级设置"):
                if st.button("重新查看引导", use_container_width=True, key="replay_ob"):
                    st.session_state["onboarded"] = False
                    st.session_state["onboarding_step"] = 1
                    st.rerun()
                if "model_choice" not in st.session_state:
                    st.session_state["model_choice"] = "MiMo (mimo-v2.5)"
                model_choice = st.radio(
                    "选择识别模型",
                    ["MiMo (mimo-v2.5)", "Agnes (agnes-2.0-flash)"],
                    index=0 if st.session_state["model_choice"].startswith("MiMo") else 1,
                )
                st.session_state["model_choice"] = model_choice
        with st.expander("📄 法律声明"):
            st.caption("AI识别仅供参考，不构成医疗建议")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if st.button("查看用户协议", use_container_width=True, key="sb_ua"):
                st.session_state["page"] = "legal_ua"
                st.rerun()
            if st.button("查看隐私政策", use_container_width=True, key="sb_pp"):
                st.session_state["page"] = "legal_pp"
                st.rerun()
        st.divider()
        show_history()

    if page == "home":
        render_home_page()
    elif page == "scan":
        render_scan_page()
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
        base_dir = os.path.dirname(os.path.abspath(__file__))
        st.markdown(_load_markdown(os.path.join(base_dir, "USER_AGREEMENT.md")))
    elif page == "legal_pp":
        render_top_nav("隐私政策", back_target="home")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        st.markdown(_load_markdown(os.path.join(base_dir, "PRIVACY_POLICY.md")))
    else:
        st.session_state["page"] = "home"
        st.rerun()

    st.markdown(
        "<div class='disclaimer-text' style='text-align:center;margin-top:24px;'>AI识别仅供参考，请以包装原文为准</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
