"""Kokoro TTS Demo：本地开源语音合成.

用途：
    对比 Kokoro 的本地离线语音合成效果.

运行方法：
    1. 安装依赖：pip install kokoro soundfile
    2. 运行：python kokoro_tts_demo.py
    3. 用播放器打开生成的 kokoro_demo.wav

注意：
    - 首次运行会自动下载模型（约 350MB），请保持网络畅通
    - 不需要 GPU，CPU 即可运行
    - 默认使用中文女声 zf_xiaoxiao
"""

import soundfile as sf
from kokoro import KPipeline

# 默认测试文本：模拟配料表识别结果的播报文案
DEFAULT_TEXT = (
    "评分 88 分。按当前档案暂未发现高风险配料。"
    "本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生。"
)

# 默认音色：中文女声
DEFAULT_VOICE = "zf_xiaoxiao"
OUTPUT_FILE = "kokoro_demo.wav"


def generate_speech(text: str, voice: str, output_path: str) -> None:
    """使用 Kokoro 生成音频文件.

    Args:
        text: 要合成的文本
        voice: Kokoro 的 voice code
        output_path: 输出音频文件路径
    """
    # lang_code='z' 表示中文
    pipeline = KPipeline(lang_code="z")

    # speed=1.0 对齐项目适老化要求
    generator = pipeline(text, voice=voice, speed=1.0)

    # 逐段生成并保存为单个音频文件
    audios = []
    sample_rate = 24000
    for _, _, audio in generator:
        audios.append(audio)

    if not audios:
        raise RuntimeError("Kokoro 未生成任何音频")

    import numpy as np

    full_audio = np.concatenate(audios)
    sf.write(output_path, full_audio, sample_rate)


def main() -> None:
    """主入口：生成示例音频并打印信息."""
    print(f"音色：{DEFAULT_VOICE}")
    print("语速：1.0x")
    print(f"文本：{DEFAULT_TEXT}")
    print("正在加载模型并生成音频（首次运行需下载约 350MB 模型）...")

    generate_speech(DEFAULT_TEXT, DEFAULT_VOICE, OUTPUT_FILE)

    print(f"生成完成：{OUTPUT_FILE}")
    print("请用音频播放器打开试听。")


if __name__ == "__main__":
    main()
