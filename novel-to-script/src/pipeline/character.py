"""阶段 1：从小说文本中提取角色档案。"""

from __future__ import annotations

from ..llm.base import BaseLLMAdapter, build_structured_schema
from ..parser.chapter import Chapter

_CHARACTER_SCHEMA = build_structured_schema(
    {
        "id": {"type": "string", "description": "角色唯一ID，格式为 序号+性别字母，如 1M（第一个出场的男性）、2F（第二个出场的女性）、1N（性别不明），按出场顺序为每种性别独立编号"},
        "name": {"type": "string", "description": "角色中文名"},
        "aliases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "别名、绰号",
        },
        "age": {"type": "string", "description": "年龄描述，如 青年、中年、老年"},
        "gender": {"type": "string", "description": "男 / 女 / 无"},
        "role_description": {"type": "string", "description": "在故事中的角色定位，如 主角、反派、配角"},
        "archetype": {"type": "string", "description": "角色原型，如 英雄、导师、阴影"},
        "traits": {
            "type": "array",
            "items": {"type": "string"},
            "description": "性格特征关键词",
        },
        "description": {"type": "string", "description": "角色概要描述"},
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "character": {"type": "string", "description": "关联角色ID（格式：序号+性别字母，如 1M、2F）"},
                    "type": {"type": "string", "description": "关系类型"},
                    "description": {"type": "string", "description": "关系描述"},
                },
                "required": ["character", "type"],
            },
            "description": "角色关系列表",
        },
    },
    required=["id", "name"],
    title="characters",
)

_WRAPPER_SCHEMA = build_structured_schema(
    {"characters": {"type": "array", "items": _CHARACTER_SCHEMA}},
    required=["characters"],
    title="character_list",
)

SYSTEM_PROMPT = """你是一位专业的剧本分析师。你的任务是从小说文本中提取所有角色信息。

要求：
1. 提取所有有名字、有对白或有重要情节作用的角色
2. 为每个角色创建唯一ID，格式为"序号+性别字母"：
   - 按角色首次出场顺序，男性和女性分别编号
   - 男性用 M，如第一个出场的男性为 "1M"，第二个为 "2M"
   - 女性用 F，如第一个出场的女性为 "1F"，第二个为 "2F"
   - 性别不明或非人类角色用 N，如 "1N"
   - 例如：林远是第一个出场的男性 → id="1M"；周雪是第一个出场的女性 → id="1F"
3. 年龄用描述性词语（青年、中年、老年），不要用具体数字
4. 性格特征简洁精炼，每个角色 3-5 个关键词
5. 分析角色之间的关系，关系中的 character 字段使用相同的 ID 格式
6. 如果角色信息不足，字段留空即可"""


def extract_characters(
    adapter: BaseLLMAdapter,
    chapters: list[Chapter],
    sample_count: int = 3,
) -> list[dict]:
    """从小说章节中提取角色列表。

    仅采样前 sample_count 章来提取角色，以减少 token 消耗。
    """
    sample = chapters[:sample_count]
    texts = []
    for ch in sample:
        texts.append(f"【{ch.title}】\n{ch.full_text}")

    combined = "\n\n---\n\n".join(texts)

    if adapter.count_tokens(combined) > 60000:
        sample = chapters[:max(1, sample_count // 2)]
        texts = [f"【{ch.title}】\n{ch.full_text}" for ch in sample]
        combined = "\n\n---\n\n".join(texts)

    result = adapter.complete_structured_with_retry(
        prompt=f"请从以下小说文本中提取所有角色信息：\n\n{combined}",
        schema=_WRAPPER_SCHEMA,
        system=SYSTEM_PROMPT,
    )

    characters: list[dict] = result.get("characters", [])

    for i, char in enumerate(characters):
        if "id" not in char:
            char["id"] = f"{i + 1}N"

    return characters
