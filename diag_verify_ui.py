"""临时验证脚本：检查首页、扫描页和结果页修复效果."""
from playwright.sync_api import sync_playwright
import time

BASE = "http://localhost:8501"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # 1. 验证首页
    page.goto(f"{BASE}/?test=1&page=home")
    page.wait_for_load_state("networkidle")
    time.sleep(5)

    home_info = page.evaluate("""() => {
        const text = document.body.innerText;
        const scanBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('扫描配料表'));
        const hintBubble = document.querySelector('.hint-bubble');
        const marker = document.querySelector('.home-scan-area-marker');
        const scanBtnRect = scanBtn ? scanBtn.getBoundingClientRect() : null;
        const hintRect = hintBubble ? hintBubble.getBoundingClientRect() : null;
        const preBlocks = document.querySelectorAll('pre');
        const codeBlocks = document.querySelectorAll('code');
        return {
            hasScanBtn: !!scanBtn,
            hasHintBubble: !!hintBubble,
            hasMarker: !!marker,
            scanBtnTop: scanBtnRect ? Math.round(scanBtnRect.top) : null,
            hintTop: hintRect ? Math.round(hintRect.top) : null,
            preBlocks: preBlocks.length,
            codeBlocks: codeBlocks.length,
            textPreview: text.slice(0, 300)
        };
    }""")
    print("=== 首页检查 ===")
    print(f"扫描按钮存在: {home_info['hasScanBtn']}, 提示气泡存在: {home_info['hasHintBubble']}, marker存在: {home_info['hasMarker']}")
    print(f"提示气泡 top: {home_info['hintTop']}, 扫描按钮 top: {home_info['scanBtnTop']}")
    print(f"页面 pre/code 块数量: {home_info['preBlocks']}/{home_info['codeBlocks']}")
    assert home_info['preBlocks'] == 0, f"首页仍有 {home_info['preBlocks']} 个 <pre> 代码块"
    assert home_info['codeBlocks'] == 0, f"首页仍有 {home_info['codeBlocks']} 个 <code> 代码块"

    page.screenshot(path="d:\\GBT\\ai-food-scanner\\diag_shots\\home_after_fix.png", full_page=True)
    print("首页截图: diag_shots/home_after_fix.png\n")

    # 2. 验证结果页（用 mock 数据，不再依赖真实上传）
    page.goto(f"{BASE}/?test=1&mock=1&page=result")
    page.wait_for_load_state("networkidle")
    time.sleep(5)

    result_info = page.evaluate("""() => {
        const text = document.body.innerText;
        const voiceFloatBar = document.querySelector('.voice-float-bar');
        const voiceBtn = voiceFloatBar ? voiceFloatBar.querySelector('button') : null;
        const voiceBtnText = voiceBtn ? voiceBtn.textContent : '';
        const bottomBar = document.querySelector('.bottom-action-bar-marker');
        const bottomBarParent = bottomBar ? bottomBar.closest('div[data-testid="stVerticalBlock"]') : null;
        const bottomButtons = bottomBarParent ? bottomBarParent.querySelectorAll('button') : [];
        const preBlocks = document.querySelectorAll('pre');
        const codeBlocks = document.querySelectorAll('code');
        const hasRawJS = text.includes('function doSpeak') || text.includes('var text =');
        return {
            voiceFloatBarExists: !!voiceFloatBar,
            voiceBtnExists: !!voiceBtn,
            voiceBtnText: voiceBtnText,
            bottomBarMarkerExists: !!bottomBar,
            bottomButtonCount: bottomButtons.length,
            preBlocks: preBlocks.length,
            codeBlocks: codeBlocks.length,
            hasRawJS: hasRawJS,
            textPreview: text.slice(0, 400)
        };
    }""")
    print("=== 结果页检查 ===")
    print(f"voice-float-bar 存在: {result_info['voiceFloatBarExists']}")
    print(f"语音按钮存在: {result_info['voiceBtnExists']}, 文本: {result_info['voiceBtnText']}")
    print(f"底部操作栏 marker 存在: {result_info['bottomBarMarkerExists']}, 按钮数: {result_info['bottomButtonCount']}")
    print(f"pre/code 块数量: {result_info['preBlocks']}/{result_info['codeBlocks']}")
    print(f"仍有原始 JS 文本: {result_info['hasRawJS']}")

    # 断言：修复后结果页不应出现可见 JS 代码块
    assert result_info['preBlocks'] == 0, f"结果页仍有 {result_info['preBlocks']} 个 <pre> 代码块"
    assert result_info['codeBlocks'] == 0, f"结果页仍有 {result_info['codeBlocks']} 个 <code> 代码块"
    assert not result_info['hasRawJS'], "结果页仍有原始 JS 文本暴露"
    assert result_info['voiceFloatBarExists'], "结果页缺少 voice-float-bar"
    assert result_info['voiceBtnExists'], "结果页缺少语音播报按钮"
    assert result_info['bottomBarMarkerExists'], "结果页缺少底部操作栏 marker"
    assert result_info['bottomButtonCount'] >= 2, f"结果页底部操作栏按钮不足: {result_info['bottomButtonCount']}"

    page.screenshot(path="d:\\GBT\\ai-food-scanner\\diag_shots\\result_after_fix.png", full_page=True)
    print("结果页截图: diag_shots/result_after_fix.png\n")

    # 3. 验证扫描页（不上传，仅检查卡片容器 marker）
    page.goto(f"{BASE}/?test=1&page=scan")
    page.wait_for_load_state("networkidle")
    time.sleep(5)

    scan_info = page.evaluate("""() => {
        const scanCardMarker = document.querySelector('.scan-card-marker');
        const scanCardParent = scanCardMarker ? scanCardMarker.closest('div[data-testid="stVerticalBlock"]') : null;
        const uploader = document.querySelector('.stFileUploader') || document.querySelector('input[type="file"]');
        const preBlocks = document.querySelectorAll('pre');
        const codeBlocks = document.querySelectorAll('code');
        return {
            scanCardMarkerExists: !!scanCardMarker,
            scanCardParentExists: !!scanCardParent,
            uploaderExists: !!uploader,
            preBlocks: preBlocks.length,
            codeBlocks: codeBlocks.length
        };
    }""")
    print("=== 扫描页检查 ===")
    print(f"上传卡片 marker 存在: {scan_info['scanCardMarkerExists']}, 父容器存在: {scan_info['scanCardParentExists']}")
    print(f"文件上传器存在: {scan_info['uploaderExists']}")
    print(f"pre/code 块数量: {scan_info['preBlocks']}/{scan_info['codeBlocks']}")
    assert scan_info['scanCardMarkerExists'], "扫描页缺少 upload 卡片 marker"
    assert scan_info['scanCardParentExists'], "扫描页 upload 卡片父容器不存在"
    assert scan_info['uploaderExists'], "扫描页缺少文件上传器"
    assert scan_info['preBlocks'] == 0, f"扫描页仍有 {scan_info['preBlocks']} 个 <pre> 代码块"
    assert scan_info['codeBlocks'] == 0, f"扫描页仍有 {scan_info['codeBlocks']} 个 <code> 代码块"

    page.screenshot(path="d:\\GBT\\ai-food-scanner\\diag_shots\\scan_after_fix.png", full_page=True)
    print("扫描页截图: diag_shots/scan_after_fix.png\n")

    print("=== 全部检查通过 ===")
    browser.close()
