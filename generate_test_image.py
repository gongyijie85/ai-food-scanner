"""
生成测试用配料表图片
用途：为 prototype_mimo.py 提供测试图片
运行环境：Python 3.10+
依赖：pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont


def create_label_image(output_path="test_label.jpg"):
    """生成一张模拟食品配料表图片."""
    # 图片尺寸：模拟手机拍摄的配料表区域(宽800,高1000)
    width, height = 800, 1000

    # 白色背景,模拟食品包装标签
    img = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # 尝试使用系统中文字体,找不到就用默认字体
    try:
        # Windows 常见中文字体
        title_font = ImageFont.truetype("msyh.ttc", 56)
        subtitle_font = ImageFont.truetype("msyh.ttc", 36)
        body_font = ImageFont.truetype("msyh.ttc", 32)
        small_font = ImageFont.truetype("msyh.ttc", 24)
    except OSError:
        # 如果找不到微软雅黑,用系统默认字体
        title_font = ImageFont.load_default()
        subtitle_font = body_font = small_font = title_font

    # 顶部标题
    draw.text((60, 60), "配 料 表", fill="#1A1A1A", font=title_font)
    draw.line((60, 140, 740, 140), fill="#CCCCCC", width=2)

    # 配料内容(故意包含常见添加剂,测试识别和分级)
    ingredients = (
        "配料：水、小麦粉、白砂糖、食用植物油、食用盐、"
        "食品添加剂(山梨酸钾、谷氨酸钠、焦糖色、特丁基对苯二酚)、"
        "食品用香精。"
    )

    # 手动换行：每行约20个汉字
    lines = []
    current_line = ""
    for char in ingredients:
        current_line += char
        if len(current_line) >= 22:
            lines.append(current_line)
            current_line = ""
    if current_line:
        lines.append(current_line)

    y = 190
    for line in lines:
        draw.text((60, y), line, fill="#333333", font=body_font)
        y += 60

    # 营养成分表标题
    y += 40
    draw.text((60, y), "营养成分表", fill="#1A1A1A", font=subtitle_font)
    draw.line((60, y + 60, 740, y + 60), fill="#CCCCCC", width=2)

    # 营养成分数据
    nutrition = [
        ("项目", "每100克", "NRV%"),
        ("能量", "2156千焦", "26%"),
        ("蛋白质", "6.8克", "11%"),
        ("脂肪", "32.5克", "54%"),
        ("碳水化合物", "52.3克", "17%"),
        ("钠", "680毫克", "34%"),
    ]

    y += 100
    col_x = [60, 400, 620]
    for row in nutrition:
        for i, text in enumerate(row):
            draw.text((col_x[i], y), text, fill="#333333", font=body_font)
        y += 55
        if row == nutrition[0]:
            # 表头下加横线
            draw.line((60, y - 10, 740, y - 10), fill="#DDDDDD", width=2)

    # 底部提示
    y += 60
    draw.text((60, y), "过敏原提示：含有小麦及其制品。", fill="#666666", font=small_font)

    # 保存图片
    img.save(output_path, quality=95)
    print(f"测试图片已生成：{output_path}")
    print(f"图片尺寸：{width}x{height}")


if __name__ == "__main__":
    create_label_image()
