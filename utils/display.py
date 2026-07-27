"""展示层纯函数：短产品名、友好时间、状态文案（不依赖 Streamlit）。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Sequence, Tuple


def short_product_name(name: str, max_len: int = 22) -> str:
    """适老化短标题：去掉前导英文品牌、品类括号，过长截断。"""
    if not name or not isinstance(name, str):
        return "未知产品"
    s = name.strip()
    if not s:
        return "未知产品"

    # 去掉开头连续英文/数字品牌段（保留紧跟的中文）
    s = re.sub(
        r"^[A-Za-z][A-Za-z0-9\s\.\+\-&']{0,48}(?=[\u4e00-\u9fff])",
        "",
        s,
    ).strip()
    # 去掉末尾品类标注，如 (膨化食品)
    s = re.sub(
        r"[（(][^）)]*(食品|膨化|饮料|糖果|零食|保健)[^）)]*[）)]\s*$",
        "",
        s,
    ).strip()
    # 压缩空白
    s = re.sub(r"\s+", " ", s)
    if not s:
        s = name.strip()
    if len(s) > max_len:
        return s[: max_len - 1].rstrip() + "…"
    return s


def format_scan_time(ts: str) -> str:
    """把 ISO 时间转成『2026年7月27日 01:27』，失败则尽量可读。"""
    if not ts or not isinstance(ts, str):
        return "未知时间"
    raw = ts.strip()
    if not raw:
        return "未知时间"
    candidates = [
        raw,
        raw.replace("Z", "+00:00"),
        raw[:19],
    ]
    for c in candidates:
        try:
            if "T" in c or re.match(r"\d{4}-\d{2}-\d{2}", c):
                dt = datetime.fromisoformat(c.replace("Z", ""))
                return (
                    f"{dt.year}年{dt.month}月{dt.day}日 {dt.hour:02d}:{dt.minute:02d}"
                )
        except ValueError:
            continue
    # 已是日期前缀
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
    return raw[:16]


def status_copy_for_result(
    score: int, additives: Sequence[Any] | None = None
) -> Tuple[str, str, str]:
    """返回 (label, meaning, score_class)，与添加剂等级一致。

    score_class: score-safe | score-caution | score-danger
    """
    has_c = False
    has_b = False
    for a in additives or []:
        if not isinstance(a, dict):
            continue
        level = str(a.get("level", "") or "").upper()
        if level == "C":
            has_c = True
        elif level == "B":
            has_b = True

    if has_c or score < 60:
        return (
            "含需关注成分",
            "含有建议少吃或需特别留意的添加剂，请结合自身情况查看详情",
            "score-danger",
        )
    if has_b or score < 80:
        return (
            "有可留意项",
            "含少量需留意的添加剂，请结合健康档案查看，结果仅供参考",
            "score-caution",
        )
    return (
        "暂未发现明显问题",
        "根据当前规则，暂未标出需特别注意的添加剂；仍请以包装与医嘱为准",
        "score-safe",
    )


def build_detail_speak(
    product_name: str,
    score: int,
    additives: List[Dict],
    advice: str = "",
    ingredients: List[str] | None = None,
) -> str:
    """详情页语音摘要。"""
    short = short_product_name(product_name, max_len=28)
    parts = [f"产品详情。{short}，配料参考分{score}分。"]
    caution = []
    friendly = []
    for a in additives or []:
        if not isinstance(a, dict) or not a.get("name"):
            continue
        level = str(a.get("level", "") or "").upper()
        name = str(a["name"])
        if level == "C":
            caution.append(name)
        elif level == "B":
            caution.append(name)
        elif level == "A":
            friendly.append(name)
    if caution:
        parts.append("需要留意：" + "、".join(caution[:5]) + "。")
    elif friendly:
        parts.append("识别到的添加剂较友好，例如：" + "、".join(friendly[:3]) + "。")
    if ingredients:
        preview = [str(x) for x in ingredients[:5] if str(x).strip()]
        if preview:
            parts.append("主要配料：" + "、".join(preview) + "。")
    if advice:
        parts.append(advice if advice.endswith("。") else advice + "。")
    parts.append("本结果仅供参考，不构成医疗建议。")
    return "".join(parts)
