"""AutoRunner 模块测试 - 三 Agent 自主创作编排器。"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from loom.agents.critic import Critic
from loom.agents.manager import Manager
from loom.agents.writer import Writer
from loom.core.auto_runner import AutoRunner, ChapterResult, RunReport
from loom.core.config import LoomConfig
from loom.schemas.evaluation import ChapterEvaluation, DimensionScore
from loom.schemas.manager_update import ManagerUpdateResult
from loom.schemas.outline import ChapterOutline, SceneBreakdown

# ── Mock LiteLLM 响应对象（属性访问模式）──


class MockMessage:
    def __init__(self, text: str) -> None:
        self.content = text


class MockChoice:
    def __init__(self, text: str) -> None:
        self.message = MockMessage(text)


class MockUsage:
    def __init__(self) -> None:
        self.prompt_tokens = 10
        self.completion_tokens = 10
        self.total_tokens = 20


class MockLLMResponse:
    """模拟 LiteLLM 响应对象（属性访问，非字典）。"""

    def __init__(self, text: str) -> None:
        self.choices = [MockChoice(text)]
        self.usage = MockUsage()


class MockLLMBus:
    """模拟 LLMBus，可控的响应序列。"""

    def __init__(self, responses: list[str]) -> None:
        self.responses = [MockLLMResponse(r) for r in responses]
        self.call_count = 0
        self.last_messages: list[dict[str, str]] = []

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> MockLLMResponse:
        response = self.responses[self.call_count]
        self.call_count += 1
        self.last_messages = messages
        return response


# ── Fixtures ──


def make_outline(chapter_id: str = "ch_001") -> ChapterOutline:
    """构造测试用 ChapterOutline。"""
    return ChapterOutline(
        chapter_id=chapter_id,
        title="第一章：相遇",
        summary="四人在加油站相遇，气氛紧张",
        scenes=[
            SceneBreakdown(
                scene_id="scene_1",
                description="加油站场景",
                characters_involved=["char_001"],
                emotional_tone="紧张",
                estimated_words=800,
            )
        ],
        character_arcs={"char_001": "从怀疑到信任"},
        key_plot_points=["四人首次相遇"],
        narrative_rhythm="快节奏",
        target_words=3000,
    )


def make_evaluation(total_score: int = 85) -> ChapterEvaluation:
    """构造测试用 ChapterEvaluation。"""
    return ChapterEvaluation(
        total_score=total_score,
        dimensions=[
            DimensionScore(dimension="文笔质量", score=18, comment="优秀"),
            DimensionScore(dimension="情节逻辑", score=17, comment="合理"),
            DimensionScore(dimension="角色一致性", score=17, comment="一致"),
            DimensionScore(dimension="节奏把控", score=16, comment="紧凑"),
            DimensionScore(dimension="情感表达", score=17, comment="细腻"),
        ],
        summary="整体质量不错",
        issues=[],
        suggestions=[],
    )


def make_manager_result() -> ManagerUpdateResult:
    """构造测试用 ManagerUpdateResult。"""
    return ManagerUpdateResult(
        character_updates=[],
        events=[],
        chapter_summary="第一章摘要：四人相遇",
    )


@pytest.fixture
def empty_project_root(tmp_path: Path) -> Path:
    """临时项目根目录，包含标准目录结构。"""
    root = tmp_path / "test_project"
    root.mkdir()
    (root / "draft").mkdir()
    (root / "characters").mkdir()
    (root / "canon").mkdir()
    (root / "outlines").mkdir()
    (root / "prompts").mkdir()
    (root / ".snapshots").mkdir()
    (root / ".index").mkdir()
    # 写入 loom.yaml 配置
    (root / "loom.yaml").write_text(
        "model: test-model\napi_base: http://localhost:8080\napi_key: test-key\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def default_config() -> LoomConfig:
    """默认测试配置。"""
    return LoomConfig(
        model="test-model",
        api_base="http://localhost:8080",
        api_key="test-key",
        creative_direction="黑暗奇幻风格",
        target_chapters=5,
        words_per_chapter=3000,
    )


@pytest.fixture
def outline_text() -> str:
    """测试大纲文本。"""
    return """## 第一章：相遇

