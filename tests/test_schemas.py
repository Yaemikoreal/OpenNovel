"""schemas 模块测试 - 数据模型校验。"""

import pytest
from pydantic import ValidationError

from loom.schemas.character import (
    CharacterFrontmatter,
    EmotionalState,
    PhysicalState,
)
from loom.schemas.event import EventCreate, EventLog, EventType


class TestEventLog:
    """EventLog 数据模型测试。

    注意：SQLModel table=True 模式下 Pydantic field_validator 不自动触发，
    因此校验逻辑的测试放在 TestEventCreate 中（纯 Pydantic 模型）。
    """

    def test_event_log_creation(self) -> None:
        """测试 EventLog 基本创建。"""
        event = EventLog(
            event_id="evt_ch001_001",
            chapter_id="ch_001",
            timestamp="第3天·午后",
            character_id="char_001",
            event_type="INJURY",
            description="左臂被巨剑斩伤",
            causal_pressure=0.9,
        )
        assert event.event_id == "evt_ch001_001"
        assert event.event_type == "INJURY"
        assert event.causal_pressure == 0.9


class TestEventCreate:
    """EventCreate 请求模型测试（纯 Pydantic，校验器正常触发）。"""

    def test_event_create_valid(self) -> None:
        """测试合法的事件创建请求。"""
        event = EventCreate(
            event_id="evt_ch001_001",
            chapter_id="ch_001",
            timestamp="第3天·午后",
            character_id="char_001",
            event_type=EventType.INJURY,
            description="左臂骨折",
            causal_pressure=0.9,
        )
        assert event.event_type == EventType.INJURY

    def test_causal_pressure_validation(self) -> None:
        """测试因果压强范围校验（通过 EventCreate 的 ge/le 约束）。"""
        with pytest.raises(ValidationError):
            EventCreate(
                event_id="evt_001",
                chapter_id="ch_001",
                timestamp="第1天",
                character_id="char_001",
                event_type=EventType.INJURY,
                description="test",
                causal_pressure=1.5,
            )

    def test_causal_pressure_negative(self) -> None:
        """测试因果压强负值校验。"""
        with pytest.raises(ValidationError):
            EventCreate(
                event_id="evt_001",
                chapter_id="ch_001",
                timestamp="第1天",
                character_id="char_001",
                event_type=EventType.INJURY,
                description="test",
                causal_pressure=-0.1,
            )

    def test_event_type_enum(self) -> None:
        """测试事件类型枚举完整性。"""
        expected_types = {
            "INJURY", "HEAL", "ITEM_GAIN", "ITEM_LOSS",
            "KNOWLEDGE", "LOCATION_CHANGE", "EMOTION_SHIFT",
            "RELATIONSHIP_CHANGE", "CUSTOM",
        }
        actual_types = {e.value for e in EventType}
        assert actual_types == expected_types


class TestCharacterFrontmatter:
    """CharacterFrontmatter 数据模型测试。"""

    def test_character_creation(self) -> None:
        """测试角色 Frontmatter 基本创建。"""
        char = CharacterFrontmatter(
            id="char_001",
            name="Alice",
            aliases=["Alys", "The Witch"],
        )
        assert char.id == "char_001"
        assert char.name == "Alice"
        assert len(char.aliases) == 2

    def test_character_id_validation(self) -> None:
        """测试角色 ID 必须使用 char_xxx 格式。"""
        with pytest.raises(ValidationError):
            CharacterFrontmatter(id="alice", name="Alice")

    def test_location_validation(self) -> None:
        """测试地点 ID 必须使用 loc_xxx 格式。"""
        with pytest.raises(ValidationError):
            CharacterFrontmatter(id="char_001", name="Alice", location="tower")

    def test_emotional_state_defaults(self) -> None:
        """测试情绪状态默认值。"""
        emotional = EmotionalState()
        assert emotional.grief == 0.0
        assert emotional.joy == 0.0

    def test_emotional_state_range(self) -> None:
        """测试情绪值范围校验。"""
        with pytest.raises(ValidationError):
            EmotionalState(grief=1.5)

    def test_physical_state_defaults(self) -> None:
        """测试物理状态默认值。"""
        physical = PhysicalState()
        assert physical.injuries == []
        assert physical.buffs == []
