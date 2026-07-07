"""AI食品配料表识别工具 - Streamlit Demo 优化版 v0.5.9
用途：上传配料表图片，调用 MiMo Vision API，展示识别结果
特性：适老化样式 + 语音播报 + 历史记录 + 健康档案 + 三端适配
运行环境：Python 3.10+
依赖：pip install streamlit requests pillow
运行命令：streamlit run app.py
"""

import base64
import csv
import html
import io
import json
import logging
import os
import re
import time
from datetime import datetime

from dotenv import load_dotenv

import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from utils.data import _load_markdown, load_gb2760_risk, load_health_data
from utils.helpers import detect_device_type, switch_page
from utils.history import add_history, load_history, load_history_full, save_history, save_history_full, show_history
from utils.score import (
    ADDITIVE_BLOCKLIST,
    C_LEVEL_DENSITY_PENALTY,
    C_LEVEL_DENSITY_THRESHOLD,
    SCORE_PENALTY,
    SUPPLEMENT_EXCIPIENTS,
    check_drug_food_conflicts,
    compute_score_from_additives,
    is_supplement_excipient,
    normalize_additive,
)
from utils.security import _safe

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

# MiMo Token Plan - 新加坡集群
API_URL = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions"
MODEL_NAME = "mimo-v2.5"

# Agnes 降級備用模型（僅在 MiMo 失敗時調用）
AGNES_API_URL = "https://api.agnes-ai.com/v1/chat/completions"
AGNES_MODEL_NAME = "agnes-20-flash"

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

_DATA_DIR = os.path.join(_BASE_DIR, "data")

# 建议文案模板（降低模型随机性，统一兜底）
ADVICE_TEMPLATES = {
    "default": "普通人群可适量食用，建议保持均衡饮食。",
    "糖尿病": "糖尿病患者请注意控制摄入量，具体请咨询医生或营养师。",
    "高血压": "高血压患者建议关注钠含量，具体请咨询医生或营养师。",
    "脑梗/心血管": "脑梗/心血管人群建议低脂低盐饮食，具体请咨询医生或营养师。",
    "减脂": "减脂人群建议关注糖分和脂肪含量，具体请咨询教练或营养师。",
    "过敏": "过敏体质请仔细核对配料，具体请咨询医生。",
    "孕妇/儿童": "孕妇及儿童人群请谨慎选择，具体请咨询医生或营养师。",
    "儿童": "儿童请谨慎选择，具体请咨询医生或营养师。",
    "孕妇": "孕妇请谨慎选择，具体请咨询医生或营养师。",
}

# 内联 SVG 图标（关键位置替代 emoji，保证跨平台一致）
_ICON_BACK = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M19 12H5M12 19l-7-7 7-7'/></svg>"
_ICON_HEART = "<svg class='icon-svg' viewBox='0 0 24 24' fill='currentColor'><path d='M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z'/></svg>"
_ICON_CAMERA = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><rect x='3' y='6' width='18' height='12' rx='2'/><circle cx='12' cy='13' r='3'/><path d='M8 6h8l-1-2h-6l-1 2z'/></svg>"
_ICON_HOME = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'/></svg>"
_ICON_SPEAKER = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/><path d='M15.54 8.46a5 5 0 010 7.07M19.07 4.93a10 10 0 010 14.14'/></svg>"
_ICON_HISTORY = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M3 7h18M3 12h18M3 17h18'/></svg>"
_ICON_PROFILE = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><circle cx='12' cy='8' r='4'/><path d='M4 20c0-4 4-6 8-6s8 2 8 6'/></svg>"
_ICON_CHECK = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polyline points='20 6 9 17 4 12'/></svg>"
_ICON_REFRESH = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M23 4v6h-6M1 20v-6h6'/><path d='M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15'/></svg>"
_ICON_SHARE = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><circle cx='18' cy='5' r='3'/><circle cx='6' cy='12' r='3'/><circle cx='18' cy='19' r='3'/><path d='M8.59 13.51l6.83 3.98M8.59 10.49l6.83-3.98'/></svg>"
_ICON_EMPTY = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M22 12h-6l-2 3h-4l-2-3H2'/><path d='M5.55 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.55-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.69.11z'/></svg>"
_ICON_FOOD = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M6 8a6 6 0 0 1 12 0c0 7-3 9-3 9H9s-3-2-3-9zm4.5 0V5a2.5 2.5 0 0 1 5 0v3'/><line x1='3' y1='21' x2='21' y2='21'/></svg>"
# 用于嵌入 JS 字符串的 SVG（单引号已转义）
_ICON_SPEAKER_JS = _ICON_SPEAKER.replace("'", "\\'")
_ICON_MUTE_JS = "<svg class='icon-svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polygon points='11 5 6 9 2 9 2 15 6 15 11 19 11 5'/><line x1='23' y1='9' x2='17' y2='15'/><line x1='17' y1='9' x2='23' y2='15'/></svg>".replace("'", "\\'")


