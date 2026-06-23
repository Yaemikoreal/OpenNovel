"""Writer Agent 测试 - 沉浸式创作代理（mock LLM）。"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from loom.agents.writer import Writer
from loom.schemas.outline import ChapterOutline
from loom.storage.yaml_storage import YAMLStorage

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


@pytest.fixture
def valid_outline_json() -> str:
    """合法的 ChapterOutline JSON。"""
    return json.dumps(
        {
            "chapter_id": "ch_001",
            "title": "相遇",
            "summary": "四人在废弃加油站相遇，气氛紧张。",
            "scenes": [
                {
                    "scene_id": "scene_1",
                    "description": "加油站外景，黄昏时分",
                    "characters_involved": ["char_001"],
                    "emotional_tone": "紧张",
                    "estimated_words": 800,
                },
                {
                    "scene_id": "scene_2",
                    "description": "加油站内，四人对峙",
                    "characters_involved": ["char_001", "char_002"],
                    "emotional_tone": "压抑",
                    "estimated_words": 1200,
                },
            ],
            "character_arcs": {"char_001": "从警惕到试探"},
            "key_plot_points": ["四人首次碰面", "发现地图线索"],
            "narrative_rhythm": "先慢后快，逐步升温",
            "target_words": 3000,
        },
        ensure_ascii=False,
    )


@pytest.fixture
def invalid_json_response() -> str:
    """非法 JSON（缺少逗号）。"""
    return '{"chapter_id": "ch_001" "title": "test"}'


@pytest.fixture
def empty_project_root(tmp_path: Path) -> Path:
    """临时项目根目录。"""
    root = tmp_path / "test_project"
    root.mkdir()
    (root / "draft").mkdir()
    (root / "characters").mkdir()
    (root / "outlines").mkdir()
    (root / "prompts").mkdir()
    return root


@pytest.fixture
def sample_chapter_text() -> str:
    """示例章节正文。"""
    return """# 相遇

黄昏的余晖洒在废弃加油站的屋顶上，空气中弥漫着汽油和尘土的混合气味。

