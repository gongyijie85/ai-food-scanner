"""语音播报面板组件（浏览器原生 SpeechSynthesis，零依赖）."""

import streamlit as st
import streamlit.components.v1 as components

from components.icons import _ICON_MUTE_JS, _ICON_SPEAKER, _ICON_SPEAKER_JS
from utils.security import _safe

# 播报按钮全局递增 ID，避免时间戳冲突
_tts_counter = 0


def _next_tts_id(prefix: str) -> str:
    """生成唯一的 TTS 元素 ID."""
    global _tts_counter
    _tts_counter += 1
    return f"{prefix}-{_tts_counter}"


def _render_tts_namespace():
    """通过 iframe 注入全局语音播报命名空间与按钮事件绑定（幂等）.

    Streamlit 的 st.markdown 会过滤 <script>，导致脚本不执行；
    使用 st.components.v1.html 在隐藏 iframe 中执行脚本，并把函数挂到
    window.parent。

    关键兼容：Streamlit/React 在 hydration 时会剥离 HTML 元素的
    onclick="..." 字符串属性，因此按钮不能依赖内联 onclick。
    这里改为在父页面用 MutationObserver 自动发现带
    .food-scanner-tts-btn / .food-scanner-tts-stop-btn /
    .food-scanner-tts-replay-btn 类的元素，并通过 addEventListener 绑定点击
    事件，确保事件在用户手势同步路径中触发 speechSynthesis.speak()，同时
    避免 React hydration 剥离内联 onclick。
    """
    components.html(
        """
        <script>
        (function() {
            var parent = null;
            try {
                parent = window.parent;
                if (!parent || !parent.document || !parent.speechSynthesis) {
                    throw new Error('parent context unavailable');
                }
            } catch (e) {
                var fallback = {
                    speak: function() { alert('语音组件加载失败，请刷新页面后重试'); },
                    stop: function() {}
                };
                try { if (window.parent) window.parent.foodScannerTts = fallback; } catch(_) {}
                window.foodScannerTts = fallback;
                return;
            }

            function bindTtsButton(btn) {
                if (!btn || btn.__foodScannerTtsBound) return;
                btn.__foodScannerTtsBound = true;
                var action = btn.getAttribute('data-action') || 'speak';
                if (action === 'stop') {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        parent.foodScannerTts.stop();
                    });
                    return;
                }
                if (action === 'replay') {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        var scope = btn.closest('.result-score-hero') || parent.document;
                        var voiceBtn = scope.querySelector('.food-scanner-tts-btn');
                        if (voiceBtn) voiceBtn.click();
                    });
                    return;
                }
                var errId = btn.getAttribute('data-err-id') || '';
                var text = btn.getAttribute('data-text') || '';
                var rate = parseFloat(btn.getAttribute('data-rate') || '1.0') || 1.0;
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    parent.foodScannerTts.speak(btn.id, errId, text, rate);
                });
            }

            function bindAllTtsButtons() {
                var btns = parent.document.querySelectorAll('.food-scanner-tts-btn, .food-scanner-tts-stop-btn, .food-scanner-tts-replay-btn');
                for (var i = 0; i < btns.length; i++) {
                    bindTtsButton(btns[i]);
                }
            }

            parent.foodScannerTts = parent.foodScannerTts || {
                speak: function(btnId, errId, text, rate) {
                    var btn = parent.document.getElementById(btnId);
                    var err = parent.document.getElementById(errId);
                    var synth = parent.speechSynthesis;
                    if (!synth) {
                        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="voice-btn-icon">ICON_MUTE</span> 不支持播报'; }
                        if (err) err.textContent = '您的浏览器不支持语音播报功能';
                        return;
                    }
                    var originalHtml = btn ? btn.innerHTML : '';
                    if (btn) btn.innerHTML = '<span class="voice-btn-icon">ICON_SPEAKER</span> 播报中…';
                    if (err) err.textContent = '';

                    try { synth.cancel(); } catch(e) {}
                    try { synth.resume(); } catch(e) {}

                    var u = new parent.SpeechSynthesisUtterance(text);
                    u.lang = 'zh-CN';
                    u.rate = rate;
                    u.pitch = 1.0;
                    u.volume = 1.0;

                    var voices = synth.getVoices();
                    var selected = null;
                    for (var i = 0; i < voices.length; i++) {
                        var name = voices[i].name || '';
                        var lang = voices[i].lang || '';
                        var lowerName = name.toLowerCase();
                        if (!selected && (lowerName.indexOf('xiaoxiao') >= 0 || lowerName.indexOf('晓晓') >= 0)) {
                            selected = voices[i];
                        }
                        if (!selected && (lowerName.indexOf('yaoyao') >= 0 || lowerName.indexOf('瑶瑶') >= 0)) {
                            selected = voices[i];
                        }
                        if (!selected && name.indexOf('Google 普通话') >= 0) {
                            selected = voices[i];
                        }
                        if (!selected && name.indexOf('Google 中文') >= 0) {
                            selected = voices[i];
                        }
                        if (!selected && (lang.indexOf('zh-CN') === 0 || lang.indexOf('cmn-CN') === 0)) {
                            selected = voices[i];
                        }
                    }
                    if (selected) u.voice = selected;

                    u.onend = function() {
                        if (btn) btn.innerHTML = originalHtml;
                        if (err) err.textContent = '';
                    };
                    u.onerror = function(e) {
                        if (btn) btn.innerHTML = originalHtml;
                        var errMsg = '播报失败，请尝试刷新页面或调高手机音量';
                        try {
                            var errType = (e && (e.error || e.type || e.message || '')).toString().toLowerCase();
                            if (errType.indexOf('not-allowed') >= 0 || errType.indexOf('notallowed') >= 0) {
                                errMsg = '浏览器阻止了语音播放，请刷新后点击页面任意位置再试';
                            }
                        } catch(_) {}
                        if (err) err.textContent = errMsg;
                        console.warn('[TTS error]', e);
                    };

                    try {
                        synth.speak(u);
                    } catch(e) {
                        if (btn) btn.innerHTML = originalHtml;
                        if (err) err.textContent = '播报失败，请刷新页面后重试';
                        console.warn('[TTS speak]', e);
                    }
                },
                stop: function() {
                    try { parent.speechSynthesis.cancel(); } catch(e) {}
                }
            };

            bindAllTtsButtons();

            try {
                var observer = new parent.MutationObserver(function(mutations) {
                    bindAllTtsButtons();
                });
                observer.observe(parent.document.body, { childList: true, subtree: true });
            } catch(e) {
                console.warn('[TTS observer]', e);
            }
        })();
        </script>
        """.replace("ICON_MUTE", _ICON_MUTE_JS).replace(
            "ICON_SPEAKER", _ICON_SPEAKER_JS
        ),
        height=0,
    )


