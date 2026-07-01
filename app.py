"""
AI食品配料表识别工具 - Streamlit Demo 优化版 v2
用途：上传配料表图片，调用 MiMo Vision API，展示识别结果
特性：适老化样式 + 语音播报 + 历史记录 + 健康档案
运行环境：Python 3.10+
依赖：pip install streamlit requests pillow
运行命令：streamlit run app.py
"""

import base64
import io
import json
import os
import re

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

# 六大人群选项
HEALTH_GROUPS = ["糖尿病", "高血压", "脑梗/心血管", "减脂", "过敏", "孕妇/儿童"]


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

        /* 评分色块 */
        .score-box {
            padding: 24px; border-radius: 16px; text-align: center;
            color: white; margin: 12px 0;
        }
        .score-num { font-size: 56px; font-weight: bold; }
        .score-label { font-size: 22px; }

        /* 添加剂卡片 */
        .additive-row {
            display: flex; justify-content: space-between;
            align-items: center; padding: 14px 16px;
            border-radius: 10px; margin: 6px 0;
            background: #FAFAF5; font-size: 18px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# ========== 语音播报（浏览器原生，零依赖）==========

def speak_text(text: str):
    """用浏览器原生 SpeechSynthesis API 播报中文语音."""
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
            u.rate = 1.0;
            u.pitch = 1.0;
            u.volume = 1.0;
            var v = pickZhVoice();
            if (v) u.voice = v;
            speechSynthesis.cancel();
            speechSynthesis.speak(u);
            // 调试日志（不影响功能）
            console.log('[speak] attempt=' + attempt + ' voice=' + (v ? v.name : 'default') + ' text=' + '{safe}'.slice(0, 30));
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
        "每个添加剂含 name、code(INS/E号，没有留空)、level(green/yellow/red)\n"
        "- score: 0-100 综合安全评分\n"
        "- advice: 针对以下人群的一句话建议：" + group_str + "\n\n"
        "level 分级：\n"
        "- green: 安全常见，如柠檬酸、维生素C、碳酸氢钠\n"
        "- yellow: 需适量关注，如山梨酸钾、苯甲酸钠、焦糖色\n"
        "- red: 建议规避，如特丁基对苯二酚(TBHQ)、部分人工合成色素\n\n"
        "## 强制规则（两类产品都适用）\n"
        "- product_name **必须中文**，英文产品名翻译成中文或填'该产品'\n"
        "- 所有引用包装的内容（health_claims/suitable_for/usage）**严格按包装原文**，不评价、不推荐、不补全\n"
        "- 禁止任何医学疗效措辞：'治疗/疗效/降三高/防癌/增强免疫力+治愈'等\n"
        "- 所有健康相关结论以'建议咨询医生'收尾"
    )


def call_api(api_key, image_b64, system_prompt, model="mimo"):
    """统一调用 MiMo 或 Agnes Vision API，返回模型回复文本."""
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
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=90)
    except requests.exceptions.Timeout:
        st.error("API 请求超时（90秒），请重试。")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"网络请求失败：{e}")
        return None
    if resp.status_code != 200:
        st.error(f"API 状态码 {resp.status_code}")
        st.code(resp.text[:500])
        return None
    try:
        return resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        st.error(f"解析 API 响应失败：{e}")
        st.code(resp.text[:500])
        return None


def parse_result(raw):
    """解析模型返回的 JSON 文本."""
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
    return result


# ========== 历史记录（session_state）==========

def add_history(result, image_bytes):
    """把一次扫描结果存入历史（最多5条）."""
    if "history" not in st.session_state:
        st.session_state["history"] = []
    st.session_state["history"].insert(0, {
        "product_name": result.get("product_name", "未知"),
        "score": result.get("score", 0),
        "additives_count": len(result.get("additives", [])),
        "advice": result.get("advice", ""),
        "image": image_bytes
    })
    # 只保留最近5条
    st.session_state["history"] = st.session_state["history"][:5]


