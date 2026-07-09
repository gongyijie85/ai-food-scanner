"""API 调用、提示词构建与模型输出归一化工具。"""

import base64
import io
import json
import logging
import os
import re
import time

import requests
import streamlit as st
from PIL import Image

from utils.score import (
    _clean_name,
    _is_blocklisted,
    compute_score_from_additives,
    normalize_additive,
)

logger = logging.getLogger("ai-food-scanner")

# MiMo Token Plan - 新加坡集群
API_URL = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions"
MODEL_NAME = "mimo-v2.5"

# Agnes 降級備用模型（僅在 MiMo 失敗時調用）
AGNES_API_URL = "https://api.agnes-ai.com/v1/chat/completions"
AGNES_MODEL_NAME = "agnes-20-flash"

# 建议文案模板（降低模型随机性，统一兜底）
# 键必须与 CONDITION_ITEMS 中的疾病名一致；"孕妇/儿童" 永不匹配（HEALTH_GROUPS 无此组合），已移除
ADVICE_TEMPLATES = {
    "default": "普通人群可适量食用，建议保持均衡饮食。",
    "糖尿病": "糖尿病患者请注意控制摄入量，具体请咨询医生或营养师。",
    "高血压": "高血压患者建议关注钠含量，具体请咨询医生或营养师。",
    "脑梗/心血管": "脑梗/心血管人群建议低脂低盐饮食，具体请咨询医生或营养师。",
    "减脂": "减脂人群建议关注糖分和脂肪含量，具体请咨询教练或营养师。",
    "过敏": "过敏体质请仔细核对配料，具体请咨询医生。",
    "儿童": "儿童请谨慎选择，具体请咨询医生或营养师。",
    "孕妇": "孕妇请谨慎选择，具体请咨询医生或营养师。",
}


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
        '- type: "supplement"\n'
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
        '- type: "food"\n'
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
    - 原始错误信息仅写入日志（v0.7.2 起不再在 UI 折叠区展示，防泄露）
    """

    def _err(msg, detail=""):
        """统一错误提示；detail 仅写入日志，不在 UI 展示（防泄露 resp.text）.

        安全说明：
        - resp.text 可能包含上游服务返回的请求 ID / 鉴权细节，不可信；
        - 用户侧只看 msg（友好文案），detail 只进 logger，便于事后排查。
        """
        st.error(msg)
        if detail:
            logger.error(f"API错误详情: {detail}")

    headers = {"api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                    {"type": "text", "text": "请分析这张配料表图片，按规则返回 JSON。"},
                ],
            },
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
        # 发起请求
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.Timeout:
            # 超时属于网络错误，可重试
            logger.warning(f"API请求超时: attempt={attempt}, timeout=30s")
            if attempt < max_attempts:
                time.sleep(2**attempt)  # attempt=1→2秒，attempt=2→4秒
                continue
            elapsed = time.time() - start_time
            logger.error(f"API调用失败: 超时, 总耗时={elapsed:.2f}s")
            _err(
                "识别服务暂时不可用，请稍后重试。",
                f"Timeout after 30s, attempts={attempt}",
            )
            return None
        except requests.exceptions.RequestException as e:
            # 连接错误/网络异常，可重试
            logger.warning(f"API网络错误: attempt={attempt}, error={str(e)[:200]}")
            if attempt < max_attempts:
                time.sleep(2**attempt)
                continue
            elapsed = time.time() - start_time
            logger.error(f"API调用失败: 网络错误, 总耗时={elapsed:.2f}s")
            _err("网络连接失败，请检查网络后重试。", str(e)[:1000])
            return None

        # 收到 HTTP 响应
        elapsed = time.time() - start_time
        if resp.status_code == 200:
            try:
                content = resp.json()["choices"][0]["message"]["content"]
                logger.info(
                    f"API调用成功: status=200, 耗时={elapsed:.2f}s, 响应长度={len(content)}"
                )
                return content
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                # 响应内容解析失败：不重试（重试也不会变好）
                logger.error(f"API响应解析失败: error={str(e)[:200]}")
                _err(
                    "识别结果解析失败，请重试。",
                    f"Parse error: {e}\n{resp.text[:1000]}",
                )
                return None

        # 4xx 客户端错误：不重试（密钥无效 / 限流 / 请求格式错误等）
        if 400 <= resp.status_code < 500:
            logger.error(
                f"API客户端错误: status={resp.status_code}, 耗时={elapsed:.2f}s"
            )
            # 按状态码细分用户提示，避免把限流误判为密钥问题
            if resp.status_code in (401, 403):
                user_msg = "API 密钥无效或无权限，请检查密钥后重试。"
            elif resp.status_code == 429:
                user_msg = "识别服务繁忙，请稍后再试。"
            elif resp.status_code == 404:
                user_msg = "识别服务地址错误，请联系管理员。"
            else:
                # 400 / 405 / 406 等：请求异常，不是密钥问题
                user_msg = "请求异常，请稍后重试或更换图片。"
            _err(user_msg, f"HTTP {resp.status_code}\n{resp.text[:1000]}")
            return None

        # 5xx 服务端错误：可重试
        logger.warning(
            f"API服务端错误: status={resp.status_code}, attempt={attempt}, 耗时={elapsed:.2f}s"
        )
        if attempt < max_attempts:
            time.sleep(2**attempt)
            continue
        # 最后一次仍失败
        logger.error(f"API调用失败: 服务端错误, 总耗时={elapsed:.2f}s")
        _err(
            "识别服务暂时不可用，请稍后重试。",
            f"HTTP {resp.status_code}\n{resp.text[:1000]}",
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
            agnes_key,
            image_b64,
            system_prompt,
            url=AGNES_API_URL,
            model=AGNES_MODEL_NAME,
        )
    return None


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
    if "functional_ingredients" in data and isinstance(
        data["functional_ingredients"], str
    ):
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
        if not advice or any(
            w in advice for w in ["治疗", "疗效", "降三高", "防癌", "治愈"]
        ):
            advice = _generate_advice(health_groups)
        result["advice"] = advice
    return result
