"""阶段 2：为每个章节生成简明摘要（滑动窗口上下文）。"""

from __future__ import annotations

from ..llm.base import BaseLLMAdapter
from ..parser.chapter import Chapter

SYSTEM_PROMPT = """你是一位专业的剧本分析师。请用2-3句话概括以下章节的核心情节。

要求：
1. 只概括本页面内容，不预测后续
2. 突出关键事件和人物动向
3. 简洁明了"""


def summarize_chapter(
    adapter: BaseLLMAdapter,
    chapter: Chapter,
    characters: list[dict],
    prev_summary: str = "",
) -> str:
    """生成单章摘要。"""
    char_context = _format_characters(characters)

    prompt_parts = [
        f"已知角色：\n{char_context}",
    ]
    if prev_summary:
        prompt_parts.append(f"前情提要：{prev_summary}")

    prompt_parts.append(f"请概括以下章节：\n\n【{chapter.title}】\n{chapter.full_text}")

    prompt = "\n\n".join(prompt_parts)

    summary = adapter.complete_with_retry(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        max_tokens=512,
    )
    return summary.strip()


def _format_characters(characters: list[dict]) -> str:
    """将角色列表格式化为简要参考文本。"""
    lines = []
    for c in characters:
        name = c.get("name", "")
        rid = c.get("id", "")
        desc = c.get("description", "")
        role = c.get("role_description", "")
        lines.append(f"- {name}({rid}) [{role}]: {desc}")
    return "\n".join(lines)
