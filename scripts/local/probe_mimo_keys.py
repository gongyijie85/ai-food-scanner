"""Compare env vs .env MiMo keys and probe all clusters/auth styles."""
from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import dotenv_values, load_dotenv

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


def mask(k: str) -> str:
    if not k:
        return "EMPTY"
    return f"{k[:8]}...{k[-4:]} len={len(k)} starts_tp={k.startswith('tp-')}"


def probe(label: str, url: str, headers: dict, key_label: str) -> None:
    payload = {
        "model": "mimo-v2.5-pro",
        "messages": [{"role": "user", "content": "Reply OK"}],
        "max_completion_tokens": 8,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=25)
        body = r.text[:220].replace("\n", " ")
        print(f"{r.status_code:3d} | {key_label:12s} | {label:28s} | {url.split('//')[1].split('/')[0]:36s} | {body}")
    except Exception as e:
        print(f"EXC | {key_label:12s} | {label:28s} | {type(e).__name__}: {e}")


def main() -> None:
    file_vals = dotenv_values(ENV_PATH)
    file_key = (file_vals.get("MIMO_API_KEY") or "").strip()
    os_key = (os.environ.get("MIMO_API_KEY") or "").strip()

    # default load_dotenv does NOT override existing OS env
    load_dotenv(ENV_PATH)
    loaded_key = (os.getenv("MIMO_API_KEY") or "").strip()

    print("ENV file:", ENV_PATH)
    print("from .env file:", mask(file_key))
    print("from OS env  :", mask(os_key))
    print("after load_dotenv (no override):", mask(loaded_key))
    print("file == os :", file_key == os_key)
    print("---")

    candidates = []
    if file_key:
        candidates.append(("file.env", file_key))
    if os_key and os_key != file_key:
        candidates.append(("os.env", os_key))
    if not candidates and loaded_key:
        candidates.append(("loaded", loaded_key))

    urls = [
        "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions",
        "https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
        "https://token-plan-ams.xiaomimimo.com/v1/chat/completions",
    ]

    for key_label, key in candidates:
        for url in urls:
            probe(
                "api-key",
                url,
                {"api-key": key, "Content-Type": "application/json"},
                key_label,
            )
            probe(
                "Bearer",
                url,
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                key_label,
            )
            # OpenAI SDK style often uses Authorization for OpenAI-compat
            probe(
                "api-key + max_tokens",
                url,
                {"api-key": key, "Content-Type": "application/json"},
                key_label,
            )

    # also try payload with max_tokens instead of max_completion_tokens once
    if candidates:
        key_label, key = candidates[0]
        url = urls[0]
        payload = {
            "model": "mimo-v2.5",
            "messages": [{"role": "user", "content": "Reply OK"}],
            "max_tokens": 8,
        }
        r = requests.post(
            url,
            headers={"api-key": key, "Content-Type": "application/json"},
            json=payload,
            timeout=25,
        )
        print(
            f"{r.status_code:3d} | {key_label:12s} | model=mimo-v2.5 max_tokens     | "
            f"{url.split('//')[1].split('/')[0]:36s} | {r.text[:220].replace(chr(10), ' ')}"
        )


if __name__ == "__main__":
    main()
