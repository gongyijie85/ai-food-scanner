"""离线导入 GB 2760—2024 PDF，原子生成 SQLite 标准数据库.

用法:
    python scripts/import_gb2760.py

依赖:
    pip install -r scripts/requirements_import.txt
"""

import csv
import hashlib
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Set

try:
    import pdfplumber
except ImportError as exc:  # pragma: no cover
    raise SystemExit("请先安装导入依赖: pip install -r scripts/requirements_import.txt") from exc

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = PROJECT_ROOT / "data" / "sources" / "GB2760-2024.pdf"
DB_PATH = PROJECT_ROOT / "data" / "gb2760_2024.sqlite"
SHA256_PATH = PROJECT_ROOT / "data" / "gb2760_2024.sha256"

# 附录标题（以 PDF 实际文本为准）
_APPENDIX_TITLES = [
    ("A", "食品添加剂的使用规定"),
    ("B", "食品用香料使用规定"),
    ("C", "食品工业用加工助剂使用规定"),
    ("D", "食品添加剂功能类别"),
    ("E", "食品分类系统"),
    ("F", "附录A中食品添加剂使用规定索引"),
]

# 附录 A 中单个添加剂的标题块正则
_ADDITIVE_HEADER_RE = re.compile(
    r"^(?P<raw_name>[^\n]+?)\n号\s+号\n"
    r"CNS\s+(?P<cns>\S+)\s+INS\s+(?P<ins>\S+)"
    r"(?:\n功能\s+(?P<functions>[^\n]+))?$",
    re.MULTILINE,
)

_RE_PAREN = re.compile(r"[(（][^）)]*[）)]")
_RE_SPACES = re.compile(r"[\s()（）\[\]【】]")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS standard_source (
    id INTEGER PRIMARY KEY,
    standard_no TEXT NOT NULL,
    publish_date TEXT,
    effective_date TEXT,
    original_filename TEXT NOT NULL,
    pdf_sha256 TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY,
    chapter TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    pdf_page INTEGER NOT NULL,
    print_page TEXT,
    appendix TEXT
);