def voice_control_panel(
    speak_content: str,
    key_prefix: str = "tts",
    button_text: str = f"{_ICON_SPEAKER} 点击播报",
    wrapper_class: str = "voice-control-wrap",
):
    """语音播报控制面板：简洁版，主按钮+折叠的语速控制.

    使用浏览器原生 Web Speech API，针对 iOS Safari / 微信内置浏览器等
    移动端环境做了兼容处理：
    - 点击按钮时立即 cancel 并 speak，保证处于用户手势上下文。
    - 提供可视化反馈与明确的错误提示。

    wrapper_class: 外层 div 的 class，默认 voice-control-wrap；
    结果页可传 'voice-float-bar voice-control-wrap' 实现 sticky 浮动效果。
    """
    if "tts_rate" not in st.session_state:
        st.session_state["tts_rate"] = 1.0

    rate = st.session_state["tts_rate"]
    safe = _safe(speak_content)
    btn_id = _next_tts_id(f"tts-btn-{key_prefix}")
    stop_btn_id = _next_tts_id(f"tts-stop-{key_prefix}")
    err_id = _next_tts_id(f"tts-err-{key_prefix}")

    _render_tts_namespace()
    html_block = (
        f"<div class='{wrapper_class} voice-control-inline'>"
        f"<button id='{btn_id}' aria-label='语音播报识别结果' "
        f"class='food-scanner-tts-btn voice-float-btn' data-action='speak' "
        f"data-err-id='{err_id}' data-text='{safe}' data-rate='{rate}'>"
        f"{button_text}</button>"
        f"<button id='{stop_btn_id}' class='food-scanner-tts-stop-btn voice-stop-btn' "
        f"data-action='stop' aria-label='停止播报'>停止</button>"
        f"<span id='{err_id}' class='tts-err'></span>"
        f"</div>"
    )
    st.markdown(html_block, unsafe_allow_html=True)

    with st.expander("语速调整"):
        rate_options = ["0.7x 慢速", "1.0x 正常", "1.3x 快速"]
        rate_values = [0.7, 1.0, 1.3]
        cur_idx = 1
        try:
            cur_idx = rate_values.index(st.session_state["tts_rate"])
        except ValueError:
            cur_idx = 1
        chosen = st.radio(
            "选择语速",
            rate_options,
            index=cur_idx,
            horizontal=True,
            key=f"{key_prefix}_rate_radio",
            label_visibility="collapsed",
        )
        st.session_state["tts_rate"] = rate_values[rate_options.index(chosen)]


def _preload_tts_voices():
    """页面加载时预加载浏览器语音列表，提升首次点击播报成功率."""
    components.html(
        """
        <script>
        (function() {
            var parent = null;
            try {
                parent = window.parent;
                if (!parent || !parent.speechSynthesis) return;
            } catch(e) { return; }
            function loadVoices() {
                try { parent.speechSynthesis.getVoices(); } catch(e) {}
            }
            loadVoices();
            if (parent.speechSynthesis.onvoiceschanged !== undefined) {
                parent.speechSynthesis.onvoiceschanged = loadVoices;
            }
        })();
        </script>
        """,
        height=0,
    )
