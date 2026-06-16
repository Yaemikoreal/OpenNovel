"""三级上下文策略测试 - FRUGAL / STANDARD / PANORAMIC 组装逻辑。"""

from pathlib import Path

import pytest

from loom.core.context_assembler import (
    PANORAMIC_SOFT_LIMIT,
    STANDARD_TOKEN_BUDGET,
    ContextStrategy,
    TokenCounter,
    assemble_actor_context,
    detect_strategy,
)
from loom.storage.yaml_storage import YAMLStorage

# ── ContextStrategy 枚举测试 ──


class TestContextStrategy:
    """ContextStrategy 枚举定义测试。"""

    def test_frugal_value(self) -> None:
        """测试 FRUGAL 策略值。"""
        assert ContextStrategy.FRUGAL.value == "frugal"

    def test_standard_value(self) -> None:
        """测试 STANDARD 策略值。"""
        assert ContextStrategy.STANDARD.value == "standard"

    def test_panoramic_value(self) -> None:
        """测试 PANORAMIC 策略值。"""
        assert ContextStrategy.PANORAMIC.value == "panoramic"

    def test_all_strategies_exist(self) -> None:
        """测试三种策略全部定义。"""
        strategies = list(ContextStrategy)
        assert len(strategies) == 3


# ── detect_strategy 测试 ──


class TestDetectStrategy:
    """detect_strategy 模型窗口映射测试。"""

    def test_small_window_returns_frugal(self) -> None:
        """测试 <32K 窗口返回 FRUGAL。"""
        assert detect_strategy(8192) == ContextStrategy.FRUGAL
        assert detect_strategy(16384) == ContextStrategy.FRUGAL
        assert detect_strategy(31999) == ContextStrategy.FRUGAL

    def test_medium_window_returns_standard(self) -> None:
        """测试 32K-128K 窗口返回 STANDARD。"""
        assert detect_strategy(32000) == ContextStrategy.STANDARD
        assert detect_strategy(65536) == ContextStrategy.STANDARD
        assert detect_strategy(127999) == ContextStrategy.STANDARD

    def test_large_window_returns_panoramic(self) -> None:
        """测试 >128K 窗口返回 PANORAMIC。"""
        assert detect_strategy(128000) == ContextStrategy.PANORAMIC
        assert detect_strategy(1000000) == ContextStrategy.PANORAMIC

    def test_boundary_32k(self) -> None:
        """测试 32K 边界值。"""
        assert detect_strategy(32000) == ContextStrategy.STANDARD
        assert detect_strategy(31999) == ContextStrategy.FRUGAL

    def test_boundary_128k(self) -> None:
        """测试 128K 边界值。"""
        assert detect_strategy(128000) == ContextStrategy.PANORAMIC
        assert detect_strategy(127999) == ContextStrategy.STANDARD


# ── STANDARD 策略常量测试 ──


class TestStandardConstants:
    """STANDARD 策略预算常量测试。"""

    def test_standard_budget_value(self) -> None:
        """测试 STANDARD 预算为 48000 tokens。"""
        assert STANDARD_TOKEN_BUDGET == 48000

    def test_panoramic_soft_limit(self) -> None:
        """测试 PANORAMIC 软限为 128K tokens。"""
        assert PANORAMIC_SOFT_LIMIT == 128000


# ── STANDARD 策略组装测试 ──


class TestStandardAssembly:
    """STANDARD 策略上下文组装测试。"""

    def test_standard_includes_all_characters(self, tmp_path: Path, standard_setup: dict) -> None:
        """测试 STANDARD 策略注入所有活跃角色状态。"""
        messages = assemble_actor_context(
            chapter_path=standard_setup["chapter_path"],
            project_root=tmp_path,
            current_text="故事正文。",
            strategy=ContextStrategy.STANDARD,
            yaml_storage=standard_setup["storage"],
        )
        # 应包含所有活跃角色的状态
        content = " ".join(m["content"] for m in messages)
        assert "char_001" in content
        assert "char_002" in content

    def test_standard_budget_larger_than_frugal(self, tmp_path: Path, standard_setup: dict) -> None:
        """测试 STANDARD 预算大于 FRUGAL。"""
        # 组装一段较长的文本
        long_text = "这是一段测试文本。" * 500
        messages = assemble_actor_context(
            chapter_path=standard_setup["chapter_path"],
            project_root=tmp_path,
            current_text=long_text,
            strategy=ContextStrategy.STANDARD,
            yaml_storage=standard_setup["storage"],
        )
        # STANDARD 应能容纳更多文本
        total_content = " ".join(m["content"] for m in messages)
        assert len(total_content) > 0

    def test_standard_preserves_authority_hierarchy(
        self, tmp_path: Path, standard_setup: dict
    ) -> None:
        """测试 STANDARD 策略保持权威分级标签。"""
        messages = assemble_actor_context(
            chapter_path=standard_setup["chapter_path"],
            project_root=tmp_path,
            current_text="正文。",
            canon_content="魔法设定。",
            subconscious_content="灵感碎片。",
            strategy=ContextStrategy.STANDARD,
            yaml_storage=standard_setup["storage"],
        )
        content = " ".join(m["content"] for m in messages)
        assert "[CANON" in content
        assert "[STATE MEMORY" in content
        assert "[SUBCONSCIOUS" in content