# ========== 页面路由工具 ==========

def render_top_nav(title: str, show_back: bool = True, back_target: str = "home", right_action: str | None = None, align: str = "center"):
    """渲染顶部导航栏（标题居中/居左 + 返回按钮 + 右侧可选入口）.

    right_action 可选值："profile"（心形入口）、None。
    align 可选值："center"（默认）或 "left"（首页设计稿标题居左）。

    注意：用 st.container() 分组，CSS :has(.top-nav-title) 选择器应用 sticky 样式。
    """
    with st.container():
        cols = st.columns([1, 4, 1])
        with cols[0]:
            if show_back:
                if st.button(f"{_ICON_BACK} 返回", key=f"tn_back_{title}", help="返回"):
                    target = st.session_state.get("prev_page", back_target)
                    switch_page(target)
        with cols[1]:
            title_style = "text-align:left;" if align == "left" else "text-align:center;"
            st.markdown(f"<div class='top-nav-title' style='{title_style}'>{_safe(title)}</div>", unsafe_allow_html=True)
        with cols[2]:
            if right_action == "profile":
                if st.button(_ICON_HEART, key=f"tn_profile_{title}", help="健康档案"):
                    switch_page("profile")


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


# ========== 语音播报（浏览器原生，零依赖）==========

# 播报按钮全局递增 ID，避免时间戳冲突
_tts_counter = 0


def _next_tts_id(prefix: str) -> str:
    """生成唯一的 TTS 元素 ID."""
    global _tts_counter
    _tts_counter += 1
    return f"{prefix}-{_tts_counter}"


