import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# 构造 3 条测试历史记录
now = datetime.now()
history = []
full = []
for i, (name, score, type_) in enumerate([
    ("测试牛奶", 85, "food"),
    ("测试鱼油胶囊", 72, "supplement"),
    ("测试辣条", 45, "food"),
]):
    ts = (now - timedelta(hours=i)).isoformat(timespec="seconds")
    record = {
        "timestamp": ts,
        "product_name": name,
        "score": score,
        "type": type_,
        "additives_count": i + 1,
    }
    history.append(record)
    full.append({
        **record,
        "additives": [{"name": f"添加剂{i}", "risk": "low"}],
        "ingredients": ["水", "糖"],
        "advice": "适量食用",
    })

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

        # 检查扫描按钮尺寸
        scan_btn = page.get_by_role("button", name="扫描配料表").first
        box = scan_btn.bounding_box()
        print("scan button box:", box)
        assert box["width"] < 250 and box["height"] < 250, "扫描按钮不应被放大"

        # 检查首页没有其他大按钮（比如查看按钮），跳过扫描按钮本身
        for b in page.locator("button").all():
            txt = b.inner_text().replace("\n", " ")
            if txt and "扫描配料表" not in txt and txt not in ("首页", "历史", "扫描", "健康档案"):
                bbox = b.bounding_box()
                if bbox and bbox["width"] > 100 and bbox["height"] > 100:
                    raise AssertionError(f"发现异常大按钮: {txt} {bbox}")

        # 历史页
        page.goto("http://localhost:8503/?demo=1&page=history")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="d:/GBT/ai-food-scanner/smoke_history.png", full_page=True)

        # 检查历史页有 3 条可点击行且没有单独的“查看”文字按钮
        buttons = page.locator("button").all()
        labels = [b.inner_text().replace("\n", " ") for b in buttons]
        print("history buttons:", labels[:20])
        assert "查看" not in labels, "应移除单独的查看按钮"
        # 至少能看到测试牛奶按钮
        assert any("测试牛奶" in l for l in labels), "应显示测试历史记录"

        # 点击第一条历史记录，进入详情
        page.get_by_role("button", name="测试牛奶").first.click()
        page.wait_for_timeout(1500)
        page.screenshot(path="d:/GBT/ai-food-scanner/smoke_detail.png", full_page=True)
        assert page.get_by_text("产品详情").first.is_visible()

        browser.close()
        print("smoke test passed")


if __name__ == "__main__":
    main()
