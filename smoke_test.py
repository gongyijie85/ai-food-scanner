import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

# 冒烟测试使用无效 key，专门验证本地 UI/校验路径，不消耗真实 API 额度
os.environ.setdefault("MIMO_API_KEY", "dummy-key-for-smoke-test")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# 构造 3 条测试历史记录
now = datetime.now()
history = []
full = []
for i, (name, score, type_) in enumerate(
    [
        ("测试牛奶", 85, "food"),
        ("测试鱼油胶囊", 72, "supplement"),
        ("测试辣条", 45, "food"),
    ]
):
    ts = (now - timedelta(hours=i)).isoformat(timespec="seconds")
    record = {
        "timestamp": ts,
        "product_name": name,
        "score": score,
        "type": type_,
        "additives_count": i + 1,
    }
    history.append(record)
    full.append(
        {
            **record,
            "additives": [{"name": f"添加剂{i}", "risk": "low"}],
            "ingredients": ["水", "糖"],
            "advice": "适量食用",
        }
    )


def _write_test_data():
    with open(DATA_DIR / "history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    with open(DATA_DIR / "history_full.json", "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=2)


def main():
    _write_test_data()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 首页
        page.goto("http://localhost:8503/?demo=1")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="d:/GBT/ai-food-scanner/smoke_home.png", full_page=True)

        # 检查首页"拍照识别"按钮可见且尺寸合理
        scan_btn = page.get_by_role("button", name="拍照识别").first
        box = scan_btn.bounding_box()
        print("scan button box:", box)
        assert box, "首页应存在拍照识别按钮"
        assert (
            box["width"] >= 100 and box["height"] >= 48
        ), "拍照识别按钮应满足适老化最小尺寸"

        # 检查首页没有异常超大按钮（跳过导航和已知大按钮）
        skip_texts = {
            "拍照识别",
            "健康档案",
            "查看详情",
            "查看全部历史记录",
            "首页",
            "历史",
            "扫描",
            "健康档案",
        }
        for b in page.locator("button").all():
            txt = b.inner_text().replace("\n", " ")
            if txt and txt not in skip_texts:
                bbox = b.bounding_box()
                if bbox and bbox["width"] > 250 and bbox["height"] > 150:
                    raise AssertionError(f"发现异常大按钮: {txt} {bbox}")

        # 历史页：通过导航按钮进入（URL page 参数不被 app 处理）
        page.get_by_role("button", name="历史").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="d:/GBT/ai-food-scanner/smoke_history.png", full_page=True)

        # 检查历史页有 3 条可点击行且没有单独的“查看”文字按钮
        buttons = page.locator("button").all()
        labels = [b.inner_text().replace("\n", " ") for b in buttons]
        print("history buttons:", labels[:20])
        assert "查看" not in labels, "应移除单独的查看按钮"
        # 历史记录卡片以 HTML 渲染，检查页面文本中可见产品名
        page_text = page.locator("body").inner_text()
        assert "测试牛奶" in page_text, "应显示测试历史记录"

        # 点击第一条历史记录下方的查看详情按钮，进入详情
        page.get_by_role("button", name="查看详情").first.click()
        page.wait_for_timeout(1500)
        page.screenshot(path="d:/GBT/ai-food-scanner/smoke_detail.png", full_page=True)
        assert page.get_by_text("产品详情").first.is_visible()

        # 扫描页：回归四类场景（清晰图/模糊图/非图片/接口失败）
        page.get_by_role("button", name="扫描").first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="d:/GBT/ai-food-scanner/smoke_scan.png", full_page=True)

        # 辅助函数：直接操作隐藏 input 上传文件并返回可见的错误文本列表
        def _upload_and_errors(file_path: str):
            # 若已有上传文件，先点击重新选择
            reselect = page.get_by_role("button", name="重新选择")
            if reselect.count() > 0:
                reselect.first.click()
                page.wait_for_timeout(800)
            file_input = page.locator("input[type='file']").first
            file_input.set_input_files(file_path)
            # 等待 Streamlit 完成上传与重新渲染
            page.wait_for_timeout(2500)
            return [
                el.inner_text()
                for el in page.locator("[data-testid='stAlertContentError']").all()
            ]

        # 1) 清晰配料表图片：应成功出现预览，无格式错误
        errors = _upload_and_errors("d:/GBT/ai-food-scanner/test_label.jpg")
        assert not any(
            "格式" in e or "有效图片" in e for e in errors
        ), f"清晰图不应报格式错误: {errors}"
        assert page.locator("img").count() > 0, "清晰图上传后应显示预览"
        page.screenshot(
            path="d:/GBT/ai-food-scanner/smoke_scan_clear.png", full_page=True
        )

        # 2) 模糊图片：同样应被接受（仅在识别阶段可能失败）
        errors = _upload_and_errors("d:/GBT/ai-food-scanner/test_label_blur.jpg")
        assert not any(
            "格式" in e or "有效图片" in e for e in errors
        ), f"模糊图不应报格式错误: {errors}"
        page.screenshot(
            path="d:/GBT/ai-food-scanner/smoke_scan_blur.png", full_page=True
        )

        # 3) 非图片文件（伪 jpg 内容）：应在上传后即时提示格式错误
        errors = _upload_and_errors("d:/GBT/ai-food-scanner/invalid.jpg")
        assert any(
            "格式" in e or "JPG" in e or "PNG" in e for e in errors
        ), f"非图片文件应提示格式错误: {errors}"
        page.screenshot(
            path="d:/GBT/ai-food-scanner/smoke_scan_non_image.png", full_page=True
        )

        # 4) 接口失败：上传有效图片并点击识别，因 key 无效应给出明确不可用提示
        errors = _upload_and_errors("d:/GBT/ai-food-scanner/test_label.jpg")
        assert not any(
            "格式" in e or "有效图片" in e for e in errors
        ), f"接口失败场景不应报格式错误: {errors}"
        page.get_by_role("button", name="开始识别").first.click()
        page.wait_for_timeout(5000)
        page.screenshot(
            path="d:/GBT/ai-food-scanner/smoke_scan_api_fail.png", full_page=True
        )
        body_text = page.locator("body").inner_text()
        assert "识别失败" in body_text, f"接口失败应给出明确提示: {body_text[:500]}"

        browser.close()
        print("smoke test passed")


if __name__ == "__main__":
    main()
