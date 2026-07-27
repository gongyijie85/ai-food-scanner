"""语音播报面板：浏览器 SpeechSynthesis，组件内同文档点击+播放（修手机无声）。"""

from __future__ import annotations

import base64
import html

import streamlit as st
import streamlit.components.v1 as components

from components.icons import _ICON_SPEAKER

# 播报按钮全局递增 ID（兼容旧调用）
_tts_counter = 0


def _next_tts_id(prefix: str) -> str:
    """生成唯一的 TTS 元素 ID."""
    global _tts_counter
    _tts_counter += 1
    return f"{prefix}-{_tts_counter}"


def _text_to_b64(text: str) -> str:
    """UTF-8 文本转 base64，避免 HTML 属性转义破坏中文。"""
    return base64.b64encode((text or "").encode("utf-8")).decode("ascii")


def _render_tts_namespace():
    """保留空实现：语音已改为组件内自包含，无需再向 parent 注入.

    仍被 app.py 调用，避免改动入口。
    """
    return


def _preload_tts_voices():
    """页面加载时预热 voices（可选，失败无影响）."""
    components.html(
        """
        <script>
        (function() {
          try {
            var s = window.speechSynthesis;
            if (!s) return;
            s.getVoices();
            if (typeof s.onvoiceschanged !== 'undefined') {
              s.onvoiceschanged = function() { try { s.getVoices(); } catch(e) {} };
            }
          } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )


def voice_control_panel(
    speak_content: str,
    key_prefix: str = "tts",
    button_text: str = f"{_ICON_SPEAKER} 听结果",
    wrapper_class: str = "voice-control-wrap",
):
    """语音播报控制面板.

    关键修复：按钮与 speechSynthesis.speak 必须在同一文档、同一点击回调里，
    不能再用「iframe 脚本绑定 parent 按钮」——在手机 Safari / 微信里会无声。

    实现：整个面板用 st.components.v1.html 自包含；文案用 base64 传入。
    """
    if "tts_rate" not in st.session_state:
        st.session_state["tts_rate"] = 1.0

    rate = float(st.session_state["tts_rate"] or 1.0)
    # 去掉 HTML 标签（按钮文案可能带 SVG）
    plain_label = "听结果"
    if "慢" in (button_text or ""):
        plain_label = "听结果（慢速）"
    elif button_text and "播报" in button_text:
        plain_label = "听结果"

    text_b64 = _text_to_b64(speak_content or "")
    # 供无障碍：截断预览
    preview = (speak_content or "").replace("\n", " ").strip()
    if len(preview) > 40:
        preview = preview[:40] + "…"
    preview_esc = html.escape(preview, quote=True)

    # 唯一 id，避免同页多实例冲突
    uid = _next_tts_id(key_prefix.replace(" ", "_"))

    components.html(
        f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 4px 0 8px 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
      "Microsoft YaHei", sans-serif;
    background: transparent;
  }}
  .wrap {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: stretch;
    width: 100%;
  }}
  button {{
    font-family: inherit;
    cursor: pointer;
    border-radius: 999px;
    font-weight: 700;
    border: none;
    min-height: 52px;
    padding: 12px 18px;
    font-size: 17px;
    -webkit-tap-highlight-color: transparent;
  }}
  #speak-{uid} {{
    flex: 1 1 100%;
    background: linear-gradient(135deg, #2E7D32, #43A047);
    color: #fff;
    box-shadow: 0 4px 14px rgba(46, 125, 50, 0.28);
  }}
  #speak-{uid}:active {{ transform: scale(0.98); }}
  #speak-{uid}:disabled {{ opacity: 0.7; }}
  #stop-{uid} {{
    flex: 1 1 auto;
    min-width: 96px;
    background: #fff;
    color: #555;
    border: 2px solid #ddd;
  }}
  #err-{uid} {{
    width: 100%;
    color: #C62828;
    font-size: 14px;
    line-height: 1.4;
    min-height: 1.2em;
    margin-top: 4px;
  }}
  #hint-{uid} {{
    width: 100%;
    color: #888;
    font-size: 12px;
    line-height: 1.3;
  }}
</style>
</head>
<body>
  <div class="wrap {html.escape(wrapper_class, quote=True)}">
    <button type="button" id="speak-{uid}" aria-label="语音播报识别结果">{html.escape(plain_label)}</button>
    <button type="button" id="stop-{uid}" aria-label="停止播报">停止</button>
    <div id="err-{uid}"></div>
    <div id="hint-{uid}">预览：{preview_esc}</div>
  </div>
  <script>
  (function() {{
    var TEXT_B64 = "{text_b64}";
    var RATE = {rate};
    var speakBtn = document.getElementById("speak-{uid}");
    var stopBtn = document.getElementById("stop-{uid}");
    var errEl = document.getElementById("err-{uid}");
    var labelDefault = speakBtn ? speakBtn.innerHTML : "听结果";

    function b64ToUtf8(b64) {{
      try {{
        var bin = atob(b64);
        var bytes = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        if (typeof TextDecoder !== "undefined") {{
          return new TextDecoder("utf-8").decode(bytes);
        }}
        // 旧环境回退
        return decodeURIComponent(escape(bin));
      }} catch (e) {{
        return "";
      }}
    }}

    function setErr(msg) {{
      if (errEl) errEl.textContent = msg || "";
    }}

    function pickZhVoice(synth) {{
      var voices = [];
      try {{ voices = synth.getVoices() || []; }} catch (e) {{ voices = []; }}
      var preferred = [
        "xiaoxiao", "晓晓", "yaoyao", "瑶瑶", "tingting", "婷婷",
        "meijia", "美佳", "google 普通话", "google 中文",
        "chinese (simplified)", "sin-ji", "sinji", "siri"
      ];
      var i, j, name, lang, lower;
      for (j = 0; j < preferred.length; j++) {{
        var key = preferred[j];
        for (i = 0; i < voices.length; i++) {{
          name = voices[i].name || "";
          lower = name.toLowerCase();
          if (lower.indexOf(key) >= 0 || name.indexOf(key) >= 0) return voices[i];
        }}
      }}
      for (i = 0; i < voices.length; i++) {{
        lang = (voices[i].lang || "").toLowerCase();
        if (lang.indexOf("zh") === 0 || lang.indexOf("cmn") === 0) return voices[i];
      }}
      return null;
    }}

    function splitChunks(text, maxLen) {{
      maxLen = maxLen || 80;
      text = (text || "").replace(/\\s+/g, " ").trim();
      if (!text) return [];
      var chunks = [];
      var parts = text.split(/([。！？；\\n]+)/);
      var buf = "";
      for (var i = 0; i < parts.length; i++) {{
        var p = parts[i];
        if (!p) continue;
        if ((buf + p).length <= maxLen) {{
          buf += p;
        }} else {{
          if (buf) chunks.push(buf);
          if (p.length <= maxLen) {{
            buf = p;
          }} else {{
            for (var k = 0; k < p.length; k += maxLen) {{
              chunks.push(p.slice(k, k + maxLen));
            }}
            buf = "";
          }}
        }}
      }}
      if (buf) chunks.push(buf);
      return chunks.length ? chunks : [text.slice(0, maxLen)];
    }}

    var synth = window.speechSynthesis;
    var speaking = false;
    var queueIdx = 0;
    var chunks = [];
    var selectedVoice = null;

    if (synth) {{
      try {{
        synth.getVoices();
        if (typeof synth.onvoiceschanged !== "undefined") {{
          synth.onvoiceschanged = function() {{
            selectedVoice = pickZhVoice(synth);
          }};
        }}
        selectedVoice = pickZhVoice(synth);
      }} catch (e) {{}}
    }}

    function finishOk() {{
      speaking = false;
      if (speakBtn) {{
        speakBtn.disabled = false;
        speakBtn.innerHTML = labelDefault;
      }}
    }}

    function finishErr(msg) {{
      speaking = false;
      if (speakBtn) {{
        speakBtn.disabled = false;
        speakBtn.innerHTML = labelDefault;
      }}
      setErr(msg);
    }}

    function speakNext() {{
      if (!synth) return;
      if (queueIdx >= chunks.length) {{
        finishOk();
        return;
      }}
      var u = new SpeechSynthesisUtterance(chunks[queueIdx]);
      u.lang = "zh-CN";
      u.rate = RATE || 1.0;
      u.pitch = 1.0;
      u.volume = 1.0;
      if (selectedVoice) {{
        try {{ u.voice = selectedVoice; }} catch (e) {{}}
      }}
      u.onend = function() {{
        queueIdx += 1;
        speakNext();
      }};
      u.onerror = function(e) {{
        var t = "";
        try {{ t = (e && (e.error || e.type || "")).toString().toLowerCase(); }} catch (x) {{}}
        if (t.indexOf("interrupted") >= 0 || t.indexOf("canceled") >= 0) {{
          finishOk();
          return;
        }}
        if (t.indexOf("not-allowed") >= 0) {{
          finishErr("浏览器拦截了语音。请用系统 Safari/Chrome 打开（勿用微信内打开），并允许声音。");
          return;
        }}
        finishErr("播报失败，请调高音量后重试；微信内置浏览器可能不支持语音。");
      }};
      try {{
        synth.speak(u);
      }} catch (e) {{
        finishErr("播报失败：" + (e && e.message ? e.message : "未知错误"));
      }}
    }}

    if (speakBtn) {{
      speakBtn.addEventListener("click", function(ev) {{
        // 必须在本点击回调内同步启动第一句 speak
        ev.preventDefault();
        setErr("");
        if (!synth) {{
          setErr("当前环境不支持语音播报。请用手机 Safari 或 Chrome 打开本页（不要用微信内打开）。");
          return;
        }}
        var text = b64ToUtf8(TEXT_B64);
        if (!text || !text.trim()) {{
          setErr("没有可播报的内容");
          return;
        }}
        try {{ synth.cancel(); }} catch (e) {{}}
        try {{ synth.resume(); }} catch (e) {{}}

        selectedVoice = pickZhVoice(synth) || selectedVoice;
        var ua = navigator.userAgent || "";
        var isMobile = /iPhone|iPad|iPod|Android|Mobile/i.test(ua);
        chunks = splitChunks(text, isMobile ? 50 : 100);
        queueIdx = 0;
        speaking = true;
        speakBtn.innerHTML = "播报中…";
        speakBtn.disabled = true;

        // 直接在用户手势中启动（不要先 speak 空句再 cancel，会把队列清掉）
        speakNext();
      }});
    }}

    if (stopBtn) {{
      stopBtn.addEventListener("click", function(ev) {{
        ev.preventDefault();
        try {{ if (synth) synth.cancel(); }} catch (e) {{}}
        chunks = [];
        queueIdx = 0;
        finishOk();
        setErr("");
      }});
    }}

    // 能力检测提示
    if (!synth) {{
      setErr("此浏览器无语音能力。请用 Safari / Chrome 打开链接。");
    }} else if (/MicroMessenger/i.test(navigator.userAgent || "")) {{
      setErr("提示：微信内打开经常无声音。请点右上角 ··· → 在浏览器打开。");
    }}
  }})();
  </script>
</body>
</html>
        """,
        height=130,
    )

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
        st.caption("改完语速后，请再点一次「听结果」。")
