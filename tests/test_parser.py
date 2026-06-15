"""parser 模块测试 - Markdown/Frontmatter 解析。"""

import pytest
from pathlib import Path

from loom.core.parser import (
    parse_markdown_file,
    write_markdown_file,
    update_frontmatter,
    get_frontmatter_value,
    extract_pov_character_id,
    extract_active_characters,
)


@pytest.fixture
def sample_md_file(tmp_path: Path) -> Path:
    """创建测试用 Markdown 文件。"""
    file_path = tmp_path / "test_char.md"
    metadata = {
        "id": "char_001",
        "name": "Alice",
        "aliases": ["Alys"],
        "location": "loc_tower",
    }
    body = "# Alice 的背景故事\n\n她来自北方..."
    write_markdown_file(file_path, metadata, body)
    return file_path


@pytest.fixture
def sample_chapter_file(tmp_path: Path) -> Path:
    """创建测试用章节文件。"""
    file_path = tmp_path / "ch_001.md"
    metadata = {
        "id": "ch_001",
        "title": "第一章",
        "pov": "char_001",
        "active_characters": ["char_001", "char_002"],
    }
    body = "# 第一章\n\n故事开始了..."
    write_markdown_file(file_path, metadata, body)
    return file_path


class TestParseMarkdownFile:
    """parse_markdown_file 测试。"""

    def test_parse_valid_file(self, sample_md_file: Path) -> None:
        """测试解析合法的 Markdown 文件。"""
        metadata, body = parse_markdown_file(sample_md_file)
        assert metadata["id"] == "char_001"
        assert metadata["name"] == "Alice"
        assert "Alice 的背景故事" in body

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        """测试解析不存在的文件。"""
        with pytest.raises(FileNotFoundError):
            parse_markdown_file(tmp_path / "nonexistent.md")


class TestWriteMarkdownFile:
    """write_markdown_file 测试。"""

    def test_write_and_read(self, tmp_path: Path) -> None:
        """测试写入后读取的完整性。"""
        file_path = tmp_path / "output.md"
        metadata = {"id": "char_002", "name": "Bob"}
        body = "Bob 的故事"

        write_markdown_file(file_path, metadata, body)
        read_metadata, read_body = parse_markdown_file(file_path)

        assert read_metadata["id"] == "char_002"
        assert read_metadata["name"] == "Bob"
        assert "Bob 的故事" in read_body

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """测试写入时自动创建父目录。"""
        file_path = tmp_path / "nested" / "dir" / "test.md"
        write_markdown_file(file_path, {"key": "value"}, "content")
        assert file_path.exists()


class TestUpdateFrontmatter:
    """update_frontmatter 测试。"""

    def test_update_preserves_body(self, sample_md_file: Path) -> None:
        """测试更新 Frontmatter 时保持正文不变。"""
        updated = update_frontmatter(sample_md_file, {"name": "Alice Updated"})
        assert updated["name"] == "Alice Updated"
        assert updated["id"] == "char_001"  # 未修改的字段保持不变

        _, body = parse_markdown_file(sample_md_file)
        assert "Alice 的背景故事" in body


class TestExtractFunctions:
    """提取函数测试。"""

    def test_extract_pov(self, sample_chapter_file: Path) -> None:
        """测试提取 POV 角色 ID。"""
        pov = extract_pov_character_id(sample_chapter_file)
        assert pov == "char_001"

    def test_extract_active_characters(self, sample_chapter_file: Path) -> None:
        """测试提取活跃角色列表。"""
        chars = extract_active_characters(sample_chapter_file)
        assert chars == ["char_001", "char_002"]

    def test_extract_pov_missing(self, tmp_path: Path) -> None:
        """测试无 POV 字段时返回 None。"""
        file_path = tmp_path / "no_pov.md"
        write_markdown_file(file_path, {"id": "ch_002"}, "content")
        assert extract_pov_character_id(file_path) is None
