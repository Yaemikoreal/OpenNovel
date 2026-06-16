"""context_assembler 模块测试 - Token 计数、权威组装、熔断机制。"""

from pathlib import Path

import pytest

from loom.core.context_assembler import (
    BUDGET_RATIOS,
    INPUT_TOKEN_BUDGET,
    TOTAL_TOKEN_BUDGET,
    TRUNCATION_ORDER,
    ContextMessage,
    TokenCounter,
    _apply_circuit_breaker,
    assemble_actor_context,
    load_prompt,
    wrap_with_authority_tag,
)
from loom.schemas.character import AuthorityLevel
from loom.storage.yaml_storage import YAMLStorage

# ── TokenCounter 测试 ──


class TestTokenCounter:
    """TokenCounter 基础功能测试。"""

    def test_default_encoding(self) -> None:
        """测试默认编码模型。"""
        counter = TokenCounter()
        assert counter._encoding is not None

    def test_count_simple_text(self) -> None:
        """测试简单文本计数。"""
        counter = TokenCounter()
        count = counter.count("hello world")
        assert count > 0
        assert isinstance(count, int)

    def test_count_empty_text(self) -> None:
        """测试空文本计数为 0。"""
        counter = TokenCounter()
        assert counter.count("") == 0

    def test_count_chinese_text(self) -> None:
        """测试中文文本计数。"""
        counter = TokenCounter()
        count = counter.count("你好世界")
        assert count > 0

    def test_truncate_short_text_unchanged(self) -> None:
        """测试短文本不被截断。"""
        counter = TokenCounter()
        result = counter.truncate_to_budget("hello", max_tokens=100)
        assert result == "hello"

    def test_truncate_long_text(self) -> None:
        """测试长文本被截断。"""
        counter = TokenCounter()
        text = "hello world " * 100
        result = counter.truncate_to_budget(text, max_tokens=5)
        assert counter.count(result) <= 5

    def test_unknown_encoding_fallback(self) -> None:
        """测试未知编码模型回退到 cl100k_base。"""
        counter = TokenCounter(model="nonexistent_model")
        assert counter._encoding is not None
        assert counter.count("test") > 0


# ── ContextMessage 测试 ──


class TestContextMessage:
    """ContextMessage 数据类测试。"""

    def test_creation_with_authority(self) -> None:
        """测试带权威层级的消息创建。"""
        msg = ContextMessage(
            role="system",
            content="测试内容",
            authority=AuthorityLevel.CANON,
        )
        assert msg.role == "system"
        assert msg.content == "测试内容"
        assert msg.authority == AuthorityLevel.CANON
        assert msg.token_count == 0

    def test_creation_without_authority(self) -> None:
        """测试无权威层级的消息创建（人格注入）。"""
        msg = ContextMessage(role="system", content="人格 Prompt")
        assert msg.authority is None

    def test_to_dict(self) -> None:
        """测试转换为 LLM API 格式。"""
        msg = ContextMessage(role="user", content="续写锚点")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "续写锚点"}


# ── load_prompt 测试 ──


class TestLoadPrompt:
    """load_prompt 函数测试。"""

    def test_load_existing_prompt(self, tmp_path: Path) -> None:
        """测试加载存在的 Prompt 文件。"""
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("# 测试 Prompt\n\n你是测试代理。", encoding="utf-8")

        content = load_prompt(prompt_file)
        assert "测试 Prompt" in content
        assert "测试代理" in content

    def test_load_nonexistent_prompt(self, tmp_path: Path) -> None:
        """测试加载不存在的 Prompt 文件抛出异常。"""
        with pytest.raises(FileNotFoundError):
            load_prompt(tmp_path / "nonexistent.md")


# ── wrap_with_authority_tag 测试 ──


class TestWrapWithAuthorityTag:
    """wrap_with_authority_tag 函数测试。"""

    def test_canon_tag(self) -> None:
        """测试 CANON 权威标签。"""
        result = wrap_with_authority_tag("设定内容", AuthorityLevel.CANON)
        assert "[CANON | IMMUTABLE | HIGH AUTHORITY]" in result
        assert "设定内容" in result

    def test_state_memory_tag(self) -> None:
        """测试 STATE_MEMORY 权威标签。"""
        result = wrap_with_authority_tag("状态内容", AuthorityLevel.STATE_MEMORY)
        assert "[STATE MEMORY | MEDIUM AUTHORITY]" in result

    def test_subconscious_tag(self) -> None:
        """测试 SUBCONSCIOUS 权威标签。"""
        result = wrap_with_authority_tag("灵感内容", AuthorityLevel.SUBCONSCIOUS)
        assert "[SUBCONSCIOUS FRAGMENT | LOW AUTHORITY | OPTIONAL]" in result


# ── 常量测试 ──


class TestConstants:
    """预算常量测试。"""

    def test_token_budget_values(self) -> None:
        """测试 Token 预算常量合理性。"""
        assert TOTAL_TOKEN_BUDGET == 8000
        assert INPUT_TOKEN_BUDGET == 6000  # 8000 - 2000

    def test_budget_ratios_sum(self) -> None:
        """测试各层级预算占比总和为 1.0。"""
        total = sum(BUDGET_RATIOS.values())
        assert abs(total - 1.0) < 0.001

    def test_truncation_order(self) -> None:
        """测试裁剪从低权威到高权威。"""
        assert TRUNCATION_ORDER == [
            AuthorityLevel.SUBCONSCIOUS,
            AuthorityLevel.STATE_MEMORY,
            AuthorityLevel.CANON,
        ]


# ── _apply_circuit_breaker 测试 ──


