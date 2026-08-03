"""结果呈现契约：结果页 / 语音 /（后续）历史与离线共用的纯函数出口.

Ticket A / Spec #47：用户可见主结论不得以总分或 A/B/C 等级为核心；
顺序语义为 识别状态 → 行动 → 关注项 → 证据 → 纠错 → 免责。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from utils.display import short_product_name, split_additives_by_attention

# 主结论/语音 lede 禁止出现的判决或分数叙事（子串匹配，测外部行为）
FORBIDDEN_PRIMARY_PHRASES: tuple[str, ...] = (
    "配料参考分",
    "参考分",
    "安全分",
    "能吃",
    "不能吃",
    "可以吃",
    "禁止食用",
    "放心吃",
    "100%安全",
    "绝对安全",
)

_DISCLAIMER = "本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生、药师或营养师。"


@dataclass(frozen=True)
class ResultPresentation:
    """单一呈现契约输出（不可变）."""

    product_display_name: str
    recognition_state: str  # complete | partial | unconfirmed
    recognition_label: str
    recognition_meaning: str
    action_line: str
    tone: str  # safe | caution | danger
    status_label: str
    status_meaning: str
    status_class: str  # 复用 CSS：score-safe | score-caution | score-danger
    attention_names: tuple[str, ...]
    voice_script: str
    product_full_name: str = ""


def _warning_titles(warnings: Sequence[Any] | None, limit: int = 4) -> list[str]:
    titles: list[str] = []
    for w in warnings or []:
        title = getattr(w, "title", None) or (
            w.get("title") if isinstance(w, dict) else ""
        )
        title = str(title or "").strip()
        if title and title not in titles:
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def _is_inferred_item(item: Any) -> bool:
    return bool(isinstance(item, dict) and item.get("ai_inferred"))


def _attention_names(
    additives: Sequence[Any] | None,
    limit: int = 3,
    *,
    include_inferred: bool = True,
) -> list[str]:
    attention, _ = split_additives_by_attention(additives)
    names: list[str] = []
    for a in attention:
        if not isinstance(a, dict):
            continue
        if not include_inferred and _is_inferred_item(a):
            continue
        n = str(a.get("name") or "").strip()
        if n and n not in names:
            names.append(n)
        if len(names) >= limit:
            break
    return names


def _inferred_names(additives: Sequence[Any] | None, limit: int = 5) -> list[str]:
    names: list[str] = []
    for a in additives or []:
        if not isinstance(a, dict) or not _is_inferred_item(a):
            continue
        n = str(a.get("name") or "").strip()
        if n and n not in names:
            names.append(n)
        if len(names) >= limit:
            break
    return names


def apply_result_corrections(
    result: dict | None,
    *,
    remove_additive_names: Sequence[str] | None = None,
) -> dict:
    """返回排除指定添加剂后的新结果（不可变纠错，供会话内降级结论）.

    仅移除 additives 中名称匹配项；不编造 OCR。用于「这条识别错了」即时降级。
    """
    data = dict(result) if isinstance(result, dict) else {}
    remove = {
        str(n).strip()
        for n in (remove_additive_names or [])
        if n is not None and str(n).strip()
    }
    if not remove:
        return data
    additives = data.get("additives")
    if not isinstance(additives, list):
        return data
    kept = []
    for a in additives:
        if not isinstance(a, dict):
            continue
        name = str(a.get("name") or "").strip()
        if name in remove:
            continue
        kept.append(dict(a))
    data["additives"] = kept
    data["corrections_applied"] = True
    removed_prev = list(data.get("corrected_removed") or [])
    for n in remove:
        if n not in removed_prev:
            removed_prev.append(n)
    data["corrected_removed"] = removed_prev
    return data


def infer_recognition_state(result: dict | None) -> str:
    """根据 OCR/配料完整度推断识别状态."""
    data = result if isinstance(result, dict) else {}
    ocr = str(data.get("ocr_text") or "").strip()
    ingredients = data.get("ingredients") or []
    additives = data.get("additives") or []
    recovered = bool(data.get("ingredients_recovered_from_ocr"))
    has_ings = any(str(x).strip() for x in ingredients if x is not None)
    has_add = any(
        isinstance(a, dict) and str(a.get("name") or "").strip() for a in additives
    )
    inferred = any(
        isinstance(a, dict) and a.get("ai_inferred") for a in additives
    )

    if not ocr and not has_ings and not has_add:
        return "unconfirmed"
    if recovered or inferred or (ocr and not has_ings) or (has_ings and not ocr):
        return "partial"
    if ocr and has_ings:
        return "complete"
    if has_ings or has_add:
        return "partial"
    return "unconfirmed"


def _recognition_copy(state: str) -> tuple[str, str]:
    if state == "complete":
        return (
            "识别较完整",
            "已读到配料相关文字；以下关注项仍需对照包装核对。",
        )
    if state == "partial":
        return (
            "部分识别",
            "只看清部分内容，结论不完整，请优先对照包装原文或重新拍照。",
        )
    return (
        "无法确认",
        "未能可靠识别配料表，请重新对准「配料表」拍照后再查看提示。",
    )


def _tone_and_status(
    attention_names: Sequence[str],
    additives: Sequence[Any] | None,
    recognition_state: str,
) -> tuple[str, str, str, str]:
    """返回 tone, status_label, status_meaning, status_class（不依赖总分）."""
    has_c = False
    has_b = False
    for a in additives or []:
        if not isinstance(a, dict):
            continue
        level = str(a.get("level") or "").upper()
        if level == "C":
            has_c = True
        elif level == "B":
            has_b = True

    if recognition_state == "unconfirmed":
        return (
            "caution",
            "识别未完成",
            "尚未得到可核对的配料信息，请重拍后再参考本页。",
            "score-caution",
        )
    if has_c:
        return (
            "danger",
            "含需关注成分",
            "含有建议少买或少吃前先核对的添加剂，请结合自身情况查看详情。",
            "score-danger",
        )
    if has_b or attention_names:
        return (
            "caution",
            "有可留意项",
            "有需留意的配料或待核对项，请结合健康情况与包装查看。",
            "score-caution",
        )
    if recognition_state == "partial":
        return (
            "caution",
            "信息可能不完整",
            "识别不完整时不做「省心」结论，请对照包装或重拍。",
            "score-caution",
        )
    return (
        "safe",
        "暂未标出高关注添加剂",
        "按当前规则暂未标出需特别留意的添加剂；仍请以包装与医嘱为准。",
        "score-safe",
    )


def _action_line(
    *,
    tone: str,
    recognition_state: str,
    attention_names: Sequence[str],
    inferred_names: Sequence[str],
    is_supplement: bool,
) -> str:
    """决断行动句：只引用已确认关注项；推断项不得升格为确定结论。"""
    if is_supplement:
        return "保健食品不能代替药物；请按包装说明，必要时咨询医生或药师。"
    if recognition_state == "unconfirmed":
        return "请重新对准包装上的「配料表」拍照，再查看关注提示。"
    if recognition_state == "partial":
        bits = ["识别不完整：请先核对包装"]
        if attention_names:
            bits.append("并留意" + "、".join(attention_names[:2]))
        if inferred_names:
            bits.append("有自动识别项须以包装为准")
        return "，".join(bits) + "。"
    if tone == "danger":
        if attention_names:
            return f"建议先查看需关注配料（如{'、'.join(attention_names[:2])}），再决定是否购买。"
        return "建议先查看下方需关注项，再决定是否购买。"
    if tone == "caution":
        if attention_names:
            return f"购买前请留意{'、'.join(attention_names[:2])}，并对照包装。"
        if inferred_names:
            return "有待包装核对的自动识别项，请先对照原文再参考本页。"
        return "有需留意项：请结合健康情况与包装核对后再购买。"
    if inferred_names:
        return "有自动识别项未写入包装原文，请先核对包装；暂不作为确定结论。"
    return "按当前规则暂未标出高关注添加剂；购买前仍请对照包装与个人医嘱。"


def _voice_script(
    *,
    product_display_name: str,
    recognition_label: str,
    action_line: str,
    attention_names: Sequence[str],
    inferred_names: Sequence[str],
    warning_titles: Sequence[str],
    advice: str,
    is_supplement: bool,
    summary: str,
) -> str:
    parts: list[str] = []
    if is_supplement:
        parts.append(f"保健食品。{product_display_name}。")
        if summary:
            s = summary.strip()
            parts.append(s if s.endswith("。") else s + "。")
        parts.append("保健食品不是药物，不能代替药物治疗疾病。")
        parts.append(action_line if action_line.endswith("。") else action_line + "。")
        parts.append(_DISCLAIMER)
        return "".join(parts)

    parts.append(f"识别结果。{product_display_name}。")
    parts.append(f"识别状态：{recognition_label}。")
    parts.append(action_line if action_line.endswith("。") else action_line + "。")
    if warning_titles:
        parts.append("健康档案提示：" + "；".join(warning_titles) + "。")
    if attention_names:
        parts.append("配料关注：" + "、".join(attention_names) + "。")
    if inferred_names:
        parts.append(
            "以下为自动识别、须以包装为准：" + "、".join(inferred_names[:3]) + "。"
        )
    if advice:
        a = advice.strip()
        if not re.search(r"能吃|不能吃|放心吃", a):
            parts.append(a if a.endswith("。") else a + "。")
    parts.append(_DISCLAIMER)
    return "".join(parts)


def build_result_presentation(
    result: dict | None,
    *,
    warnings: Sequence[Any] | None = None,
) -> ResultPresentation:
    """从识别结果构建呈现契约（不读总分作主结论）."""
    data = result if isinstance(result, dict) else {}
    full_name = str(data.get("product_name") or "").strip() or "该产品"
    display = short_product_name(full_name)
    additives = data.get("additives") or []
    is_supplement = str(data.get("type") or "").lower() == "supplement"
    state = (
        "complete"
        if is_supplement
        else infer_recognition_state(data)
    )
    # 保健食品：包装字段齐则 complete，否则 partial
    if is_supplement:
        has_any = any(
            str(data.get(k) or "").strip() not in ("", "未显示")
            for k in ("summary", "approval_no", "health_claims", "usage")
        ) or bool(data.get("ingredients"))
        state = "complete" if has_any else "unconfirmed"

    rec_label, rec_meaning = _recognition_copy(state)
    # 决断只引用非推断关注项；推断单独标注
    decisive_names = _attention_names(additives, include_inferred=False)
    inferred = _inferred_names(additives)
    # 状态色：推断项可进 caution，但不单独制造 danger 的「已确认」感
    tone_names = list(decisive_names) + list(inferred)
    tone, status_label, status_meaning, status_class = _tone_and_status(
        tone_names, additives, state
    )
    # 仅有推断、无确认关注且识别完整时，降为 caution，禁止 soft all-clear
    if (
        state == "complete"
        and not decisive_names
        and inferred
        and tone == "safe"
    ):
        tone, status_label, status_meaning, status_class = (
            "caution",
            "有待核对项",
            "存在未在包装原文确认的自动识别项，请先对照包装。",
            "score-caution",
        )
    action = _action_line(
        tone=tone,
        recognition_state=state,
        attention_names=decisive_names,
        inferred_names=inferred,
        is_supplement=is_supplement,
    )
    voice = _voice_script(
        product_display_name=display,
        recognition_label=rec_label,
        action_line=action,
        attention_names=decisive_names,
        inferred_names=inferred,
        warning_titles=_warning_titles(warnings),
        advice=str(data.get("advice") or ""),
        is_supplement=is_supplement,
        summary=str(data.get("summary") or ""),
    )
    return ResultPresentation(
        product_display_name=display,
        recognition_state=state,
        recognition_label=rec_label,
        recognition_meaning=rec_meaning,
        action_line=action,
        tone=tone,
        status_label=status_label,
        status_meaning=status_meaning,
        status_class=status_class,
        attention_names=tuple(decisive_names),
        voice_script=voice,
        product_full_name=full_name,
    )


def assert_primary_copy_safe(*texts: str) -> list[str]:
    """返回命中的禁用短语列表；空列表表示通过."""
    hits: list[str] = []
    blob = "\n".join(str(t or "") for t in texts)
    for p in FORBIDDEN_PRIMARY_PHRASES:
        if p in blob:
            hits.append(p)
    # 主结论中的「配料参考分NN分」形态
    if re.search(r"参考分\s*\d+", blob):
        hits.append("参考分+数字")
    return hits
