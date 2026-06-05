"""TXT / Markdown 文本解析与章节提取。"""

from __future__ import annotations

import re
from pathlib import Path

from .chapter import Chapter, detect_and_split


_ENCODINGS = ("utf-8", "gbk", "gb18030", "utf-16", "latin-1")


def parse_txt(path: str | Path) -> list[Chapter]:
    """解析 TXT / MD 文件，自动检测章节并返回 Chapter 列表。"""
    raw = _read_with_fallback(path)

    # Markdown 特殊处理：跳过 YAML front matter
    raw = _strip_front_matter(raw)

    return detect_and_split(raw)


def _read_with_fallback(path: str | Path) -> str:
    """多编码尝试读取文件。"""
    raw_bytes = Path(path).read_bytes()

    for enc in _ENCODINGS:
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    return raw_bytes.decode("utf-8", errors="replace")


def _strip_front_matter(text: str) -> str:
    """去除 Markdown YAML front matter (--- ... ---)。"""
    if text.startswith("---"):
        m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
        if m:
            return text[m.end():]
    return text
