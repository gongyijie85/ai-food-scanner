"""Vision OCR smoke test using project .env (override OS env)."""
from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)

KEY = (os.getenv("MIMO_API_KEY") or "").strip()
URL = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions"


def main() -> None:
    print("key", f"{KEY[:8]}...{KEY[-4:]}" if KEY else "EMPTY", "len", len(KEY))
    img = Image.new("RGB", (480, 160), "white")
    draw = ImageDraw.Draw(img)
    draw.text((12, 50), "PeiLiao: shan zha, ning meng suan, guo jiao", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode()

    payload = {
        "model": "mimo-v2.5",
        "messages": [
            {"role": "system", "content": "Return pure JSON only."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": 'OCR the ingredient line. Return JSON: {"ocr_text":"..."}',
                    },
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 512,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        URL,
        headers={"api-key": KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    print("status", resp.status_code)
    data = resp.json()
    msg = data.get("choices", [{}])[0].get("message", {})
    print("content", repr((msg.get("content") or "")[:400]))
    print("reasoning_head", repr((msg.get("reasoning_content") or "")[:120]))
    print("finish", data.get("choices", [{}])[0].get("finish_reason"))
    print("usage", data.get("usage"))


if __name__ == "__main__":
    main()