四人在加油站相遇，气氛紧张。

## 第二章：冲突

矛盾爆发，战斗开始。
"""


# ── 初始化测试 ──


class TestAutoRunnerInit:
    """AutoRunner 初始化测试。"""

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    @patch("loom.core.auto_runner.Writer")
    @patch("loom.core.auto_runner.Critic")
    @patch("loom.core.auto_runner.Manager")
    def test_init_creates_three_agents(
        self,
        mock_manager_cls: MagicMock,
        mock_critic_cls: MagicMock,
        mock_writer_cls: MagicMock,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试初始化创建三个 Agent。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        assert runner.writer is not None
        assert runner.critic is not None
        assert runner.manager is not None
        # 验证三个 Agent 被创建
        mock_writer_cls.assert_called_once()
        mock_critic_cls.assert_called_once()
        mock_manager_cls.assert_called_once()

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    @patch("loom.core.auto_runner.Writer")
    @patch("loom.core.auto_runner.Critic")
    @patch("loom.core.auto_runner.Manager")
    def test_init_llm_bus_configs(
        self,
        mock_manager_cls: MagicMock,
        mock_critic_cls: MagicMock,
        mock_writer_cls: MagicMock,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试四个 Agent 的 LLMBus 配置正确传递。"""
        AutoRunner(project_root=empty_project_root, config=default_config)

        # 验证 LLMBus 被创建 4 次（writer, critic, manager, director）
        assert mock_llm_bus_cls.call_count == 4

        # 验证每次调用都传递了正确的配置
        for call in mock_llm_bus_cls.call_args_list:
            kwargs = call[1]
            assert kwargs["model"] == "test-model"
            assert kwargs["api_base"] == "http://localhost:8080"
            assert kwargs["api_key"] == "test-key"

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    @patch("loom.core.auto_runner.Writer")
    @patch("loom.core.auto_runner.Critic")
    @patch("loom.core.auto_runner.Manager")
    def test_init_with_agent_specific_config(
        self,
        mock_manager_cls: MagicMock,
        mock_critic_cls: MagicMock,
        mock_writer_cls: MagicMock,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
    ) -> None:
        """测试 per-agent LLM 配置覆盖。"""
        from loom.core.config import AgentConfig

        config = LoomConfig(
            model="default-model",
            api_base="http://default:8080",
            api_key="default-key",
            agent_writer=AgentConfig(model="writer-model"),
            agent_critic=AgentConfig(model="critic-model"),
            agent_manager=AgentConfig(model="manager-model"),
        )

        AutoRunner(project_root=empty_project_root, config=config)

        # 验证每个 Agent 使用了自己的模型
        calls = mock_llm_bus_cls.call_args_list
        assert calls[0][1]["model"] == "writer-model"
        assert calls[1][1]["model"] == "critic-model"
        assert calls[2][1]["model"] == "manager-model"


# ── 大纲解析测试 ──


