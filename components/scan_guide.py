"""扫描页 UI/UX：拍得清三步引导、对比图、失败恢复."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import streamlit as st

from utils.security import _safe

# design/demo_assets 相对项目根
_ASSET_DIR = Path(__file__).resolve().parent.parent / "design" / "demo_assets"
_CLEAR_IMG = _ASSET_DIR / "demo_case_clear.png"
_BLUR_IMG = _ASSET_DIR / "demo_case_blur.png"

FailKind = Literal[
    "json", "network", "format", "oversize", "generic", "auth", "busy", "parse"
]


def build_scan_hero_html() -> str:
    """主标题 + 取景示意（纯 CSS 四角框，不依赖图片）."""
    return (
        "<div class='scan-hero'>"
        "<p class='scan-page-tip'>对准包装上的「配料表」拍照</p>"
        "<p class='scan-page-tip-sub'>"
        "不要只拍商品名那一面；小字越清楚，识别越稳"
        "</p>"
        "<div class='scan-viewfinder' aria-hidden='true'>"
        "<span class='scan-vf-corner scan-vf-tl'></span>"
        "<span class='scan-vf-corner scan-vf-tr'></span>"
        "<span class='scan-vf-corner scan-vf-bl'></span>"
        "<span class='scan-vf-corner scan-vf-br'></span>"
        "<div class='scan-viewfinder-label'>把「配料」二字放进框内</div>"
        "</div>"
        "</div>"
    )


def build_scan_steps_html() -> str:
    """三步硬引导：光线 / 平行 / 占满."""
    steps = [
        ("1", "光线够", "靠近窗边或开灯，避免反光发白"),
        ("2", "尽量平", "手机与包装平行，不要歪着拍"),
        ("3", "字要大", "配料小字尽量占满画面再拍"),
    ]
    items = []
    for num, title, desc in steps:
        items.append(
            "<div class='scan-step-card'>"
            f"<div class='scan-step-num'>{_safe(num)}</div>"
            "<div class='scan-step-body'>"
            f"<div class='scan-step-title'>{_safe(title)}</div>"
            f"<p class='scan-step-desc'>{_safe(desc)}</p>"
            "</div></div>"
        )
    return "<div class='scan-steps' role='list'>" + "".join(items) + "</div>"


def build_scan_fail_html(kind: FailKind = "generic") -> str:
    """识别失败后的恢复引导（大字 + 三步复盘）."""
    titles = {
        "json": "没能读懂这张图",
        "network": "识别服务暂时连不上",
        "format": "文件好像不是有效图片",
        "oversize": "图片太大了（超过 5MB）",
        "auth": "识别密钥无效（不是照片问题）",
        "busy": "识别服务正忙",
        "parse": "结果解析失败",
        "generic": "这次没识别成功",
    }
    leads = {
        "json": "多半是拍糊、反光，或只拍了包装正面。按下面三步重拍，成功率更高。",
        "network": "服务超时或网络不通。您的照片可能没问题，请检查网络后重试；管理员需确认 API 可用。",
        "format": "请重新选择 jpg 或 png 图片。",
        "oversize": "请压缩图片、截图配料区域后再传。",
        "auth": "请更新环境变量 MIMO_API_KEY（或 AGNES_API_KEY）后重启应用。与是否对准配料表无关。",
        "busy": "请稍等半分钟再点「开始识别」。",
        "parse": "服务有返回但格式异常，请重试一次；仍失败可换更清晰的配料表特写。",
        "generic": "请按下面提示重拍配料表，再试一次。",
    }
    title = titles.get(kind, titles["generic"])
    lead = leads.get(kind, leads["generic"])
    return (
        "<div class='scan-fail-card' role='alert'>"
        f"<p class='scan-fail-title'>{_safe(title)}</p>"
        f"<p class='scan-fail-lead'>{_safe(lead)}</p>"
        "<div class='scan-fail-steps'>"
        "<div class='scan-fail-step'><span>1</span>光线充足，避开反光</div>"
        "<div class='scan-fail-step'><span>2</span>手机与包装平行</div>"
        "<div class='scan-fail-step'><span>3</span>「配料」小字占满画面</div>"
        "</div>"
        "</div>"
    )


def render_scan_compare_examples() -> None:
    """清晰 vs 模糊对比（有资源则展示，无则跳过）."""
    if not (_CLEAR_IMG.is_file() and _BLUR_IMG.is_file()):
        return
    st.markdown(
        "<p class='scan-compare-title'>拍成这样更容易成功</p>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.image(str(_CLEAR_IMG), caption="✓ 清晰 · 配料字清楚", width="stretch")
    with c2:
        st.image(str(_BLUR_IMG), caption="✗ 模糊 · 容易失败", width="stretch")


def render_scan_guide_block(*, show_compare: bool = True) -> None:
    """扫描页完整引导块：英雄区 + 三步 + 可选对比图."""
    st.markdown(
        "<div class='scan-page-tip-wrap'>"
        + build_scan_hero_html()
        + build_scan_steps_html()
        + "</div>",
        unsafe_allow_html=True,
    )
    if show_compare:
        render_scan_compare_examples()


def render_scan_fail_block(kind: FailKind = "generic") -> None:
    """失败态卡片 + 对比图强化记忆."""
    st.markdown(build_scan_fail_html(kind), unsafe_allow_html=True)
    render_scan_compare_examples()
