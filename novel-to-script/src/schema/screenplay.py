from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]


# ── Meta ───────────────────────────────────────────────────────────────


class Genre(str, Enum):
    ACTION = "动作"
    ADVENTURE = "冒险"
    COMEDY = "喜剧"
    CRIME = "犯罪"
    DRAMA = "剧情"
    FANTASY = "奇幻"
    HORROR = "恐怖"
    MYSTERY = "悬疑"
    ROMANCE = "爱情"
    SCIFI = "科幻"
    THRILLER = "惊悚"
    WAR = "战争"
    HISTORICAL = "历史"
    BIOGRAPHY = "传记"


class ScreenplayFormat(str, Enum):
    FEATURE = "feature"
    SHORT = "short"
    EPISODE = "episode"
    STAGE = "stage"


class Meta(BaseModel):
    """剧本元信息。"""

    title: NonEmptyStr
    source: str = ""
    author: str = ""
    adapted_by: str = ""
    genre: list[Genre] = Field(default_factory=list)
    format: ScreenplayFormat = ScreenplayFormat.FEATURE
    version: str = "0.1.0"
    created_at: datetime = Field(default_factory=datetime.now)
    notes: str = ""


# ── Characters ─────────────────────────────────────────────────────────


class CharacterRole(str, Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MINOR = "minor"
    CAMEO = "cameo"


class CharacterRelationship(BaseModel):
    """角色关系。"""

    character: str = Field(..., description="关联角色 ID")
    type: str = Field(..., description="关系类型，如 父子、恋人、仇敌")
    description: str = ""


class Character(BaseModel):
    """剧本角色。"""

    id: NonEmptyStr
    name: NonEmptyStr
    aliases: list[str] = Field(default_factory=list)
    age: str = ""
    gender: str = ""
    role: CharacterRole = CharacterRole.SUPPORTING
    archetype: str = ""
    traits: list[str] = Field(default_factory=list)
    description: str = ""
    relationships: list[CharacterRelationship] = Field(default_factory=list)
    notes: str = ""


# ── Structure: beats within a scene ────────────────────────────────────


class LocationType(str, Enum):
    INT = "INT"
    EXT = "EXT"
    INT_EXT = "INT/EXT"


class SceneHeading(BaseModel):
    """场次标题（Hollywood slug line）。"""

    location_type: LocationType = Field(..., description="INT / EXT / INT/EXT")
    location: NonEmptyStr = Field(..., description="地点名称")
    time: str = Field(default="白天", description="时间描述，如 白天、夜晚、黄昏")


class ActionBeat(BaseModel):
    """动作 / 舞台指示。"""

    type: Literal["action"] = "action"
    description: NonEmptyStr
    notes: str = ""


class DialogueBeat(BaseModel):
    """对白。"""

    type: Literal["dialogue"] = "dialogue"
    character: NonEmptyStr = Field(..., description="说话角色 ID")
    line: NonEmptyStr = Field(..., description="台词")
    parenthetical: str = Field(default="", description="括号指示，如 (低语) (停顿)")
    notes: str = ""


class TransitionBeat(BaseModel):
    """转场。"""

    type: Literal["transition"] = "transition"
    transition: NonEmptyStr = Field(..., description="转场标记，如 CUT TO:、FADE OUT.")


Beat = Annotated[
    ActionBeat | DialogueBeat | TransitionBeat,
    Field(discriminator="type"),
]


class Scene(BaseModel):
    """一个单独场次。"""

    scene_number: int = Field(..., ge=1)
    heading: SceneHeading
    summary: str = ""
    beats: list[Beat] = Field(default_factory=list)
    characters_in_scene: list[str] = Field(
        default_factory=list, description="本场出现的角色 ID 列表"
    )
    notes: str = ""


class Act(BaseModel):
    """一幕。"""

    act_number: int = Field(..., ge=1)
    title: str = ""
    summary: str = ""
    scenes: list[Scene] = Field(default_factory=list)
    notes: str = ""


class Structure(BaseModel):
    """剧本结构（幕→场→节拍）。"""

    acts: list[Act] = Field(default_factory=list)
    notes: str = ""


# ── Top-level ──────────────────────────────────────────────────────────


class Screenplay(BaseModel):
    """完整剧本 — 顶层 Schema。"""

    meta: Meta
    characters: list[Character] = Field(default_factory=list)
    structure: Structure = Field(default_factory=Structure)
    notes: str = ""


# ── Validation result ──────────────────────────────────────────────────


class ValidationResult(BaseModel):
    """Schema 校验结果。"""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
