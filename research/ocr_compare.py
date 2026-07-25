"""OCR+VLM 与纯 VLM 效果对比脚本。

用法：
    cd d:\GBT\ai-food-scanner
    python research\ocr_compare.py [图片路径1] [图片路径2] ...

环境变量：
    - OCR_PROVIDER=baidu（默认）/ paddle / none
    - BAIDU_OCR_APP_KEY / BAIDU_OCR_SECRET_KEY
    - MIMO_API_KEY / AGNES_API_KEY（已在 .env 中配置）

说明：
    - 对每张图分别跑「纯 VLM」和「OCR 预处理 + VLM」两套流程。
    - 打印耗时、ocr_text 长度、返回 JSON 中的 ingredients/additives 数量。
    - 不配置百度 OCR 密钥时，OCR 流程会自动回退到纯 VLM。
"""

import json
import os
import sys
import time
from pathlib import Path

# 将项目根目录加入路径
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

# 在脚本环境下屏蔽 Streamlit UI 函数，避免调用 API 时触发 RuntimeError
st.error = lambda msg, *args, **kwargs: print(f"[UI错误] {msg}")
st.toast = lambda *args, **kwargs: None

from services.ocr_provider import get_provider
from utils.api import build_system_prompt, call_api_with_fallback, encode_image_to_base64
from utils.config import AGNES_API_KEY, MIMO_API_KEY, OCR_CONFIDENCE_THRESHOLD, OCR_PROVIDER


def _count_items(raw: str) -> dict:
    """从模型返回的 JSON 中统计关键字段数量。"""
    if not raw:
        return {"ingredients": 0, "additives": 0}
    try:
        data = json.loads(raw.strip().strip("`").lstrip("json").strip())
    except json.JSONDecodeError:
        return {"ingredients": 0, "additives": 0}
    if not isinstance(data, dict):
        return {"ingredients": 0, "additives": 0}
    ingredients = data.get("ingredients", [])
    additives = data.get("additives", [])
    return {
        "ingredients": len(ingredients) if isinstance(ingredients, list) else 0,
        "additives": len(additives) if isinstance(additives, list) else 0,
    }


def _run_pipeline(image_path: str, use_ocr: bool) -> dict:
    """对单张图片运行一次识别流程。"""
    print(f"\n{'=' * 60}")
    print(f"图片: {image_path}")
    print(f"模式: {'OCR + VLM' if use_ocr else '纯 VLM'}")

    if not os.path.exists(image_path):
        print(f"⚠️ 图片不存在，跳过: {image_path}")
        return {"error": "文件不存在"}

    with open(image_path, "rb") as f:
        img_b64 = encode_image_to_base64(f)

    ocr_text = ""
    ocr_info = "未启用 OCR"
    if use_ocr:
        provider = get_provider(OCR_PROVIDER)
        print(f"OCR 提供方: {provider.name}")
        start = time.time()
        ocr_result = provider.extract(img_b64)
        ocr_elapsed = time.time() - start
        if ocr_result.is_usable(OCR_CONFIDENCE_THRESHOLD):
            ocr_text = ocr_result.text
            ocr_info = (
                f"成功（{len(ocr_text)} 字, "
                f"confidence={ocr_result.confidence:.2f}, 耗时 {ocr_elapsed:.2f}s）"
            )
        else:
            ocr_info = (
                f"失败（reason={ocr_result.error or '置信度低/无文字'}, "
                f"耗时 {ocr_elapsed:.2f}s）"
            )
        print(f"OCR 结果: {ocr_info}")

    system_prompt = build_system_prompt(groups=[])
    start = time.time()
    raw = call_api_with_fallback(
        MIMO_API_KEY,
        img_b64,
        system_prompt,
        agnes_key=AGNES_API_KEY,
        ocr_text=ocr_text,
    )
    api_elapsed = time.time() - start

    counts = _count_items(raw)
    print(f"API 总耗时: {api_elapsed:.2f}s")
    print(f"ingredients: {counts['ingredients']}, additives: {counts['additives']}")
    if raw:
        print("返回片段:", raw[:200].replace("\n", " "))
    else:
        print("返回: None")

    return {
        "ocr_text": ocr_text,
        "ocr_info": ocr_info,
        "elapsed": api_elapsed,
        "raw": raw,
        "counts": counts,
    }


def main():
    """主入口：解析参数并执行对比。"""
    if len(sys.argv) > 1:
        image_paths = sys.argv[1:]
    else:
        # 默认测试图（需自行准备到项目根目录）
        image_paths = [
            "test_label.jpg",
            "test_label_blur.jpg",
        ]

    if not MIMO_API_KEY or MIMO_API_KEY.startswith("your-"):
        print("⚠️ MIMO_API_KEY 未配置，无法进行对比。请在 .env 中配置后重试。")
        return

    print(f"当前 OCR_PROVIDER={OCR_PROVIDER}, 阈值={OCR_CONFIDENCE_THRESHOLD}")
    print(f"共 {len(image_paths)} 张图片待对比")

    summary = []
    for path in image_paths:
        vlm_result = _run_pipeline(path, use_ocr=False)
        ocr_vlm_result = _run_pipeline(path, use_ocr=True)
        summary.append(
            {
                "image": path,
                "vlm": vlm_result,
                "ocr_vlm": ocr_vlm_result,
            }
        )

    print("\n" + "=" * 60)
    print("对比摘要")
    print("=" * 60)
    for item in summary:
        vlm = item["vlm"]
        ocr = item["ocr_vlm"]
        print(
            f"\n{item['image']}:"
            f"\n  纯 VLM     : ingredients={vlm['counts']['ingredients']} "
            f"additives={vlm['counts']['additives']} 耗时={vlm['elapsed']:.2f}s"
            f"\n  OCR+VLM    : ingredients={ocr['counts']['ingredients']} "
            f"additives={ocr['counts']['additives']} 耗时={ocr['elapsed']:.2f}s "
            f"OCR={ocr['ocr_info']}"
        )


if __name__ == "__main__":
    main()
