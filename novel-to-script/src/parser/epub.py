"""EPUB 电子书解析与章节提取。"""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from .chapter import Chapter, detect_and_split

try:
    from ebooklib import ITEM_DOCUMENT, epub
except ImportError:
    epub = None  # type: ignore[assignment]
    ITEM_DOCUMENT = None  # type: ignore[assignment]


def parse_epub(path: str | Path) -> list[Chapter]:
    """解析 EPUB 文件，提取章节。"""
    if epub is None:
        raise ImportError("请安装 ebooklib: pip install ebooklib")

    book = epub.read_epub(str(path))
    documents = list(book.get_items_of_type(ITEM_DOCUMENT))

    if not documents:
        return []

    toc_titles = _extract_toc_titles(book)

    chapters: list[Chapter] = []
    chapter_idx = 0

    for doc in documents:
        fname = doc.file_name.lower()
        if "nav" in fname or "ncx" in fname or "toc" in fname:
            continue

        soup = BeautifulSoup(doc.get_body_content(), "lxml")
        text = soup.get_text(separator="\n")
        text = _clean_text(text)

        title = toc_titles.get(doc.file_name, "")

        sub = detect_and_split(text)

        for ch in sub:
            chapter_idx += 1
            ch.index = chapter_idx
            if not ch.title or ch.title == "全文":
                ch.title = title or f"章节{chapter_idx}"
            chapters.append(ch)

    return chapters


def _extract_toc_titles(book) -> dict[str, str]:
    """从 EPUB 目录提取标题映射。"""
    result: dict[str, str] = {}
    try:
        for item in book.toc:
            if isinstance(item, tuple):
                for sub in item:
                    if hasattr(sub, "title") and hasattr(sub, "href"):
                        result[_normalize_href(sub.href)] = sub.title
            elif hasattr(item, "title") and hasattr(item, "href"):
                result[_normalize_href(item.href)] = item.title
    except Exception:
        pass
    return result


def _normalize_href(href: str) -> str:
    return href.split("#")[0]


def _clean_text(text: str) -> str:
    """清理 EPUB 提取文本中的多余空行和空白。"""
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines)
