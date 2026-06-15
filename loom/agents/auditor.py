"""Auditor 代理 - 状态审阅与提取代理人格。

Auditor 是 L.O.O.M. 的"审稿官"，核心职责：
- 分析正文，提取结构化事件（伤势、物品、情绪变化等）
- 强制输出 JSON 格式的事件列表，经 Pydantic 校验
- 生成 Diff 供人工审阅
- 绝不直接写入状态，必须经过人工确认

铁律 3：AI 只能提议状态变更，人类拥有绝对否决权。
"""

import json
import logging
from pathlib import Path
from typing import Optional

from loom.core.llm import LLMBus, extract_text_from_response
from loom.core.state_manager import StateManager
from loom.schemas.event import EventCreate, EventDiff

logger = logging.getLogger(__name__)


class Auditor:
    """Auditor 代理 - 状态审阅与提取引擎。

    使用方式:
        auditor = Auditor(llm_bus=bus, state_manager=sm, project_root=root)
        events = auditor.extract_events(chapter_path, chapter_text)
        diffs = auditor.generate_diffs(events)
        # 展示 diffs 给用户审阅
        auditor.apply_confirmed_events(confirmed_events)
    """

    def __init__(
        self,
        llm_bus: LLMBus,
        state_manager: StateManager,
        project_root: Path,
        prompt_path: Optional[Path] = None,
    ) -> None:
        """初始化 Auditor 代理。

        Args:
            llm_bus: LLM 调用总线实例
            state_manager: 状态管理器实例
            project_root: 项目根目录路径
            prompt_path: Auditor 人格 Prompt 文件路径
        """
        self.llm_bus = llm_bus
        self.state_manager = state_manager
        self.project_root = project_root
        self.prompt_path = prompt_path or project_root / "prompts" / "auditor.v1.md"

    def _load_prompt(self) -> str:
        """加载 Auditor 人格 Prompt。

        Returns:
            Prompt 文本内容
        """
        if not self.prompt_path.exists():
            logger.warning("Auditor Prompt 文件不存在: %s", self.prompt_path)
            return "你是一个叙事状态审计员。分析正文，提取结构化事件。"
        return self.prompt_path.read_text(encoding="utf-8")

    def extract_events(
        self,
        chapter_id: str,
        chapter_text: str,
        active_characters: Optional[list[str]] = None,
    ) -> list[EventCreate]:
        """从正文中提取结构化事件。

        将正文发送给 LLM，要求输出 JSON 格式的事件列表，
        然后用 Pydantic 校验格式，不符合则打回重试。

        Args:
            chapter_id: 章节 ID
            chapter_text: 章节正文
            active_characters: 活跃角色 ID 列表

        Returns:
            提取到的事件列表（未经人工确认）
        """
        prompt = self._load_prompt()
        characters_info = ""
        if active_characters:
            characters_info = f"活跃角色 ID: {', '.join(active_characters)}"

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"章节 ID: {chapter_id}\n"
                    f"{characters_info}\n\n"
                    f"正文内容:\n{chapter_text}\n\n"
                    f"请提取所有状态变更事件，输出 JSON 数组。"
                ),
            },
        ]

        response = self.llm_bus.chat(messages, temperature=0.3)
        text = extract_text_from_response(response)

        return self._parse_events_from_text(text, chapter_id)

    def _parse_events_from_text(
        self, text: str, chapter_id: str
    ) -> list[EventCreate]:
        """解析 LLM 输出的 JSON 事件列表。

        若 JSON 格式不符 EventCreate 模型，直接打回。

        Args:
            text: LLM 输出的文本
            chapter_id: 章节 ID（用于补充缺失字段）

        Returns:
            校验通过的事件列表
        """
        events: list[EventCreate] = []

        # 尝试从文本中提取 JSON
        try:
            # 清理可能的 markdown 代码块标记
            cleaned = text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            raw_events = json.loads(cleaned)
            if not isinstance(raw_events, list):
                raw_events = [raw_events]

            for raw in raw_events:
                try:
                    # 确保 chapter_id 一致
                    raw.setdefault("chapter_id", chapter_id)
                    event = EventCreate(**raw)
                    events.append(event)
                except Exception as e:
                    logger.warning("事件校验失败，跳过: %s, 错误: %s", raw, e)

        except json.JSONDecodeError as e:
            logger.error("LLM 输出非合法 JSON，提取失败: %s", e)

        return events

    def generate_diffs(self, events: list[EventCreate]) -> list[EventDiff]:
        """将提取的事件转换为 Diff 格式，用于终端展示。

        Args:
            events: 提取到的事件列表

        Returns:
            事件变更 Diff 列表
        """
        return [EventDiff(action="add", event=event) for event in events]

    def apply_confirmed_events(
        self, events: list[EventCreate], chapter_id: str
    ) -> list[str]:
        """将经过人工确认的事件写入状态。

        Args:
            events: 人工确认后的事件列表
            chapter_id: 章节 ID

        Returns:
            写入的事件 ID 列表
        """
        event_ids: list[str] = []
        for event in events:
            self.state_manager.apply_event(event)
            event_ids.append(event.event_id)
        return event_ids
