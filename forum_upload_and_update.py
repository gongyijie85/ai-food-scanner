"""从 Chrome/Edge 解密读取 forum.trae.cn 登录 cookie，上传 Demo 配图，并更新论坛帖子.

需要：
- 同一 Windows 用户已用 Chrome/Edge 登录 forum.trae.cn
- 运行前关闭 Chrome/Edge，避免 Cookies 数据库被锁定
- 安装了 requests、cryptography
"""

import base64
import ctypes
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORUM_HOST = "https://forum.trae.cn"
TOPIC_ID = 51391
TOPIC_URL = f"{FORUM_HOST}/t/topic/{TOPIC_ID}"

ASSET_DIR = Path(__file__).resolve().parent / "design" / "demo_assets"
FILES = [
    ("demo_compare_ocr.png", ASSET_DIR / "demo_compare_ocr.png"),
    ("demo_case_clear.png", ASSET_DIR / "demo_case_clear.png"),
    ("demo_case_blur.png", ASSET_DIR / "demo_case_blur.png"),
]

# 本地草稿 Markdown（更新后将用 CDN 链接替换占位符）
LOCAL_MARKDOWN_PATH = Path(r"d:\GBT\初赛Demo帖_AI食品配料表识别工具.md")


def _unprotect_data(data: bytes) -> bytes:
    """调用 Windows DPAPI CryptUnprotectData 解密 bytes."""

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.c_ulong),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    blob_in = DATA_BLOB()
    blob_in.cbData = len(data)
    blob_in.pbData = ctypes.cast(
        ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_ubyte)
    )

    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    ):
        raise OSError("CryptUnprotectData 失败")

    result = bytes(blob_out.pbData[: blob_out.cbData])
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return result


def _get_chrome_master_key(user_data_dir: Path) -> bytes:
    """从 Chrome Local State 读取并解密 master key."""
    local_state_path = user_data_dir / "Local State"
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    encrypted_key = local_state["os_crypt"]["encrypted_key"]
    key_data = base64.b64decode(encrypted_key)
    return _unprotect_data(key_data[5:])


def _decrypt_cookie_value(encrypted_value: bytes, key: bytes) -> str:
    """用 AES-GCM 解密 cookie 的 encrypted_value."""
    if encrypted_value[:3] in (b"v10", b"v11"):
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:-16]
        tag = encrypted_value[-16:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext + tag, None).decode("utf-8")
    return _unprotect_data(encrypted_value).decode("utf-8")


def _get_session_cookie() -> str:
    """从 Chrome/Edge 解密读取 _forum_session."""
    user_data_dirs = [
        Path(os.path.expandvars(r"%LOCALAPPDATA%")) / "Google" / "Chrome" / "User Data",
        Path(os.path.expandvars(r"%LOCALAPPDATA%"))
        / "Microsoft"
        / "Edge"
        / "User Data",
    ]
    for user_data_dir in user_data_dirs:
        if not user_data_dir.exists():
            continue
        cookie_db = user_data_dir / "Default" / "Network" / "Cookies"
        if not cookie_db.exists():
            cookie_db = user_data_dir / "Default" / "Cookies"
        if not cookie_db.exists():
            continue

        try:
            key = _get_chrome_master_key(user_data_dir)
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            tmp_path.write_bytes(cookie_db.read_bytes())
            try:
                conn = sqlite3.connect(str(tmp_path))
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT encrypted_value FROM cookies WHERE host_key LIKE '%forum.trae.cn%' AND name = '_forum_session'"
                )
                row = cursor.fetchone()
                conn.close()
                if row:
                    return _decrypt_cookie_value(row[0], key)
            finally:
                tmp_path.unlink(missing_ok=True)
        except PermissionError:
            print(f"无法读取 {cookie_db}，可能浏览器正在运行")
        except Exception as exc:
            print(f"读取 {user_data_dir.name} cookie 失败：{exc}")
    raise RuntimeError(
        "未找到 forum.trae.cn 的 _forum_session cookie，请确认已登录并关闭浏览器"
    )


def _get_csrf(session: requests.Session) -> str:
    """访问编辑页获取 CSRF token."""
    resp = session.get(TOPIC_URL, timeout=30)
    resp.raise_for_status()
    # Discourse 的 CSRF token 通常在 meta 标签或页面数据中
    m = re.search(r'<meta name="csrf-token" content="([^"]+)"', resp.text)
    if m:
        return m.group(1)
    m = re.search(r'"csrf-token":"([^"]+)"', resp.text)
    if m:
        return m.group(1)
    raise RuntimeError("未找到 CSRF token")


