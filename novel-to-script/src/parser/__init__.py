"""文本解析 — EPUB / TXT / Markdown 章节提取。

用法:
    from src.parser import parse_file
    chapters = parse_file("novel.epub")  # 或 .txt / .md
"""

from __future__ import annotations

from pathlib import Path

from .chapter import Chapter, detect_and_split
from .epub import parse_epub
from .txt import parse_txt


def parse_file(path: str | Path) -> list[Chapter]:
    """统一解析入口：根据扩展名分发。"""
    suffix = Path(path).suffix.lower()
    if suffix in (".epub",):
        return parse_epub(path)
    return parse_txt(path)


__all__ = [
    "Chapter",
    "detect_and_split",
    "parse_epub",
    "parse_file",
    "parse_txt",
]
