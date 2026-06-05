"""阶段 5：将流水线中间结果组装为完整 Screenplay 对象。"""

from __future__ import annotations

from ..schema.screenplay import (
    Act,
    ActionBeat,
    Character,
    CharacterRelationship,
    CharacterRole,
    DialogueBeat,
    LocationType,
    Meta,
    Scene,
    SceneHeading,
    Screenplay,
    ScreenplayFormat,
    Structure,
    TransitionBeat,
)


def assemble_screenplay(
    *,
    meta: dict,
    characters_raw: list[dict],
    chapters_data: list[dict],
) -> Screenplay:
    """组装最终 Screenplay。

    chapters_data 格式:
        [{"chapter_title": str, "scenes": [scene_dict, ...]}, ...]

    每个 scene_dict 格式（来自 detect_scenes + extract_beats 合并）:
        {
            "location_type": "INT",
            "location": "...",
            "time": "白天",
            "summary": "...",
            "characters_in_scene": [...],
            "beats": [{beat_dict}, ...]
        }
    """
    characters = _build_characters(characters_raw)
    character_id_map = {c.id for c in characters}

    acts = _build_acts(chapters_data, character_id_map)

    return Screenplay(
        meta=_build_meta(meta),
        characters=characters,
        structure=Structure(acts=acts),
    )


def _build_meta(info: dict) -> Meta:
    genre_names = info.get("genre", [])
    genres = []
    for g in genre_names:
        try:
            from ..schema.screenplay import Genre
            genres.append(Genre(g))
        except ValueError:
            pass

    fmt = ScreenplayFormat.FEATURE
    if info.get("format"):
        try:
            fmt = ScreenplayFormat(info["format"])
        except ValueError:
            pass

    return Meta(
        title=info.get("title", "未命名剧本"),
        source=info.get("source", ""),
        author=info.get("author", ""),
        adapted_by=info.get("adapted_by", "AI 辅助改编"),
        genre=genres,
        format=fmt,
        version=info.get("version", "0.1.0"),
        notes=info.get("notes", ""),
    )


def _build_characters(raw: list[dict]) -> list[Character]:
    characters: list[Character] = []
    for c in raw:
        relationships = []
        for r in c.get("relationships", []):
            relationships.append(
                CharacterRelationship(
                    character=r.get("character", ""),
                    type=r.get("type", ""),
                    description=r.get("description", ""),
                )
            )

        try:
            role = CharacterRole(c.get("role_description", "supporting"))
        except ValueError:
            role = CharacterRole.SUPPORTING

        characters.append(
            Character(
                id=c.get("id", f"char_{len(characters) + 1}"),
                name=c.get("name", ""),
                aliases=c.get("aliases", []),
                age=c.get("age", ""),
                gender=c.get("gender", ""),
                role=role,
                archetype=c.get("archetype", ""),
                traits=c.get("traits", []),
                description=c.get("description", ""),
                relationships=relationships,
            )
        )
    return characters


def _build_acts(
    chapters_data: list[dict],
    character_ids: set[str],
) -> list[Act]:
    """将章节数据转换为幕→场结构。

    简单策略：前三幕分配（第一章 → 第一幕，中间章节 → 第二幕，最后一章 → 第三幕）。
    """
    total = len(chapters_data)
    if total == 0:
        return []

    scene_counter = 0

    if total <= 2:
        # 1-2章：全部放入第一幕
        acts = [
            Act(act_number=1, title="第一幕", summary=""),
        ]
        chapter_to_act = [0] * total
    else:
        # 三幕结构
        act_1_end = max(1, total // 3)
        act_2_end = max(act_1_end + 1, total * 2 // 3)

        acts = [
            Act(act_number=1, title="第一幕", summary=""),
            Act(act_number=2, title="第二幕", summary=""),
            Act(act_number=3, title="第三幕", summary=""),
        ]

        chapter_to_act = []
        for i in range(total):
            if i < act_1_end:
                chapter_to_act.append(0)
            elif i < act_2_end:
                chapter_to_act.append(1)
            else:
                chapter_to_act.append(2)

    for ch_idx, ch_data in enumerate(chapters_data):
        act_idx = chapter_to_act[ch_idx]
        scenes_raw = ch_data.get("scenes", [])

        for sc in scenes_raw:
            scene_counter += 1
            heading = SceneHeading(
                location_type=_parse_location_type(sc.get("location_type", "INT")),
                location=sc.get("location", "未知地点"),
                time=sc.get("time", "白天"),
            )

            beats = _build_beats(sc.get("beats", []), character_ids)

            chars_in_scene = [
                cid for cid in sc.get("characters_in_scene", [])
                if cid in character_ids
            ]

            acts[act_idx].scenes.append(
                Scene(
                    scene_number=scene_counter,
                    heading=heading,
                    summary=sc.get("summary", ""),
                    beats=beats,
                    characters_in_scene=chars_in_scene,
                )
            )

    return [a for a in acts if a.scenes]


def _build_beats(beats_raw: list[dict], character_ids: set[str]) -> list:
    beats = []
    for b in beats_raw:
        btype = b.get("type", "")
        if btype == "action":
            beats.append(ActionBeat(description=b.get("description", "")))
        elif btype == "dialogue":
            char_id = b.get("character", "")
            if char_id not in character_ids:
                char_id = "unknown"
            beats.append(
                DialogueBeat(
                    character=char_id,
                    line=b.get("line", ""),
                    parenthetical=b.get("parenthetical", ""),
                )
            )
        elif btype == "transition":
            beats.append(TransitionBeat(transition=b.get("transition", "")))
    return beats


def _parse_location_type(raw: str) -> LocationType:
    raw_upper = raw.upper()
    if raw_upper in ("INT", "内景"):
        return LocationType.INT
    if raw_upper in ("EXT", "外景"):
        return LocationType.EXT
    if raw_upper in ("INT/EXT", "INT。EXT", "内外景"):
        return LocationType.INT_EXT
    return LocationType.INT
