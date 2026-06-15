"""状态管理器 - YAML/SQLite 读写与 Diff 生成。

核心职责：
- 管理 YAML Frontmatter 的读写（通过 parser 模块）
- 管理 SQLite 事件账本的读写（通过 storage 模块）
- 生成状态变更的 Diff 展示
- 快照的创建与恢复
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import orjson

from loom.core.parser import parse_markdown_file, update_frontmatter, write_markdown_file
from loom.schemas.character import CharacterFrontmatter
from loom.schemas.event import EventCreate, EventDiff, SnapshotMeta
from loom.storage.sqlite import EventStore

logger = logging.getLogger(__name__)


class StateManager:
    """状态管理器，统一管理 YAML Frontmatter 和 SQLite 事件账本。

    铁律 3：人工审核关口。AI 只能提议状态变更，人类拥有绝对否决权。
    铁律 4：操作可逆。任何破坏性写入前必须生成 Snapshot。
    """

    def __init__(self, project_root: Path, db_path: Optional[Path] = None) -> None:
        """初始化状态管理器。

        Args:
            project_root: 项目根目录路径
            db_path: SQLite 数据库路径，默认为 project_root / ".loom.db"
        """
        self.project_root = project_root
        self.snapshots_dir = project_root / ".snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._event_store: Optional[EventStore] = None
        self._db_path = db_path or project_root / ".loom.db"

    @property
    def event_store(self) -> EventStore:
        """懒加载事件存储实例。"""
        if self._event_store is None:
            self._event_store = EventStore(self._db_path)
        return self._event_store

    def create_snapshot(self, chapter_id: str) -> SnapshotMeta:
        """创建当前状态的快照，用于回滚恢复。

        铁律 4：任何破坏性状态写入前必须生成 Snapshot。

        Args:
            chapter_id: 关联的章节 ID

        Returns:
            快照元数据
        """
        timestamp = datetime.now().isoformat()
        snapshot_id = f"{chapter_id}_{int(datetime.now().timestamp())}"
        snapshot_path = self.snapshots_dir / f"{snapshot_id}.snapshot.json"

        # 收集当前所有角色的 Frontmatter 状态
        frontmatter_before: dict[str, dict] = {}
        characters_dir = self.project_root / "characters"
        if characters_dir.exists():
            for char_file in characters_dir.glob("*.md"):
                metadata, _ = parse_markdown_file(char_file)
                frontmatter_before[char_file.stem] = metadata

        snapshot_data = {
            "snapshot_id": snapshot_id,
            "chapter_id": chapter_id,
            "timestamp": timestamp,
            "frontmatter_before": frontmatter_before,
            "frontmatter_after": None,
            "events_added": [],
        }

        with open(snapshot_path, "wb") as f:
            f.write(orjson.dumps(snapshot_data, option=orjson.OPT_INDENT_2))

        logger.info("快照已创建: %s", snapshot_path)
        return SnapshotMeta(**snapshot_data)

    def update_snapshot_after(
        self, snapshot_id: str, frontmatter_after: dict, events_added: list[str]
    ) -> None:
        """在 commit 完成后更新快照的 after 状态。

        Args:
            snapshot_id: 快照 ID
            frontmatter_after: commit 后的 Frontmatter 状态
            events_added: 新增的事件 ID 列表
        """
        snapshot_path = self.snapshots_dir / f"{snapshot_id}.snapshot.json"
        if not snapshot_path.exists():
            logger.warning("快照文件不存在: %s", snapshot_path)
            return

        with open(snapshot_path, "rb") as f:
            data = orjson.loads(f.read())

        data["frontmatter_after"] = frontmatter_after
        data["events_added"] = events_added

        with open(snapshot_path, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def rollback_snapshot(self, snapshot_id: str) -> bool:
        """从快照恢复状态，撤销 commit 操作。

        铁律 4：支持 loom rollback 秒级恢复。

        Args:
            snapshot_id: 要恢复的快照 ID

        Returns:
            恢复是否成功
        """
        snapshot_path = self.snapshots_dir / f"{snapshot_id}.snapshot.json"
        if not snapshot_path.exists():
            logger.error("快照文件不存在: %s", snapshot_path)
            return False

        with open(snapshot_path, "rb") as f:
            data = orjson.loads(f.read())

        before = data.get("frontmatter_before", {})
        characters_dir = self.project_root / "characters"

        # 恢复每个角色的 Frontmatter
        for char_id, metadata in before.items():
            char_path = characters_dir / f"{char_id}.md"
            if char_path.exists():
                _, body = parse_markdown_file(char_path)
                write_markdown_file(char_path, metadata, body)
                logger.info("已恢复角色 %s 的 Frontmatter", char_id)

        # 删除该 commit 新增的事件
        events_added = data.get("events_added", [])
        if events_added:
            self.event_store.delete_events_by_ids(events_added)
            logger.info("已删除 %d 条事件记录", len(events_added))

        return True

    def apply_character_diff(
        self, character_id: str, updates: dict
    ) -> CharacterFrontmatter:
        """将角色状态变更应用到 Frontmatter。

        Args:
            character_id: 角色 Canonical ID
            updates: 需要更新的 Frontmatter 字段字典

        Returns:
            更新后的 CharacterFrontmatter 对象
        """
        char_path = self.project_root / "characters" / f"{character_id}.md"
        if not char_path.exists():
            raise FileNotFoundError(f"角色文件不存在: {char_path}")

        new_metadata = update_frontmatter(char_path, updates)
        return CharacterFrontmatter(**new_metadata)

    def apply_event(self, event: EventCreate) -> None:
        """将事件写入 SQLite 事件账本。

        Args:
            event: 经过人工审核确认的事件
        """
        self.event_store.add_event(event)
        logger.info("事件已写入账本: %s", event.event_id)

    def generate_diff_text(self, diffs: list[EventDiff]) -> str:
        """生成人类可读的 Diff 文本，用于终端展示。

        Args:
            diffs: 事件变更列表

        Returns:
            格式化的 Diff 文本
        """
        lines: list[str] = []
        for diff in diffs:
            if diff.action == "add":
                lines.append(f"+ [Event] {diff.event.character_id} {diff.event.event_type}: {diff.event.description}")
            elif diff.action == "remove":
                lines.append(f"- [Event] {diff.event.character_id} {diff.event.event_type}: {diff.event.description}")
            elif diff.action == "modify" and diff.before:
                lines.append(
                    f"~ [Event] {diff.event.character_id} {diff.event.event_type}: "
                    f"{diff.before.description} -> {diff.event.description}"
                )
        return "\n".join(lines)

    def list_snapshots(self) -> list[SnapshotMeta]:
        """列出所有可用的快照。

        Returns:
            快照元数据列表，按时间倒序排列
        """
        snapshots: list[SnapshotMeta] = []
        for snapshot_file in self.snapshots_dir.glob("*.snapshot.json"):
            with open(snapshot_file, "rb") as f:
                data = orjson.loads(f.read())
            snapshots.append(SnapshotMeta(**data))
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        return snapshots
