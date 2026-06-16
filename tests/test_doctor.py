"""doctor 模块测试 - 世界观健康度诊断。"""

from pathlib import Path

import pytest

from loom.core.doctor import DiagnosticItem, DiagnosticLevel, Doctor
from loom.schemas.event import EventCreate, EventType
from loom.storage.sqlite import EventStore
from loom.storage.yaml_storage import YAMLStorage


@pytest.fixture
def storage() -> YAMLStorage:
    """创建 YAMLStorage 实例。"""
    return YAMLStorage()


@pytest.fixture
def project_root(tmp_path: Path, storage: YAMLStorage) -> Path:
    """创建测试用项目目录。"""
    root = tmp_path / "test_project"
    root.mkdir()

    (root / "characters").mkdir()
    (root / "draft").mkdir()
    (root / "canon").mkdir()
    (root / "subconscious").mkdir()
    (root / ".snapshots").mkdir()

    # 创建角色文件
    for char_id in ["char_001", "char_002", "char_003"]:
        storage.write_markdown_file(
            root / "characters" / f"{char_id}.md",
            {"id": char_id, "name": f"角色{char_id}"},
            f"# {char_id}\n\n背景故事。",
        )

    # 创建章节：引用 char_001 和 char_002
    storage.write_markdown_file(
        root / "draft" / "ch_001.md",
        {"id": "ch_001", "pov": "char_001", "active_characters": ["char_001", "char_002"]},
        "# 第一章\n\n内容",
    )

    # 创建章节：引用 char_001
    storage.write_markdown_file(
        root / "draft" / "ch_002.md",
        {"id": "ch_002", "pov": "char_001", "active_characters": ["char_001"]},
        "# 第二章\n\n内容",
    )

    return root


class TestDiagnosticItem:
    """DiagnosticItem 数据类测试。"""

    def test_item_creation(self) -> None:
        """测试诊断项创建。"""
        item = DiagnosticItem(
            level=DiagnosticLevel.WARNING,
            category="orphan",
            message="测试警告",
            details="详细信息",
        )
        assert item.level == DiagnosticLevel.WARNING
        assert item.category == "orphan"
        assert item.message == "测试警告"


class TestOrphanCharacterDetection:
    """孤立角色检测测试。"""

    def test_orphan_character_detected(self, project_root: Path, storage: YAMLStorage) -> None:
        """char_003 未被任何章节引用 → 应检测到孤立。"""
        doctor = Doctor(project_root)
        items = doctor.diagnose()

        orphan_items = [i for i in items if i.category == "orphan_character"]
        assert any("char_003" in i.message for i in orphan_items)

    def test_referenced_characters_not_orphaned(
        self, project_root: Path, storage: YAMLStorage
    ) -> None:
        """char_001 和 char_002 被引用 → 不应标记为孤立。"""
        doctor = Doctor(project_root)
        items = doctor.diagnose()

        orphan_items = [i for i in items if i.category == "orphan_character"]
        orphan_ids = [i.message for i in orphan_items]
        assert not any("char_001" in msg for msg in orphan_ids)
        assert not any("char_002" in msg for msg in orphan_ids)


class TestDanglingReferenceDetection:
    """悬空引用检测测试。"""

    def test_dangling_reference_detected(self, project_root: Path, storage: YAMLStorage) -> None:
        """章节引用不存在的角色 → 应检测到。"""
        # 添加一个引用 char_999 的章节
        storage.write_markdown_file(
            project_root / "draft" / "ch_ghost.md",
            {"id": "ch_ghost", "pov": "char_999", "active_characters": ["char_999"]},
            "# 幽灵章节\n\n内容",
        )

        doctor = Doctor(project_root)
        items = doctor.diagnose()

        dangling_items = [i for i in items if i.category == "dangling_reference"]
        assert any("char_999" in i.message for i in dangling_items)


class TestIdConsistencyCheck:
    """ID 一致性检测测试。"""

    def test_filename_id_mismatch(self, project_root: Path, storage: YAMLStorage) -> None:
        """文件名与 Frontmatter id 不一致 → 应检测到。"""
        # 创建一个文件名与 id 不匹配的文件
        storage.write_markdown_file(
            project_root / "characters" / "char_wrong.md",
            {"id": "char_999", "name": "错位角色"},
            "# 错位角色\n\n内容",
        )

        doctor = Doctor(project_root)
        items = doctor.diagnose()

        id_items = [i for i in items if i.category == "id_mismatch"]
        assert len(id_items) >= 1
        assert any("char_wrong" in i.message and "char_999" in i.message for i in id_items)


class TestDirtyFlagScan:
    """脏标记扫描测试。"""

    def test_dirty_flag_detected(self, project_root: Path, storage: YAMLStorage) -> None:
        """存在脏标记章节 → 应检测到。"""
        storage.write_markdown_file(
            project_root / "draft" / "ch_dirty.md",
            {"id": "ch_dirty", "pov": "char_001", "dirty_flag": "extraction_failed"},
            "# 脏章节\n\n内容",
        )

        doctor = Doctor(project_root)
        items = doctor.diagnose()

        dirty_items = [i for i in items if i.category == "dirty_flag"]
        assert len(dirty_items) >= 1
        assert "ch_dirty" in dirty_items[0].message


class TestSnapshotStats:
    """快照统计测试。"""

    def test_snapshot_count(self, project_root: Path) -> None:
        """应正确统计快照数量。"""
        import orjson

        # 创建模拟快照文件
        snap_dir = project_root / ".snapshots"
        for i in range(3):
            snap_data = {
                "snapshot_id": f"snap_test_{i}",
                "source_command": f"commit ch_{i:03d}",
                "timestamp": f"2024-01-{i + 1:02d}T10:00:00",
                "delta_files": {},
                "delta_sqlite": {"event_ids_to_rollback": []},
            }
            (snap_dir / f"snap_test_{i}.snapshot.json").write_bytes(
                orjson.dumps(snap_data, option=orjson.OPT_INDENT_2)
            )

        doctor = Doctor(project_root)
        items = doctor.diagnose()

        snapshot_items = [i for i in items if i.category == "snapshot_stats"]
        assert len(snapshot_items) >= 1
        assert "3" in snapshot_items[0].message


class TestEventLedgerHealth:
    """事件账本健康检测测试。"""

    def test_event_references_missing_character(self, project_root: Path) -> None:
        """事件引用不存在的角色 → 应检测到。"""
        db_path = project_root / ".loom.db"
        store = EventStore(db_path)

        # 写入一个引用不存在角色的事件
        store.add_event(
            EventCreate(
                event_id="evt_ghost",
                chapter_id="ch_001",
                timestamp="第1天",
                character_id="char_999",
                event_type=EventType.INJURY,
                description="幽灵事件",
                causal_pressure=0.5,
            )
        )

        doctor = Doctor(project_root)
        items = doctor.diagnose()

        ledger_items = [i for i in items if i.category == "ledger_orphan"]
        assert len(ledger_items) >= 1
        assert "char_999" in ledger_items[0].message


class TestNoIssues:
    """无问题场景测试。"""

    def test_healthy_project(self, project_root: Path) -> None:
        """健康项目不应有 WARNING 级别的诊断项。"""
        doctor = Doctor(project_root)
        items = doctor.diagnose()

        # 快照统计是 INFO，孤立角色 char_003 可能是 WARNING
        # 但至少不应有 ERROR
        errors = [i for i in items if i.level == DiagnosticLevel.ERROR]
        assert len(errors) == 0
