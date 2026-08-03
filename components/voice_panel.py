"""语音播报：优先 edge-tts 自然女声，失败回退浏览器 SpeechSynthesis。"""

from __future__ import annotations

import base64
import html

import streamlit as st
import streamlit.components.v1 as components

_tts_counter = 0


def _next_tts_id(prefix: str) -> str:
    global _tts_counter
    _tts_counter += 1
    return f"{prefix}-{_tts_counter}"


def _text_to_b64(text: str) -> str:
    return base64.b64encode((text or "").encode("utf-8")).decode("ascii")


def _render_tts_namespace():
    """兼容 app.py 调用；语音逻辑已自包含。"""
    return


def _preload_tts_voices():
    components.html(
        """
        <script>
        (function() {
          try {
            var s = window.speechSynthesis;
            if (!s) return;
            s.getVoices();
          } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )


def voice_control_panel(
    speak_content: str,
    key_prefix: str = "tts",
    button_text: str = "听结果",
    wrapper_class: str = "voice-control-wrap",
):
    """听结果面板：云端自然语音优先，浏览器 TTS 兜底。"""
    if "tts_rate" not in st.session_state:
        st.session_state["tts_rate"] = 1.0

    rate = float(st.session_state["tts_rate"] or 1.0)
    text = (speak_content or "").strip()
    # button_text / wrapper_class 保留 API 兼容；面板标签用纯文本
    _ = wrapper_class
    if button_text and "慢" in str(button_text):
        pass

    # 尝试生成更自然的 MP3（edge-tts）
    audio_b64 = ""
    engine_label = "系统语音"
    try:
        from services.tts_engine import synthesize_mp3

        # 语速：edge 用 rate 字符串，浏览器用数字
        mp3 = synthesize_mp3(text)
        if mp3:
            audio_b64 = base64.b64encode(mp3).decode("ascii")
            engine_label = "自然女声"
    except Exception:
        audio_b64 = ""

    text_b64 = _text_to_b64(text)
    preview = text.replace("\n", " ").strip()
    if len(preview) > 36:
        preview = preview[:36] + "…"
    preview_esc = html.escape(preview, quote=True)
    uid = _next_tts_id(key_prefix.replace(" ", "_"))

    # playbackRate 近似 0.7 / 1.0 / 1.3
    components.html(
        f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  body {{ margin:0; padding:4px 0 6px; font-family: -apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:transparent; }}
  .wrap {{ display:flex; flex-wrap:wrap; gap:10px; width:100%; }}
  button {{ font-family:inherit; cursor:pointer; border-radius:999px; font-weight:700; border:none;
    min-height:52px; padding:12px 18px; font-size:17px; -webkit-tap-highlight-color:transparent; }}
  #speak-{uid} {{ flex:1 1 100%; background:linear-gradient(135deg,#2E7D32,#43A047); color:#fff;
    box-shadow:0 4px 14px rgba(46,125,50,.28); }}
  #stop-{uid} {{ flex:1 1 auto; min-width:96px; background:#fff; color:#555; border:2px solid #ddd; }}
  #err-{uid} {{ width:100%; color:#C62828; font-size:14px; min-height:1.2em; }}
  #meta-{uid} {{ width:100%; color:#888; font-size:12px; }}
  audio {{ display:none; }}
</style></head><body>
<div class="wrap">
  <button type="button" id="speak-{uid}">听结果</button>
  <button type="button" id="stop-{uid}">停止</button>
  <div id="err-{uid}"></div>
  <div id="meta-{uid}">音色：{html.escape(engine_label)} · 预览：{preview_esc}</div>
</div>
<audio id="audio-{uid}" playsinline></audio>
<script>
(function() {{
  var AUDIO_B64 = "{audio_b64}";
  var TEXT_B64 = "{text_b64}";
  var RATE = {rate};
  var speakBtn = document.getElementById("speak-{uid}");
  var stopBtn = document.getElementById("stop-{uid}");
  var errEl = document.getElementById("err-{uid}");
  var audio = document.getElementById("audio-{uid}");
  var label0 = "听结果";
  var synth = window.speechSynthesis;
  var queueIdx = 0, chunks = [], selectedVoice = null;

  function setErr(m) {{ if (errEl) errEl.textContent = m || ""; }}
  function b64ToUtf8(b64) {{
    try {{
      var bin = atob(b64);
      var bytes = new Uint8Array(bin.length);
      for (var i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
      return new TextDecoder("utf-8").decode(bytes);
    }} catch(e) {{ return ""; }}
  }}
  function pickZhVoice(s) {{
    var voices=[]; try {{ voices=s.getVoices()||[]; }} catch(e) {{}}
    var pref=["xiaoxiao","晓晓","yaoyao","tingting","google 普通话","google 中文","chinese"];
    for (var j=0;j<pref.length;j++) for (var i=0;i<voices.length;i++) {{
      var n=(voices[i].name||"").toLowerCase();
      if (n.indexOf(pref[j])>=0) return voices[i];
    }}
    for (var k=0;k<voices.length;k++) {{
      var lang=(voices[k].lang||"").toLowerCase();
      if (lang.indexOf("zh")===0||lang.indexOf("cmn")===0) return voices[k];
    }}
    return null;
  }}
  function splitChunks(text, maxLen) {{
    text=(text||"").replace(/\\s+/g," ").trim();
    if (!text) return [];
    var parts=text.split(/([。！？；\\n]+)/), buf="", out=[];
    for (var i=0;i<parts.length;i++) {{
      var p=parts[i]; if(!p) continue;
      if ((buf+p).length<=maxLen) buf+=p;
      else {{ if(buf) out.push(buf); if(p.length<=maxLen) buf=p; else {{
        for(var k=0;k<p.length;k+=maxLen) out.push(p.slice(k,k+maxLen)); buf="";
      }} }}
    }}
    if (buf) out.push(buf);
    return out.length?out:[text.slice(0,maxLen)];
  }}
  function finish() {{
    if (speakBtn) {{ speakBtn.disabled=false; speakBtn.innerHTML=label0; }}
  }}
  function speakBrowser() {{
    if (!synth) {{
      setErr("当前环境不支持语音。请用 Safari/Chrome 打开（微信内请点···→在浏览器打开）。");
      finish(); return;
    }}
    var text = b64ToUtf8(TEXT_B64);
    if (!text.trim()) {{ setErr("没有可播报内容"); finish(); return; }}
    try {{ synth.cancel(); }} catch(e) {{}}
    try {{ synth.resume(); }} catch(e) {{}}
    selectedVoice = pickZhVoice(synth);
    var mobile = /iPhone|iPad|Android|Mobile/i.test(navigator.userAgent||"");
    chunks = splitChunks(text, mobile?50:100);
    queueIdx = 0;
    function next() {{
      if (queueIdx>=chunks.length) {{ finish(); return; }}
      var u = new SpeechSynthesisUtterance(chunks[queueIdx]);
      u.lang="zh-CN"; u.rate=RATE||1; u.volume=1;
      if (selectedVoice) try {{ u.voice=selectedVoice; }} catch(e) {{}}
      u.onend=function(){{ queueIdx++; next(); }};
      u.onerror=function(e){{
        var t=""; try{{t=(e.error||"").toString().toLowerCase();}}catch(x){{}}
        if (t.indexOf("interrupted")>=0||t.indexOf("canceled")>=0) {{ finish(); return; }}
        setErr("播报失败。微信内请改用系统浏览器；并检查手机未静音。");
        finish();
      }};
      try {{ synth.speak(u); }} catch(e) {{ setErr("播报失败"); finish(); }}
    }}
    next();
  }}
  function speakCloud() {{
    if (!AUDIO_B64) {{ speakBrowser(); return; }}
    try {{
      audio.src = "data:audio/mpeg;base64," + AUDIO_B64;
      audio.playbackRate = RATE || 1.0;
      var p = audio.play();
      if (p && p.then) {{
        p.then(function(){{ setErr(""); }})
         .catch(function(){{
           setErr("自动播放被拦截，已改用系统语音…");
           speakBrowser();
         }});
      }}
      audio.onended = function(){{ finish(); }};
      audio.onerror = function(){{ setErr("音频播放失败，改用系统语音…"); speakBrowser(); }};
    }} catch(e) {{ speakBrowser(); }}
  }}

  if (speakBtn) speakBtn.addEventListener("click", function(ev) {{
    ev.preventDefault();
    setErr("");
    speakBtn.innerHTML = "播报中…";
    speakBtn.disabled = true;
    if (AUDIO_B64) speakCloud(); else speakBrowser();
  }});
  if (stopBtn) stopBtn.addEventListener("click", function(ev) {{
    ev.preventDefault();
    try {{ if (synth) synth.cancel(); }} catch(e) {{}}
    try {{ audio.pause(); audio.currentTime=0; }} catch(e) {{}}
    finish(); setErr("");
  }});
  if (/MicroMessenger/i.test(navigator.userAgent||"")) {{
    setErr("提示：微信内可能无声。请点右上角 ··· → 在浏览器打开后再听。");
  }}
}})();
</script>
</body></html>
        """,
        height=140,
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
        st.caption("改完语速后请再点一次「听结果」。自然女声需联网首次生成。")
