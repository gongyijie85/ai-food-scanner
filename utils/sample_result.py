"""本地预览 / 深链用的示例识别结果（不调用 API）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

from utils.data import _DATA_DIR

# 与 session 路由一致的可深链页面
ALLOWED_URL_PAGES = frozenset(
    {"home", "scan", "result", "history", "profile", "detail"}
)

# 离线结果目录（API 不可用时人工/脚本写入的 JSON）
_OFFLINE_DIR = Path(_DATA_DIR) / "offline_results"

# sample= 别名 → 文件名（不含 .json）
_OFFLINE_ALIASES = {
    "ymgs": "ymgs_shanzha",
    "shanzha": "ymgs_shanzha",
    "山楂": "ymgs_shanzha",
    "沂蒙公社": "ymgs_shanzha",
}


def _param_str(query_params: Mapping[str, Any], key: str) -> str:
    """从 Streamlit query_params 或普通 dict 取标量字符串."""
    raw = query_params.get(key)
    if raw is None:
        return ""
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else ""
    return str(raw).strip()


def is_truthy_param(query_params: Mapping[str, Any], key: str) -> bool:
    return _param_str(query_params, key).lower() in ("1", "true", "yes", "on")


def load_offline_result(name: str) -> Optional[Dict[str, Any]]:
    """从 data/offline_results/<name>.json 加载离线识别结果."""
    key = (name or "").strip()
    if not key:
        return None
    key = _OFFLINE_ALIASES.get(key, key)
    # 安全：仅允许简单文件名
    if "/" in key or "\\" in key or ".." in key:
        return None
    path = _OFFLINE_DIR / f"{key}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("_sample_preview", True)
    data.setdefault("_offline", True)
    return data


def build_sample_food_result() -> Dict[str, Any]:
    """示例结果：多等级添加剂 + 配料标签；分数仅内部字段，UI 走呈现契约."""
    return {
        "type": "food",
        "product_name": "某品牌谷物夹心饼干（巧克力味） 200g",
        "score": 72,
        "scan_date": "2026-08-01",
        "timestamp": "2026-08-01T10:00:00",
        "advice": (
            "留意甜味剂与色素相关关注项；"
            "有相关健康管理需求时先咨询医生或营养师。"
        ),
        "ingredients": [
            "小麦粉",
            "白砂糖",
            "植物油",
            "可可粉",
            "山梨酸钾",
            "阿斯巴甜",
            "食用香精",
        ],
        "ocr_text": (
            "配料：小麦粉、白砂糖、植物油、可可粉、山梨酸钾、阿斯巴甜、食用香精。"
        ),
        "additives": [
            {
                "name": "山梨酸钾",
                "canonical_name": "山梨酸钾",
                "level": "A",
                "status": "rated",
                "function": "防腐剂",
                "cns": "17.004",
                "ins": "202",
            },
            {
                "name": "阿斯巴甜",
                "canonical_name": "阿斯巴甜",
                "level": "B",
                "status": "rated",
                "function": "甜味剂",
                "cns": "19.004",
                "ins": "951",
            },
            {
                "name": "胭脂红",
                "canonical_name": "胭脂红",
                "level": "C",
                "status": "rated",
                "function": "着色剂",
                "cns": "08.002",
                "ins": "124",
            },
            {
                "name": "某添加剂",
                "canonical_name": "某添加剂",
                "level": "",
                "status": "pending_rating",
                "function": "",
                "note": "请以包装与官方说明为准",
            },
        ],
        "_sample_preview": True,
    }


def resolve_deep_link(query_params: Mapping[str, Any]) -> Dict[str, Any]:
    """解析 URL 深链意图（纯函数，便于单测）.

    支持：
      ?page=result&sample=1  — 跳过同意/引导，注入示例结果并打开结果页
      ?page=result&preview=1 — 同上
      ?page=result&sample=ymgs — 离线结果（沂蒙公社山楂等）
      ?demo=1&page=result    — 评委模式 + 指定页（示例结果在无 last_result 时注入）
      ?page=scan|home|…     — 仅路由（仍受法律/引导门控，除非 sample/preview/demo）
    """
    page = _param_str(query_params, "page").lower()
    if page not in ALLOWED_URL_PAGES:
        page = ""

    sample_raw = _param_str(query_params, "sample")
    preview = is_truthy_param(query_params, "preview")
    demo = is_truthy_param(query_params, "demo")
    # sample=1 / true → 默认示例；sample=ymgs → 离线别名
    sample_flag = sample_raw.lower() in ("1", "true", "yes", "on", "demo")
    offline_name = ""
    if sample_raw and not sample_flag:
        offline_name = sample_raw
    if preview and not sample_flag and not offline_name:
        sample_flag = True

    skip_gates = bool(sample_flag or offline_name or demo or preview)
    seed_sample = bool(page == "result" and (sample_flag or demo) and not offline_name)
    seed_offline = bool(page == "result" and offline_name)

    return {
        "page": page or None,
        "skip_gates": skip_gates,
        "seed_sample": seed_sample,
        "seed_offline": seed_offline,
        "offline_name": offline_name or None,
    }


def apply_deep_link(
    session_state: MutableMapping[str, Any],
    query_params: Mapping[str, Any],
) -> Optional[str]:
    """把深链应用到 session_state；每个浏览器会话只应用一次.

    返回实际设置的 page（若有），否则 None。
    """
    if session_state.get("_url_deep_link_applied"):
        return None

    intent = resolve_deep_link(query_params)
    session_state["_url_deep_link_applied"] = True

    if intent["skip_gates"]:
        session_state["legal_agreed"] = True
        session_state["onboarded"] = True

    if not session_state.get("last_result"):
        if intent.get("seed_offline") and intent.get("offline_name"):
            offline = load_offline_result(str(intent["offline_name"]))
            if offline:
                session_state["last_result"] = offline
        elif intent.get("seed_sample"):
            session_state["last_result"] = build_sample_food_result()

    if intent["page"]:
        # 结果页无数据且未 seed：仍跳转，由空态引导扫描 / 示例按钮
        if intent["page"] == "result" and not session_state.get("last_result"):
            if intent.get("seed_offline") and intent.get("offline_name"):
                offline = load_offline_result(str(intent["offline_name"]))
                if offline:
                    session_state["last_result"] = offline
            elif intent.get("seed_sample"):
                session_state["last_result"] = build_sample_food_result()
        session_state["page"] = intent["page"]
        return intent["page"]

    return None
