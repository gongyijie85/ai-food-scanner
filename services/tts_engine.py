"""自然语言 TTS：优先 edge-tts（微软神经网络音色），失败返回 None 由 UI 回退浏览器。"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger("ai-food-scanner")

# 晓晓：自然女声，适老化听感较好
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
_CACHE_DIR = Path(tempfile.gettempdir()) / "ai_food_scanner_tts"
_MAX_CHARS = 500  # 控制生成时长与体积


def _cache_path(text: str, voice: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"{voice}\n{text}".encode("utf-8")).hexdigest()[:32]
    return _CACHE_DIR / f"{key}.mp3"


async def _edge_save(text: str, voice: str, out: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out))


def synthesize_mp3(
    text: str,
    voice: str = DEFAULT_VOICE,
) -> bytes | None:
    """生成 MP3 字节；不可用时返回 None（调用方回退浏览器 TTS）."""
    text = (text or "").strip()
    if not text:
        return None
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "……详情请在屏幕查看。"

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        logger.info("edge-tts 未安装，跳过云端语音")
        return None

    path = _cache_path(text, voice)
    try:
        if path.exists() and path.stat().st_size > 100:
            return path.read_bytes()
        asyncio.run(_edge_save(text, voice, path))
        if path.exists() and path.stat().st_size > 100:
            return path.read_bytes()
    except Exception as e:
        logger.warning("edge-tts 合成失败: %s", e)
        return None
    return None
