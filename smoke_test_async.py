"""异步 API 冒烟测试：验证上传图片后点击识别，页面不会卡死。

本测试使用无效 API key，专门验证 UI 流程和超时/失败处理，不消耗真实额度。
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

# 使用无效 key，确保不会真正调用成功
os.environ.setdefault("MIMO_API_KEY", "dummy-key-for-smoke-test")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto("http://localhost:8503/?demo=1")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)

        # 进入扫描页
        page.get_by_role("button", name="扫描").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)

        # 上传测试图
        file_input = page.locator("input[type='file']").first
        file_input.set_input_files("d:/GBT/ai-food-scanner/test_label.jpg")
        page.wait_for_timeout(2500)

        # 点击开始识别
        page.get_by_role("button", name="开始识别").first.click()

        # 关键断言：点击后 2 秒内页面不能进入“无响应”状态；
        # 我们等待状态文本出现（上传/分析/评分/失败之一）
        page.wait_for_timeout(2000)
        body_text = page.locator("body").inner_text()

        # 只要出现以下任一状态，说明异步流程在跑且页面没卡死
        expected_keywords = [
            "正在上传图片",
            "正在提取配料文字",
            "正在分析成分风险",
            "正在计算评分",
            "识别失败",
            "识别超时",
        ]
        matched = [k for k in expected_keywords if k in body_text]
        print("页面识别状态关键词命中:", matched)
        assert matched, f"点击识别后页面无状态反馈: {body_text[:500]}"

        # 继续等待到超时或失败（API key 无效）
        page.wait_for_timeout(config.API_TIMEOUT * 1000 + 3000)
        body_text = page.locator("body").inner_text()
        print("最终页面文本片段:", body_text[:500])

        assert (
            "识别失败" in body_text
            or "重新识别" in body_text
            or "识别超时" in body_text
        ), "无效 key 下应给出失败/重试提示"

        page.screenshot(
            path="d:/GBT/ai-food-scanner/smoke_async_result.png", full_page=True
        )
        browser.close()
        print("async smoke test passed")


if __name__ == "__main__":
    # 延迟导入 config，避免初始化时 dotenv 还没加载
    from utils import config

    main()
