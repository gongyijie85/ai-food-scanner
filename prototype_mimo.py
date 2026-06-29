"""
AI食品配料表识别工具 - 最小验证原型
用途：验证 MiMo Vision API 能否从配料表图片中提取成分并给出健康建议
运行环境：Python 3.10+
依赖：pip install requests
作者：AI助手
版本：v1.0
"""

import base64
import io
import json
import os
import sys

import requests
from PIL import Image


# ========== 用户配置区 ==========
# 把你的 MiMo API 密钥放到系统环境变量 MIMO_API_KEY 中
# 临时测试也可以直接填字符串(但不建议上传代码库)
API_KEY = os.getenv("MIMO_API_KEY", "")

# MiMo Token Plan - 新加坡集群 Base URL
# 文档地址: https://mimo.mi.com/docs/zh-CN/tokenplan/Token%20Plan/quick-access
# OpenAI 兼容协议格式: BASE_URL/chat/completions
API_URL = "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions"

# 使用的模型名称(以官方文档为准,视觉模型可能不同)
# mimo-v2.5 是多模态模型,支持图片输入
# 之前空响应疑似图片过大,现加入压缩逻辑
MODEL_NAME = "mimo-v2.5"

# 测试图片路径(相对或绝对路径均可)
IMAGE_PATH = "test_label.jpg"


# ========== 核心函数 ==========

def encode_image_to_base64(image_path, max_size=1024):
    """把本地图片文件压缩后转成 base64 字符串,用于传给 API."""
    # 检查文件是否存在,不存在时给出清晰提示
    if not os.path.exists(image_path):
        print(f"错误：找不到图片文件 {image_path}")
        print("请把一张配料表照片放到同一目录,并重命名为 test_label.jpg")
        sys.exit(1)

    # 打开图片并按比例压缩,减少 base64 体积
    with Image.open(image_path) as img:
        # 统一转成 RGB,避免 PNG 透明通道导致格式问题
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 如果最长边超过 max_size,等比例缩放
        width, height = img.size
        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # 保存到内存字节流,再编码为 base64
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def build_system_prompt():
    """构建 system 角色的规则说明,把规则和图片分开,减少 user 消息长度."""
    return (
        "你是食品营养分析助手,专门解读中国预包装食品配料表。\n"
        "用户会上传一张配料表图片,你必须返回合法 JSON,不要 Markdown 代码块,不要解释。\n\n"
        "输出字段：\n"
        "- product_name: 产品名称,图片未显示则填\"未知\"\n"
        "- ingredients: 所有配料成分列表,按原文顺序\n"
        "- additives: 只含 GB 2760 具体食品添加剂。不要把食品用香精、食用盐、水、糖、油、面粉等基础配料列入。每个添加剂包含 name、code(INS/E号,没有留空)、level(green/yellow/red)\n"
        "- score: 0-100 综合安全评分\n"
        "- advice: 给老年人或慢病人群的一句话建议\n\n"
        "level 分级：\n"
        "- green: 安全常见,如柠檬酸、维生素C、碳酸氢钠\n"
        "- yellow: 需适量关注,如山梨酸钾、苯甲酸钠、焦糖色\n"
        "- red: 建议规避,如特丁基对苯二酚(TBHQ)、部分人工合成色素"
    )


def build_user_prompt():
    """构建 user 角色的简短指令."""
    return "请分析这张配料表图片,按规则返回 JSON。"


def call_mimo_vision(api_key, image_base64, system_prompt, user_prompt):
    """调用 MiMo Vision API,传入图片和提示词,返回模型回复文本."""
    # 设置请求头
    # MiMo Token Plan 使用 "api-key" 头,不是 OpenAI 的 "Authorization: Bearer"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }

    # 构造 OpenAI 兼容格式的消息体
    # system 放规则说明, user 放图片+简短指令,减少单条消息长度
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
            }
        ],
        "temperature": 0.2,
        "max_tokens": 4096
    }

    # 发送请求并处理超时
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    except requests.exceptions.Timeout:
        print("错误：API 请求超时(60秒),请检查网络或稍后重试。")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"错误：网络请求失败 - {e}")
        sys.exit(1)

    # 调试输出：打印 HTTP 状态码和原始响应
    print(f"\n[调试] HTTP 状态码: {response.status_code}")
    print(f"[调试] 响应头 Content-Type: {response.headers.get('Content-Type', '未知')}")
    print(f"[调试] 响应原文(前2000字符):")
    print(response.text[:2000])
    print(f"[调试] 响应原文结束\n")

    # 如果返回非 200,打印错误详情
    if response.status_code != 200:
        print(f"错误：API 返回状态码 {response.status_code}")
        print(response.text)
        sys.exit(1)

    # 解析 JSON 响应
    try:
        data = response.json()
        # OpenAI 兼容格式: choices[0].message.content
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"错误：无法解析 API 响应 - {e}")
        print(response.text)
        sys.exit(1)


def parse_result(raw_text):
    """把模型返回的文本解析为 Python 字典."""
    # 有些模型会包裹 Markdown 代码块,先清理
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # 去掉可能的 json 语言标记
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"错误：模型返回的内容不是合法 JSON - {e}")
        print("原始内容：")
        print(raw_text)
        return None


def print_result(result):
    """以友好的中文格式打印识别结果."""
    if not result:
        return

    print("\n========== 识别结果 ==========")
    print(f"产品名称：{result.get('product_name', '未知')}")
    print(f"综合评分：{result.get('score', 'N/A')} 分")
    print(f"\n全部配料：{', '.join(result.get('ingredients', []))}")

    additives = result.get("additives", [])
    if additives:
        print("\n食品添加剂：")
        for item in additives:
            level_map = {
                "green": "安全",
                "yellow": "注意",
                "red": "规避"
            }
            level = level_map.get(item.get("level", ""), item.get("level", ""))
            print(f"  - {item.get('name', '未知')} ({level})")
    else:
        print("\n未识别到明显食品添加剂。")

    print(f"\n健康建议：{result.get('advice', '无')}")
    print("==============================\n")


# ========== 主程序 ==========

def main():
    """程序入口：检查配置、调用 API、打印结果."""
    # 检查 API 密钥
    if not API_KEY:
        print("错误：缺少 MIMO_API_KEY 环境变量。")
        print("设置方法( PowerShell )：")
        print('  $env:MIMO_API_KEY="你的密钥"')
        print("设置方法( 永久 )：")
        print("  系统设置 → 环境变量 → 新建 MIMO_API_KEY")
        sys.exit(1)

    # 编码图片
    print(f"正在读取图片：{IMAGE_PATH}")
    image_base64 = encode_image_to_base64(IMAGE_PATH)
    print(f"图片已编码，大小约 {len(image_base64) // 1024} KB\n")

    # 构建提示词并调用 API
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt()
    print("正在调用 MiMo Vision API，请稍候...")
    raw_text = call_mimo_vision(API_KEY, image_base64, system_prompt, user_prompt)

    # 保存原始输出，方便调试
    with open("last_api_response.txt", "w", encoding="utf-8") as f:
        f.write(raw_text)
    print("原始响应已保存到 last_api_response.txt\n")

    # 解析并打印
    result = parse_result(raw_text)
    print_result(result)


if __name__ == "__main__":
    main()