def _render_tts_namespace():
    """通过 iframe 注入全局语音播报命名空间与按钮事件绑定（幂等）.

    Streamlit 的 st.markdown 会过滤 <script>，导致脚本不执行；
    使用 st.components.v1.html 在隐藏 iframe 中执行脚本，并把函数挂到
    window.parent。

    关键兼容：Streamlit/React 在 hydration 时会剥离 HTML 元素的
    onclick="..." 字符串属性，因此按钮不能依赖内联 onclick。
    这里改为在父页面用 MutationObserver 自动发现带
    .food-scanner-tts-btn / .food-scanner-tts-stop-btn /
    .food-scanner-tts-replay-btn 类的元素，并通过 addEventListener 绑定点击
    事件，确保事件在用户手势同步路径中触发 speechSynthesis.speak()，同时
    避免 React hydration 剥离内联 onclick。
    """
    components.html(
        """
        <script>
        (function() {
            var parent = null;
            try {
                parent = window.parent;
                if (!parent || !parent.document || !parent.speechSynthesis) {
                    throw new Error('parent context unavailable');
                }
            } catch (e) {
                var fallback = {
                    speak: function() { alert('语音组件加载失败，请刷新页面后重试'); },
                    stop: function() {}
                };
                try { if (window.parent) window.parent.foodScannerTts = fallback; } catch(_) {}
                window.foodScannerTts = fallback;
                return;
            }

            function bindTtsButton(btn) {
                if (!btn || btn.__foodScannerTtsBound) return;
                btn.__foodScannerTtsBound = true;
                var action = btn.getAttribute('data-action') || 'speak';
                if (action === 'stop') {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        parent.foodScannerTts.stop();
                    });
                    return;
                }
                if (action === 'replay') {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        var scope = btn.closest('.result-score-hero') || parent.document;
                        var voiceBtn = scope.querySelector('.food-scanner-tts-btn');
                        if (voiceBtn) voiceBtn.click();
                    });
                    return;
                }
                var errId = btn.getAttribute('data-err-id') || '';
                var text = btn.getAttribute('data-text') || '';
                var rate = parseFloat(btn.getAttribute('data-rate') || '1.0') || 1.0;
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    parent.foodScannerTts.speak(btn.id, errId, text, rate);
                });
            }

            function bindAllTtsButtons() {
                var btns = parent.document.querySelectorAll('.food-scanner-tts-btn, .food-scanner-tts-stop-btn, .food-scanner-tts-replay-btn');
                for (var i = 0; i < btns.length; i++) {
                    bindTtsButton(btns[i]);
                }
            }

            parent.foodScannerTts = parent.foodScannerTts || {
                speak: function(btnId, errId, text, rate) {
                    var btn = parent.document.getElementById(btnId);
                    var err = parent.document.getElementById(errId);
                    var synth = parent.speechSynthesis;
                    if (!synth) {
                        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="voice-btn-icon">ICON_MUTE</span> 不支持播报'; }
                        if (err) err.textContent = '您的浏览器不支持语音播报功能';
                        return;
                    }
                    var originalHtml = btn ? btn.innerHTML : '';
                    if (btn) btn.innerHTML = '<span class="voice-btn-icon">ICON_SPEAKER</span> 播报中…';
                    if (err) err.textContent = '';

                    try { synth.cancel(); } catch(e) {}
                    try { synth.resume(); } catch(e) {}

                    var u = new parent.SpeechSynthesisUtterance(text);
                    u.lang = 'zh-CN';
                    u.rate = rate;
                    u.pitch = 1.0;
                    u.volume = 1.0;

                    var voices = synth.getVoices();
                    var selected = null;
                    for (var i = 0; i < voices.length; i++) {
                        var name = voices[i].name || '';
                        var lang = voices[i].lang || '';
                        if (name.indexOf('Yaoyao') >= 0 || name.indexOf('yaoyao') >= 0) {
                            selected = voices[i];
                            break;
                        }
                        if (!selected && (lang.indexOf('zh') === 0 || lang.indexOf('cmn') === 0)) {
                            selected = voices[i];
                        }
                    }
                    if (selected) u.voice = selected;

                    u.onend = function() {
                        if (btn) btn.innerHTML = originalHtml;
                        if (err) err.textContent = '';
                    };
                    u.onerror = function(e) {
                        if (btn) btn.innerHTML = originalHtml;
                        var errMsg = '播报失败，请尝试刷新页面或调高手机音量';
                        try {
                            var errType = (e && (e.error || e.type || e.message || '')).toString().toLowerCase();
                            if (errType.indexOf('not-allowed') >= 0 || errType.indexOf('notallowed') >= 0) {
                                errMsg = '浏览器阻止了语音播放，请刷新后点击页面任意位置再试';
                            }
                        } catch(_) {}
                        if (err) err.textContent = errMsg;
                        console.warn('[TTS error]', e);
                    };

                    try {
                        synth.speak(u);
                    } catch(e) {
                        if (btn) btn.innerHTML = originalHtml;
                        if (err) err.textContent = '播报失败，请刷新页面后重试';
                        console.warn('[TTS speak]', e);
                    }
                },
                stop: function() {
                    try { parent.speechSynthesis.cancel(); } catch(e) {}
                }
            };

            bindAllTtsButtons();

            try {
                var observer = new parent.MutationObserver(function(mutations) {
                    bindAllTtsButtons();
                });
                observer.observe(parent.document.body, { childList: true, subtree: true });
            } catch(e) {
                console.warn('[TTS observer]', e);
            }
        })();
        </script>
        """.replace("ICON_MUTE", _ICON_MUTE_JS).replace("ICON_SPEAKER", _ICON_SPEAKER_JS),
        height=0,
    )


def speak_text(text: str, rate: float = 1.0):
    """用浏览器原生 SpeechSynthesis API 播报中文语音.

    参数：
        text: 要播报的文本
        rate: 语速，0.7 慢速 / 1.0 正常 / 1.3 快速 / 0.75 慢速重播

    注意：手机浏览器要求语音播报必须由用户手势同步触发。
    此函数注入一个纯 HTML 按钮 + 全局 JS 函数调用，点击时直接在浏览器端
    调用 speechSynthesis.speak()，不经过 Python rerun，确保
    用户手势上下文不丢失。
    """
    rate = max(0.5, min(2.0, float(rate)))
    safe = _safe(text)
    btn_id = _next_tts_id("tts-simple-btn")
    err_id = _next_tts_id("tts-simple-err")
    _render_tts_namespace()
    js = (
        f"<div style='text-align:center;margin:12px 0;'>"
        f"<button id='{btn_id}' aria-label='语音播报识别结果' "
        f"class='food-scanner-tts-btn' data-err-id='{err_id}' data-text='{safe}' data-rate='{rate}' "
        f"style='font-size:20px;height:56px;padding:0 28px;border-radius:12px;"
        f"border:2px solid #2E7D32;background:#E8F5E9;color:#1B5E20;"
        f"font-weight:bold;cursor:pointer;min-width:200px;'>"
        f"{_ICON_SPEAKER} 点击播报</button>"
        f"<span id='{err_id}' class='tts-err' style='color:#D32F2F;font-size:14px;margin-left:8px;'></span>"
        f"</div>"
    )
    st.markdown(js, unsafe_allow_html=True)


