"""角色数据模型 - 角色档案的 Pydantic/SQLModel 定义。

角色档案采用 Markdown + YAML Frontmatter 结构：
- 作者只编辑正文区（Markdown body）
- Auditor 只编辑 Frontmatter 区（YAML shadow）
- 两者物理隔离，互不干扰
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AuthorityLevel(str, Enum):
    """上下文权威等级枚举，定义注入时的优先级。"""

    CANON = "CANON"              # 不可变设定，最高权威
    STATE_MEMORY = "STATE_MEMORY"  # 角色当前状态，中等权威
    SUBCONSCIOUS = "SUBCONSCIOUS"  # 灵感碎片，最低权威


class PhysicalState(BaseModel):
    """角色物理状态模型，记录伤势、能力等身体状态。"""

    injuries: list[str] = Field(default_factory=list, description="当前伤势列表，如 ['left_arm_fracture']")
    buffs: list[str] = Field(default_factory=list, description="当前增益效果列表")
    debuffs: list[str] = Field(default_factory=list, description="当前减益效果列表")


class EmotionalState(BaseModel):
    """角色情绪状态模型，使用连续值表示情绪维度。"""

    grief: float = Field(default=0.0, ge=0.0, le=1.0, description="悲伤程度")
    anger: float = Field(default=0.0, ge=0.0, le=1.0, description="愤怒程度")
    fear: float = Field(default=0.0, ge=0.0, le=1.0, description="恐惧程度")
    joy: float = Field(default=0.0, ge=0.0, le=1.0, description="喜悦程度")
    determination: float = Field(default=0.0, ge=0.0, le=1.0, description="决心程度")


class CharacterFrontmatter(BaseModel):
    """角色 Frontmatter 数据模型，对应角色 Markdown 文件的 YAML 区域。

    铁律 1：ID 即锚点。所有系统内部关联必须使用 id 字段，严禁使用 name。
    """

    id: str = Field(description="Canonical ID，如 char_001，全局唯一锚点")
    name: str = Field(description="角色当前代号/姓名")
    aliases: list[str] = Field(default_factory=list, description="历史曾用名/代号列表")
    location: Optional[str] = Field(default=None, description="当前所在地点 Canonical ID，如 loc_tower")
    physical: PhysicalState = Field(default_factory=PhysicalState, description="物理状态")
    emotional: EmotionalState = Field(default_factory=EmotionalState, description="情绪状态")
    inventory: list[str] = Field(default_factory=list, description="持有物品 Canonical ID 列表")
    knowledge: list[str] = Field(default_factory=list, description="已知信息/知识列表")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """校验角色 ID 遵循 Canonical ID 规范。"""
        if not v.startswith("char_"):
            raise ValueError(f"角色 ID 必须使用 char_xxx 格式，当前值: {v}")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        """校验地点 ID 遵循 Canonical ID 规范。"""
        if v is not None and not v.startswith("loc_"):
            raise ValueError(f"地点 ID 必须使用 loc_xxx 格式，当前值: {v}")
        return v


class CharacterFile(BaseModel):
    """完整的角色文件模型，包含 Frontmatter 和正文。"""

    frontmatter: CharacterFrontmatter = Field(description="角色 YAML 状态区")
    body: str = Field(default="", description="角色正文区，作者自由书写的区域")


class CharacterDiff(BaseModel):
    """角色状态变更的 Diff 模型，用于 commit 审阅展示。"""

    character_id: str = Field(description="角色 Canonical ID")
    field_path: str = Field(description="变更字段的路径，如 'physical.injuries'")
    before: Optional[str] = Field(default=None, description="变更前的值")
    after: Optional[str] = Field(default=None, description="变更后的值")
