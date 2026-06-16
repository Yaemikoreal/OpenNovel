"""cli/main 模块测试 - init、rollback、diff、doctor 命令。"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from loom.cli.main import app

runner = CliRunner()


class TestInitCommand:
    """loom init 命令测试。"""

    def test_init_creates_directories(self, tmp_path: Path) -> None:
        """测试 init 创建标准目录结构。"""
        project_dir = tmp_path / "my_novel"
        project_dir.mkdir()

        result = runner.invoke(app, ["init", str(project_dir)])

        assert result.exit_code == 0
        assert (project_dir / "canon").is_dir()
        assert (project_dir / "characters").is_dir()
        assert (project_dir / "draft").is_dir()
        assert (project_dir / "outlines").is_dir()
        assert (project_dir / "subconscious").is_dir()
        assert (project_dir / ".snapshots").is_dir()

    def test_init_creates_templates(self, tmp_path: Path) -> None:
        """测试 init 生成模板文件。"""
        project_dir = tmp_path / "my_novel"
        project_dir.mkdir()

        result = runner.invoke(app, ["init", str(project_dir)])

        assert result.exit_code == 0
        assert (project_dir / "characters" / "char_001.md").exists()
        assert (project_dir / "canon" / "world_rules.md").exists()
        assert (project_dir / "draft" / "ch_001.md").exists()
        assert (project_dir / "loom.yaml").exists()

    def test_init_idempotent(self, tmp_path: Path) -> None:
        """测试 init 幂等性（重复运行不报错）。"""
        project_dir = tmp_path / "my_novel"
        project_dir.mkdir()

        runner.invoke(app, ["init", str(project_dir)])
        result = runner.invoke(app, ["init", str(project_dir)])

        assert result.exit_code == 0

    def test_init_default_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """测试默认路径（当前目录）。"""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (tmp_path / "canon").is_dir()


class TestDiffCommand:
    """loom diff 命令测试。"""

    def test_diff_no_chapters(self, tmp_path: Path) -> None:
        """测试无章节文件时正常退出（直接调用函数）。"""
        from loom.core.diff_checker import DiffChecker

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "draft").mkdir()
        (project_dir / "characters").mkdir()

        checker = DiffChecker(project_dir)
        mismatches = checker.check_all()
        assert mismatches == []

    def test_diff_nonexistent_chapter(self, tmp_path: Path) -> None:
        """测试指定不存在的章节应报错。"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "draft").mkdir()

        result = runner.invoke(app, ["diff", "nonexistent.md", str(project_dir)])

        assert result.exit_code != 0


class TestDoctorCommand:
    """loom doctor 命令测试。"""

    def test_doctor_empty_project(self, tmp_path: Path) -> None:
        """测试空项目诊断。"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "characters").mkdir()
        (project_dir / "draft").mkdir()
        (project_dir / ".snapshots").mkdir()

        result = runner.invoke(app, ["doctor", str(project_dir)])

        assert result.exit_code == 0
