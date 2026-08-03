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


def _additive_status_str(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    status = item.get("status")
    if hasattr(status, "value"):
        return str(status.value or "").lower()
    return str(status or "").lower()


def is_attention_additive(item: Any) -> bool:
    """是否默认展示在「需要留意」列表（非较友好 A 级）。"""
    if not isinstance(item, dict):
        return True
    status = _additive_status_str(item)
    if status in ("unmatched", "pending_rating"):
        return True
    level = str(item.get("level", "") or "").upper()
    if level == "A":
        return False
    # B/C/空 level：默认需要人看一眼
    return True


def split_additives_by_attention(
    additives: Sequence[Any] | None,
) -> Tuple[List[Any], List[Any]]:
    """拆成 (需要留意, 较友好)， internally 仍按风险大致排序。"""
    attention: List[Any] = []
    friendly: List[Any] = []
    for a in additives or []:
        if is_attention_additive(a):
            attention.append(a)
        else:
            friendly.append(a)

    def _risk_key(x: Any) -> int:
        if not isinstance(x, dict):
            return 1
        level = str(x.get("level", "") or "").upper()
        status = _additive_status_str(x)
        if level == "C":
            return 0
        if status == "unmatched" or level == "B" or status == "pending_rating":
            return 1
        if level == "A":
            return 3
        return 2

    attention = sorted(attention, key=_risk_key)
    friendly = sorted(friendly, key=lambda x: str((x or {}).get("name", "")))
    return attention, friendly


def family_conclusion_for_result(
    score: int, additives: Sequence[Any] | None = None
) -> Tuple[str, str]:
    """家人一句话结论：(文案, tone)。

    tone: safe | caution | danger — 对应 CSS family-verdict-*。
    口语、短句、不写医疗承诺。
    """
    try:
        score_i = int(score)
    except (TypeError, ValueError):
        score_i = 0

    _, _, score_class = status_copy_for_result(score_i, additives)
    attention, _friendly = split_additives_by_attention(additives)

    names: List[str] = []
    for a in attention:
        if not isinstance(a, dict):
            continue
        n = str(a.get("name") or "").strip()
        if n and n not in names:
            names.append(n)
        if len(names) >= 2:
            break
    name_part = "、".join(names) if names else ""

    if score_class == "score-danger":
        if name_part:
            text = f"给家人：建议少买或少吃 · 留意{name_part}"
        else:
            text = "给家人：建议少买或少吃 · 请先看下方关注项"
        return text, "danger"
    if score_class == "score-caution":
        if name_part:
            text = f"给家人：可以偶尔吃 · 留意{name_part}"
        else:
            text = "给家人：可以偶尔吃 · 有少量需留意项"
        return text, "caution"
    # safe
    if name_part:
        # 仅有待核对包装等灰项时仍可能进 attention
        text = f"给家人：配料较省心 · 请核对{name_part}"
        return text, "caution"
    return "给家人：配料看起来比较省心 · 仍请对照包装", "safe"


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


def history_band_for_score(score: int) -> Tuple[str, str, str]:
    """历史/首页列表状态：(css_class, 文案, 色值).

    与结果页语气对齐：较省心 / 要注意 / 建议少吃（不用「良好/高风险」恐吓感）。
    """
    try:
        s = int(score)
    except (TypeError, ValueError):
        s = 0
    if s >= 80:
        return "safe", "较省心", "#43A047"
    if s >= 60:
        return "caution", "要注意", "#FF9800"
    return "danger", "建议少吃", "#E53935"


def history_needs_attention(score: int) -> bool:
    """分数 < 80 视为「要注意」（含注意 + 建议少吃）."""
    try:
        return int(score) < 80
    except (TypeError, ValueError):
        return True


def filter_history_entries(
    history: Sequence[Any] | None,
    *,
    search: str = "",
    band: str = "全部",
) -> List[Tuple[int, Any]]:
    """按搜索与档位筛选历史，返回 [(原下标, item), ...].

    band: 全部 | 要注意 | 较省心
    """
    q = (search or "").strip().lower()
    band = (band or "全部").strip()
    out: List[Tuple[int, Any]] = []
    for idx, item in enumerate(history or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("product_name", "") or "")
        if q and q not in name.lower():
            continue
        score = item.get("score", 0)
        if band == "要注意" and not history_needs_attention(score):
            continue
        if band == "较省心" and history_needs_attention(score):
            continue
        out.append((idx, item))
    return out


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
