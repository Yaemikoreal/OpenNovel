"""事件账本数据模型 - SQLite 事件日志的 SQLModel 定义。

事件账本是 L.O.O.M. 的全局因果追踪核心，记录所有叙事中的状态变更事件。
每个事件通过 Canonical ID 关联角色/地点/物品，并携带因果压强指标。
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import SQLModel, Field as SQLField


class EventType(str, Enum):
    """事件类型枚举，定义所有合法的状态变更类型。"""

    INJURY = "INJURY"
    HEAL = "HEAL"
    ITEM_GAIN = "ITEM_GAIN"
    ITEM_LOSS = "ITEM_LOSS"
    KNOWLEDGE = "KNOWLEDGE"
    LOCATION_CHANGE = "LOCATION_CHANGE"
    EMOTION_SHIFT = "EMOTION_SHIFT"
    RELATIONSHIP_CHANGE = "RELATIONSHIP_CHANGE"
    CUSTOM = "CUSTOM"


class EventLogBase(SQLModel):
    """事件账本基础模型，包含字段校验逻辑。

    SQLModel table=True 模式下 field_validator 不自动触发，
    因此将校验逻辑放在基类中，通过 model_config 启用校验。
    """

    model_config = ConfigDict(validate_default=True)

    event_id: str = SQLField(index=True, description="唯一事件标识，如 evt_001_injury")
    chapter_id: str = SQLField(index=True, description="章节 ID，如 ch_001")
    timestamp: str = SQLField(description="故事内绝对时间")
    character_id: str = SQLField(index=True, description="关联角色 Canonical ID，如 char_001")
    event_type: str = SQLField(description="事件类型，参见 EventType 枚举")
    description: str = SQLField(description="事件的自然语言描述")
    causal_pressure: float = SQLField(
        default=0.5,
        description="因果压强 0.1~1.0，值越高表示该事件对后续叙事影响越大",
    )

    @field_validator("causal_pressure")
    @classmethod
    def validate_causal_pressure(cls, v: float) -> float:
        """校验因果压强在合法范围内。"""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"causal_pressure 必须在 0.0~1.0 之间，当前值: {v}")
        return round(v, 2)

    @field_validator("character_id")
    @classmethod
    def validate_character_id(cls, v: str) -> str:
        """校验角色 ID 遵循 Canonical ID 规范。"""
        if not v.startswith("char_"):
            raise ValueError(
                f"character_id 必须使用 Canonical ID 规范（char_xxx），当前值: {v}"
            )
        return v


class EventLog(EventLogBase, table=True):
    """SQLite 事件账本表模型。

    记录叙事中发生的所有状态变更事件，支持跨章节因果溯源。
    所有 ID 字段必须使用 Canonical ID 规范（如 char_001, loc_london）。
    """

    __tablename__ = "event_log"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    created_at: Optional[str] = SQLField(
        default=None, description="记录创建时间（系统时间）"
    )


class EventCreate(BaseModel):
    """创建事件的请求模型，用于 Auditor 提取结果的结构化校验。"""

    event_id: str = Field(description="唯一事件标识")
    chapter_id: str = Field(description="章节 ID")
    timestamp: str = Field(description="故事内绝对时间")
    character_id: str = Field(description="关联角色 Canonical ID")
    event_type: EventType = Field(description="事件类型")
    description: str = Field(description="事件描述")
    causal_pressure: float = Field(
        default=0.5, ge=0.0, le=1.0, description="因果压强"
    )


class EventDiff(BaseModel):
    """事件变更的 Diff 模型，用于 commit 审阅时展示变更。"""

    action: str = Field(description="操作类型: add / remove / modify")
    event: EventCreate = Field(description="涉及的事件")
    before: Optional[EventCreate] = Field(default=None, description="修改前的事件（仅 modify 操作）")


class SnapshotMeta(BaseModel):
    """快照元数据模型，采用文件级增量结构。

    只记录本次 commit 实际涉及的文件（章节 + 角色），不扫描无关文件。
    回滚时校验 fm_after 防止覆盖人类在间隙中的手动修改。
    """

    snapshot_id: str = Field(description="快照唯一标识，如 snap_ch_001_1698765432")
    source_command: str = Field(description="触发快照的命令，如 commit ch_001")
    timestamp: str = Field(description="快照生成时间（系统时间）")
    delta_files: dict[str, dict] = Field(
        default_factory=dict,
        description="文件级增量，key=文件相对路径，value={'fm_before': {...}, 'fm_after': {...}}",
    )
    delta_sqlite: dict = Field(
        default_factory=lambda: {"event_ids_to_rollback": []},
        description="SQLite 增量，需回滚的事件 ID 列表",
    )
