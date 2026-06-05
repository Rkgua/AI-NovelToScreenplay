"""阶段 4：从场景文本中提取节拍（动作 / 对白 / 转场）。"""

from __future__ import annotations

from ..llm.base import BaseLLMAdapter, build_structured_schema

_BEAT_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["action"]},
                "description": {"type": "string", "description": "动作描述或舞台指示"},
            },
            "required": ["type", "description"],
        },
        {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["dialogue"]},
                "character": {"type": "string", "description": "说话角色 ID"},
                "line": {"type": "string", "description": "台词"},
                "parenthetical": {"type": "string", "description": "括号指示，如 (低语) (停顿)"},
            },
            "required": ["type", "character", "line"],
        },
        {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["transition"]},
                "transition": {"type": "string", "description": "转场标记，如 CUT TO:"},
            },
            "required": ["type", "transition"],
        },
    ],
}

_WRAPPER_SCHEMA = build_structured_schema(
    {"beats": {"type": "array", "items": _BEAT_SCHEMA}},
    required=["beats"],
    title="beat_list",
)

SYSTEM_PROMPT = """你是一位专业的剧本编剧。请将小说场景文本转换为剧本节拍序列。

转换规则：
1. 将叙事性描写转化为视觉动作（action）
2. 保留原文对白，转换为对话（dialogue），注意对白归属给正确的角色
3. 角色名用给定的角色ID
4. 人物内心独白要转化为动作或潜台词，不要直接保留内心描写
5. 环境描写转化为开场的动作指示
6. 场景结束时可添加转场（transition）
7. 节拍按时间顺序排列
8. 如果原文没有明确对白归属，根据上下文推断"""


def extract_beats(
    adapter: BaseLLMAdapter,
    scene_text: str,
    characters: list[dict],
) -> list[dict]:
    """从单场文本中提取节拍序列。"""
    char_context = _format_characters(characters)

    prompt = (
        f"角色列表：\n{char_context}\n\n"
        f"请将以下场景文本转换为剧本节拍序列：\n\n{scene_text}"
    )

    result = adapter.complete_structured_with_retry(
        prompt=prompt,
        schema=_WRAPPER_SCHEMA,
        system=SYSTEM_PROMPT,
    )

    return result.get("beats", [])


def _format_characters(characters: list[dict]) -> str:
    lines = []
    for c in characters:
        lines.append(
            f"- {c.get('id', '')}: {c.get('name', '')} "
            f"({c.get('role_description', '')}) — {c.get('description', '')}"
        )
    return "\n".join(lines)