class TestCircuitBreaker:
    """_apply_circuit_breaker 熔断机制测试。"""

    def test_no_truncation_under_budget(self) -> None:
        """测试未超限时不裁剪。"""
        counter = TokenCounter()
        messages = [
            ContextMessage(role="system", content="短文本", authority=AuthorityLevel.CANON),
        ]
        messages[0].token_count = counter.count("短文本")

        result = _apply_circuit_breaker(messages, counter, budget=10000)
        assert len(result) == 1
        assert result[0].content == "短文本"

    def test_truncates_subconscious_first(self) -> None:
        """测试超限时优先裁剪 SUBCONSCIOUS。"""
        counter = TokenCounter()

        # 创建三个层级的消息，总 token 超限
        canon_text = "A" * 500
        state_text = "B" * 500
        sub_text = "C" * 500

        messages = [
            ContextMessage(role="system", content=canon_text, authority=AuthorityLevel.CANON),
            ContextMessage(
                role="system", content=state_text, authority=AuthorityLevel.STATE_MEMORY
            ),
            ContextMessage(role="system", content=sub_text, authority=AuthorityLevel.SUBCONSCIOUS),
        ]
        for m in messages:
            m.token_count = counter.count(m.content)

        total_tokens = sum(m.token_count for m in messages)
        # 设置预算刚好够 CANON + STATE，不够 SUBCONSCIOUS
        budget = total_tokens - counter.count(sub_text) + 10

        result = _apply_circuit_breaker(messages, counter, budget=budget)

        # SUBCONSCIOUS 应被裁剪
        sub_msg = [m for m in result if m.authority == AuthorityLevel.SUBCONSCIOUS]
        if sub_msg:
            assert sub_msg[0].token_count < counter.count(sub_text)

    def test_preserves_none_authority(self) -> None:
        """测试人格注入（authority=None）不被裁剪。"""
        counter = TokenCounter()
        messages = [
            ContextMessage(role="system", content="人格", authority=None),
            ContextMessage(
                role="system",
                content="X" * 2000,
                authority=AuthorityLevel.SUBCONSCIOUS,
            ),
        ]
        messages[0].token_count = counter.count("人格")
        messages[1].token_count = counter.count("X" * 2000)

        # 预算只够人格消息
        budget = counter.count("人格") + 50
        result = _apply_circuit_breaker(messages, counter, budget=budget)

        # 人格消息应保留
        persona_msgs = [m for m in result if m.authority is None]
        assert len(persona_msgs) == 1
        assert persona_msgs[0].content == "人格"


# ── assemble_actor_context 测试 ──


class TestAssembleActorContext:
    """assemble_actor_context 完整组装测试。"""

    def test_basic_assembly(self, tmp_path: Path) -> None:
        """测试基本的上下文组装。"""
        # 创建项目结构
        project_root = tmp_path
        (project_root / "characters").mkdir()
        (project_root / "prompts").mkdir()

        # 创建角色文件
        storage = YAMLStorage()
        storage.write_markdown_file(
            project_root / "characters" / "char_001.md",
            {
                "id": "char_001",
                "name": "测试角色",
                "physical": {"injuries": [], "buffs": [], "debuffs": []},
            },
            "# 角色背景",
        )

        # 创建 Prompt 文件
        prompt_path = project_root / "prompts" / "actor.v1.md"
        prompt_path.write_text("# Actor Prompt\n\n你是写作代理。", encoding="utf-8")

        # 创建章节文件
        chapter_path = project_root / "ch_001.md"
        storage.write_markdown_file(
            chapter_path,
            {"id": "ch_001", "pov": "char_001", "active_characters": ["char_001"]},
            "# 第一章\n\n故事开始。",
        )

        messages = assemble_actor_context(
            chapter_path=chapter_path,
            project_root=project_root,
            current_text="故事开始的文本。",
            prompt_path=prompt_path,
            canon_content="魔法消耗寿命。",
            subconscious_content="灵感碎片。",
            yaml_storage=storage,
        )

        # 应该包含：人格 + CANON + STATE + SUBCONSCIOUS + 近期正文
        assert len(messages) >= 4
        # 检查消息角色
        roles = [m["role"] for m in messages]
        assert "system" in roles
        assert "user" in roles

    def test_assembly_without_optional_content(self, tmp_path: Path) -> None:
        """测试不提供可选内容时的组装。"""
        project_root = tmp_path
        (project_root / "characters").mkdir()

        storage = YAMLStorage()
        storage.write_markdown_file(
            project_root / "characters" / "char_001.md",
            {"id": "char_001", "name": "角色"},
            "# 背景",
        )

        chapter_path = project_root / "ch_001.md"
        storage.write_markdown_file(
            chapter_path,
            {"id": "ch_001", "pov": "char_001"},
            "# 第一章",
        )

        messages = assemble_actor_context(
            chapter_path=chapter_path,
            project_root=project_root,
            current_text="正文内容",
            yaml_storage=storage,
        )

        # 至少应有 STATE + 近期正文
        assert len(messages) >= 2

    def test_messages_are_valid_dict_format(self, tmp_path: Path) -> None:
        """测试返回的消息列表格式正确。"""
        project_root = tmp_path
        (project_root / "characters").mkdir()

        storage = YAMLStorage()
        storage.write_markdown_file(
            project_root / "characters" / "char_001.md",
            {"id": "char_001", "name": "角色"},
            "# 背景",
        )

        chapter_path = project_root / "ch_001.md"
        storage.write_markdown_file(
            chapter_path,
            {"id": "ch_001", "pov": "char_001"},
            "# 第一章",
        )

        messages = assemble_actor_context(
            chapter_path=chapter_path,
            project_root=project_root,
            current_text="正文",
            yaml_storage=storage,
        )

        for msg in messages:
            assert isinstance(msg, dict)
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("system", "user", "assistant")
