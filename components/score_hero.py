"""评分英雄区组件（设计稿：产品名+分数横向排布）."""

import streamlit as st
import streamlit.components.v1 as components

from utils.security import _safe


def _render_score_hero(
    score: int,
    product_name: str,
    show_slow_replay: bool = True,
    scan_date: str = "",
    status_label: str = "",
    status_meaning: str = "",
    score_class: str = "",
):
    """渲染新版评分摘要卡片.

    布局参考 result_optimized_v2.html：
    - 顶部横向：左侧产品名+识别时间，右侧放大分数圆形
    - 中部：圆角胶囊状态标签 + 状态含义
    - 底部：免责声明 + 慢速重听按钮
    - 分数圈带 popIn / pulseRing / rotateRing 动画
    可根据添加剂等级传入 status_*，避免「高分却写暂无问题」不一致。
    """
    if not (status_label and status_meaning and score_class):
        if score >= 80:
            status_label = status_label or "暂未发现明显问题"
            status_meaning = (
                status_meaning
                or "根据当前规则，暂未标出需特别注意的添加剂；仍请以包装与医嘱为准"
            )
            score_class = score_class or "score-safe"
        elif score >= 60:
            status_label = status_label or "有可留意项"
            status_meaning = status_meaning or "含少量需留意的成分，请结合自身情况查看"
            score_class = score_class or "score-caution"
        else:
            status_label = status_label or "含需关注成分"
            status_meaning = (
                status_meaning or "该食品含多种高关注配料，建议查看详情后再选择"
            )
            score_class = score_class or "score-danger"

    label = status_label
    meaning = status_meaning

    if score_class == "score-safe":
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<polyline points='20 6 9 17 4 12'/></svg>"
        )
    elif score_class == "score-caution":
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<path d='M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'/>"
            "<line x1='12' y1='9' x2='12' y2='13'/><line x1='12' y1='17' x2='12.01' y2='17'/></svg>"
        )
    else:
        pill_icon = (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<circle cx='12' cy='12' r='10'/><line x1='12' y1='8' x2='12' y2='12'/>"
            "<line x1='12' y1='16' x2='12.01' y2='16'/></svg>"
        )

    meta_html = ""
    if scan_date:
        meta_html = f"<p class='product-meta'>配料表识别于 {_safe(scan_date)}</p>"

    replay_btn = ""
    if show_slow_replay:
        replay_id = f"slow-replay-{score}"
        replay_btn = (
            f"<button id='{replay_id}' class='btn-replay food-scanner-tts-replay-btn' "
            f"data-action='replay' aria-label='慢速再读一遍'>"
            f"<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            f"stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
            f"<path d='M1 4v6h6'/><path d='M3.51 15a9 9 0 1 0 2.13-9.36L1 10'/></svg>"
            f"<span>慢速再读一遍</span></button>"
        )

    # data-target 供下方脚本做 0→score 滚动；先显示目标分避免脚本失败时空白
    st.markdown(
        f"<div class='score-card {score_class}'>"
        f"<div class='score-card-top'>"
        f"<div class='product-info'>"
        f"<h1 class='product-name'>{_safe(product_name)}</h1>"
        f"{meta_html}"
        f"</div>"
        f"<div class='score-circle'>"
        f"<div class='score-ring'></div>"
        f"<span class='score-number' data-score-target='{int(score)}'>{int(score)}</span>"
        f"<span class='score-label'>配料参考分</span>"
        f"</div></div>"
        f"<div class='status-pill'>{pill_icon}<span>{_safe(label)}</span></div>"
        f"<p class='score-card-subtitle'>{_safe(meaning)}</p>"
        f"<div class='score-card-footer'>"
        f"<p class='disclaimer'>结果仅供参考，不能代替医生诊断。"
        f"身体不适或患有疾病，请先咨询医生。</p>"
        f"{replay_btn}"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    # 分数滚动动画（读 parent DOM；不依赖用户手势）
    components.html(
        f"""
        <script>
        (function() {{
          try {{
            var doc = window.parent && window.parent.document;
            if (!doc) return;
            var nodes = doc.querySelectorAll('.score-number[data-score-target]');
            if (!nodes || !nodes.length) return;
            var el = nodes[nodes.length - 1];
            if (el.getAttribute('data-animated') === '1') return;
            el.setAttribute('data-animated', '1');
            var target = parseInt(el.getAttribute('data-score-target') || '0', 10) || 0;
            var duration = 900;
            var start = 0;
            var t0 = null;
            function easeOut(t) {{ return 1 - Math.pow(1 - t, 3); }}
            function frame(ts) {{
              if (t0 === null) t0 = ts;
              var p = Math.min(1, (ts - t0) / duration);
              var val = Math.round(start + (target - start) * easeOut(p));
              el.textContent = String(val);
              if (p < 1) {{
                window.parent.requestAnimationFrame(frame);
              }} else {{
                el.textContent = String(target);
              }}
            }}
            el.textContent = '0';
            window.parent.requestAnimationFrame(frame);
          }} catch (e) {{}}
        }})();
        </script>
        """,
        height=0,
    )
