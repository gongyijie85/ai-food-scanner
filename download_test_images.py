"""
下载测试用配料表图片
用途：从公开网络来源下载食品配料表图片，保存到 test_images/ 用于业务测试
注意：图片仅用于本地/线上测试，不加入 git（已在 .gitignore 中排除）
"""

import os
import requests

# 目标目录
TARGET_DIR = r"d:\GBT\ai-food-scanner\test_images"
os.makedirs(TARGET_DIR, exist_ok=True)

# 图片来源：什么值得买等测评网站的公开配料表实拍图
# 由于电商商品详情页需要 JS 渲染/反爬，这里优先使用测评文章中公开的配料表图片
SOURCES = [
    # 文件名, URL, 来源文章/页面
    ("taobao_001.jpg", "https://aka.doubaocdn.com/s/yX0b1whRz2", "什么值得买：一文教你看懂食品配料表"),
    ("taobao_002.jpg", "https://aka.doubaocdn.com/s/rteo1whRz2", "什么值得买：一文教你看懂食品配料表"),
    ("taobao_003.jpg", "https://aka.doubaocdn.com/s/aP8A1whRz2", "什么值得买：一文教你看懂食品配料表"),
    ("jd_001.jpg", "https://aka.doubaocdn.com/s/vNEH1whRz2", "什么值得买：水饺配料表怎么看"),
    ("jd_002.jpg", "https://aka.doubaocdn.com/s/Uxwu1whRz2", "什么值得买：水饺配料表怎么看"),
    ("jd_003.jpg", "https://aka.doubaocdn.com/s/RmZh1whRz2", "什么值得买：一文教你看懂食品配料表"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}


def download_image(filename, url):
    """下载单张图片并保存."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.raise_for_status()
        path = os.path.join(TARGET_DIR, filename)
        with open(path, "wb") as f:
            f.write(response.content)
        size_kb = len(response.content) / 1024
        print(f"✅ {filename}: 下载成功，{size_kb:.1f} KB")
        return True
    except Exception as e:
        print(f"❌ {filename}: 下载失败 - {e}")
        return False


def main():
    print(f"开始下载测试图片到：{TARGET_DIR}")
    success_count = 0
    for filename, url, source in SOURCES:
        if download_image(filename, url):
            success_count += 1
    print(f"\n下载完成：{success_count}/{len(SOURCES)} 张成功")


if __name__ == "__main__":
    main()
