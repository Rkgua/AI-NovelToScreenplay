"""阶段 3+4 合并：一次调用完成分场 + 节拍提取，避免重复。"""

from __future__ import annotations

from ..llm.base import BaseLLMAdapter, build_structured_schema
from ..parser.chapter import Chapter

_BEAT_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["action"]},
                "description": {"type": "string", "description": "动作描述"},
            },
            "required": ["type", "description"],
        },
        {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["dialogue"]},
                "character": {"type": "string", "description": "说话角色 ID"},
                "line": {"type": "string", "description": "台词"},
                "parenthetical": {"type": "string", "description": "括号指示"},
            },
            "required": ["type", "character", "line"],
        },
        {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["transition"]},
                "transition": {"type": "string", "description": "转场标记"},
            },
            "required": ["type", "transition"],
        },
    ],
}

_SCENE_WITH_BEATS_SCHEMA = build_structured_schema(
    {
        "location_type": {
            "type": "string",
            "enum": ["INT", "EXT", "INT/EXT"],
            "description": "INT内景 / EXT外景 / INT/EXT",
        },
        "location": {"type": "string", "description": "地点名称"},
        "time": {"type": "string", "description": "时间"},
        "summary": {"type": "string", "description": "本场概要"},
        "characters_in_scene": {
            "type": "array",
            "items": {"type": "string"},
            "description": "本场出现的角色ID",
        },
        "beats": {
            "type": "array",
            "items": _BEAT_SCHEMA,
            "description": "本场节拍序列",
        },
    },
    required=["location_type", "location", "time", "summary", "beats"],
    title="scene_with_beats",
)

_WRAPPER_SCHEMA = build_structured_schema(
    {"scenes": {"type": "array", "items": _SCENE_WITH_BEATS_SCHEMA}},
    required=["scenes"],
    title="chapter_scenes",
)

SYSTEM_PROMPT = """你是一位专业的剧本编剧。请将以下章节文本一次性切分为场次，并为每场提取完整的剧本节拍。

步骤：
1. 先按地点/时间变化切分场次
2. 为每场标注 INT/EXT、地点、时间、概要
3. 为每场提取按时间排列的节拍序列

节拍规则：
- action: 将叙事描写转为视觉动作
- dialogue: 保留对白，角色用给定的 ID
- transition: 场末可加转场标记
- 内心独白转为动作或潜台词

每场只包含该场独有的内容，不要跨场重复。"""


def process_chapter(
    adapter: BaseLLMAdapter,
    chapter: Chapter,
    characters: list[dict],
    prev_summary: str = "",
) -> list[dict]:
    """一次调用完成章节的分场 + 节拍提取。"""
    char_context = _format_characters(characters)

    prompt_parts = [
        f"角色列表：\n{char_context}",
    ]
    if prev_summary:
        prompt_parts.append(f"前一章摘要：{prev_summary}")

    prompt_parts.append(f"请将以下章节切分为场次并提取节拍：\n\n【{chapter.title}】\n{chapter.full_text}")

    prompt = "\n\n".join(prompt_parts)

    result = adapter.complete_structured_with_retry(
        prompt=prompt,
        schema=_WRAPPER_SCHEMA,
        system=SYSTEM_PROMPT,
    )

    return result.get("scenes", [])


def _format_characters(characters: list[dict]) -> str:
    lines = []
    for c in characters:
        lines.append(
            f"- {c.get('id', '')}: {c.get('name', '')} "
            f"({c.get('role_description', '')}) — {c.get('description', '')}"
        )
    return "\n".join(lines)
