"""Probe MiMo SGP + Agnes against official docs (text-only)."""
from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

MIMO_KEY = os.getenv("MIMO_API_KEY", "")
AGNES_KEY = os.getenv("AGNES_API_KEY", "")
MIMO_URL = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions"
AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"


def mask(k: str) -> str:
    if not k:
        return "EMPTY"
    return f"{k[:6]}...{k[-4:]} (len={len(k)})"


def probe(name: str, url: str, headers: dict, model: str, payload_extra: dict | None = None) -> None:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "temperature": 0,
    }
    if payload_extra:
        payload.update(payload_extra)
    else:
        payload["max_tokens"] = 16
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        body = r.text[:400].replace("\n", " ")
        print(f"[{name}] model={model} status={r.status_code} body={body}")
    except Exception as e:
        print(f"[{name}] model={model} EXC={type(e).__name__}: {e}")


def main() -> int:
    print("MIMO_API_KEY:", mask(MIMO_KEY))
    print("AGNES_API_KEY:", mask(AGNES_KEY))
    print("---")

    h_mimo = {"api-key": MIMO_KEY, "Content-Type": "application/json"}
    h_mimo_bearer = {"Authorization": f"Bearer {MIMO_KEY}", "Content-Type": "application/json"}
    h_agnes = {"Authorization": f"Bearer {AGNES_KEY}", "Content-Type": "application/json"}
    h_agnes_apikey = {"api-key": AGNES_KEY, "Content-Type": "application/json"}

    if MIMO_KEY:
        for m in ("mimo-v2.5", "mimo-v2.5-pro", "mimo-v2"):
            probe("MiMo api-key + max_tokens", MIMO_URL, h_mimo, m)
        probe(
            "MiMo api-key + max_completion_tokens",
            MIMO_URL,
            h_mimo,
            "mimo-v2.5-pro",
            {"max_completion_tokens": 16},
        )
        probe("MiMo Bearer + max_tokens", MIMO_URL, h_mimo_bearer, "mimo-v2.5-pro")
    else:
        print("Skip MiMo: no key")

    print("---")
    if AGNES_KEY:
        for m in ("agnes-2.5-flash", "agnes-2.5", "agnes-20-flash", "agnes-2.5-pro"):
            probe("Agnes Bearer", AGNES_URL, h_agnes, m)
        probe("Agnes api-key (wrong)", AGNES_URL, h_agnes_apikey, "agnes-2.5-flash")
    else:
        print("Skip Agnes: no key")
    return 0


if __name__ == "__main__":
    sys.exit(main())
