"""验证证据账本接缝（Spec #53）：样本行校验 + 邀约文案禁语检查.

纯函数，不依赖 Streamlit。访谈记录应写入 research/validation-sample-log.csv
的字段约定；本模块保证「什么叫一行有效账本」可被单测卡住。
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

# 邀约/对外话术禁止子串（对齐发布门槛与合规红线）
FORBIDDEN_OUTREACH_PHRASES: tuple[str, ...] = (
    "能吃",
    "不能吃",
    "放心吃",
    "医疗诊断",
    "医生认证",
    "食药监",
    "治愈",
    "疗效",
    "停药",
    "100%安全",
    "绝对安全",
    "官方合格",
)

# 账本必填列（与 validation-sample-log.csv 表头一致的核心集）
REQUIRED_LOG_FIELDS: tuple[str, ...] = (
    "id",
    "date",
    "channel",
    "role",
    "path_complete",
    "reuse_verbal",
    "pay_tier",
    "valid_sample",
    "recognition_honesty",
    "gate_incident",
)

VALID_ROLES = frozenset({"子女", "老人", "配对子女", "配对老人", "其他"})
VALID_YES_NO_UNKNOWN = frozenset({"是", "否", "未知", "跳过", ""})
VALID_PAY_TIER = frozenset({"1", "2", "3", "未知", ""})
VALID_HONESTY = frozenset(
    {"完整", "部分", "无法确认", "未观察", "未知", ""}
)
VALID_YN = frozenset({"是", "否"})


def outreach_forbidden_hits(text: str) -> list[str]:
    """返回邀约/对外文案中命中的禁用短语."""
    blob = str(text or "")
    return [p for p in FORBIDDEN_OUTREACH_PHRASES if p in blob]


def default_wechat_invite(*, public_url: str) -> str:
    """门槛通过后的微信 1v1 邀约模板（非医疗）."""
    url = (public_url or "").strip() or "（粘贴公开体验链接）"
    return (
        "嗨，我在做一个小工具的用户验证，想请你帮个忙（大约 15 分钟）。\n\n"
        "场景：很多子女想帮父母看食品包装上的配料，但字小又难懂。\n"
        "工具：手机打开网页，对准「配料表」拍照，会结合你填的父母健康情况，\n"
        "给出需要留意的参考提示，并能语音读出来。\n"
        "注意：只是标签识读/科普参考，不是医生建议，也不能替代就医。\n\n"
        "如果你方便：\n"
        f"1）用你自己的手机打开：{url}\n"
        "2）按页面走一遍（可填父母大概的慢病情况，没有可少填）\n"
        "3）看结果里的「识别状态」和「建议下一步」，可点听结果\n"
        "4）结束后我问你几句真实感受（会不会再用、哪里看不懂）\n\n"
        "完全自愿；记录会匿名化，不公开你的个人信息。\n"
        "这周哪个晚上方便？"
    )


def default_group_notice(*, public_url: str) -> str:
    url = (public_url or "").strip() or "（粘贴公开体验链接）"
    return (
        "【拍了就懂 · 验证体验群】\n"
        "请用自己手机打开：\n"
        f"{url}\n"
        "请走完：同意 → 健康档案（能填就填）→ 对准配料表拍照 → "
        "看识别状态/关注项 → 听语音。\n"
        "做完后私聊我「做完了」，我约 10 分钟简单聊几句。\n"
        "本工具仅为配料科普参考，不构成医疗建议。"
    )


def _norm(v: Any) -> str:
    return str(v if v is not None else "").strip()


def validate_evidence_row(row: Mapping[str, Any]) -> list[str]:
    """校验一行证据账本；返回错误列表，空列表表示通过结构校验.

    不判断「商业上是否该 Go」，只判断这一行是否可记账。
    """
    errors: list[str] = []
    for key in REQUIRED_LOG_FIELDS:
        if key not in row:
            errors.append(f"missing_field:{key}")
    if errors:
        return errors

    rid = _norm(row.get("id"))
    if not rid or rid.startswith("S0") and "YYYY" in _norm(row.get("date")):
        # 模板占位行：允许 id 存在但标记为 placeholder
        if "YYYY" in _norm(row.get("date")) or rid in ("S01", "id"):
            errors.append("placeholder_row")

    if _norm(row.get("role")) and _norm(row.get("role")) not in VALID_ROLES:
        errors.append("invalid_role")

    for key in (
        "path_complete",
        "reuse_verbal",
        "valid_sample",
        "gate_incident",
        "archive_filled",
        "voice_ok",
        "reuse_rescan_7d",
        "delta_clear",
    ):
        if key in row and _norm(row.get(key)) not in VALID_YES_NO_UNKNOWN | VALID_YN:
            # 允许未知
            if _norm(row.get(key)) not in VALID_YES_NO_UNKNOWN:
                errors.append(f"invalid_yn:{key}")

    pay = _norm(row.get("pay_tier"))
    if pay and pay not in VALID_PAY_TIER:
        errors.append("invalid_pay_tier")

    honesty = _norm(row.get("recognition_honesty"))
    if honesty and honesty not in VALID_HONESTY:
        errors.append("invalid_recognition_honesty")

    # 有效样本硬条件（对齐 kit / #28）
    if _norm(row.get("valid_sample")) == "是":
        if _norm(row.get("role")) not in ("子女", "配对子女"):
            # 老人可记但不计入 #28 主闸门；仍可 valid_sample=是 用于 #40
            pass
        if _norm(row.get("path_complete")) != "是":
            errors.append("valid_requires_path_complete")
        if _norm(row.get("gate_incident")) == "是":
            errors.append("valid_forbids_gate_incident")

    quote = _norm(row.get("quote"))
    hits = outreach_forbidden_hits(quote)
    # 用户原话可含「能吃」——不拦 quote；只拦 operator notes 若需要
    notes = _norm(row.get("soft_fail_notes")) + _norm(row.get("blocker_notes"))
    note_hits = outreach_forbidden_hits(notes)
    # 执行备注里写「我们告诉用户能吃」才危险；子串仍提示
    for h in note_hits:
        if h in ("能吃", "不能吃", "放心吃", "停药"):
            errors.append(f"notes_forbidden:{h}")

    return errors


def is_gate_blocking_incident(row: Mapping[str, Any]) -> bool:
    """是否应触发发布门槛停止线（扩招暂停）."""
    return _norm(row.get("gate_incident")) == "是"


def compute_reuse_count(row: Mapping[str, Any]) -> int:
    """再用人数计数：口头再用或 7 日复扫任一为「是」→ 1."""
    if _norm(row.get("reuse_verbal")) == "是":
        return 1
    if _norm(row.get("reuse_rescan_7d")) == "是":
        return 1
    return 0


def compute_pay_signal(row: Mapping[str, Any]) -> bool:
    """假门 ②或③ 视为付费信号."""
    return _norm(row.get("pay_tier")) in ("2", "3")


def summarize_valid_children(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """对有效子女样本做 #28 速算（不代替人工最终判定）."""
    valid = [
        r
        for r in rows
        if _norm(r.get("valid_sample")) == "是"
        and _norm(r.get("role")) in ("子女", "配对子女")
        and "placeholder_row" not in validate_evidence_row(r)
    ]
    n = len(valid)
    reuse_n = sum(1 for r in valid if compute_reuse_count(r) >= 1)
    pay_n = sum(1 for r in valid if compute_pay_signal(r))
    incidents = sum(1 for r in rows if is_gate_blocking_incident(r))
    return {
        "valid_children_n": n,
        "reuse_n": reuse_n,
        "reuse_rate": (reuse_n / n) if n else 0.0,
        "pay_signal_n": pay_n,
        "gate_incidents_n": incidents,
        "enough_for_gate": n >= 8,
    }