def voice_control_panel(speak_content: str, key_prefix: str = "tts", button_text: str = f"{_ICON_SPEAKER} 点击播报", wrapper_class: str = "voice-control-wrap"):
    """语音播报控制面板：简洁版，主按钮+折叠的语速控制.

    使用浏览器原生 Web Speech API，针对 iOS Safari / 微信内置浏览器等
    移动端环境做了兼容处理：
    - 点击按钮时立即 cancel 并 speak，保证处于用户手势上下文。
    - 提供可视化反馈与明确的错误提示。

    wrapper_class: 外层 div 的 class，默认 voice-control-wrap；
    结果页可传 'voice-float-bar voice-control-wrap' 实现 sticky 浮动效果。
    """
    if "tts_rate" not in st.session_state:
        st.session_state["tts_rate"] = 1.0

    rate = st.session_state["tts_rate"]
    safe = _safe(speak_content)
    safe_button_text = _safe(button_text)
    btn_id = _next_tts_id(f"tts-btn-{key_prefix}")
    stop_btn_id = _next_tts_id(f"tts-stop-{key_prefix}")
    err_id = _next_tts_id(f"tts-err-{key_prefix}")

    _render_tts_namespace()
    html_block = (
        f"<div class='{wrapper_class}'>"
        f"<button id='{btn_id}' aria-label='语音播报识别结果' "
        f"class='food-scanner-tts-btn voice-float-btn' data-action='speak' "
        f"data-err-id='{err_id}' data-text='{safe}' data-rate='{rate}'>"
        f"{safe_button_text}</button>"
        f"<button id='{stop_btn_id}' class='food-scanner-tts-stop-btn voice-stop-btn' "
        f"data-action='stop' aria-label='停止播报'>停止</button>"
        f"<span id='{err_id}' class='tts-err'></span>"
        f"</div>"
    )
    st.markdown(html_block, unsafe_allow_html=True)

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


def _preload_tts_voices():
    """页面加载时预加载浏览器语音列表，提升首次点击播报成功率."""
    components.html(
        """
        <script>
        (function() {
            var parent = null;
            try {
                parent = window.parent;
                if (!parent || !parent.speechSynthesis) return;
            } catch(e) { return; }
            function loadVoices() {
                try { parent.speechSynthesis.getVoices(); } catch(e) {}
            }
            loadVoices();
            if (parent.speechSynthesis.onvoiceschanged !== undefined) {
                parent.speechSynthesis.onvoiceschanged = loadVoices;
            }
        })();
        </script>
        """,
        height=0,
    )


# ========== 核心函数（API 调用）==========

def get_api_key():
    """从环境变量或 secrets 读取 MiMo API 密钥.

    安全说明：
    - 本地开发使用 .env（已被 .gitignore 排除，禁止提交）；
    - 生产环境（Streamlit Cloud）必须使用 Settings → Secrets 配置，禁止在源码中写死 key；
    - 不要把真实 key 写入 README、issue、commit message 或聊天记录。
    """
    key = os.getenv("MIMO_API_KEY", "")
    if key:
        return key
    try:
        return st.secrets["MIMO_API_KEY"]
    except (KeyError, FileNotFoundError):
        return ""


