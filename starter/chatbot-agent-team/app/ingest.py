"""Nạp tài liệu vào kho tri thức (đường nhanh).

Dùng: python -m app.ingest kb --reset
- .md, .txt: đọc trực tiếp.
- .pdf, .docx, .xlsx, .pptx, .html...: cần cài thêm `pip install "markitdown[all]"`.
"""
import argparse
from pathlib import Path

from . import db

TEXT_SUFFIXES = {".md", ".txt"}


def read_file(path: Path) -> str | None:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8")
    try:
        from markitdown import MarkItDown
    except ImportError:
        print(f"  Bỏ qua {path} (cài 'markitdown[all]' để đọc định dạng này)")
        return None
    return MarkItDown().convert(str(path)).text_content


def chunk(text: str, max_chars: int = 1200) -> list[tuple[str, str]]:
    """Chia theo đoạn văn, gom đến khoảng max_chars; tiêu đề lấy từ dòng '#' gần nhất."""
    chunks, buf, title = [], [], ""

    def flush():
        if buf:
            chunks.append((title, "\n\n".join(buf)))
            buf.clear()

    for para in (p.strip() for p in text.split("\n\n")):
        if not para:
            continue
        if para.startswith("#"):
            flush()
            title = para.splitlines()[0].lstrip("#").strip()
            rest = "\n".join(para.splitlines()[1:]).strip()
            if rest:
                buf.append(rest)
            continue
        if sum(len(b) for b in buf) + len(para) > max_chars:
            flush()
        buf.append(para)
    flush()
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp tài liệu vào kho tri thức")
    parser.add_argument("paths", nargs="+", help="File hoặc thư mục")
    parser.add_argument("--reset", action="store_true", help="Xóa kho tri thức cũ trước khi nạp")
    args = parser.parse_args()

    db.init_db()
    if args.reset:
        db.clear_kb()
    total = 0
    for root in map(Path, args.paths):
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in files:
            text = read_file(path)
            if not text:
                continue
            parts = chunk(text)
            for title, content in parts:
                db.add_kb_chunk(path.name, title or path.stem, content)
            total += len(parts)
            print(f"  {path}: {len(parts)} đoạn")
    print(f"Xong: đã nạp {total} đoạn vào kho tri thức.")


if __name__ == "__main__":
    main()
