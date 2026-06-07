"""章节数据结构与通用切分逻辑。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Chapter:
    """一个章节。"""

    index: int
    title: str
    paragraphs: list[str] = field(default_factory=list)
    raw_text: str = ""

    @property
    def full_text(self) -> str:
        """以换行连接的完整正文（不含 title）。"""
        return "\n\n".join(self.paragraphs)

    @property
    def char_count(self) -> int:
        return len(self.full_text)

    def __repr__(self) -> str:
        return f"Chapter({self.index}, {self.title!r}, {self.char_count} chars)"


# 中文章节正则（兼容 Markdown # heading）
_RE_CN_CHAPTER = re.compile(
    r"^\s*(?:#+\s*)?(?:第[零一二三四五六七八九十百千万\d]+[章回节卷])\s*.+",
    re.MULTILINE,
)
# 中文卷
_RE_CN_VOLUME = re.compile(
    r"^\s*(?:第[零一二三四五六七八九十百千万\d]+卷)\s*.+",
    re.MULTILINE,
)
# 序言 / 尾声 / 楔子 / 番外
_RE_CN_SPECIAL = re.compile(
    r"^\s*(?:序[章言篇]?|楔子|引子|尾声|后记|番外[篇]?|终章|结局).*",
    re.MULTILINE,
)
# 英文章节
_RE_EN_CHAPTER = re.compile(
    r"^\s*(?:Chapter|CHAPTER|Part|PART)\s+\d+.*",
    re.MULTILINE,
)


def _strip_empty(paragraphs: list[str]) -> list[str]:
    return [p.strip() for p in paragraphs if p.strip()]


def detect_and_split(text: str) -> list[Chapter]:
    """自动检测章节标记并切分。"""
    markers = _find_chapter_markers(text)

    if not markers:
        return [Chapter(index=1, title="全文", paragraphs=_strip_empty(text.split("\n")), raw_text=text)]

    chapters: list[Chapter] = []
    for i, (start, end, title) in enumerate(markers):
        body = text[start:end].strip()
        paragraphs = _strip_empty(body.split("\n"))
        chapters.append(
            Chapter(
                index=i + 1,
                title=title,
                paragraphs=paragraphs,
                raw_text=body,
            )
        )

    return chapters


def _find_chapter_markers(text: str) -> list[tuple[int, int, str]]:
    """检测所有章节标记位置，返回 [(正文起点, 正文终点, 标题), ...]。"""
    patterns: list[tuple[re.Pattern[str], int]] = [
        (_RE_CN_CHAPTER, 0),
        (_RE_CN_VOLUME, 0),
        (_RE_CN_SPECIAL, 1),
        (_RE_EN_CHAPTER, 1),
    ]

    matches: list[tuple[int, str, bool]] = []
    for pattern, priority in patterns:
        for m in pattern.finditer(text):
            title = m.group().strip()
            matches.append((m.start(), title, priority == 0))

    matches.sort(key=lambda x: x[0])
    matches = _dedup_close_matches(matches)

    markers: list[tuple[int, int, str]] = []
    for idx, (pos, title, _prefer) in enumerate(matches):
        title_start = pos
        body_start = text.index("\n", title_start) + 1 if "\n" in text[title_start:] else title_start + len(title)
        body_end = matches[idx + 1][0] if idx + 1 < len(matches) else len(text)
        markers.append((body_start, body_end, title))

    return markers


def _dedup_close_matches(
    matches: list[tuple[int, str, bool]],
    min_dist: int = 5,
) -> list[tuple[int, str, bool]]:
    """去除距离过近的重复匹配（同一标题被不同正则命中）。"""
    if not matches:
        return matches
    result: list[tuple[int, str, bool]] = [matches[0]]
    for cur in matches[1:]:
        prev = result[-1]
        if abs(cur[0] - prev[0]) < min_dist:
            # 保留优先的那一个（中文章节优先）
            if cur[2]:
                result[-1] = cur
        else:
            result.append(cur)
    return result