def encode_image_to_base64(image_file, max_size=768):
    """压缩图片并转 base64：默认 768px、quality 75，兼顾速度与识别率."""
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75, optimize=True)
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
        "- additives: 只含 GB 2760 具体食品添加剂。**绝对不要**把以下基础配料列入：水、饮用水、白砂糖、白糖、冰糖、红糖、食用盐、食盐、食用油、植物油、菜籽油、花生油、面粉、小麦粉、大米、淀粉、食品用香精、食用香精、香精、酵母、蜂蜜、麦芽糖浆、果葡糖浆、葡萄糖浆。"
        "每个添加剂必须含 name（字符串），可选 code（INS/E号，没有留空）。additives 必须是数组，无添加剂时传 []。**不要输出 level 字段，不要给 score 评分，风险等级由系统判定。**\n"
        "- advice: 针对以下人群的一句话建议，使用固定句式：" + group_str + "。"
        "例如：普通人群可适量食用，建议保持均衡饮食；糖尿病患者请注意控制摄入量，具体请咨询医生或营养师。"
        "只输出一句，禁止医学疗效词。\n\n"
        "## 强制规则（两类产品都适用）\n"
        "- product_name **必须中文**，英文产品名翻译成中文或填'该产品'\n"
        "- 所有引用包装的内容（health_claims/suitable_for/usage）**严格按包装原文**，不评价、不推荐、不补全\n"
        "- 禁止任何医学疗效措辞：'治疗/疗效/降三高/防癌/增强免疫力+治愈'等\n"
        "- 所有健康相关结论以'请咨询医生/药师/营养师'收尾\n"
        "- 返回必须是纯 JSON 对象，不要数组、不要 Markdown、不要注释\n\n"
        "## 输出示例（仅供格式参考，不要返回多余说明）\n"
        "### 普通食品示例\n"
        '{"type":"food","product_name":"某牌苏打饼干","ingredients":["小麦粉","植物油","食用盐","碳酸氢钠","酵母"],'
        '"additives":[{"name":"碳酸氢钠","code":"500ii"}],'
        '"advice":"普通人群可适量食用，建议保持均衡饮食。"}\n'
        "### 保健食品示例\n"
        '{"type":"supplement","product_name":"某牌鱼油软胶囊","approval_no":"国食健注G20251234",'
        '"ingredients":["鱼油","明胶","甘油","纯化水"],'
        '"functional_ingredients":["每100g含EPA 18g、DHA 12g"],'
        '"health_claims":"辅助降血脂","suitable_for":"血脂偏高者","unsuitable_for":"少年儿童、孕妇、乳母",'
        '"usage":"每日2次，每次1粒，口服","storage":"置阴凉干燥处","shelf_life":"24个月",'
        '"summary":"鱼油软胶囊，每日2次每次1粒"}\n\n'
        "## 格式强制规则\n"
        "- 必须返回纯 JSON 对象，不要 Markdown 代码块，不要任何解释。\n"
        "- additives 数组中只允许出现 GB 2760 规定的食品添加剂名称，禁止出现食品原料、基础配料、保健品辅料。\n"
        "- 同一添加剂只出现一次，不要重复。\n"
        "- 不要输出 '未检出'、'无' 等文字，无添加剂时 additives 必须是空数组 []。\n"
    )


def call_api(api_key, image_b64, system_prompt, url=API_URL, model=MODEL_NAME):
    """调用多模态 API（默认 MiMo，可切換 Agnes），返回模型回复文本.

    Phase 4 (v0.2.5) 健壮性增强：
    - 最多 2 次指数退避重试（第1次等2秒，第2次等4秒）
    - 仅网络错误或 5xx 状态码才重试，4xx 直接返回不重试
    - 错误提示使用用户友好文案，不直接展示 resp.text
    - 原始错误信息仅在 DEBUG=1 时通过折叠区展示
    """

    def _err(msg, detail=""):
        """统一错误提示；DEBUG=1 时显示详情折叠区."""
        st.error(msg)
        if os.getenv("DEBUG") == "1" and detail:
            with st.expander("调试：错误详情"):
                st.code(detail)

    headers = {"api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": "请分析这张配料表图片，按规则返回 JSON。"}
            ]}
        ],
        "temperature": 0,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }

    # 日志：记录请求开始
    img_size_kb = len(image_b64) / 1024
    logger.info(f"API调用开始: model={model}, 图片大小={img_size_kb:.1f}KB")
    start_time = time.time()

    # 指数退避重试：1 次初始 + 最多 2 次重试 = 共 3 次
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        # ===== 发起请求 =====
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.Timeout:
            # 超时属于网络错误，可重试
            logger.warning(f"API请求超时: attempt={attempt}, timeout=30s")
            if attempt < max_attempts:
                time.sleep(2 ** attempt)  # attempt=1→2秒，attempt=2→4秒
                continue
            elapsed = time.time() - start_time
            logger.error(f"API调用失败: 超时, 总耗时={elapsed:.2f}s")
            _err(
                "识别服务暂时不可用，请稍后重试。",
                f"Timeout after 30s, attempts={attempt}"
            )
            return None
        except requests.exceptions.RequestException as e:
            # 连接错误/网络异常，可重试
            logger.warning(f"API网络错误: attempt={attempt}, error={str(e)[:200]}")
            if attempt < max_attempts:
                time.sleep(2 ** attempt)
                continue
            elapsed = time.time() - start_time
            logger.error(f"API调用失败: 网络错误, 总耗时={elapsed:.2f}s")
            _err(
                "网络连接失败，请检查网络后重试。",
                str(e)[:1000]
            )
            return None

        # ===== 收到 HTTP 响应 =====
        elapsed = time.time() - start_time
        if resp.status_code == 200:
            try:
                content = resp.json()["choices"][0]["message"]["content"]
                logger.info(f"API调用成功: status=200, 耗时={elapsed:.2f}s, 响应长度={len(content)}")
                return content
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                # 响应内容解析失败：不重试（重试也不会变好）
                logger.error(f"API响应解析失败: error={str(e)[:200]}")
                _err(
                    "识别结果解析失败，请重试。",
                    f"Parse error: {e}\n{resp.text[:1000]}"
                )
                return None

        # 4xx 客户端错误：不重试（API Key 无效、请求格式错误等）
        if 400 <= resp.status_code < 500:
            logger.error(f"API客户端错误: status={resp.status_code}, 耗时={elapsed:.2f}s")
            _err(
                "API 密钥无效或请求被拒绝，请检查密钥后重试。",
                f"HTTP {resp.status_code}\n{resp.text[:1000]}"
            )
            return None

        # 5xx 服务端错误：可重试
        logger.warning(f"API服务端错误: status={resp.status_code}, attempt={attempt}, 耗时={elapsed:.2f}s")
        if attempt < max_attempts:
            time.sleep(2 ** attempt)
            continue
        # 最后一次仍失败
        logger.error(f"API调用失败: 服务端错误, 总耗时={elapsed:.2f}s")
        _err(
            "识别服务暂时不可用，请稍后重试。",
            f"HTTP {resp.status_code}\n{resp.text[:1000]}"
        )
        return None

    return None


