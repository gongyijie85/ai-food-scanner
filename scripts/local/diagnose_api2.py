"""Agnes API 模型名称排查。"""

import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()

AGNES_KEY = os.getenv("AGNES_API_KEY", "")
AGNES_URL = "https://api.agnes-ai.com/v1/chat/completions"

# 尝试多种模型名称变体
model_names = [
    "Agnes-2.0-Flash",
    "Agnes-2.0-flash",
    "agnes-2.0-flash",
    "agnes-2.0-Flash",
    "Agnes-20-Flash",
    "agnes-20-flash",
]

headers = {"api-key": AGNES_KEY, "Content-Type": "application/json"}

for model in model_names:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 5,
    }
    try:
        resp = requests.post(AGNES_URL, headers=headers, json=payload, timeout=10)
        status = "OK" if resp.status_code == 200 else f"ERR {resp.status_code}"
        print(f"{model:25s} -> {status}")
    except Exception as e:
        print(f"{model:25s} -> EXC {str(e)[:50]}")
