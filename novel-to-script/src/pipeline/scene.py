"""阶段 3：将章节切分为场次。"""

from __future__ import annotations

from ..llm.base import BaseLLMAdapter, build_structured_schema
from ..parser.chapter import Chapter

_SCENE_SCHEMA = build_structured_schema(
    {
        "location_type": {
            "type": "string",
            "enum": ["INT", "EXT", "INT/EXT"],
            "description": "INT内景 / EXT外景 / INT/EXT",
        },
        "location": {"type": "string", "description": "地点名称"},
        "time": {"type": "string", "description": "时间，如 白天、夜晚、黄昏"},
        "summary": {"type": "string", "description": "本场内容概要"},
        "characters_in_scene": {
            "type": "array",
            "items": {"type": "string"},
            "description": "本场出现的角色ID列表",
        },
    },
    required=["location_type", "location", "time", "summary"],
    title="scene",
)

_WRAPPER_SCHEMA = build_structured_schema(
    {"scenes": {"type": "array", "items": _SCENE_SCHEMA}},
    required=["scenes"],
    title="scene_list",
)

SYSTEM_PROMPT = """你是一位专业的剧本分场师。请将章节内容切分为独立的场次。

分场规则：
1. 地点发生变化 → 新场次
2. 时间发生明显跳跃 → 新场次
3. 新角色登场引发独立场景 → 新场次
4. 每场标注 INT/EXT、具体地点、时间
5. characters_in_scene 使用角色ID列表
6. summary 用一句话概括本场核心内容"""


def detect_scenes(
    adapter: BaseLLMAdapter,
    chapter: Chapter,
    characters: list[dict],
    prev_summary: str = "",
) -> list[dict]:
    """将单章切分为场次列表。"""
    char_context = _format_characters(characters)

    prompt_parts = [
        f"角色列表：\n{char_context}",
    ]
    if prev_summary:
        prompt_parts.append(f"前一章摘要：{prev_summary}")

    prompt_parts.append(f"请将以下章节切分为场次：\n\n【{chapter.title}】\n{chapter.full_text}")

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
        lines.append(f"- {c.get('id', '')}: {c.get('name', '')} ({c.get('role_description', '')})")
    return "\n".join(lines)