def call_api_with_fallback(mimo_key, image_b64, system_prompt, agnes_key=None):
    """先调用 MiMo，失败时降级到 Agnes.

    正常流程只调用 MiMo（3 秒），不增加延迟。
    仅当 MiMo 返回 None（超时/网络错误/5xx/4xx）且配置了 agnes_key 时，
    自动调用 Agnes 兜底，确保老人用户在 MiMo 故障时仍能得到结果。
    """
    raw = call_api(mimo_key, image_b64, system_prompt)
    if raw:
        return raw
    if agnes_key:
        logger.warning("MiMo 调用失败，降级到 Agnes 备用模型")
        st.toast("主识别服务繁忙，已自动切换备用服务", icon="🔄")
        return call_api(
            agnes_key, image_b64, system_prompt,
            url=AGNES_API_URL, model=AGNES_MODEL_NAME,
        )
    return None


def _clean_name(name) -> str:
    """清洗名称：去空白、去首尾标点，返回字符串."""
    if not isinstance(name, str):
        name = str(name)
    return name.strip().strip("，,、.;；")


def _is_blocklisted(name: str) -> bool:
    """判断名称是否为基础配料黑名单（避免误识别为添加剂）."""
    n = _clean_name(name)
    if not n:
        return True
    return n in ADDITIVE_BLOCKLIST


def normalize_model_output(raw: str) -> str:
    """把 MiMo 的原始返回统一成标准 JSON 字符串.

    职责：
    - 去掉 Markdown 代码块；
    - 字段别名映射（兼容可能的历史字段名）；
    - 类型修正：additives 强制 list、ingredients 字符串自动切分；
    - 过滤基础配料黑名单与异常条目；
    - product_name 英文时替换为「该产品」；
    - 删除模型自带的 score / level，统一由本地 GB2760 库判定。

    参数：
        raw: 模型原始返回文本

    返回：
        清洗后的 JSON 字符串；若解析失败则原样返回，让下游 parse_result 处理。
    """
    s = raw.strip()
    # 1) 去掉 Markdown 代码块
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].strip()

    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        return s

    if not isinstance(data, dict):
        return s

    # 2) 字段别名映射（保留少量兼容字段）
    alias_map = {
        "additive": "additives",
        "additive_list": "additives",
        "ingredient": "ingredients",
        "ingredient_list": "ingredients",
        "supplement_facts": "functional_ingredients",
        "health_function": "health_claims",
        "functions": "health_claims",
        "applicant": "suitable_for",
        "target": "suitable_for",
        "contraindication": "unsuitable_for",
        "nutrition": "nutrition_nrv",
        "nrv": "nutrition_nrv",
        "营养成分": "nutrition_nrv",
    }
    for old_key, new_key in alias_map.items():
        if old_key in data and new_key not in data:
            data[new_key] = data.pop(old_key)

    # 3) 类型修正与兜底
    if "additives" in data and not isinstance(data["additives"], list):
        data["additives"] = []
    if "ingredients" in data:
        if isinstance(data["ingredients"], str):
            data["ingredients"] = [
                x.strip()
                for x in re.split(r"[,，、;；]", data["ingredients"])
                if x.strip()
            ]
        elif not isinstance(data["ingredients"], list):
            data["ingredients"] = []
    if "functional_ingredients" in data and isinstance(data["functional_ingredients"], str):
        data["functional_ingredients"] = [data["functional_ingredients"].strip()]

    # 4) product_name 强制中文，英文替换为「该产品」
    if "product_name" in data:
        name = data["product_name"]
        if not isinstance(name, str):
            name = str(name)
        name = name.strip()
        is_english_name = re.fullmatch(r"[A-Za-z\s\-.&]+", name)
        if not name or is_english_name:
            name = "该产品"
        data["product_name"] = name

    # 5) 过滤 additives：去掉黑名单基础配料、空名称、过长/过短条目
    if isinstance(data.get("additives"), list):
        cleaned = []
        for a in data["additives"]:
            if not isinstance(a, dict):
                continue
            a.pop("level", None)
            a.pop("score", None)
            n = _clean_name(a.get("name", ""))
            if not n or len(n) < 2 or len(n) > 30 or _is_blocklisted(n):
                continue
            a["name"] = n
            cleaned.append(a)
        data["additives"] = cleaned

    # 6) 删除模型自带评分
    data.pop("score", None)

    return json.dumps(data, ensure_ascii=False)