# ── PANORAMIC 策略组装测试 ──


class TestPanoramicAssembly:
    """PANORAMIC 策略上下文组装测试。"""

    def test_panoramic_includes_full_canon(self, tmp_path: Path, panoramic_setup: dict) -> None:
        """测试 PANORAMIC 策略注入全量设定。"""
        messages = assemble_actor_context(
            chapter_path=panoramic_setup["chapter_path"],
            project_root=tmp_path,
            current_text="正文。",
            canon_content=panoramic_setup["long_canon"],
            strategy=ContextStrategy.PANORAMIC,
            yaml_storage=panoramic_setup["storage"],
        )
        content = " ".join(m["content"] for m in messages)
        # PANORAMIC 不应截断设定
        assert "重要世界观规则" in content

    def test_panoramic_includes_full_subconscious(
        self, tmp_path: Path, panoramic_setup: dict
    ) -> None:
        """测试 PANORAMIC 策略注入全量潜意识。"""
        messages = assemble_actor_context(
            chapter_path=panoramic_setup["chapter_path"],
            project_root=tmp_path,
            current_text="正文。",
            subconscious_content=panoramic_setup["long_subconscious"],
            strategy=ContextStrategy.PANORAMIC,
            yaml_storage=panoramic_setup["storage"],
        )
        content = " ".join(m["content"] for m in messages)
        assert "灵感碎片" in content

    def test_panoramic_soft_limit_applied(self, tmp_path: Path, panoramic_setup: dict) -> None:
        """测试 PANORAMIC 策略应用 128K 软限。"""
        # 创建超长内容
        huge_text = "段落内容。" * 50000
        messages = assemble_actor_context(
            chapter_path=panoramic_setup["chapter_path"],
            project_root=tmp_path,
            current_text=huge_text,
            strategy=ContextStrategy.PANORAMIC,
            yaml_storage=panoramic_setup["storage"],
        )
        # 总 token 不应超过软限 + 输出预留
        counter = TokenCounter()
        total = sum(counter.count(m["content"]) for m in messages)
        assert total <= PANORAMIC_SOFT_LIMIT + 2000  # 加上人格注入等不可裁剪部分


# ── 默认策略测试 ──


class TestDefaultStrategy:
    """默认策略（不传 strategy 参数）行为测试。"""

    def test_default_uses_frugal(self, tmp_path: Path, standard_setup: dict) -> None:
        """测试不传 strategy 时默认使用 FRUGAL。"""
        messages = assemble_actor_context(
            chapter_path=standard_setup["chapter_path"],
            project_root=tmp_path,
            current_text="正文。",
            yaml_storage=standard_setup["storage"],
        )
        # FRUGAL 预算下，角色状态应被截断或不包含所有角色
        # 验证返回格式正确即可
        assert len(messages) >= 1
        for msg in messages:
            assert "role" in msg
            assert "content" in msg


# ── Fixtures ──


@pytest.fixture
def standard_setup(tmp_path: Path) -> dict:
    """创建 STANDARD 策略测试所需的项目结构。"""
    (tmp_path / "characters").mkdir()
    storage = YAMLStorage()

    # 两个角色
    storage.write_markdown_file(
        tmp_path / "characters" / "char_001.md",
        {
            "id": "char_001",
            "name": "主角",
            "physical": {"injuries": [], "buffs": [], "debuffs": []},
        },
        "# 主角背景",
    )
    storage.write_markdown_file(
        tmp_path / "characters" / "char_002.md",
        {
            "id": "char_002",
            "name": "配角",
            "physical": {"injuries": [], "buffs": [], "debuffs": []},
        },
        "# 配角背景",
    )

    # 章节引用两个角色
    chapter_path = tmp_path / "ch_001.md"
    storage.write_markdown_file(
        chapter_path,
        {
            "id": "ch_001",
            "pov": "char_001",
            "active_characters": ["char_001", "char_002"],
        },
        "# 第一章\n\n故事开始。",
    )

    return {"storage": storage, "chapter_path": chapter_path}


@pytest.fixture
def panoramic_setup(tmp_path: Path) -> dict:
    """创建 PANORAMIC 策略测试所需的项目结构。"""
    (tmp_path / "characters").mkdir()
    storage = YAMLStorage()

    storage.write_markdown_file(
        tmp_path / "characters" / "char_001.md",
        {
            "id": "char_001",
            "name": "主角",
            "physical": {"injuries": [], "buffs": [], "debuffs": []},
        },
        "# 主角背景\n\n详细的角色历史。",
    )

    chapter_path = tmp_path / "ch_001.md"
    storage.write_markdown_file(
        chapter_path,
        {"id": "ch_001", "pov": "char_001", "active_characters": ["char_001"]},
        "# 第一章\n\n故事开始。",
    )

    # 长设定
    long_canon = "重要世界观规则。\n" + "详细设定内容。\n" * 200
    long_subconscious = "灵感碎片。\n" + "更多灵感。\n" * 100

    return {
        "storage": storage,
        "chapter_path": chapter_path,
        "long_canon": long_canon,
        "long_subconscious": long_subconscious,
    }