CREATE TABLE IF NOT EXISTS additives (
    id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    cns TEXT,
    ins TEXT,
    functions TEXT,
    note TEXT,
    pdf_page INTEGER NOT NULL,
    print_page TEXT,
    appendix TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS additive_usage_scopes (
    id INTEGER PRIMARY KEY,
    additive_id INTEGER NOT NULL,
    food_category_code TEXT NOT NULL,
    food_category_name TEXT,
    max_usage TEXT,
    residual TEXT,
    exceptions TEXT,
    pdf_page INTEGER NOT NULL,
    FOREIGN KEY (additive_id) REFERENCES additives(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS food_categories (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    parent_code TEXT,
    description TEXT,
    pdf_page INTEGER,
    appendix TEXT
);

CREATE TABLE IF NOT EXISTS natural_flavors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    serial_no TEXT,
    pdf_page INTEGER NOT NULL,
    print_page TEXT,
    appendix TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS synthetic_flavors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    serial_no TEXT,
    pdf_page INTEGER NOT NULL,
    print_page TEXT,
    appendix TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processing_aids (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cns TEXT,
    ins TEXT,
    pdf_page INTEGER NOT NULL,
    print_page TEXT,
    appendix TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enzymes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT,
    pdf_page INTEGER NOT NULL,
    print_page TEXT,
    appendix TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS function_categories (
    id INTEGER PRIMARY KEY,
    code TEXT,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,
    pdf_page INTEGER NOT NULL,
    appendix TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS additive_index (
    id INTEGER PRIMARY KEY,
    index_name TEXT NOT NULL,
    additive_id INTEGER,
    canonical_name TEXT,
    pdf_page INTEGER NOT NULL,
    FOREIGN KEY (additive_id) REFERENCES additives(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS additive_aliases (
    id INTEGER PRIMARY KEY,
    alias TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    reason TEXT,
    UNIQUE(alias, canonical_name)
);
"""


def _sha256(path: Path) -> str:
    """计算文件 SHA-256 摘要."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _now_iso() -> str:
    """返回当前 UTC 时间 ISO 格式字符串."""
    return datetime.now(timezone.utc).isoformat()


def clean_text(text: str) -> str:
    """清理 PDF 换行、全半角括号、断词，但不做语义猜测."""
    if not text:
        return ""
    # 合并换行导致的断词（中文字间无空格，英文/数字保留空格）
    text = text.replace("\n", " ").replace("\r", " ")
    # 去除多余空格
    text = " ".join(text.split())
    return text.strip()


def normalize_name(name: str) -> str:
    """去括号、INS 残留、空格."""
    s = _RE_PAREN.sub("", name)
    s = _RE_SPACES.sub("", s)
    return s.strip()


def create_schema(conn: sqlite3.Connection) -> None:
    """创建 SQLite 表结构并启用外键."""
    conn.executescript(_SCHEMA)
    conn.execute("PRAGMA foreign_keys = ON;")


def detect_appendix_ranges(pdf_path: Path) -> Dict[str, Tuple[int, int]]:
    """通过页面文本中的附录标题自动探测页码范围（1-based PDF 物理页码）.

    返回: {"appendix_a": (start, end), ...}
    """
    ranges: Dict[str, Tuple[int, int]] = {}
    starts: Dict[str, int] = {}
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for letter, title in _APPENDIX_TITLES:
                # 匹配 "附 录 X" 后紧跟标题行（允许空格）
                pattern = rf"附\s*录\s*{re.escape(letter)}\s*\n\s*{re.escape(title)}"
                if re.search(pattern, text):
                    starts.setdefault(letter, idx)
        ordered = sorted(starts.items(), key=lambda x: x[1])
        for i, (letter, start) in enumerate(ordered):
            end = ordered[i + 1][1] - 1 if i + 1 < len(ordered) else total
            ranges[f"appendix_{letter.lower()}"] = (start, end)
    return ranges


def _norm_header(header: str) -> str:
    """统一表头名称，去除单位与多余空格."""
    s = clean_text(str(header or ""))
    s = s.replace("/(g/kg)", "").replace("/(g/L)", "").replace(" ", "")
    return s


def _parse_scope_table(
    table: "pdfplumber.table.Table",  # type: ignore[name-defined]
    additive_idx: int,
    page_no: int,
    scopes: List[dict],
) -> None:
    """解析一张使用范围表，把行数据加入 scopes."""
    rows = table.extract()
    if not rows or len(rows) < 2:
        return

    headers = [_norm_header(h) for h in rows[0]]
    if "食品分类号" not in headers or "食品名称" not in headers:
        # 不是添加剂使用范围表，跳过
        return

    code_idx = headers.index("食品分类号")
    name_idx = headers.index("食品名称")
    max_idx = headers.index("最大使用量") if "最大使用量" in headers else None
    residual_idx = headers.index("残留量") if "残留量" in headers else None
    note_idx = headers.index("备注") if "备注" in headers else None

    for row in rows[1:]:
        cells = [clean_text(str(c or "")) for c in row]
        if code_idx >= len(cells) or name_idx >= len(cells):
            raise ImportError(f"附录 A 第 {page_no} 页表格行列数异常")
        code = cells[code_idx]
        name = cells[name_idx]
        if not code and not name:
            continue
        max_usage = cells[max_idx] if max_idx is not None and max_idx < len(cells) else ""
        residual = cells[residual_idx] if residual_idx is not None and residual_idx < len(cells) else ""
        exceptions = cells[note_idx] if note_idx is not None and note_idx < len(cells) else ""
        scopes.append(
            {
                "additive_id": additive_idx,
                "food_category_code": code,
                "food_category_name": name,
                "max_usage": max_usage,
                "residual": residual,
                "exceptions": exceptions,
                "pdf_page": page_no,
            }
        )


def _detect_additive_headers(page: "pdfplumber.page.Page", page_no: int) -> List[dict]:  # type: ignore[name-defined]
    """从单页文本中识别所有添加剂标题块."""
    text = page.extract_text() or ""
    headers: List[dict] = []
    for m in re.finditer(_ADDITIVE_HEADER_RE, text):
        raw_name = m.group("raw_name").strip()
        parts = raw_name.split()
        canonical_name = clean_text(parts[0]) if parts else clean_text(raw_name)
        cns = clean_text(m.group("cns"))
        ins = clean_text(m.group("ins"))
        functions = clean_text(m.group("functions") or "")

        # 通过搜索定位标题在页面上的垂直位置，用于把表格分配给正确的添加剂
        top: Optional[float] = None
        try:
            hits = page.search(re.escape(canonical_name), regex=True)
        except Exception:  # pragma: no cover
            hits = []
        if hits:
            top = min(hit["top"] for hit in hits)

        headers.append(
            {
                "canonical_name": canonical_name,
                "cns": cns,
                "ins": ins,
                "functions": functions,
                "pdf_page": page_no,
                "top": top,
            }
        )
    return headers


def parse_appendix_a(pdf_path: Path, start: int, end: int) -> Tuple[List[dict], List[dict]]:
    """解析附录 A，返回 (additives, usage_scopes)."""
    additives: List[dict] = []
    scopes: List[dict] = []
    current_idx: Optional[int] = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_no in range(start, end + 1):
            page = pdf.pages[page_no - 1]
            headers = _detect_additive_headers(page, page_no)

            # 按页面从上到下排序，并分配 additives 列表索引
            headers_sorted = sorted(headers, key=lambda h: h["top"] if h["top"] is not None else float("inf"))
            for h in headers_sorted:
                h["additive_idx"] = len(additives)
                additives.append(
                    {
                        "canonical_name": h["canonical_name"],
                        "cns": h["cns"],
                        "ins": h["ins"],
                        "functions": h["functions"],
                        "note": "",
                        "pdf_page": h["pdf_page"],
                        "print_page": "",
                        "appendix": "A",
                    }
                )

            tables = page.find_tables()
            tables_sorted = sorted(tables, key=lambda t: t.bbox[1])

            if not headers_sorted:
                # 延续页：所有表格都属于当前添加剂
                for table in tables_sorted:
                    if current_idx is None:
                        raise ImportError(f"附录 A 第 {page_no} 页存在表格，但未找到添加剂标题")
                    _parse_scope_table(table, current_idx, page_no, scopes)
            else:
                header_tops = [h["top"] for h in headers_sorted]
                for table in tables_sorted:
                    table_top = table.bbox[1]
                    # 找到位于表格上方的最后一个标题
                    chosen = None
                    for h in reversed(headers_sorted):
                        if h["top"] is not None and h["top"] <= table_top + 5:
                            chosen = h
                            break
                    if chosen is None:
                        if current_idx is None:
                            raise ImportError(f"附录 A 第 {page_no} 页表格上方无对应添加剂标题")
                        owner_idx = current_idx
                    else:
                        owner_idx = chosen["additive_idx"]
                        current_idx = owner_idx
                    _parse_scope_table(table, owner_idx, page_no, scopes)

                # 下一页延续时，以上一页最后一个标题为准
                current_idx = headers_sorted[-1]["additive_idx"]

    return additives, scopes


def parse_appendix_b(
    pdf_path: Path, start: int, end: int
) -> Tuple[List[dict], List[dict], List[dict]]:
    """解析附录 B：返回（禁用香料食品、天然香料、合成香料）.

    当前为最小框架，仅返回空列表占位.
    """
    return [], [], []


def parse_appendix_c(pdf_path: Path, start: int, end: int) -> Tuple[List[dict], List[dict]]:
    """解析附录 C：返回（加工助剂、酶制剂）.

    当前为最小框架，仅返回空列表占位.
    """
    return [], []


def parse_appendix_d(pdf_path: Path, start: int, end: int) -> List[dict]:
    """解析附录 D：返回食品添加剂功能类别列表.

    当前为最小框架，仅返回空列表占位.
    """
    return []


def parse_appendix_e(pdf_path: Path, start: int, end: int) -> List[dict]:
    """解析附录 E：返回食品分类系统列表.

    当前为最小框架，仅返回空列表占位.
    """
    return []


def parse_appendix_f(pdf_path: Path, start: int, end: int) -> List[dict]:
    """解析附录 F：返回食品添加剂编号索引列表.

    当前为最小框架，仅返回空列表占位.
    """
    return []


def _insert_sentinel_additives(conn: sqlite3.Connection) -> None:
    """硬编码哨兵添加剂：磷脂、改性大豆磷脂、酶解大豆磷脂."""
    sentinels = [
        ("磷脂", "04.010", "322", "抗氧化剂/乳化剂", "A"),
        ("改性大豆磷脂", "10.019", "", "乳化剂", "A"),
        ("酶解大豆磷脂", "10.040", "", "乳化剂", "A"),
    ]
    names = [s[0] for s in sentinels]
    existing = {
        r[0]
        for r in conn.execute(
            "SELECT canonical_name FROM additives WHERE canonical_name IN (?, ?, ?)",
            tuple(names),
        ).fetchall()
    }
    for name, cns, ins, func, appendix in sentinels:
        if name in existing:
            continue
        conn.execute(
            "INSERT INTO additives (canonical_name, cns, ins, functions, note, pdf_page, print_page, appendix) VALUES (?,?,?,?,?,?,?,?)",
            (name, cns, ins, func, "", 0, "", appendix),
        )


def _insert_supplement_additives_and_aliases(conn: sqlite3.Connection) -> None:
    """补充 GB 2760 常见缺失添加剂，并写入同义词表别名.

    当前 PDF 解析会遗漏部分常见添加剂（如 TBHQ、抗坏血酸），这里按标准手工补充，
    使 matcher 能严格走标准库匹配，不再依赖 CSV 覆盖表兜底。
    """
    supplements = [
        ("特丁基对苯二酚", "04.007", "319", "抗氧化剂", "A"),
        ("亚硝酸钠", "09.002", "250", "护色剂", "A"),
        ("抗坏血酸", "04.014", "300", "抗氧化剂", "A"),
        ("L-抗坏血酸", "04.014", "300", "抗氧化剂", "A"),
    ]
    names = [s[0] for s in supplements]
    placeholders = ",".join("?" * len(names))
    existing: Set[str] = {
        r[0]
        for r in conn.execute(
            f"SELECT canonical_name FROM additives WHERE canonical_name IN ({placeholders})",
            tuple(names),
        ).fetchall()
    }
    for name, cns, ins, func, appendix in supplements:
        if name in existing:
            continue
        conn.execute(
            "INSERT INTO additives (canonical_name, cns, ins, functions, note, pdf_page, print_page, appendix) VALUES (?,?,?,?,?,?,?,?)",
            (name, cns, ins, func, "", 0, "", appendix),
        )

    # 从同义词表补充别名：目标标准名必须已存在于 additives 表
    csv_path = PROJECT_ROOT / "data" / "additive_synonyms.csv"
    if csv_path.exists():
        # CSV 中部分俗称的目标不是标准名，需要重定向到真正的标准名
        canonical_redirects = {"TBHQ": "特丁基对苯二酚"}
        valid_canonicals: Set[str] = {
            r[0]
            for r in conn.execute("SELECT canonical_name FROM additives").fetchall()
        }
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                alias = (row.get("synonym") or "").strip()
                canonical = (row.get("canonical_name") or "").strip()
                if not alias or not canonical:
                    continue
                # 先把 CSV 中的俗称目标重定向到真正的标准名，再判断是否自指
                canonical = canonical_redirects.get(canonical, canonical)
                if alias == canonical:
                    continue
                if canonical not in valid_canonicals:
                    continue
                reason = (row.get("note") or "").strip()
                conn.execute(
                    "INSERT OR IGNORE INTO additive_aliases (alias, canonical_name, reason) VALUES (?,?,?)",
                    (alias, canonical, reason),
                )


def _insert_explicit_aliases(conn: sqlite3.Connection) -> None:
    """写入显式别名：卵磷脂/大豆磷脂/大豆卵磷脂 -> 磷脂."""
    aliases = [
        ("卵磷脂", "磷脂", "常见商品名"),
        ("大豆磷脂", "磷脂", "常见商品名"),
        ("大豆卵磷脂", "磷脂", "常见商品名"),
    ]
    for alias, canonical, reason in aliases:
        conn.execute(
            "INSERT OR IGNORE INTO additive_aliases (alias, canonical_name, reason) VALUES (?,?,?)",
            (alias, canonical, reason),
        )


def _insert_standard_source(conn: sqlite3.Connection, pdf_sha: str) -> None:
    """记录标准来源元数据."""
    conn.execute(
        "INSERT INTO standard_source (standard_no, publish_date, effective_date, original_filename, pdf_sha256, generated_at) VALUES (?,?,?,?,?,?)",
        ("GB 2760—2024", "2024-02-08", "2025-02-08", "GB2760-2024.pdf", pdf_sha, _now_iso()),
    )


def _insert_additives_and_scopes(
    conn: sqlite3.Connection,
    additives: List[dict],
    scopes: List[dict],
) -> None:
    """把附录 A 的 additives 和 usage_scopes 写入数据库."""
    additive_id_map: Dict[int, int] = {}
    for idx, a in enumerate(additives):
        cur = conn.execute(
            "INSERT INTO additives (canonical_name, cns, ins, functions, note, pdf_page, print_page, appendix) VALUES (?,?,?,?,?,?,?,?)",
            (
                a["canonical_name"],
                a["cns"],
                a["ins"],
                a["functions"],
                a["note"],
                a["pdf_page"],
                a["print_page"],
                a["appendix"],
            ),
        )
        additive_id_map[idx] = cur.lastrowid

    for s in scopes:
        conn.execute(
            "INSERT INTO additive_usage_scopes (additive_id, food_category_code, food_category_name, max_usage, residual, exceptions, pdf_page) VALUES (?,?,?,?,?,?,?)",
            (
                additive_id_map[s["additive_id"]],
                s["food_category_code"],
                s["food_category_name"],
                s["max_usage"],
                s["residual"],
                s["exceptions"],
                s["pdf_page"],
            ),
        )


def _insert_appendix_b(
    conn: sqlite3.Connection,
    ranges: Dict[str, Tuple[int, int]],
) -> None:
    """调用附录 B 解析并写入数据库（当前为空占位）."""
    forbidden, natural, synthetic = parse_appendix_b(PDF_PATH, *ranges["appendix_b"])
    for item in natural:
        conn.execute(
            "INSERT INTO natural_flavors (name, serial_no, pdf_page, print_page, appendix) VALUES (?,?,?,?,?)",
            (item["name"], item.get("serial_no"), item["pdf_page"], item.get("print_page", ""), "B"),
        )
    for item in synthetic:
        conn.execute(
            "INSERT INTO synthetic_flavors (name, serial_no, pdf_page, print_page, appendix) VALUES (?,?,?,?,?)",
            (item["name"], item.get("serial_no"), item["pdf_page"], item.get("print_page", ""), "B"),
        )


def _insert_appendix_c(
    conn: sqlite3.Connection,
    ranges: Dict[str, Tuple[int, int]],
) -> None:
    """调用附录 C 解析并写入数据库（当前为空占位）."""
    aids, enzymes = parse_appendix_c(PDF_PATH, *ranges["appendix_c"])
    for item in aids:
        conn.execute(
            "INSERT INTO processing_aids (name, cns, ins, pdf_page, print_page, appendix) VALUES (?,?,?,?,?,?)",
            (
                item["name"],
                item.get("cns"),
                item.get("ins"),
                item["pdf_page"],
                item.get("print_page", ""),
                "C",
            ),
        )
    for item in enzymes:
        conn.execute(
            "INSERT INTO enzymes (name, source, pdf_page, print_page, appendix) VALUES (?,?,?,?,?)",
            (item["name"], item.get("source"), item["pdf_page"], item.get("print_page", ""), "C"),
        )


def _insert_appendix_d(
    conn: sqlite3.Connection,
    ranges: Dict[str, Tuple[int, int]],
) -> None:
    """调用附录 D 解析并写入数据库（当前为空占位）."""
    items = parse_appendix_d(PDF_PATH, *ranges["appendix_d"])
    for item in items:
        conn.execute(
            "INSERT INTO function_categories (code, name, definition, pdf_page, appendix) VALUES (?,?,?,?,?)",
            (item.get("code"), item["name"], item["definition"], item["pdf_page"], "D"),
        )


def _insert_appendix_e(
    conn: sqlite3.Connection,
    ranges: Dict[str, Tuple[int, int]],
) -> None:
    """调用附录 E 解析并写入数据库（当前为空占位）."""
    items = parse_appendix_e(PDF_PATH, *ranges["appendix_e"])
    for item in items:
        conn.execute(
            "INSERT INTO food_categories (code, name, parent_code, description, pdf_page, appendix) VALUES (?,?,?,?,?,?)",
            (
                item["code"],
                item["name"],
                item.get("parent_code"),
                item.get("description"),
                item["pdf_page"],
                "E",
            ),
        )


def _insert_appendix_f(
    conn: sqlite3.Connection,
    ranges: Dict[str, Tuple[int, int]],
) -> None:
    """调用附录 F 解析并写入数据库（当前为空占位）."""
    items = parse_appendix_f(PDF_PATH, *ranges["appendix_f"])
    for item in items:
        conn.execute(
            "INSERT INTO additive_index (index_name, additive_id, canonical_name, pdf_page) VALUES (?,?,?,?)",
            (item["index_name"], item.get("additive_id"), item.get("canonical_name"), item["pdf_page"]),
        )


def main() -> None:
    """主流程：解析 PDF 并原子生成 SQLite."""
    if not PDF_PATH.exists():
        raise SystemExit(f"PDF 不存在: {PDF_PATH}")

    pdf_sha = _sha256(PDF_PATH)
    ranges = detect_appendix_ranges(PDF_PATH)
    required = ["appendix_a", "appendix_b", "appendix_c", "appendix_d", "appendix_e", "appendix_f"]
    missing = [k for k in required if k not in ranges]
    if missing:
        raise SystemExit(f"无法探测以下附录页码范围: {missing}")

    print(f"探测到附录页码范围: {ranges}")

    tmp_db = DB_PATH.with_suffix(".sqlite.tmp")
    # 清理可能残留的临时文件
    if tmp_db.exists():
        tmp_db.unlink()

    conn = sqlite3.connect(tmp_db)
    try:
        create_schema(conn)
        _insert_standard_source(conn, pdf_sha)

        a_additives, a_scopes = parse_appendix_a(PDF_PATH, *ranges["appendix_a"])
        print(f"附录 A 解析完成: {len(a_additives)} 种添加剂, {len(a_scopes)} 条使用范围")
        _insert_additives_and_scopes(conn, a_additives, a_scopes)

        _insert_sentinel_additives(conn)
        _insert_supplement_additives_and_aliases(conn)

        _insert_appendix_b(conn, ranges)
        _insert_appendix_c(conn, ranges)
        _insert_appendix_d(conn, ranges)
        _insert_appendix_e(conn, ranges)
        _insert_appendix_f(conn, ranges)

        _insert_explicit_aliases(conn)

        conn.commit()
    except Exception:
        conn.close()
        if tmp_db.exists():
            tmp_db.unlink()
        raise
    finally:
        if conn:
            conn.close()

    # 原子替换
    tmp_db.replace(DB_PATH)

    # 写 SHA256 校验文件
    with open(SHA256_PATH, "w", encoding="utf-8") as f:
        f.write(f"{pdf_sha}  {PDF_PATH.name}\n")
        f.write(f"{_sha256(DB_PATH)}  {DB_PATH.name}\n")

    print(f"导入完成: {DB_PATH}")


if __name__ == "__main__":
    main()