李明握紧了手中的地图，目光警惕地扫视四周。远处传来了脚步声。"""


@pytest.fixture
def sample_outline() -> ChapterOutline:
    """示例 ChapterOutline 对象。"""
    return ChapterOutline(
        chapter_id="ch_001",
        title="相遇",
        summary="四人在废弃加油站相遇，气氛紧张。",
        scenes=[
            {
                "scene_id": "scene_1",
                "description": "加油站外景，黄昏时分",
                "characters_involved": ["char_001"],
                "emotional_tone": "紧张",
                "estimated_words": 800,
            },
        ],
        character_arcs={"char_001": "从警惕到试探"},
        key_plot_points=["四人首次碰面"],
        narrative_rhythm="先慢后快",
        target_words=3000,
    )


# ── Writer 初始化测试 ──


class TestWriterInit:
    """Writer 初始化测试。"""

    def test_default_prompt_path(self, empty_project_root: Path) -> None:
        """测试默认 prompt 路径指向 prompts/writer.v1.md。"""
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(llm_bus=bus, retriever=ret, project_root=empty_project_root)
        assert writer.prompt_path == Path(__file__).parent.parent / "loom" / "prompts" / "writer.v1.md"

    def test_custom_prompt_path(self, empty_project_root: Path) -> None:
        """测试自定义 prompt 路径。"""
        bus = MagicMock()
        ret = MagicMock()
        custom = empty_project_root / "custom_prompt.md"
        writer = Writer(
            llm_bus=bus, retriever=ret,
            project_root=empty_project_root, prompt_path=custom,
        )
        assert writer.prompt_path == custom

    def test_attributes_stored(self, empty_project_root: Path) -> None:
        """测试属性正确存储。"""
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(llm_bus=bus, retriever=ret, project_root=empty_project_root)
        assert writer.llm_bus is bus
        assert writer.retriever is ret
        assert writer.project_root == empty_project_root

    def test_creative_direction_stored(self, empty_project_root: Path) -> None:
        """测试创作方向参数正确存储。"""
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(
            llm_bus=bus, retriever=ret,
            project_root=empty_project_root,
            creative_direction="暗黑风格",
        )
        assert writer.creative_direction == "暗黑风格"

    def test_words_per_chapter_stored(self, empty_project_root: Path) -> None:
        """测试目标字数参数正确存储。"""
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(
            llm_bus=bus, retriever=ret,
            project_root=empty_project_root,
            words_per_chapter=5000,
        )
        assert writer.words_per_chapter == 5000


# ── Writer 思考阶段测试 ──


class TestWriterThink:
    """Writer.think 思考阶段测试。"""

    def test_think_returns_chapter_outline(
        self, empty_project_root: Path, valid_outline_json: str
    ) -> None:
        """测试思考阶段返回 ChapterOutline 结构。"""
        llm_bus = MockLLMBus([valid_outline_json])
        ret = MagicMock()
        ret.query_canon.return_value = "魔法世界观设定"

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        outline = writer.think("ch_001", "四人在加油站相遇")

        assert isinstance(outline, ChapterOutline)
        assert outline.chapter_id == "ch_001"
        assert outline.title == "相遇"
        assert len(outline.scenes) == 2
        assert outline.target_words == 3000

    def test_think_calls_retriever_canon(
        self, empty_project_root: Path, valid_outline_json: str
    ) -> None:
        """测试思考阶段调用 retriever.query_canon()。"""
        llm_bus = MockLLMBus([valid_outline_json])
        ret = MagicMock()
        ret.query_canon.return_value = "设定内容"

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        writer.think("ch_001", "大纲提示")

        ret.query_canon.assert_called_once_with("大纲提示", top_k=3)

    def test_think_passes_messages_to_llm(
        self, empty_project_root: Path, valid_outline_json: str
    ) -> None:
        """测试思考阶段将消息列表传给 LLM。"""
        llm_bus = MockLLMBus([valid_outline_json])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        writer.think("ch_001", "大纲提示")

        call_args = llm_bus.last_messages
        assert isinstance(call_args, list)
        assert len(call_args) >= 2
        assert all("role" in m and "content" in m for m in call_args)

    def test_think_with_markdown_code_block(
        self, empty_project_root: Path
    ) -> None:
        """测试 LLM 返回被 markdown 代码块包裹的 JSON。"""
        outline_json = """```json
{
    "chapter_id": "ch_001",
    "title": "相遇",
    "summary": "四人在加油站相遇。",
    "scenes": [
        {
            "scene_id": "scene_1",
            "description": "加油站外景",
            "characters_involved": ["char_001"],
            "emotional_tone": "紧张",
            "estimated_words": 800
        }
    ],
    "character_arcs": {"char_001": "从警惕到试探"},
    "key_plot_points": ["首次碰面"],
    "narrative_rhythm": "先慢后快",
    "target_words": 3000
}
```"""
        llm_bus = MockLLMBus([outline_json])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        outline = writer.think("ch_001", "大纲提示")

        assert isinstance(outline, ChapterOutline)
        assert outline.title == "相遇"


# ── Writer 思考重试测试 ──


class TestWriterThinkRetry:
    """Writer.think JSON 解析失败重试测试。"""

    def test_retry_then_success(
        self, empty_project_root: Path, valid_outline_json: str, invalid_json_response: str
    ) -> None:
        """测试第一次 JSON 解析失败后重试成功。"""
        llm_bus = MockLLMBus([invalid_json_response, valid_outline_json])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        outline = writer.think("ch_001", "大纲提示")

        assert isinstance(outline, ChapterOutline)
        assert llm_bus.call_count == 2

    def test_all_retries_fail_raises_runtime_error(
        self, empty_project_root: Path, invalid_json_response: str
    ) -> None:
        """测试所有重试都失败后抛出 RuntimeError。"""
        llm_bus = MockLLMBus([
            invalid_json_response,
            invalid_json_response,
            invalid_json_response,
        ])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        with pytest.raises(RuntimeError, match="Writer 思考失败"):
            writer.think("ch_001", "大纲提示")
        assert llm_bus.call_count == 3

    def test_empty_text_retry(
        self, empty_project_root: Path, valid_outline_json: str
    ) -> None:
        """测试 LLM 返回空文本后重试成功。"""
        llm_bus = MockLLMBus(["", valid_outline_json])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        outline = writer.think("ch_001", "大纲提示")

        assert isinstance(outline, ChapterOutline)
        assert llm_bus.call_count == 2


# ── Writer 创作阶段测试 ──


class TestWriterWrite:
    """Writer.write 创作阶段测试。"""

    def test_write_returns_text(
        self, empty_project_root: Path, sample_outline: ChapterOutline, sample_chapter_text: str
    ) -> None:
        """测试创作阶段返回生成文本。"""
        llm_bus = MockLLMBus([sample_chapter_text])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        result = writer.write("ch_001", sample_outline)

        assert result == sample_chapter_text
        assert llm_bus.call_count == 1

    def test_write_passes_messages_to_llm(
        self, empty_project_root: Path, sample_outline: ChapterOutline
    ) -> None:
        """测试创作阶段将消息列表传给 LLM。"""
        llm_bus = MockLLMBus(["生成的正文内容"])
        ret = MagicMock()
        ret.query_canon.return_value = "设定"

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        writer.write("ch_001", sample_outline, previous_chapter_text="前文内容")

        call_args = llm_bus.last_messages
        assert isinstance(call_args, list)
        assert len(call_args) >= 2
        assert all("role" in m and "content" in m for m in call_args)

    def test_write_with_previous_chapter(
        self, empty_project_root: Path, sample_outline: ChapterOutline
    ) -> None:
        """测试创作阶段传入前一章正文。"""
        llm_bus = MockLLMBus(["新章节内容"])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        result = writer.write("ch_001", sample_outline, previous_chapter_text="前一章结尾")

        assert result == "新章节内容"

    def test_write_empty_text_raises_error(
        self, empty_project_root: Path, sample_outline: ChapterOutline
    ) -> None:
        """测试 LLM 返回空文本时抛出 RuntimeError。"""
        llm_bus = MockLLMBus([""])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        with pytest.raises(RuntimeError, match="Writer 创作返回空文本"):
            writer.write("ch_001", sample_outline)


# ── Writer 修订阶段测试 ──


class TestWriterRevise:
    """Writer.revise 修订阶段测试。"""

    def test_revise_returns_text(
        self, empty_project_root: Path, sample_outline: ChapterOutline
    ) -> None:
        """测试修订阶段返回修订后的文本。"""
        revised_text = "# 相遇\n\n修订后的正文内容。"
        llm_bus = MockLLMBus([revised_text])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        result = writer.revise(
            "ch_001", sample_outline,
            current_text="原始正文",
            feedback="角色对话需要更自然",
        )

        assert result == revised_text
        assert llm_bus.call_count == 1

    def test_revise_passes_feedback_to_llm(
        self, empty_project_root: Path, sample_outline: ChapterOutline
    ) -> None:
        """测试修订阶段将反馈传给 LLM。"""
        llm_bus = MockLLMBus(["修订后的内容"])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        writer.revise(
            "ch_001", sample_outline,
            current_text="原始正文",
            feedback="情节转折太突兀",
        )

        # 验证消息中包含反馈内容
        user_messages = [m for m in llm_bus.last_messages if m["role"] == "user"]
        feedback_found = any("情节转折太突兀" in m["content"] for m in user_messages)
        assert feedback_found

    def test_revise_empty_text_raises_error(
        self, empty_project_root: Path, sample_outline: ChapterOutline
    ) -> None:
        """测试 LLM 返回空文本时抛出 RuntimeError。"""
        llm_bus = MockLLMBus([""])
        ret = MagicMock()
        ret.query_canon.return_value = ""

        writer = Writer(
            llm_bus=llm_bus,  # type: ignore[arg-type]
            retriever=ret,
            project_root=empty_project_root,
        )
        with pytest.raises(RuntimeError, match="Writer 修订返回空文本"):
            writer.revise(
                "ch_001", sample_outline,
                current_text="原始正文",
                feedback="需要修改",
            )


# ── Writer Prompt 加载测试 ──


class TestWriterLoadPrompt:
    """Writer._load_prompt Prompt 加载测试。"""

    def test_load_prompt_fallback_when_missing(self, empty_project_root: Path) -> None:
        """测试 Prompt 文件不存在时返回默认文本。"""
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(
            llm_bus=bus, retriever=ret,
            project_root=empty_project_root,
            prompt_path=empty_project_root / "nonexistent.md",
        )
        prompt = writer._load_prompt()
        assert "小说创作者" in prompt

    def test_load_prompt_from_file(self, empty_project_root: Path) -> None:
        """测试从文件加载 Prompt。"""
        prompt_path = empty_project_root / "writer.v1.md"
        prompt_path.write_text("你是自定义写作代理。", encoding="utf-8")
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(
            llm_bus=bus, retriever=ret,
            project_root=empty_project_root,
            prompt_path=prompt_path,
        )
        prompt = writer._load_prompt()
        assert "自定义写作代理" in prompt


# ── Writer 解析逻辑测试 ──


class TestWriterParseOutline:
    """Writer._parse_outline_from_text 解析逻辑测试。"""

    def test_parse_valid_json(self, empty_project_root: Path) -> None:
        """测试解析合法 JSON。"""
        text = json.dumps(
            {
                "chapter_id": "ch_001",
                "title": "测试",
                "summary": "测试概要",
                "scenes": [
                    {
                        "scene_id": "scene_1",
                        "description": "场景描述",
                        "characters_involved": ["char_001"],
                        "emotional_tone": "平静",
                        "estimated_words": 500,
                    }
                ],
                "character_arcs": {},
                "key_plot_points": [],
                "narrative_rhythm": "平缓",
                "target_words": 1000,
            },
            ensure_ascii=False,
        )
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(llm_bus=bus, retriever=ret, project_root=empty_project_root)

        outline = writer._parse_outline_from_text(text, "ch_001")
        assert isinstance(outline, ChapterOutline)
        assert outline.chapter_id == "ch_001"

    def test_parse_json_with_markdown_block(self, empty_project_root: Path) -> None:
        """测试解析被 markdown 代码块包裹的 JSON。"""
        text = """```json
{"chapter_id": "ch_001", "title": "test", "summary": "测试概要", "scenes": [{"scene_id": "s1", "description": "d", "characters_involved": ["char_001"], "emotional_tone": "t", "estimated_words": 100}], "character_arcs": {}, "key_plot_points": [], "narrative_rhythm": "r", "target_words": 1000}
```"""
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(llm_bus=bus, retriever=ret, project_root=empty_project_root)

        outline = writer._parse_outline_from_text(text, "ch_001")
        assert isinstance(outline, ChapterOutline)

    def test_parse_invalid_json_raises(self, empty_project_root: Path) -> None:
        """测试非法 JSON 抛出异常。"""
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(llm_bus=bus, retriever=ret, project_root=empty_project_root)

        with pytest.raises(json.JSONDecodeError):
            writer._parse_outline_from_text("{broken json}", "ch_001")

    def test_parse_missing_required_field_raises(self, empty_project_root: Path) -> None:
        """测试缺少必填字段时抛出 ValidationError。"""
        text = '{"chapter_id": "ch_001"}'
        bus = MagicMock()
        ret = MagicMock()
        writer = Writer(llm_bus=bus, retriever=ret, project_root=empty_project_root)

        with pytest.raises(Exception):
            writer._parse_outline_from_text(text, "ch_001")
