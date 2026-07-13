"""TTS 统一对比页：在同一界面试听浏览器 TTS / edge-tts / Kokoro.

运行方法：
    1. 进入本目录：cd demos/tts_comparison
    2. 安装依赖：pip install -r requirements_demo.txt
    3. 启动：streamlit run tts_compare_app.py
    4. 在浏览器中输入文字，点击三种方案按钮试听

说明：
    - 浏览器 TTS 直接在页面上朗读
    - edge-tts 和 Kokoro 会生成临时音频文件，通过 st.audio 播放
"""

import asyncio
import html
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# 页面配置
st.set_page_config(
    page_title="TTS 方案对比",
    page_icon="🔊",
    layout="centered",
)

# 默认测试文本
DEFAULT_TEXT = (
    "评分 88 分。按当前档案暂未发现高风险配料。"
    "本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生。"
)

# 注入浏览器 TTS 所需的 JavaScript 命名空间与按钮事件绑定
_BROWSER_TTS_JS = """
<script>
(function() {
    var parent = null;
    try {
        parent = window.parent;
        if (!parent || !parent.document || !parent.speechSynthesis) {
            throw new Error('parent context unavailable');
        }
    } catch (e) {
        console.warn('[TTS] parent context unavailable');
        return;
    }

    function pickVoice() {
        var voices = parent.speechSynthesis.getVoices();
        var selected = null;
        selected = voices.find(function(v) { return /xiaoxiao|晓晓/i.test(v.name); });
        if (!selected) selected = voices.find(function(v) { return /yaoyao|瑶瑶/i.test(v.name); });
        if (!selected) selected = voices.find(function(v) { return v.name.indexOf('Google 普通话') >= 0; });
        if (!selected) selected = voices.find(function(v) { return v.name.indexOf('Google 中文') >= 0; });
        if (!selected) selected = voices.find(function(v) { return /^zh-CN|^cmn-CN/i.test(v.lang); });
        return selected;
    }

    function bindBtn(btn) {
        if (!btn || btn.__ttsBound) return;
        btn.__ttsBound = true;
        var action = btn.getAttribute('data-action');
        var text = btn.getAttribute('data-text') || '';
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (action === 'stop') {
                try { parent.speechSynthesis.cancel(); } catch(err) {}
                return;
            }
            var synth = parent.speechSynthesis;
            synth.cancel();
            try { synth.resume(); } catch(err) {}
            var u = new parent.SpeechSynthesisUtterance(text);
            u.lang = 'zh-CN';
            u.rate = 1.0;
            u.pitch = 1.0;
            u.volume = 1.0;
            var voice = pickVoice();
            if (voice) u.voice = voice;
            synth.speak(u);
        });
    }

    function bindAll() {
        var btns = parent.document.querySelectorAll('.tts-compare-btn');
        for (var i = 0; i < btns.length; i++) {
            bindBtn(btns[i]);
        }
    }

    bindAll();
    try {
        var observer = new parent.MutationObserver(function() { bindAll(); });
        observer.observe(parent.document.body, { childList: true, subtree: true });
    } catch(err) {
        console.warn('[TTS observer]', err);
    }
})();
</script>
"""


def _inject_browser_tts() -> None:
    """通过 iframe 注入浏览器 TTS 全局对象与事件绑定."""
    components.html(_BROWSER_TTS_JS, height=0)


def _safe(text: str) -> str:
    """对 HTML 属性中的文本做安全转义."""
    return html.escape(text, quote=True)


def render_browser_tts_section(text: str) -> None:
    """渲染浏览器原生 TTS 试听区."""
    st.subheader("1. 浏览器原生 TTS")
    st.caption("当前 ai-food-scanner 项目使用的方案，依赖浏览器内置语音列表")

    _inject_browser_tts()

    # 使用 class + data-* 属性，由上方 JS 通过 MutationObserver 绑定点击事件
    safe_text = _safe(text)
    html_block = (
        f"<button class='tts-compare-btn' data-action='speak' data-text='{safe_text}' "
        f"style='font-size:20px;padding:16px 24px;border:none;border-radius:12px;"
        f"background:#2E7D32;color:white;cursor:pointer;margin-right:12px;'>"
        f"朗读</button>"
        f"<button class='tts-compare-btn' data-action='stop' "
        f"style='font-size:20px;padding:16px 24px;border:2px solid #2E7D32;"
        f"border-radius:12px;background:white;color:#2E7D32;cursor:pointer;'>"
        f"停止</button>"
    )
    st.markdown(html_block, unsafe_allow_html=True)


def render_edge_tts_section(text: str) -> None:
    """渲染 edge-tts 试听区."""
    st.subheader("2. edge-tts")
    st.caption("调用微软在线语音接口，需要联网")

    if st.button("生成并播放 edge-tts", key="edge_tts_btn"):
        try:
            import edge_tts
        except ImportError:
            st.error("未安装 edge-tts，请运行：pip install edge-tts")
            return

        output_path = Path("edge_tts_compare.mp3")
        with st.spinner("正在调用 edge-tts，请稍候..."):
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            asyncio.run(communicate.save(str(output_path)))

        if output_path.exists():
            st.audio(str(output_path), format="audio/mp3")
            st.success(f"已生成：{output_path}")
        else:
            st.error("音频生成失败")


def render_kokoro_section(text: str) -> None:
    """渲染 Kokoro 试听区."""
    st.subheader("3. Kokoro（本地开源）")
    st.caption("本地推理，首次运行需下载约 350MB 模型")

    if st.button("生成并播放 Kokoro", key="kokoro_btn"):
        try:
            import numpy as np
            import soundfile as sf
            from kokoro import KPipeline
        except ImportError as e:
            st.error(f"缺少依赖：{e}，请运行：pip install kokoro soundfile numpy")
            return

        output_path = Path("kokoro_compare.wav")
        with st.spinner("正在加载 Kokoro 模型并生成音频，首次较慢..."):
            pipeline = KPipeline(lang_code="z")
            generator = pipeline(text, voice="zf_xiaoxiao", speed=1.0)

            audios = []
            for _, _, audio in generator:
                audios.append(audio)

            if not audios:
                st.error("Kokoro 未生成任何音频")
                return

            full_audio = np.concatenate(audios)
            sf.write(str(output_path), full_audio, 24000)

        if output_path.exists():
            st.audio(str(output_path), format="audio/wav")
            st.success(f"已生成：{output_path}")
        else:
            st.error("音频生成失败")


def main() -> None:
    """Streamlit 主入口."""
    st.title("🔊 TTS 方案对比")
    st.markdown(
        "输入同一段文字，分别试听三种 TTS 方案的效果。"
        "注意：浏览器 TTS 在不同设备上音色可能不一致。"
    )

    text = st.text_area(
        "输入要朗读的文字",
        value=DEFAULT_TEXT,
        height=120,
        key="tts_text",
    )

    st.divider()
    render_browser_tts_section(text)

    st.divider()
    render_edge_tts_section(text)

    st.divider()
    render_kokoro_section(text)


if __name__ == "__main__":
    main()
