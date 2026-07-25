"""API连接诊断脚本。"""

import os
import sys
import requests
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

MIMO_KEY = os.getenv("MIMO_API_KEY", "")
AGNES_KEY = os.getenv("AGNES_API_KEY", "")

MIMO_URL = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions"
AGNES_URL = "https://api.agnes-ai.com/v1/chat/completions"

print("=" * 50)
print("API连接诊断")
print("=" * 50)
print(f"MiMo Key: {'已配置' if MIMO_KEY else '未配置'} (长度 {len(MIMO_KEY)})")
print(f"Agnes Key: {'已配置' if AGNES_KEY else '未配置'} (长度 {len(AGNES_KEY)})")
print()


def test_api(name, url, api_key, model_name):
    """测试单个API连接。"""
    print(f"测试 {name} ({model_name})...")

    if not api_key:
        print(f"  跳过: 未配置API密钥")
        return False

    # 构建最小请求（文本模式，不需要图片）
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'OK' and nothing else."},
        ],
        "temperature": 0,
        "max_tokens": 10,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"  HTTP状态: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"  响应内容: {content[:50]}")
            print(f"  结果: 正常")
            return True
        elif resp.status_code == 401:
            print(f"  结果: 认证失败 (401) - API密钥已过期或无效")
        elif resp.status_code == 429:
            print(f"  结果: 请求过多 (429) - 配额已用完")
        elif resp.status_code == 503:
            print(f"  结果: 服务不可用 (503)")
        else:
            print(f"  结果: 错误 ({resp.status_code})")
            print(f"  响应: {resp.text[:200]}")

    except requests.exceptions.Timeout:
        print(f"  结果: 超时 (15秒无响应)")
    except requests.exceptions.ConnectionError as e:
        print(f"  结果: 连接失败 - {str(e)[:100]}")
    except Exception as e:
        print(f"  结果: 异常 - {str(e)[:100]}")

    return False


# 测试两个API
mimo_ok = test_api("MiMo", MIMO_URL, MIMO_KEY, "mimo-v2.5")
print()
agnes_ok = test_api("Agnes", AGNES_URL, AGNES_KEY, "Agnes-2.0-Flash")

print()
print("=" * 50)
if mimo_ok or agnes_ok:
    print("诊断结论: 至少一个API可用")
else:
    print("诊断结论: 两个API均不可用")
    print()
    print("可能原因:")
    if not MIMO_KEY and not AGNES_KEY:
        print("  1. API密钥未配置")
    else:
        print("  1. API密钥已过期/被撤销")
        print("  2. 服务已停止运营")
        print("  3. 网络连接问题")
    print()
    print("解决方案:")
    print("  1. 检查 .env 文件中的 API 密钥是否最新")
    print("  2. 联系 API 提供商确认服务状态")
    print("  3. 考虑更换为其他 Vision API（如百度、阿里、OpenAI）")
print("=" * 50)