def upload_images(session: requests.Session, csrf: str) -> dict[str, str]:
    """上传 3 张图片，返回文件名到 CDN URL 的映射."""
    upload_url = f"{FORUM_HOST}/uploads.json"
    headers = {
        "X-CSRF-Token": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": TOPIC_URL,
    }
    cdn_map = {}
    for name, path in FILES:
        if not path.exists():
            print(f"跳过不存在的文件：{path}")
            continue
        with open(path, "rb") as f:
            files = {"file": (name, f, "image/png")}
            data = {"type": "composer", "authenticity_token": csrf}
            resp = session.post(
                upload_url, headers=headers, files=files, data=data, timeout=60
            )
        print(f"{name}: HTTP {resp.status_code}")
        print(resp.text[:500])
        if resp.status_code == 200:
            body = resp.json()
            cdn_map[name] = body.get("url", body.get("short_url", ""))
    return cdn_map


def _get_topic_and_post_id(session: requests.Session) -> tuple[int, int]:
    """获取 topic 的第一个 post id."""
    url = f"{FORUM_HOST}/t/{TOPIC_ID}.json"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    post_id = data["post_stream"]["posts"][0]["id"]
    return data["id"], post_id


def _clean_title(title: str) -> str:
    """移除标题中追加的 base64 乱码."""
    base_pattern = re.compile(r"[A-Za-z0-9+/=]{1000,}")
    cleaned = base_pattern.sub("", title).strip()
    return cleaned


def update_post(
    session: requests.Session, csrf: str, post_id: int, cdn_map: dict[str, str]
):
    """更新帖子正文：用本地 Markdown 内容，替换占位符为 CDN 链接."""
    raw_md = LOCAL_MARKDOWN_PATH.read_text(encoding="utf-8")

    # 替换占位符为 CDN 链接
    for filename, cdn_url in cdn_map.items():
        # 匹配不同 alt 文本
        raw_md = re.sub(
            rf"!\[[^\]]*\]\({re.escape(filename)}\)",
            f"![{filename.replace('.png', '')}]({cdn_url})",
            raw_md,
        )

    # 删除上传说明文字
    raw_md = re.sub(r"> 上传说明：[^\n]*\n", "", raw_md)
    raw_md = re.sub(r"> 截图位置：[^\n]*\n", "", raw_md)

    edit_url = f"{FORUM_HOST}/posts/{post_id}.json"
    headers = {
        "X-CSRF-Token": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": TOPIC_URL,
        "Content-Type": "application/json",
    }
    payload = {
        "raw": raw_md,
        "edit_reason": "上传 Demo 配图并替换为 CDN 链接",
    }
    resp = session.put(edit_url, headers=headers, data=json.dumps(payload), timeout=60)
    print(f"更新 post {post_id}: HTTP {resp.status_code}")
    print(resp.text[:500])
    return resp.status_code == 200


def update_title(session: requests.Session, csrf: str, topic_id: int, title: str):
    """更新帖子标题."""
    url = f"{FORUM_HOST}/t/{topic_id}.json"
    headers = {
        "X-CSRF-Token": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": TOPIC_URL,
        "Content-Type": "application/json",
    }
    payload = {"title": title}
    resp = session.put(url, headers=headers, data=json.dumps(payload), timeout=60)
    print(f"更新标题: HTTP {resp.status_code}")
    print(resp.text[:500])
    return resp.status_code == 200


def main():
    session_cookie = _get_session_cookie()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    session.cookies.set("_forum_session", session_cookie, domain="forum.trae.cn")

    csrf = _get_csrf(session)
    print(f"CSRF: {csrf[:20]}...")

    print("\n开始上传图片...")
    cdn_map = upload_images(session, csrf)
    print("\nCDN 映射：")
    print(json.dumps(cdn_map, ensure_ascii=False, indent=2))

    if not cdn_map:
        print("图片上传失败，停止更新帖子")
        return

    print("\n获取帖子信息...")
    topic_id, post_id = _get_topic_and_post_id(session)
    print(f"topic_id={topic_id}, post_id={post_id}")

    print("\n更新帖子正文...")
    update_post(session, csrf, post_id, cdn_map)

    print("\n清理标题...")
    title = "【智慧助老赛道】 拍了就懂 AI 食品配料表识别工具（初赛 Demo）"
    update_title(session, csrf, topic_id, title)

    print("\n完成。请打开帖子检查效果。")


if __name__ == "__main__":
    main()