def _generate_advice(health_groups):
    """根据 health_groups 返回固定模板建议，降低模型随机性."""
    groups = health_groups or []
    matched = [g for g in groups if g in ADVICE_TEMPLATES]
    if matched:
        return " ".join(ADVICE_TEMPLATES[g] for g in matched)
    return ADVICE_TEMPLATES["default"]


def parse_result(raw, health_groups=None):
    """解析模型返回的 JSON 文本，并对 type=food 强制按 GB 2760 库覆盖 level 和 score.

    返回：解析成功返回 dict，失败返回 None（不直接调用 st.error，由调用方处理）。
    """
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        result = json.loads(s)
    except json.JSONDecodeError:
        return None
    if not isinstance(result, dict):
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
        # advice 兜底：若为空或包含禁用词，用本地模板替换
        advice = str(result.get("advice", "")).strip()
        if not advice or any(w in advice for w in ["治疗", "疗效", "降三高", "防癌", "治愈"]):
            advice = _generate_advice(health_groups)
        result["advice"] = advice
    return result


# ========== 客户端权威判定（GB 2760 库 + 药物冲突）==========

def is_supplement_excipient(name: str) -> bool:
    """判断是否为保健品辅料（不扣分）."""
    n = str(name).strip()
    return n in SUPPLEMENT_EXCIPIENTS or any(k in n for k in ["胶囊壳", "软胶囊"])


