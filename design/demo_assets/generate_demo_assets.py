"""生成初赛 Demo 帖所需的 3 张配图.

输出:
- demo_compare_ocr.png: 普通 OCR 与本项目能力对比
- demo_case_clear.png: 清晰配料表识别案例
- demo_case_blur.png: 模糊图片失败案例
"""

import os

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# 适老化配色
COLOR_BG = "#FFF8F0"
COLOR_TEXT = "#1A1A1A"
COLOR_RED = "#D32F2F"
COLOR_GREEN = "#388E3C"
COLOR_BLUE = "#1976D2"
COLOR_GRAY = "#757575"
COLOR_ORANGE = "#F57C00"


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """尝试加载系统字体，找不到就用默认字体."""
    candidates = [
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
        "C:\\Windows\\Fonts\\simsun.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    """绘制圆角矩形."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)


def generate_compare_ocr():
    """生成普通 OCR vs 本项目对比图."""
    width, height = 1000, 600
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(36)
    header_font = _get_font(28)
    body_font = _get_font(22)
    small_font = _get_font(18)

    # 标题
    title = "普通 OCR  vs  本项目：不只是'转录'配料表"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (bbox[2] - bbox[0])) // 2, 30), title, fill=COLOR_TEXT, font=title_font)

    # 左侧：普通 OCR
    _draw_rounded_rect(draw, (40, 100, 470, 540), 16, "white", "#E0E0E0", 2)
    draw.text((80, 130), "普通 OCR", fill=COLOR_GRAY, font=header_font)
    items = [
        "只能把图片转成文字",
        "老人仍需逐个查添加剂含义",
        "无法判断慢病风险",
        "容易被小字、反光影响",
    ]
    y = 190
    for item in items:
        draw.text((70, y), f"· {item}", fill=COLOR_TEXT, font=body_font)
        y += 48
    draw.text((80, 430), "示例输出：", fill=COLOR_GRAY, font=small_font)
    draw.text((70, 470), "鲜山楂、低聚果糖、浓缩苹果汁", fill=COLOR_TEXT, font=body_font)

    # 右侧：本项目
    _draw_rounded_rect(draw, (530, 100, 960, 540), 16, "white", COLOR_GREEN, 2)
    draw.text((570, 130), "本项目（AI + GB 2760）", fill=COLOR_GREEN, font=header_font)
    items2 = [
        "OCR 原文校验，降低幻觉",
        "本地 GB 2760 名称匹配分类",
        "AI 推断添加剂明确标记",
        "结合档案给出个性化建议",
    ]
    y = 190
    for item in items2:
        draw.text((560, y), f"✓ {item}", fill=COLOR_TEXT, font=body_font)
        y += 48
    draw.text((570, 430), "示例输出：", fill=COLOR_GRAY, font=small_font)
    draw.text((560, 470), "0 种高风险 · 暂未发现已知高风险提示", fill=COLOR_GREEN, font=body_font)

    img.save(os.path.join(OUTPUT_DIR, "demo_compare_ocr.png"), "PNG")


def generate_case_clear():
    """生成清晰配料表案例图."""
    width, height = 900, 520
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(32)
    header_font = _get_font(26)
    body_font = _get_font(22)

    draw.text((50, 30), "清晰配料表案例：沂蒙公社山楂糕", fill=COLOR_TEXT, font=title_font)

    # 原图模拟框
    _draw_rounded_rect(draw, (50, 90, 430, 260), 12, "white", COLOR_GRAY, 1)
    draw.text((70, 110), "【原图示意】", fill=COLOR_GRAY, font=header_font)
    draw.text((70, 160), "棕色包装上的小字配料表", fill=COLOR_TEXT, font=body_font)
    draw.text((70, 200), "鲜山楂、低聚果糖、浓缩苹果汁", fill=COLOR_TEXT, font=body_font)

    # 识别结果
    _draw_rounded_rect(draw, (470, 90, 850, 260), 12, "white", COLOR_GREEN, 2)
    draw.text((490, 110), "【识别结果】", fill=COLOR_GREEN, font=header_font)
    draw.text((490, 160), "OCR 原文：鲜山楂、低聚果糖、浓缩苹果汁", fill=COLOR_TEXT, font=body_font)
    draw.text((490, 200), "GB 2760 命中：0 种", fill=COLOR_GREEN, font=body_font)

    # 最终提示
    _draw_rounded_rect(draw, (50, 300, 850, 470), 12, "#E8F5E9", COLOR_GREEN, 2)
    draw.text((70, 325), "最终提示", fill=COLOR_GREEN, font=header_font)
    draw.text((70, 380), "暂未发现已知高风险提示", fill=COLOR_GREEN, font=body_font)
    draw.text((70, 420), "配料简洁，按当前档案暂未发现高风险配料", fill=COLOR_TEXT, font=body_font)

    img.save(os.path.join(OUTPUT_DIR, "demo_case_clear.png"), "PNG")


def generate_case_blur():
    """生成模糊图片失败案例图."""
    width, height = 900, 460
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(32)
    header_font = _get_font(26)
    body_font = _get_font(22)

    draw.text((50, 30), "模糊图片失败案例：手抖/光线不足", fill=COLOR_TEXT, font=title_font)

    # 问题描述
    _draw_rounded_rect(draw, (50, 90, 850, 220), 12, "#FFF3E0", COLOR_ORANGE, 2)
    draw.text((70, 110), "可能出现的问题", fill=COLOR_ORANGE, font=header_font)
    draw.text((70, 160), "· 小字漏识：'浓缩苹果汁'可能识别不全", fill=COLOR_TEXT, font=body_font)
    draw.text((70, 200), "· 数字误读：'35%' 可能被误读为 '5.5%'", fill=COLOR_TEXT, font=body_font)

    # 解决方式
    _draw_rounded_rect(draw, (50, 250, 850, 400), 12, "#E3F2FD", COLOR_BLUE, 2)
    draw.text((70, 270), "建议重试方式", fill=COLOR_BLUE, font=header_font)
    draw.text((70, 320), "1. 点击'重新选择'", fill=COLOR_TEXT, font=body_font)
    draw.text((70, 360), "2. 在光线充足处，让配料表占满画面后重新拍摄", fill=COLOR_TEXT, font=body_font)

    img.save(os.path.join(OUTPUT_DIR, "demo_case_blur.png"), "PNG")


def main():
    """批量生成全部配图."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generate_compare_ocr()
    generate_case_clear()
    generate_case_blur()
    print(f"已生成 3 张配图到：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