class TestParseOutline:
    """_parse_outline 大纲解析测试。"""

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    @patch("loom.core.auto_runner.Writer")
    @patch("loom.core.auto_runner.Critic")
    @patch("loom.core.auto_runner.Manager")
    def test_parse_two_chapters(
        self,
        mock_manager_cls: MagicMock,
        mock_critic_cls: MagicMock,
        mock_writer_cls: MagicMock,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
        outline_text: str,
    ) -> None:
        """测试解析两章大纲。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        chapters = runner._parse_outline(outline_text)

        assert len(chapters) == 2
        assert chapters[0][0] == "ch_001"
        assert "相遇" in chapters[0][1]
        assert chapters[1][0] == "ch_002"
        assert "冲突" in chapters[1][1]

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    @patch("loom.core.auto_runner.Writer")
    @patch("loom.core.auto_runner.Critic")
    @patch("loom.core.auto_runner.Manager")
    def test_parse_empty_outline(
        self,
        mock_manager_cls: MagicMock,
        mock_critic_cls: MagicMock,
        mock_writer_cls: MagicMock,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试空大纲返回空列表。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        chapters = runner._parse_outline("")
        assert chapters == []

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    @patch("loom.core.auto_runner.Writer")
    @patch("loom.core.auto_runner.Critic")
    @patch("loom.core.auto_runner.Manager")
    def test_parse_single_chapter(
        self,
        mock_manager_cls: MagicMock,
        mock_critic_cls: MagicMock,
        mock_writer_cls: MagicMock,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试单章大纲解析。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        text = "## 第一章：开篇\n\n故事开始。"
        chapters = runner._parse_outline(text)

        assert len(chapters) == 1
        assert chapters[0][0] == "ch_001"
        assert "开篇" in chapters[0][1]

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    @patch("loom.core.auto_runner.Writer")
    @patch("loom.core.auto_runner.Critic")
    @patch("loom.core.auto_runner.Manager")
    def test_parse_preserves_body_text(
        self,
        mock_manager_cls: MagicMock,
        mock_critic_cls: MagicMock,
        mock_writer_cls: MagicMock,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试大纲解析保留正文内容。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        text = "## 第一章：开篇\n\n这是第一章的详细描述。\n包含多行内容。"
        chapters = runner._parse_outline(text)

        assert "详细描述" in chapters[0][1]
        assert "多行内容" in chapters[0][1]


# ── 单章流程测试 ──


class TestRunChapter:
    """run_chapter 单章创作流程测试。"""

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_run_chapter_success(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试单章完整创作流程：think → write → evaluate → update。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        # Mock Writer
        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第一章：相遇\n\n这是正文内容。"

        # Mock Critic
        runner.critic = MagicMock(spec=Critic)
        runner.critic.evaluate.return_value = make_evaluation(85)

        # Mock Manager
        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.return_value = make_manager_result()

        result = runner.run_chapter("ch_001", "四人在加油站相遇")

        # 验证 Writer 被调用
        runner.writer.think.assert_called_once()
        runner.writer.write.assert_called_once()

        # 验证 Critic 被调用
        runner.critic.evaluate.assert_called_once()

        # 验证 Manager 被调用
        runner.manager.update.assert_called_once()

        # 验证返回结果
        assert isinstance(result, ChapterResult)
        assert result.chapter_id == "ch_001"
        assert result.evaluation.total_score == 85
        assert result.retry_count == 0
        assert result.manager_summary == "第一章摘要：四人相遇"

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_run_chapter_writes_file(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试 run_chapter 将章节写入文件。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第一章：相遇\n\n正文。"

        runner.critic = MagicMock(spec=Critic)
        runner.critic.evaluate.return_value = make_evaluation(85)

        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.return_value = make_manager_result()

        runner.run_chapter("ch_001", "四人相遇")

        # 验证章节文件已写入
        chapter_path = empty_project_root / "draft" / "ch_001.md"
        assert chapter_path.exists()

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_run_chapter_with_previous_context(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试 run_chapter 传递前文上下文。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第二章\n\n正文。"

        runner.critic = MagicMock(spec=Critic)
        runner.critic.evaluate.return_value = make_evaluation(85)

        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.return_value = make_manager_result()

        runner.run_chapter(
            "ch_002", "冲突爆发",
            previous_summary="前一章摘要",
            previous_text="前一章正文末尾",
        )

        # 验证 Writer.think 收到前文摘要
        think_call = runner.writer.think.call_args
        assert think_call[0][2] == "前一章摘要"  # previous_summary

        # 验证 Writer.write 收到前文正文
        write_call = runner.writer.write.call_args
        assert write_call[0][2] == "前一章正文末尾"  # previous_chapter_text

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_run_chapter_manager_failure_graceful(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试 Manager 失败时优雅降级（不中断流程）。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第一章\n\n正文。"

        runner.critic = MagicMock(spec=Critic)
        runner.critic.evaluate.return_value = make_evaluation(85)

        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.side_effect = RuntimeError("Manager 失败")

        result = runner.run_chapter("ch_001", "四人相遇")

        # Manager 失败不应中断流程，摘要为空
        assert result.manager_summary == ""
        assert result.evaluation.total_score == 85


# ── 不合格重试测试 ──


class TestRunChapterRetry:
    """run_chapter 不合格重试流程测试。"""

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_retry_then_pass(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试第一次不合格（75分），修订后合格（85分）。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第一章\n\n初稿正文。"
        runner.writer.revise.return_value = "# 第一章\n\n修订后正文。"

        runner.critic = MagicMock(spec=Critic)
        # 第一次 75 分（不合格），第二次 85 分（合格）
        runner.critic.evaluate.side_effect = [
            make_evaluation(75),
            make_evaluation(85),
        ]

        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.return_value = make_manager_result()

        result = runner.run_chapter("ch_001", "四人相遇")

        assert result.evaluation.total_score == 85
        assert result.retry_count == 1
        # Writer.revise 被调用一次
        runner.writer.revise.assert_called_once()
        # Critic.evaluate 被调用两次
        assert runner.critic.evaluate.call_count == 2

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_retry_passes_feedback_to_writer(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试重试时将 Critic 反馈传递给 Writer.revise。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第一章\n\n初稿。"
        runner.writer.revise.return_value = "# 第一章\n\n修订稿。"

        # 构造带 issues 和 suggestions 的评价
        bad_eval = ChapterEvaluation(
            total_score=75,
            dimensions=[
                DimensionScore(dimension="文笔质量", score=15, comment="一般"),
                DimensionScore(dimension="情节逻辑", score=15, comment="一般"),
                DimensionScore(dimension="角色一致性", score=15, comment="一般"),
                DimensionScore(dimension="节奏把控", score=15, comment="一般"),
                DimensionScore(dimension="情感表达", score=15, comment="一般"),
            ],
            summary="需要改进",
            issues=["文笔平淡", "节奏拖沓"],
            suggestions=["增加细节描写", "加快节奏"],
        )

        runner.critic = MagicMock(spec=Critic)
        runner.critic.evaluate.side_effect = [bad_eval, make_evaluation(85)]

        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.return_value = make_manager_result()

        runner.run_chapter("ch_001", "四人相遇")

        # 验证 revise 收到反馈
        revise_call = runner.writer.revise.call_args
        feedback = revise_call[0][3]  # feedback 参数
        assert "文笔平淡" in feedback
        assert "增加细节描写" in feedback


# ── 最大重试次数测试 ──


class TestRunChapterMaxRetries:
    """run_chapter 达到最大重试次数后取最高分版本。"""

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_max_retries_takes_best_score(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试 5 次重试后取最高分版本。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第一章\n\n初稿。"
        runner.writer.revise.return_value = "# 第一章\n\n修订稿。"

        # 6 次评分（1 次初始 + 5 次重试），分数递增但始终不合格
        scores = [70, 72, 74, 76, 78, 79]
        runner.critic = MagicMock(spec=Critic)
        runner.critic.evaluate.side_effect = [make_evaluation(s) for s in scores]

        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.return_value = make_manager_result()

        result = runner.run_chapter("ch_001", "四人相遇")

        # 应该取最高分版本（79 分）
        assert result.evaluation.total_score == 79
        # 重试次数为 5（最后一次 attempt）
        assert result.retry_count == 5
        # Writer.revise 被调用 5 次
        assert runner.writer.revise.call_count == 5
        # Critic.evaluate 被调用 6 次
        assert runner.critic.evaluate.call_count == 6

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_max_retries_writes_file(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试达到最大重试次数后仍写入章节文件。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第一章\n\n初稿。"
        runner.writer.revise.return_value = "# 第一章\n\n修订稿。"

        # 所有评分都不合格
        runner.critic = MagicMock(spec=Critic)
        runner.critic.evaluate.side_effect = [make_evaluation(70) for _ in range(6)]

        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.return_value = make_manager_result()

        runner.run_chapter("ch_001", "四人相遇")

        # 验证章节文件仍然写入
        chapter_path = empty_project_root / "draft" / "ch_001.md"
        assert chapter_path.exists()

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_early_pass_skips_remaining_retries(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试提前合格后跳过剩余重试。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        runner.writer = MagicMock(spec=Writer)
        runner.writer.think.return_value = make_outline()
        runner.writer.write.return_value = "# 第一章\n\n初稿。"
        runner.writer.revise.return_value = "# 第一章\n\n修订稿。"

        # 第一次不合格，第二次合格
        runner.critic = MagicMock(spec=Critic)
        runner.critic.evaluate.side_effect = [make_evaluation(75), make_evaluation(85)]

        runner.manager = MagicMock(spec=Manager)
        runner.manager.update.return_value = make_manager_result()

        result = runner.run_chapter("ch_001", "四人相遇")

        assert result.retry_count == 1
        # Writer.revise 只调用 1 次
        assert runner.writer.revise.call_count == 1
        # Critic.evaluate 只调用 2 次
        assert runner.critic.evaluate.call_count == 2


# ── 辅助方法测试 ──


class TestAutoRunnerHelpers:
    """AutoRunner 辅助方法测试。"""

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_get_active_characters_empty(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试无角色文件时返回空列表。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)
        chars = runner._get_active_characters()
        assert chars == []

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_get_active_characters_with_files(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试有角色文件时返回排序后的 ID 列表。"""
        # 创建角色文件
        chars_dir = empty_project_root / "characters"
        (chars_dir / "char_002.md").write_text("---\nid: char_002\n---\n正文", encoding="utf-8")
        (chars_dir / "char_001.md").write_text("---\nid: char_001\n---\n正文", encoding="utf-8")

        runner = AutoRunner(project_root=empty_project_root, config=default_config)
        chars = runner._get_active_characters()

        assert chars == ["char_001", "char_002"]

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_get_previous_summary_first_chapter(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试第一章无前文摘要。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)
        summary = runner._get_previous_summary(0, [])
        assert summary == ""

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_get_previous_summary_with_results(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试从前一章结果获取摘要。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        prev_result = ChapterResult(
            chapter_id="ch_001",
            outline=make_outline(),
            chapter_text="正文",
            evaluation=make_evaluation(),
            retry_count=0,
            manager_summary="前一章摘要",
            word_count=100,
        )

        summary = runner._get_previous_summary(1, [prev_result])
        assert summary == "前一章摘要"

    @patch("loom.core.auto_runner.LLMBus")
    @patch("loom.core.auto_runner.Retriever")
    @patch("loom.core.auto_runner.StateManager")
    def test_get_previous_chapter_text_truncates(
        self,
        mock_sm_cls: MagicMock,
        mock_retriever_cls: MagicMock,
        mock_llm_bus_cls: MagicMock,
        empty_project_root: Path,
        default_config: LoomConfig,
    ) -> None:
        """测试前文正文超过 2000 字时截断。"""
        runner = AutoRunner(project_root=empty_project_root, config=default_config)

        long_text = "字" * 3000
        prev_result = ChapterResult(
            chapter_id="ch_001",
            outline=make_outline(),
            chapter_text=long_text,
            evaluation=make_evaluation(),
            retry_count=0,
            manager_summary="摘要",
            word_count=3000,
        )

        text = runner._get_previous_chapter_text(1, [prev_result])
        assert len(text) == 2000