def normalize_additive(name):
    """查 GB 2760 风险库返回 (level, ins_no, note)，未匹配默认 B 兜底."""
    if not name:
        return "B", "", ""
    n = str(name).strip()
    # 基础配料黑名单：不应被识别为添加剂，直接判 A
    if _is_blocklisted(n):
        return "A", "", "基础配料，不扣分"
    # 保健品辅料豁免
    if is_supplement_excipient(n):
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
    公式: 100 - 红×25 - 黄×8 - 特殊人群命中额外扣 4 - C级密度扣分."""
    if not additives:
        return 100
    score = 100
    health_set = set(health_groups or [])
    risk = load_gb2760_risk()
    c_level_count = 0
    for a in additives:
        if not isinstance(a, dict):
            continue
        name = a.get("name", "")
        level, _, _ = normalize_additive(name)
        score -= SCORE_PENALTY.get(level, 0)
        if level == "C":
            c_level_count += 1
        # 特殊人群敏感性（如糖尿病/高血压 + 命中 warnings）
        if name in risk:
            warnings = risk[name].get("warnings", "")
            if warnings and any(w in health_set for w in warnings.split("/")):
                score -= 4
    # C 级密度惩罚：高风险添加剂过多时额外扣分
    if c_level_count >= C_LEVEL_DENSITY_THRESHOLD:
        score -= C_LEVEL_DENSITY_PENALTY
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


# ========== 结果页通用组件 ==========

def _get_level_info(level: str) -> tuple[str, str, str]:
    """统一返回添加剂等级信息：标签、颜色、形状图标."""
    mapping = {
        "A": ("可食用", "#43A047", "●"),
        "green": ("可食用", "#43A047", "●"),
        "B": ("特定人群注意", "#FF9800", "▲"),
        "yellow": ("特定人群注意", "#FF9800", "▲"),
        "C": ("建议少吃", "#E53935", "■"),
        "red": ("建议少吃", "#E53935", "■"),
    }
    return mapping.get(level, ("未知", "#9E9E9E", "●"))


def _render_score_hero(score: int, product_name: str, show_slow_replay: bool = True):
    """渲染评分英雄区（按画布设计稿：纯色卡片 + 装饰圆点 + 慢速重听）."""
    if score >= 80:
        _, label, bg = "#43A047", "可放心食用", "#43A047"
        meaning = "添加剂少，适合日常食用"
    elif score >= 60:
        _, label, bg = "#FF9800", "特定人群注意", "#FF9800"
        meaning = "含少量需注意的成分"
    else:
        _, label, bg = "#E53935", "建议咨询医生", "#E53935"
        meaning = "添加剂较多，请谨慎选择"
    shape = "●" if score >= 80 else ("▲" if score >= 60 else "■")
    clip = (
        "polygon(50% 0%, 0% 100%, 100% 100%)" if shape == "▲"
        else "polygon(0 0, 100% 0, 100% 100%, 0 100%)" if shape == "■"
        else "circle(50%)"
    )
    replay_btn = ""
    if show_slow_replay:
        replay_id = f"slow-replay-{score}"
        replay_btn = (
            f"<button id='{replay_id}' class='score-replay-btn food-scanner-tts-replay-btn' "
            f"data-action='replay' aria-label='慢速重听'>"
            f"<span>🔁</span> 慢速重听</button>"
        )
    st.markdown(
        f"<div class='result-score-hero' style='background:{bg};'>"
        f"<div class='result-score-hero-deco result-score-hero-deco-tl'></div>"
        f"<div class='result-score-hero-deco result-score-hero-deco-br'></div>"
        f"<div class='result-score-hero-product'>{_safe(product_name)}</div>"
        f"<div class='result-score-hero-number'>{score}</div>"
        f"<div class='result-score-hero-label'>"
        f"<span class='result-score-shape' style='background:#FFFFFF;clip-path:{clip};'></span>"
        f"{_safe(label)}</div>"
        f"<div class='result-score-meaning'>{_safe(meaning)}</div>"
        f"{replay_btn}"
        f"</div>",
        unsafe_allow_html=True
    )


def _render_additive_card(additives):
    """渲染添加剂清单卡片（画布设计稿：图标 + 名称/类别 + 标签 + 色盲图例）."""
    if not additives:
        st.markdown(
            "<div class='result-card'><div class='result-card-title'>🧪 添加剂清单</div>"
            "<p style='color:#666;'>未识别到需要关注的食品添加剂</p></div>",
            unsafe_allow_html=True,
        )
        return
    html = (
        "<div class='result-card'>"
        "<div class='result-card-title'>🧪 添加剂清单</div>"
        "<div class='result-additive-list'>"
    )
    for item in additives:
        name = _safe(item.get("name", "未知"))
        level = item.get("level", "B")
        note = _safe(item.get("note", ""))
        label, color, shape = _get_level_info(level)
        label = _safe(label)
        clip = (
            "polygon(50% 0%, 0% 100%, 100% 100%)" if shape == "▲"
            else "polygon(0 0, 100% 0, 100% 100%, 0 100%)" if shape == "■"
            else "circle(50%)"
        )
        note_html = f"<div class='result-additive-note'>{note}</div>" if note else ""
        html += (
            f"<div class='result-additive-item' style='border-left-color:{color};'>"
            f"<span class='result-additive-shape' style='background:{color};clip-path:{clip};'></span>"
            f"<div class='result-additive-body'>"
            f"<div class='result-additive-name'>{name}</div>"
            f"{note_html}"
            f"</div>"
            f"<span class='result-additive-level' style='color:{color};border-color:{color};background:{color}11;'>{label}</span>"
            f"</div>"
        )
    html += (
        "</div>"
        "<div class='result-additive-legend'>"
        "<div class='legend-item'><span class='legend-shape' style='background:#43A047;clip-path:circle(50%);'></span><span>圆=安全</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#FF9800;clip-path:polygon(50% 0%,0% 100%,100% 100%);'></span><span>三角=中等</span></div>"
        "<div class='legend-item'><span class='legend-shape' style='background:#E53935;clip-path:polygon(0 0,100% 0,100% 100%,0 100%);'></span><span>方块=高风险</span></div>"
        "</div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


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
    st.markdown(
        "<div class='result-card'>"
        "<div class='result-card-title'>📊 营养成分</div>",
        unsafe_allow_html=True,
    )
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
            f"<span class='nrv-bar-name'>{_safe(name)} <small>({level_text})</small></span>"
            f"<span class='nrv-bar-value' style='color:{bar_color};'>{pct:.0f}%</span>"
            f"</div>"
            f"<div class='nrv-bar-track'>"
            f"<div class='nrv-bar-fill' style='width:{pct_clamped:.0f}%;background:{bar_color};'></div>"
            f"</div>"
            f"<div class='nrv-bar-caption'>占每日推荐摄入量 <strong style='color:{bar_color};'>{pct:.0f}%</strong></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


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
