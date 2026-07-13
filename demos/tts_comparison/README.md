# TTS 方案对比 Demo

为 `ai-food-scanner` 项目准备的三种免费 TTS 方案对比，帮助你听完再决定用哪个。

---

## 三种方案

| 方案 | 文件 | 是否需要联网 | 特点 |
|------|------|--------------|------|
| 浏览器原生 TTS | `browser_tts_demo.html` | 否 | 项目当前方案，零依赖，但 iOS/微信浏览器兼容性差 |
| edge-tts | `edge_tts_demo.py` | 是 | 调用微软在线接口，音质好，一行代码生成 MP3 |
| Kokoro | `kokoro_tts_demo.py` | 首次需下载模型 | 本地开源，离线可用，模型约 350MB |

---

## 快速开始

### 1. 安装依赖

```powershell
cd demos/tts_comparison
pip install -r requirements_demo.txt
```

### 2. 运行独立 Demo

**浏览器原生 TTS：**

直接用浏览器双击打开 `browser_tts_demo.html`，点击「朗读」。

**edge-tts：**

```powershell
python edge_tts_demo.py
# 生成 edge_tts_demo.mp3，用播放器打开
```

**Kokoro：**

```powershell
python kokoro_tts_demo.py
# 首次运行下载约 350MB 模型，生成 kokoro_demo.wav
```

### 3. 运行统一对比页

```powershell
streamlit run tts_compare_app.py
```

在浏览器中输入文字，分别点击三种方案试听。

---

## 对比建议

- **只想快速验证 / 不改动项目**：用 `browser_tts_demo.html`
- **想后端生成稳定音频 / 能接受联网**：用 `edge-tts`，代码最简单
- **想离线运行 / 可商用 / 不依赖微软服务**：用 `Kokoro`，但首次下载模型较大

---

## 与主项目的关系

- 本目录下所有文件**不参与主应用运行**
- 不修改 `app.py`、`pages/`、`components/`、`utils/`
- 主项目 `requirements.txt` 未增加 TTS 依赖
