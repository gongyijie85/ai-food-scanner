"""
AI食品配料表识别工具 - Streamlit Demo 优化版 v0.2.6
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

import requests
import streamlit as st
from PIL import Image


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


# ========== 适老化样式 ==========

def inject_elder_css():
    """注入适老化 CSS：大字体、大按钮、高对比度."""
    st.markdown(
        """
        <style>
        /* 全局字体放大 */
        .stApp { font-size: 18px; }
        h1 { font-size: 32px !important; }
        h2 { font-size: 26px !important; }
        h3 { font-size: 22px !important; }

        /* 按钮放大 */
        .stButton > button {
            font-size: 20px !important;
            height: 56px !important;
            border-radius: 12px !important;
            font-weight: bold !important;
        }

        /* 输入框放大 */
        .stTextInput input, .stTextArea textarea {
            font-size: 18px !important;
        }

        /* 评分色块：默认深色文字，避免黄底白字对比度不足 */
        .score-box {
            padding: 24px; border-radius: 16px; text-align: center;
            color: #333333; margin: 12px 0;
            display: flex; align-items: center; justify-content: center; gap: 16px;
        }
        .score-num { font-size: 56px; font-weight: bold; }
        .score-label { font-size: 22px; }
        /* 评分等级形状图标（色盲友好：圆/三角/方块）*/
        .score-shape {
            font-size: 56px; line-height: 1; font-weight: bold;
            display: inline-block; min-width: 64px;
        }

        /* 添加剂卡片：色盲友好三重编码（颜色+形状+文字）*/
        .additive-row {
            display: flex; justify-content: space-between;
            align-items: center; padding: 14px 16px;
            border-radius: 10px; margin: 6px 0;
            background: #FAFAF5; font-size: 18px;
        }
        .additive-shape {
            display: inline-block; width: 36px; height: 36px;
            font-size: 28px; line-height: 36px; text-align: center;
            margin-right: 10px; vertical-align: middle; font-weight: bold;
        }
        .additive-level {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 6px 12px; border-radius: 8px; font-weight: bold;
            color: #333333;
        }

        /* 健康档案：大复选框 32px + 绿色边框反馈 */
        .stCheckbox {
            padding: 8px 0;
        }
        .stCheckbox > label {
            font-size: 20px !important;
        }
        .stCheckbox > label > div {
            min-width: 32px !important; min-height: 32px !important;
        }

        /* 首页大圆形扫描按钮 */
        .scan-circle-btn {
            display: block; width: 200px; height: 200px; margin: 24px auto;
            border-radius: 50%; background: linear-gradient(135deg, #43A047, #2E7D32);
            color: white; font-size: 24px; font-weight: bold; text-align: center;
            line-height: 200px; box-shadow: 0 6px 20px rgba(67,160,71,0.4);
            cursor: pointer; border: none;
        }
        .scan-circle-btn:hover { transform: scale(1.05); }

        /* 营养成分可视化条 */
        .nrv-bar-wrap {
            margin: 10px 0; padding: 8px 0;
        }
        .nrv-bar-label {
            display: flex; justify-content: space-between;
            font-size: 18px; margin-bottom: 4px; color: #333;
        }
        .nrv-bar-track {
            width: 100%; height: 24px; background: #E0E0E0;
            border-radius: 12px; overflow: hidden;
        }
        .nrv-bar-fill {
            height: 100%; border-radius: 12px;
            transition: width 0.3s;
        }

        /* 底部固定语音按钮 */
        .sticky-voice-bar {
            position: sticky; bottom: 0; left: 0; right: 0;
            background: #fff; padding: 12px 16px;
            border-top: 2px solid #43A047; z-index: 100;
            box-shadow: 0 -4px 12px rgba(0,0,0,0.08);
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
    """
    # 限制 rate 范围，避免极端值
    rate = max(0.5, min(2.0, float(rate)))
    # 转义文本中的特殊字符，防止 JS 注入
    safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
    js = f"""
    <script>
    (function() {{
        function pickZhVoice() {{
            var voices = speechSynthesis.getVoices();
            if (!voices || voices.length === 0) return null;
            // 优先级：Microsoft Yaoyao（年轻女声）→ Huihui → Google 普通话 → 任意 zh-CN → 任意 zh
            var pref = voices.find(v => v.name.indexOf('Yaoyao') >= 0);
            if (pref) return pref;
            pref = voices.find(v => v.name.indexOf('Huihui') >= 0);
            if (pref) return pref;
            pref = voices.find(v => v.name.indexOf('Google') >= 0 && v.lang === 'zh-CN');
            if (pref) return pref;
            pref = voices.find(v => v.lang === 'zh-CN');
            if (pref) return pref;
            return voices.find(v => v.lang.indexOf('zh') === 0);
        }}
        function trySpeak(attempt) {{
            attempt = attempt || 0;
            var u = new SpeechSynthesisUtterance('{safe}');
            u.lang = 'zh-CN';
            u.rate = {rate};
            u.pitch = 1.0;
            u.volume = 1.0;
            var v = pickZhVoice();
            if (v) u.voice = v;
            speechSynthesis.cancel();
            speechSynthesis.speak(u);
            // 调试日志（不影响功能）
            console.log('[speak] attempt=' + attempt + ' voice=' + (v ? v.name : 'default') + ' rate=' + {rate} + ' text=' + '{safe}'.slice(0, 30));
        }}
        // 第一次立刻尝试，voices 没加载完就等
        if (speechSynthesis.getVoices().length > 0) {{
            trySpeak(0);
        }} else {{
            speechSynthesis.addEventListener('voiceschanged', function once() {{
                speechSynthesis.removeEventListener('voiceschanged', once);
                trySpeak(0);
            }});
            // 兜底：500ms 后强制尝试一次
            setTimeout(function() {{ trySpeak(1); }}, 500);
        }}
    }})();
    </script>
    """
    st.components.v1.html(js, height=0)


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
    st.components.v1.html(js, height=0)


def voice_control_panel(speak_content: str, key_prefix: str = "tts"):
    """语音播报控制面板：语速选择 + 暂停/继续/重播/慢速重播按钮.

    参数：
        speak_content: 要播报的文本
        key_prefix: 按钮唯一 key 前缀（避免不同结果页冲突）
    """
    # 初始化 session_state：记忆语速
    if "tts_rate" not in st.session_state:
        st.session_state["tts_rate"] = 1.0

    st.markdown("#### 🔊 语音播报控制")
    # 语速选择（横排三选一）
    rate_options = ["0.7x 慢速", "1.0x 正常", "1.3x 快速"]
    rate_values = [0.7, 1.0, 1.3]
    cur_idx = 1  # 默认 1.0x
    try:
        cur_idx = rate_values.index(st.session_state["tts_rate"])
    except ValueError:
        cur_idx = 1
    chosen = st.radio(
        "语速",
        rate_options,
        index=cur_idx,
        horizontal=True,
        key=f"{key_prefix}_rate_radio",
        label_visibility="collapsed",
    )
    # 同步到 session_state
    st.session_state["tts_rate"] = rate_values[rate_options.index(chosen)]

    # 4 个控制按钮，4 列排布（适老化大按钮）
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("▶️ 重播", key=f"{key_prefix}_replay", use_container_width=True):
            speak_text(speak_content, rate=st.session_state["tts_rate"])
    with c2:
        if st.button("🐢 慢速重播", key=f"{key_prefix}_slow", use_container_width=True):
            speak_text(speak_content, rate=0.75)
    with c3:
        if st.button("⏸️ 暂停", key=f"{key_prefix}_pause", use_container_width=True):
            _js_speech_control("pause")
    with c4:
        if st.button("▶ 继续播放", key=f"{key_prefix}_resume", use_container_width=True):
            _js_speech_control("resume")


# ========== 核心函数（API 调用）==========

def get_api_key(model="mimo"):
    """从环境变量或 secrets 读取 API 密钥，按模型选不同变量名."""
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


# ========== 结果展示 ==========

def render_food(result):
    """展示普通食品结果（评分 + 添加剂红绿灯 + 建议）."""
    score = result.get("score", 0)
    if score >= 80:
        color, label = "#43A047", "较常见"
    elif score >= 60:
        color, label = "#FF9800", "特定人群建议关注"
    else:
        color, label = "#E53935", "建议咨询专业人士"

    # AI 识别不确定性提示
    st.warning("AI 识别可能存在错误，请以包装原文为准。")

    # 评分大色块（橙色背景用深色文字保证对比度；附形状图标色盲友好）
    text_color = "#333333" if color == "#FF9800" else "white"
    # 形状图标：A 绿圆 ● / B 橙三角 ▲ / C 红方块 ■（色盲友好三重编码）
    if score >= 80:
        shape_icon = "●"
    elif score >= 60:
        shape_icon = "▲"
    else:
        shape_icon = "■"
    st.markdown(
        f"<div class='score-box' style='background:{color};color:{text_color};'>"
        f"<div class='score-shape'>{shape_icon}</div>"
        f"<div><div class='score-num'>{score}</div>"
        f"<div class='score-label'>{label}</div></div></div>",
        unsafe_allow_html=True
    )
    st.caption("评分仅供参考，不构成安全判断。")

    # 产品名 + 健康建议
    st.markdown(f"### {result.get('product_name', '未知')}")
    advice = result.get("advice", "")
    if advice:
        st.info(f"健康建议：{advice}")

    # 语音播报：自动播报 + 控制面板（语速 / 暂停 / 重播 / 慢速重播）
    speak_content = f"评分{score}分，{label}。{advice}本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生/药师/营养师。"
    st.session_state["last_speak_content"] = speak_content
    # 自动播报：用 product_name + score 作为唯一 key，避免 rerun 重复播报
    result_key = f"food_{result.get('product_name', '')}_{score}"
    if st.session_state.get("last_spoken_key") != result_key:
        st.session_state["last_spoken_key"] = result_key
        speak_text(speak_content, rate=st.session_state.get("tts_rate", 1.0))
    voice_control_panel(speak_content, key_prefix="tts_food")

    st.divider()

    # 添加剂清单（色盲友好：颜色+形状+文字三重编码）
    st.markdown("### 食品添加剂")
    st.caption("在 GB 2760 合规使用范围内是安全的；以下为科普化展示，仅供参考。")
    additives = result.get("additives", [])
    # level_map：等级 → (标签, 背景色, 形状图标)
    level_map = {
        "green": ("较常见", "#43A047", "●"),
        "A": ("较常见", "#43A047", "●"),
        "yellow": ("特定人群建议关注", "#FF9800", "▲"),
        "B": ("特定人群建议关注", "#FF9800", "▲"),
        "red": ("建议咨询专业人士", "#E53935", "■"),
        "C": ("建议咨询专业人士", "#E53935", "■"),
    }
    if additives:
        for item in additives:
            name = item.get("name", "未知")
            code = item.get("code", "")
            level = item.get("level", "")
            lv_label, lv_color, lv_shape = level_map.get(level, (level, "#888", "●"))
            st.markdown(
                f"<div class='additive-row'>"
                f"<span><b>{name}</b>{f' ({code})' if code else ''}<br>"
                f"<small style='color:#666;'>在 GB 2760 合规使用范围内是安全的。</small></span>"
                f"<span class='additive-level' style='background:{lv_color}33; border:2px solid {lv_color};'>"
                f"<span class='additive-shape' style='color:{lv_color};'>{lv_shape}</span>"
                f"<span style='color:{lv_color};'>{lv_label}</span>"
                f"</span></div>",
                unsafe_allow_html=True
            )
    else:
        st.success("未识别到食品添加剂")
    st.caption("数据来源：GB 2760-2024")

    st.divider()

    # 全部配料
    ingredients = result.get("ingredients", [])
    if ingredients:
        st.markdown("### 全部配料")
        st.write("、".join(ingredients))

    # 营养成分可视化条（Task 10.3，仅当识别结果含 NRV 数据时显示）
    render_nutrition_bars(result)

    # 个性化警告：药物-食物冲突 + 过敏原匹配
    render_personal_warnings(result, ingredients)

    # 原始 JSON
    with st.expander("查看原始 JSON"):
        st.json(result)

    # 底部固定语音按钮（Task 10.4）：复用 last_speak_content
    last_speak = st.session_state.get("last_speak_content", "")
    if last_speak:
        st.markdown("<div class='sticky-voice-bar'>", unsafe_allow_html=True)
        if st.button("🔊 再听一遍结果", key="tts_sticky_replay", use_container_width=True):
            speak_text(last_speak, rate=st.session_state.get("tts_rate", 1.0))
        st.markdown("</div>", unsafe_allow_html=True)


def render_personal_warnings(result, ingredients):
    """根据用户健康档案个性化警告（药物-食物冲突 + 过敏原匹配）."""
    user_profile = st.session_state.get("user_profile", {})
    user_drugs = user_profile.get("drugs", [])
    user_allergens = user_profile.get("allergens", [])

    if not user_drugs and not user_allergens:
        return  # 没有档案数据，跳过

    has_warning = False

    # 1. 药物-食物冲突
    if user_drugs:
        conflicts = check_drug_food_conflicts(ingredients, user_drugs)
        if conflicts:
            has_warning = True
            st.warning("检测到您正在服用的药物与配料中某些成分可能存在关联，仅供参考。")
            # 按药物分组展示
            grouped = {}
            for c in conflicts:
                grouped.setdefault(c["drug"], []).append(c)
            for drug, items in grouped.items():
                food_names = "、".join(sorted({c["matched_keyword"] for c in items}))
                with st.expander(f"{drug} 与 {food_names}（建议关注）"):
                    st.markdown(
                        f"{drug} 与 {food_names} 可能存在相互作用，"
                        "具体用药方案请咨询医生或药师。"
                    )
                    st.caption(f"数据来源：{items[0].get('source', '')}")
            st.warning("本工具不提供用药建议。")

    # 2. 过敏原匹配
    if user_allergens:
        health_data = load_health_data()
        allergen_warnings = []
        all_ingredient_text = " ".join(ingredients) + " " + " ".join(
            a.get("name", "") for a in result.get("additives", [])
        )
        for allergen in user_allergens:
            # allergen 是 dict {code, name, examples}
            if allergen.get("name") in all_ingredient_text:
                allergen_warnings.append(allergen)
                continue
            for ex in allergen.get("examples", []):
                if ex in all_ingredient_text:
                    allergen_warnings.append({**allergen, "matched": ex})
                    break
        if allergen_warnings:
            has_warning = True
            st.warning(f"⚠️ 检测到 {len(allergen_warnings)} 个过敏原")
            st.warning("配料表识别可能遗漏致敏物质，严重过敏者请勿仅依赖本工具。")
            for a in allergen_warnings:
                matched = a.get("matched", a.get("name"))
                st.markdown(f"- **{a.get('name')}**（匹配关键词：{matched}）")

    if not has_warning and (user_drugs or user_allergens):
        st.success("✅ 您当前用药/过敏原与本食品无冲突")


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
    """展示保健食品结果（只翻译包装信息，不评价、不推荐，强制免责声明）."""
    # 顶部固定：红条强制免责
    st.markdown(
        "<div style='background:#E53935;color:#fff;padding:14px 16px;"
        "border-radius:8px;font-size:18px;font-weight:bold;margin-bottom:14px;'>"
        "⚠️ 本产品为保健食品<br>保健食品不是药物，不能代替药物治疗疾病<br>"
        "内容为包装原文摘录，不代表本工具立场；AI 识别可能存在错误，请以包装原文为准。"
        "</div>",
        unsafe_allow_html=True
    )

    # 产品名 + 一句话事实摘要
    st.markdown(f"### 💊 {result.get('product_name', '未知')}")
    summary = result.get("summary", "")
    if summary:
        st.info(f"📦 {summary}")

    # 语音播报：仅朗读事实 + 强制免责（自动播报 + 控制面板）
    speak_content = (
        f"保健食品：{result.get('product_name', '未知')}。"
        f"{summary}。"
        f"保健食品不是药物，不能代替药物治疗疾病。"
        f"如需选择，请咨询医生/药师/营养师。"
    )
    st.session_state["last_speak_content"] = speak_content
    # 自动播报：用 product_name + summary 作为唯一 key，避免 rerun 重复播报
    result_key = f"supp_{result.get('product_name', '')}_{summary}"
    if st.session_state.get("last_spoken_key") != result_key:
        st.session_state["last_spoken_key"] = result_key
        speak_text(speak_content, rate=st.session_state.get("tts_rate", 1.0))
    voice_control_panel(speak_content, key_prefix="tts_supp")

    st.divider()

    # 批准文号 / 备案号
    approval_no = result.get("approval_no", "未显示")
    st.markdown("### 🏛️ 批准文号（据包装）")
    st.code(approval_no, language=None)

    # 标志性成分 / 功效成分
    functional = result.get("functional_ingredients", [])
    if functional:
        st.markdown("### 🧪 标志性成分及含量（据包装）")
        for item in functional:
            st.markdown(f"- {item}")

    # 保健功能
    st.markdown("### 💡 保健功能（据包装原文）")
    st.warning(result.get("health_claims", "未显示"))

    # 适宜 / 不适宜人群
    st.markdown("### ✅ 适宜人群（据包装原文）")
    st.success(result.get("suitable_for", "未显示"))
    st.markdown("### ❌ 不适宜人群（据包装原文）")
    st.error(result.get("unsuitable_for", "未显示"))

    # 食用方法及食用量
    st.markdown("### 💊 食用方法及食用量（据包装原文）")
    st.info(result.get("usage", "未显示"))

    # 贮藏 + 保质期
    storage = result.get("storage", "")
    shelf_life = result.get("shelf_life", "")
    if storage or shelf_life:
        st.markdown("### 📅 贮藏与保质期（据包装）")
        if storage:
            st.markdown(f"**贮藏**：{storage}")
        if shelf_life:
            st.markdown(f"**保质期**：{shelf_life}")

    st.divider()

    # 全部配料 / 原料
    ingredients = result.get("ingredients", [])
    if ingredients:
        st.markdown("### 📋 全部原料（据包装）")
        st.write("、".join(ingredients))

    # 原始 JSON
    with st.expander("查看原始 JSON"):
        st.json(result)

    # 底部固定：再次免责 + 建议咨询医生/药师/营养师
    st.markdown(
        "<div style='background:#FFF3E0;border-left:6px solid #E53935;"
        "padding:12px 16px;border-radius:6px;margin-top:14px;'>"
        "<b>❗ 重要提醒</b><br>"
        "本工具仅翻译包装内容，<b>不评价</b>该产品是否适合您。<br>"
        "选购或服用前，请<b>咨询医生/药师/营养师</b>。"
        "</div>",
        unsafe_allow_html=True
    )


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
    """健康档案：基本信息 + 基础疾病 + 过敏原 + 当前用药 + 档案摘要.
    数据来源：data/common_diseases.json + allergens.json + common_drugs.json（GB 7718 / NMPA 权威）."""
    st.markdown("## 👤 我的健康档案")
    st.caption("填写档案后，识别结果会按您的健康情况给个性化建议（包括药物-食物冲突）")
    st.warning(
        "疾病、过敏原、用药属于敏感个人信息，填写即表示您同意我们按《隐私政策》处理这些信息。"
    )
    st.info(
        "Demo 提示：本工具为公开技术展示，建议不要输入真实姓名、身份证号、详细病史等真实个人信息；"
        "健康档案仅在当前浏览器会话中使用，关闭页面后自动清空。"
    )

    # 初始化 session_state
    if "health_profile" not in st.session_state:
        st.session_state["health_profile"] = {
            "name": "",
            "age": 60,
            "diseases": [],   # 改：原 groups → 改用结构化疾病 ID 列表
            "allergens": [],  # 改：原 allergies 文本 → 改用结构化过敏原
            "drugs": [],      # 改：原 medications 文本 → 改用结构化药物
        }
    if "user_profile" not in st.session_state:
        # user_profile 是 render_personal_warnings 用的结构化数据
        st.session_state["user_profile"] = {
            "drugs": [],     # [{id, name, category}]
            "allergens": [], # [{code, name, examples}]
        }
    profile = st.session_state["health_profile"]
    health_data = load_health_data()
    diseases = health_data.get("diseases", [])
    allergens = health_data.get("allergens", [])
    drug_categories = health_data.get("drugs", [])

    # ===== 基本信息 =====
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

    # ===== 基础疾病（多分类多选 + 一键组合）=====
    st.markdown("### 🏥 基础疾病（可多选）")
    st.caption("数据来源：ICD-10 + 国家慢病防治指南，按系统分类")
    if diseases:
        # 把所有疾病拍平为 (id, name) 列表，便于 multiselect
        all_disease_options = []
        for cat in diseases:
            for d in cat.get("diseases", []):
                all_disease_options.append(d["name"])
        # 一键组合按钮（Task 9.2）：点击后填入对应疾病组合
        st.markdown("**一键选择常见组合：**")
        cb1, cb2, cb3 = st.columns(3)
        with cb1:
            if st.button("💔 我有三高", key="combo_sangao", use_container_width=True,
                         help="高血压 + 高脂血症 + 2型糖尿病"):
                st.session_state["hp_diseases"] = ["高血压", "高脂血症", "2型糖尿病"]
                st.rerun()
        with cb2:
            if st.button("🧠 脑梗/心血管", key="combo_naogeng", use_container_width=True,
                         help="高血压 + 脑梗死 + 冠心病（默认档案）"):
                st.session_state["hp_diseases"] = ["高血压", "脑梗死", "冠心病"]
                st.rerun()
        with cb3:
            if st.button("🗑️ 清空疾病", key="combo_clear_dis", use_container_width=True):
                st.session_state["hp_diseases"] = []
                st.rerun()
        profile["diseases"] = st.multiselect(
            "您有以下疾病吗？",
            options=all_disease_options,
            default=profile.get("diseases", []),
            key="hp_diseases",
        )
    else:
        st.warning("⚠️ 疾病库加载失败")

    # ===== 过敏原（GB 7718 8 大类 + 一键组合）=====
    st.markdown("### ⚠️ 过敏原（GB 7718 八大类）")
    st.caption("数据来源：GB 7718-2025 食品标识（2027-03-16 实施）")
    if allergens:
        allergen_options = [a["name"] for a in allergens]
        # 一键组合：常见过敏原
        st.markdown("**一键选择常见过敏原：**")
        ab1, ab2 = st.columns(2)
        with ab1:
            if st.button("🥜 花生/牛奶过敏", key="combo_pn_milk", use_container_width=True,
                         help="花生及其制品 + 乳及乳制品"):
                st.session_state["hp_allergens"] = ["花生及其制品", "乳及乳制品"]
                st.rerun()
        with ab2:
            if st.button("🗑️ 清空过敏原", key="combo_clear_alg", use_container_width=True):
                st.session_state["hp_allergens"] = []
                st.rerun()
        selected_allergens = st.multiselect(
            "您对以下食物过敏吗？",
            options=allergen_options,
            default=[a["name"] for a in profile.get("allergens", []) if isinstance(a, dict)],
            key="hp_allergens",
        )
        # 转成结构化
        profile["allergens"] = [
            next((a for a in allergens if a["name"] == name), {"name": name, "examples": []})
            for name in selected_allergens
        ]
    else:
        st.warning("⚠️ 过敏原库加载失败")

    # ===== 当前用药（按系统搜索式选择）=====
    st.markdown("### 💊 当前用药")
    st.caption("数据来源：NMPA 老年常用药目录（60+ 药，按系统分类）")
    if drug_categories:
        # 拍平为 (id, name_with_category)
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
        # 转成结构化
        profile["drugs"] = [drug_id_map[label] for label in selected_drug_labels]
    else:
        st.warning("⚠️ 药物库加载失败")

    # ===== 自由补充 =====
    with st.expander("📝 自由补充（药物/过敏原）"):
        profile["medications_free"] = st.text_area(
            "其他用药（库外的）",
            value=profile.get("medications_free", ""),
            placeholder="如：自购保健品、中药等",
            height=60,
        )
        profile["allergies_free"] = st.text_input(
            "其他过敏（库外的）",
            value=profile.get("allergies_free", ""),
            placeholder="如：特定添加剂、特殊食物",
        )

    st.divider()
    health_confirm = st.checkbox(
        "我确认以上健康信息真实准确，同意用于药物-食物冲突科普提示",
        key="hp_save_confirm"
    )
    if st.button(
        "💾 保存档案",
        type="primary",
        use_container_width=True,
        disabled=not health_confirm,
        key="hp_save_btn"
    ):
        # 同步到 user_profile（供 render_personal_warnings 使用）
        st.session_state["user_profile"] = {
            "drugs": profile.get("drugs", []),
            "allergens": profile.get("allergens", []),
        }
        st.session_state["health_profile"] = profile
        st.success("✅ 档案已保存！下次识别会自动检测药物-食物冲突")

    st.divider()
    # ===== 档案摘要 =====
    st.markdown("### 📋 当前档案摘要")
    summary = []
    if profile.get("name"):
        summary.append(f"**称呼**：{profile['name']}")
    summary.append(f"**年龄**：{profile.get('age', 60)} 岁")
    if profile.get("diseases"):
        summary.append(f"**基础疾病**：{'、'.join(profile['diseases'])}")
    if profile.get("allergens"):
        summary.append(
            f"**过敏原**：{'、'.join(a['name'] for a in profile['allergens'] if isinstance(a, dict))}"
        )
    if profile.get("drugs"):
        summary.append(
            f"**当前用药**：{'、'.join(d['name'] for d in profile['drugs'] if isinstance(d, dict))}"
        )
    if profile.get("medications_free"):
        summary.append(f"**其他用药**：{profile['medications_free']}")
    if profile.get("allergies_free"):
        summary.append(f"**其他过敏**：{profile['allergies_free']}")
    if len(summary) == 1:
        st.info("档案为空，请填写后保存")
    else:
        for s in summary:
            st.markdown(f"- {s}")


# ========== 主程序 ==========

def main():
    """主程序入口."""
    st.set_page_config(page_title="AI食品配料表识别", page_icon="🥫", layout="centered")
    inject_elder_css()

    # DEBUG 信息块：仅当环境变量 DEBUG=1 时显示，用于部署后排查 API 配置
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

    # 已完成引导：进入主页
    st.title("🥫 AI食品配料表识别工具")
    st.caption("拍照配料表，3秒读懂添加剂风险")
    # 首页显著风险提示：高对比度、大字号、醒目色块，确保老人可见
    st.markdown(
        "<div style='background:#FFF3E0;border-left:8px solid #FF9800;padding:18px 20px;"
        "border-radius:10px;margin:14px 0;color:#5D4037;font-size:20px;font-weight:bold;'>"
        "本 Demo 仅供技术展示，不构成任何医疗或消费建议"
        "</div>",
        unsafe_allow_html=True
    )
    st.info("📋 本工具仅翻译包装信息，不构成医疗建议。如有健康问题请咨询医生。")

    # Phase 4 / Task 12：数据文件启动校验，异常不阻断运行，仅在顶部警告
    data_issues = validate_data_files()
    if data_issues:
        st.warning(
            "部分数据文件异常，相关功能可能不可用：\n- " +
            "\n- ".join(data_issues)
        )

    # 侧边栏：页面菜单 + 模型选择 + 历史 + 法律文件入口
    with st.sidebar:
        st.header("📋 功能菜单")
        page = st.radio(
            "选择页面",
            ["🔍 扫描识别", "👤 健康档案"],
            label_visibility="collapsed",
        )
        st.divider()
        st.header("模型选择")
        model_choice = st.radio("选择识别模型", ["MiMo (mimo-v2.5)", "Agnes (agnes-2.0-flash)"])
        model = "agnes" if "Agnes" in model_choice else "mimo"
        st.divider()
        show_history()
        st.divider()
        if st.button("🔄 重新查看引导", use_container_width=True, key="replay_ob"):
            st.session_state["onboarded"] = False
            st.session_state["onboarding_step"] = 1
            st.rerun()
        st.divider()
        # 隐私政策/用户协议入口：随时可重新查看
        with st.expander("📜 用户协议与隐私政策"):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            user_agreement = _load_markdown(os.path.join(base_dir, "USER_AGREEMENT.md"))
            privacy_policy = _load_markdown(os.path.join(base_dir, "PRIVACY_POLICY.md"))
            with st.expander("《用户协议及免责声明》"):
                st.markdown(user_agreement)
            with st.expander("《隐私政策》"):
                st.markdown(privacy_policy)

        # 法律合规评估入口
        with st.expander("⚖️ 法律合规评估"):
            legal_review = _load_markdown(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "LEGAL_REVIEW.md")
            )
            st.markdown(legal_review)

        st.divider()
        # 侧边栏常驻：跨境传输披露
        st.markdown(
            "<div style='background:#E3F2FD;border-left:6px solid #1976D2;padding:12px 14px;"
            "border-radius:8px;color:#0D47A1;font-size:16px;font-weight:bold;'>"
            "服务部署于境外服务器，识别过程可能涉及跨境数据传输"
            "</div>",
            unsafe_allow_html=True
        )

    # 健康档案页（不显示扫描界面）
    if page == "👤 健康档案":
        render_health_profile()
        return

    # ===== 扫描识别页 =====
    # 从健康档案读取人群（默认空）
    profile = st.session_state.get("health_profile", {})
    groups = profile.get("diseases", [])
    if groups:
        st.success(f"✅ 已加载健康档案：{'、'.join(groups)}（建议基于此档案生成）")
    else:
        st.warning("⚠️ 未设置健康档案，建议先到左侧'健康档案'填写 → 建议更准确")

    # API 密钥（按模型选不同 key）
    api_key = get_api_key(model)
    if not api_key:
        var_name = "AGNES_API_KEY" if model == "agnes" else "MIMO_API_KEY"
        label = "Agnes API 密钥" if model == "agnes" else "MiMo API 密钥 (tp-xxxxx)"
        st.warning(f"未检测到环境变量 {var_name}，请在下方输入密钥")
        api_key = st.text_input(label, type="password")

    # 大圆形扫描按钮（视觉引导，Task 10.1）+ 文件上传
    st.markdown(
        "<div class='scan-circle-btn' role='img' aria-label='扫描按钮'>"
        "📷 拍照 / 上传配料表"
        "</div>"
        "<p style='text-align:center;color:#666;font-size:16px;margin-top:-8px;'>"
        "点击下方按钮选择图片</p>",
        unsafe_allow_html=True
    )
    uploaded = st.file_uploader("上传配料表图片", type=["jpg", "jpeg", "png"])

    if uploaded is not None:
        st.image(uploaded, caption="已上传", use_container_width=True)

        if st.button("🔍 开始识别", type="primary", use_container_width=True):
            if not api_key:
                st.error("请先输入 API 密钥")
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

        # 移到按钮块外：rerun 时也能渲染上次结果（语音播报不会清空）
        if "last_result" in st.session_state:
            st.divider()
            show_result(st.session_state["last_result"])

    # 页面底部：跨境传输披露（高对比度、醒目样式，常驻展示）
    st.divider()
    st.markdown(
        "<div style='background:#E3F2FD;border-left:8px solid #1976D2;padding:16px 20px;"
        "border-radius:10px;margin-top:14px;color:#0D47A1;font-size:18px;font-weight:bold;'>"
        "服务部署于境外服务器，识别过程可能涉及跨境数据传输"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
