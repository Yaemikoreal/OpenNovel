"""Markdown/Frontmatter 解析器 - 安全读写隔离的文件操作层。

基于 python-frontmatter 实现 Markdown 正文与 YAML Frontmatter 的物理隔离：
- 作者只编辑正文区（Markdown body）
- Auditor 只编辑 Frontmatter 区（YAML shadow）
- 读取时返回结构化对象，写入时保持格式完整性
"""

from pathlib import Path
from typing import Any, Optional

import frontmatter

from loom.schemas.character import CharacterFile, CharacterFrontmatter


def parse_markdown_file(file_path: Path) -> tuple[dict[str, Any], str]:
    """解析 Markdown 文件，分离 Frontmatter 和正文。

    Args:
        file_path: Markdown 文件的绝对路径

    Returns:
        元组 (frontmatter_dict, body_text)，frontmatter_dict 为解析后的字典，
        body_text 为正文内容

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: Frontmatter 格式错误
    """
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    post = frontmatter.load(str(file_path))
    return dict(post.metadata), post.content


def parse_character_file(file_path: Path) -> CharacterFile:
    """解析角色 Markdown 文件，返回结构化的 CharacterFile 对象。

    Args:
        file_path: 角色 Markdown 文件的绝对路径

    Returns:
        包含 Frontmatter 和正文的 CharacterFile 对象

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: Frontmatter 不符合 CharacterFrontmatter 模型规范
    """
    metadata, body = parse_markdown_file(file_path)
    frontmatter_obj = CharacterFrontmatter(**metadata)
    return CharacterFile(frontmatter=frontmatter_obj, body=body)


def write_markdown_file(
    file_path: Path,
    metadata: dict[str, Any],
    body: str,
) -> None:
    """将 Frontmatter 和正文合并写入 Markdown 文件。

    Args:
        file_path: 目标文件路径
        metadata: Frontmatter 字典
        body: 正文内容
    """
    post = frontmatter.Post(body, **metadata)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))


def update_frontmatter(file_path: Path, updates: dict[str, Any]) -> dict[str, Any]:
    """仅更新 Markdown 文件的 Frontmatter 区域，保持正文不变。

    此方法是 Auditor 写入状态的核心入口，确保正文区不被机器篡改。

    Args:
        file_path: 目标文件路径
        updates: 需要更新的 Frontmatter 字段字典

    Returns:
        更新后的完整 Frontmatter 字典
    """
    metadata, body = parse_markdown_file(file_path)
    metadata.update(updates)
    write_markdown_file(file_path, metadata, body)
    return metadata


def get_frontmatter_value(file_path: Path, key: str) -> Optional[Any]:
    """获取 Markdown 文件 Frontmatter 中指定字段的值。

    Args:
        file_path: 文件路径
        key: 字段名

    Returns:
        字段值，若不存在则返回 None
    """
    metadata, _ = parse_markdown_file(file_path)
    return metadata.get(key)


def extract_pov_character_id(chapter_path: Path) -> Optional[str]:
    """从章节文件中提取 POV 角色 ID。

    Args:
        chapter_path: 章节 Markdown 文件路径

    Returns:
        POV 角色的 Canonical ID，若未指定则返回 None
    """
    return get_frontmatter_value(chapter_path, "pov")


def extract_active_characters(chapter_path: Path) -> list[str]:
    """从章节文件中提取活跃角色 ID 列表。

    Args:
        chapter_path: 章节 Markdown 文件路径

    Returns:
        活跃角色的 Canonical ID 列表
    """
    value = get_frontmatter_value(chapter_path, "active_characters")
    return value if isinstance(value, list) else []