def show_history():
    """在侧边栏展示历史记录（调用时需已在 sidebar 上下文内）."""
    st.header("历史记录")
    history = st.session_state.get("history", [])
    if not history:
        st.caption("暂无记录")
        return
    for i, item in enumerate(history):
        score = item["score"]
        color = "green" if score >= 80 else ("orange" if score >= 60 else "red")
        st.markdown(
            f"<div style='border-left:4px solid {color};padding:8px 12px;margin:6px 0;background:#FAFAF5;border-radius:6px;'>"
            f"<b>{item['product_name']}</b><br>"
            f"<span style='color:{color};font-size:20px;font-weight:bold;'>{score}分</span> "
            f"<span style='color:#888;'>{item['additives_count']}种添加剂</span>"
            f"</div>",
            unsafe_allow_html=True
        )


# ========== 结果展示 ==========

def render_food(result):
    """展示普通食品结果（评分 + 添加剂红绿灯 + 建议）."""
    score = result.get("score", 0)
    if score >= 80:
        color, label = "#43A047", "安全"
    elif score >= 60:
        color, label = "#FF9800", "注意"
    else:
        color, label = "#E53935", "警告"

    # 评分大色块
    st.markdown(
        f"<div class='score-box' style='background:{color};'>"
        f"<div class='score-num'>{score}</div>"
        f"<div class='score-label'>{label}</div></div>",
        unsafe_allow_html=True
    )

    # 产品名 + 健康建议
    st.markdown(f"### {result.get('product_name', '未知')}")
    advice = result.get("advice", "")
    if advice:
        st.info(f"健康建议：{advice}")

    # 语音播报按钮
    speak_content = f"评分{score}分，{label}。{advice}"
    if st.button("语音播报", key="btn_speak", use_container_width=True):
        speak_text(speak_content)

    st.divider()

    # 添加剂清单
    st.markdown("### 食品添加剂")
    additives = result.get("additives", [])
    level_map = {
        "green": ("安全", "#43A047"),
        "yellow": ("注意", "#FF9800"),
        "red": ("规避", "#E53935")
    }
    if additives:
        for item in additives:
            name = item.get("name", "未知")
            code = item.get("code", "")
            level = item.get("level", "")
            lv_label, lv_color = level_map.get(level, (level, "#888"))
            st.markdown(
                f"<div class='additive-row'>"
                f"<span><b>{name}</b>{f' ({code})' if code else ''}</span>"
                f"<span style='color:{lv_color};font-weight:bold;'>{lv_label}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.success("未识别到食品添加剂")

    st.divider()

    # 全部配料
    ingredients = result.get("ingredients", [])
    if ingredients:
        st.markdown("### 全部配料")
        st.write("、".join(ingredients))

    # 原始 JSON
    with st.expander("查看原始 JSON"):
        st.json(result)


def render_supplement(result):
    """展示保健食品结果（只翻译包装信息，不评价、不推荐，强制免责声明）."""
    # 顶部固定：红条强制免责
    st.markdown(
        "<div style='background:#E53935;color:#fff;padding:14px 16px;"
        "border-radius:8px;font-size:18px;font-weight:bold;margin-bottom:14px;'>"
        "⚠️ 本产品为保健食品<br>保健食品不是药物，不能代替药物治疗疾病"
        "</div>",
        unsafe_allow_html=True
    )

    # 产品名 + 一句话事实摘要
    st.markdown(f"### 💊 {result.get('product_name', '未知')}")
    summary = result.get("summary", "")
    if summary:
        st.info(f"📦 {summary}")

    # 语音播报：仅朗读事实 + 强制免责
    speak_content = (
        f"保健食品：{result.get('product_name', '未知')}。"
        f"{summary}。"
        f"保健食品不是药物，不能代替药物治疗疾病。"
        f"如需选择，请咨询医生。"
    )
    if st.button("语音播报", key="btn_speak", use_container_width=True):
        speak_text(speak_content)

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

    # 底部固定：再次免责 + 建议咨询医生
    st.markdown(
        "<div style='background:#FFF3E0;border-left:6px solid #E53935;"
        "padding:12px 16px;border-radius:6px;margin-top:14px;'>"
        "<b>❗ 重要提醒</b><br>"
        "本工具仅翻译包装内容，<b>不评价</b>该产品是否适合您。<br>"
        "选购或服用前，请<b>咨询医生或营养师</b>。"
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


# ========== 首次引导页（4 步）==========

def render_onboarding():
    """首次访问的 4 步引导：欢迎 → 选人群 → 使用说明 → 开始."""
    if "onboarding_step" not in st.session_state:
        st.session_state["onboarding_step"] = 1
    if "onboarded" not in st.session_state:
        st.session_state["onboarded"] = False

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
        # 第 2 步：选人群
        st.markdown("## 👴 第 2 步：请选择您的健康状况")
        st.caption("我们会根据您的情况给个性化建议（可多选）")
        selected = st.multiselect(
            "您有以下情况吗？（可多选）",
            HEALTH_GROUPS,
            default=st.session_state.get("onboarding_groups", []),
            key="onboarding_groups_widget",
        )
        st.session_state["onboarding_groups"] = selected
        if selected:
            st.info(f"已选：{'、'.join(selected)}")

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
                st.session_state["health_profile"]["groups"] = st.session_state.get("onboarding_groups", [])
                st.session_state["onboarded"] = True
                st.session_state["onboarding_step"] = 1
                st.rerun()


# ========== 健康档案页 ==========

def render_health_profile():
    """健康档案：姓名/年龄/病史/过敏/用药 + 摘要."""
    st.markdown("## 👤 我的健康档案")
    st.caption("填写档案后，识别结果会按您的健康情况给个性化建议")

    if "health_profile" not in st.session_state:
        st.session_state["health_profile"] = {
            "name": "",
            "age": 60,
            "groups": [],
            "allergies": "",
            "medications": "",
        }
    profile = st.session_state["health_profile"]

    st.markdown("### 📝 基本信息")
    col1, col2 = st.columns(2)
    with col1:
        profile["name"] = st.text_input("称呼（可选）", value=profile.get("name", ""), placeholder="如：张奶奶")
    with col2:
        profile["age"] = st.number_input("年龄", min_value=1, max_value=120, value=profile.get("age", 60), step=1)

    st.markdown("### 🏥 健康状况（可多选）")
    profile["groups"] = st.multiselect(
        "您有以下情况吗？",
        HEALTH_GROUPS,
        default=profile.get("groups", []),
        key="hp_groups",
    )

    st.markdown("### ⚠️ 过敏食物")
    profile["allergies"] = st.text_input(
        "如：花生、海鲜、鸡蛋（多个用顿号分隔）",
        value=profile.get("allergies", ""),
        placeholder="无则不填",
    )

    st.markdown("### 💊 当前用药")
    profile["medications"] = st.text_area(
        "如：降压药、阿司匹林（可不填）",
        value=profile.get("medications", ""),
        placeholder="无则不填",
        height=80,
    )

    st.divider()
    if st.button("💾 保存档案", type="primary", use_container_width=True):
        st.session_state["health_profile"] = profile
        st.success("✅ 档案已保存！识别结果会参考此档案给建议")

    st.divider()
    # 档案摘要
    st.markdown("### 📋 当前档案摘要")
    summary = []
    if profile.get("name"):
        summary.append(f"**称呼**：{profile['name']}")
    summary.append(f"**年龄**：{profile.get('age', 60)} 岁")
    if profile.get("groups"):
        summary.append(f"**健康状况**：{'、'.join(profile['groups'])}")
    if profile.get("allergies"):
        summary.append(f"**过敏食物**：{profile['allergies']}")
    if profile.get("medications"):
        summary.append(f"**当前用药**：{profile['medications']}")
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

    # 首次访问：触发 4 步引导
    if "onboarded" not in st.session_state:
        st.session_state["onboarded"] = False
    if not st.session_state["onboarded"]:
        render_onboarding()
        return

    # 已完成引导：进入主页
    st.title("🥫 AI食品配料表识别工具")
    st.caption("拍照配料表，3秒读懂添加剂风险")
    st.info("📋 本工具仅翻译包装信息，不构成医疗建议。如有健康问题请咨询医生。")

    # 侧边栏：页面菜单 + 模型选择 + 历史
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

    # 健康档案页（不显示扫描界面）
    if page == "👤 健康档案":
        render_health_profile()
        return

    # ===== 扫描识别页 =====
    # 从健康档案读取人群（默认空）
    profile = st.session_state.get("health_profile", {})
    groups = profile.get("groups", [])
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

    # 图片上传
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
                    result = parse_result(raw)
                    if result:
                        st.session_state["last_result"] = result
                        add_history(result, uploaded.getvalue())

        # 移到按钮块外：rerun 时也能渲染上次结果（语音播报不会清空）
        if "last_result" in st.session_state:
            st.divider()
            show_result(st.session_state["last_result"])


if __name__ == "__main__":
    main()
