"""YAML 剧本加载、校验、导出。"""

from __future__ import annotations

from pathlib import Path

import yaml

from .screenplay import (
    Character,
    DialogueBeat,
    Screenplay,
    ValidationResult,
)


def load_screenplay(path: str | Path) -> tuple[Screenplay | None, str | None]:
    """从 YAML 文件加载剧本，失败时返回 (None, 错误信息)。"""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"文件不存在: {path}"
    except Exception as e:
        return None, f"读取文件失败: {e}"

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return None, f"YAML 解析失败: {e}"

    if not isinstance(data, dict):
        return None, f"YAML 根节点必须是 dict，实际类型: {type(data).__name__}"

    try:
        screenplay = Screenplay.model_validate(data)
    except Exception as e:
        return None, f"Schema 校验失败: {e}"

    return screenplay, None


def validate_screenplay(path: str | Path) -> ValidationResult:
    """校验 YAML 剧本并返回结构化结果。"""
    errors: list[str] = []
    warnings: list[str] = []

    screenplay, load_err = load_screenplay(path)
    if load_err:
        errors.append(load_err)
        return ValidationResult(valid=False, errors=errors)

    assert screenplay is not None

    errors.extend(_check_semantic_rules(screenplay))
    warnings.extend(_check_quality_hints(screenplay))

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def save_screenplay(screenplay: Screenplay, path: str | Path) -> None:
    """将剧本导出为 YAML 文件。"""

    class ScreenplayDumper(yaml.Dumper):
        pass

    def _str_representer(dumper: yaml.Dumper, data: str) -> str:
        if "\n" in data or len(data) > 80:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    ScreenplayDumper.add_representer(str, _str_representer)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data = screenplay.model_dump(mode="json", exclude_none=True)
    yaml_text = yaml.dump(
        data,
        Dumper=ScreenplayDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    Path(path).write_text(yaml_text, encoding="utf-8")


def _check_semantic_rules(sp: Screenplay) -> list[str]:
    """语义规则检查（高于 Schema 结构本身的约束）。"""
    errors: list[str] = []
    char_ids: set[str] = {c.id for c in sp.characters}

    for char in sp.characters:
        for rel in char.relationships:
            if rel.character not in char_ids:
                errors.append(
                    f"角色 '{char.id}' 的关系引用了不存在的角色 '{rel.character}'"
                )

    for act in sp.structure.acts:
        for scene in act.scenes:
            for cid in scene.characters_in_scene:
                if cid not in char_ids:
                    errors.append(
                        f"第{act.act_number}幕第{scene.scene_number}场"
                        f"引用了不存在的角色 '{cid}'"
                    )
            for beat in scene.beats:
                if isinstance(beat, DialogueBeat) and beat.character not in char_ids:
                    errors.append(
                        f"第{act.act_number}幕第{scene.scene_number}场"
                        f"的对白引用了不存在的角色 '{beat.character}'"
                    )

    if not sp.structure.acts:
        errors.append("剧本结构为空：至少需要一幕")

    scene_numbers = [
        s.scene_number for a in sp.structure.acts for s in a.scenes
    ]
    if len(scene_numbers) != len(set(scene_numbers)):
        errors.append("场次编号重复")

    for i, num in enumerate(scene_numbers):
        if i > 0 and num <= scene_numbers[i - 1]:
            errors.append(
                f"场次编号不是严格递增：场景 {scene_numbers[i-1]} 后出现场景 {num}"
            )

    return errors


def _check_quality_hints(sp: Screenplay) -> list[str]:
    """质量提示（不影响合法性的软性建议）。"""
    warnings: list[str] = []

    if not sp.characters:
        warnings.append("角色列表为空")

    total_beats = sum(
        len(s.beats) for a in sp.structure.acts for s in a.scenes
    )
    if total_beats == 0:
        warnings.append("剧本没有任何节拍（动作/对白/转场）")

    dialogue_count = sum(
        1
        for a in sp.structure.acts
        for s in a.scenes
        for b in s.beats
        if isinstance(b, DialogueBeat)
    )
    if dialogue_count == 0:
        warnings.append("剧本中没有任何对白")

    for act in sp.structure.acts:
        if not act.scenes:
            warnings.append(f"第{act.act_number}幕没有任何场次")

    uncast_characters: set[str] = set()
    for act in sp.structure.acts:
        for scene in act.scenes:
            for beat in scene.beats:
                if isinstance(beat, DialogueBeat):
                    uncast_characters.add(beat.character)
    defined_ids = {c.id for c in sp.characters}
    orphan_speakers = uncast_characters - defined_ids
    if orphan_speakers:
        warnings.append(f"以下角色有对白但未在角色列表中定义: {', '.join(sorted(orphan_speakers))}")

    return warnings
