"""GB 2760-2024 导入脚本测试."""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.import_gb2760 import DB_PATH, SHA256_PATH


def test_sqlite_exists():
    """数据库文件必须存在."""
    assert DB_PATH.exists(), f"数据库不存在: {DB_PATH}"


def test_sentinel_additives():
    """磷脂、改性大豆磷脂、酶解大豆磷脂三个哨兵记录正确."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT canonical_name, cns, ins FROM additives WHERE canonical_name IN (?, ?, ?)",
        ("磷脂", "改性大豆磷脂", "酶解大豆磷脂"),
    ).fetchall()
    names = {r["canonical_name"]: (r["cns"], r["ins"]) for r in rows}
    assert "磷脂" in names
    assert names["磷脂"][0] == "04.010"
    assert names["磷脂"][1] == "322"
    assert "改性大豆磷脂" in names
    assert names["改性大豆磷脂"][0] == "10.019"
    assert "酶解大豆磷脂" in names
    assert names["酶解大豆磷脂"][0] == "10.040"
    conn.close()


def test_explicit_aliases():
    """显式别名指向磷脂."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT alias, canonical_name FROM additive_aliases").fetchall()
    aliases = {r["alias"]: r["canonical_name"] for r in rows}
    assert aliases.get("卵磷脂") == "磷脂"
    assert aliases.get("大豆磷脂") == "磷脂"
    assert aliases.get("大豆卵磷脂") == "磷脂"
    conn.close()


def test_foreign_keys_enabled():
    """数据库 schema 启用了外键约束."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    row = conn.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1
    # 确认 usage_scopes 表存在外键定义
    fk_rows = conn.execute("PRAGMA foreign_key_list(additive_usage_scopes)").fetchall()
    assert any(r["table"] == "additives" for r in fk_rows)
    conn.close()


def test_sha256_file_exists():
    """SHA-256 校验文件存在且包含 PDF 和 SQLite 两项."""
    assert SHA256_PATH.exists(), f"校验文件不存在: {SHA256_PATH}"
    content = SHA256_PATH.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    assert len(lines) >= 2
    assert "GB2760-2024.pdf" in lines[0]
    assert "gb2760_2024.sqlite" in lines[1]
