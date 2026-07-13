"""edge-tts Demo：调用微软在线语音合成接口生成音频文件.

用途：
    对比 edge-tts 的音质和延迟，与当前项目使用的浏览器原生 TTS 做比较.

运行方法：
    1. 安装依赖：pip install edge-tts
    2. 运行：python edge_tts_demo.py
    3. 用播放器打开生成的 edge_tts_demo.mp3

注意：
    - 需要联网
    - 默认使用 zh-CN-XiaoxiaoNeural（晓晓）女声
"""

import asyncio

import edge_tts

# 默认测试文本：模拟配料表识别结果的播报文案
DEFAULT_TEXT = (
    "评分 88 分。按当前档案暂未发现高风险配料。"
    "本工具仅供参考，不构成医疗建议。如有健康问题请咨询医生。"
)

# 默认音色：Microsoft Xiaoxiao（晓晓）女声
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
OUTPUT_FILE = "edge_tts_demo.mp3"


async def generate_speech(text: str, voice: str, output_path: str) -> None:
    """使用 edge-tts 生成音频文件.

    Args:
        text: 要合成的文本
        voice: edge-tts 的 voice name
        output_path: 输出音频文件路径
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


async def main() -> None:
    """主入口：生成示例音频并打印信息."""
    print(f"音色：{DEFAULT_VOICE}")
    print(f"语速：1.0x（edge-tts 默认）")
    print(f"文本：{DEFAULT_TEXT}")
    print("正在生成音频...")

    await generate_speech(DEFAULT_TEXT, DEFAULT_VOICE, OUTPUT_FILE)

    print(f"生成完成：{OUTPUT_FILE}")
    print("请用音频播放器打开试听。")


if __name__ == "__main__":
    asyncio.run(main())
