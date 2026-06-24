"""Writer Agent - 沉浸式创作代理。

负责思考规划（输出结构化大纲）和文学创作（输出章节正文）。
两阶段工作流: think → write/revise。
"""

import json
import logging
from pathlib import Path

from opennovel.core.context_assembler import ContextStrategy, assemble_context
from opennovel.core.llm import LLMBus
from opennovel.core.retriever import Retriever
from opennovel.schemas.outline import ChapterOutline
from opennovel.storage.sqlite import EventStore

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class Writer:
    """Writer Agent — 小说创作代理。

    使用方式:
        writer = Writer(llm_bus=llm_bus, retriever=retriever, project_root=project_root)
        outline = writer.think("ch_001", "四人在加油站相遇", previous_summary="")
        chapter_text = writer.write("ch_001", outline, previous_chapter_text="")
    """

    def __init__(
        self,
        llm_bus: LLMBus,
        retriever: Retriever,
        project_root: Path,
        prompt_path: Path | None = None,
        creative_direction: str = "",
        words_per_chapter: int = 3000,
        event_store: EventStore | None = None,
    ) -> None:
        self.llm_bus = llm_bus
        self.retriever = retriever
        self.project_root = project_root
        self.prompt_path = prompt_path or (
            Path(__file__).parent.parent / "prompts" / "writer.v1.md"
        )
        self.creative_direction = creative_direction
        self.words_per_chapter = words_per_chapter
        self.event_store = event_store

    def _load_prompt(self) -> str:
        """加载 Writer Prompt，文件不存在时返回硬编码兜底。"""
        if not self.prompt_path.exists():
            logger.warning("Writer Prompt 文件不存在: %s", self.prompt_path)
            return "你是一位专业的小说创作者。根据大纲和角色状态进行创作。"
        return self.prompt_path.read_text(encoding="utf-8")

    def _build_context(
        self,
        task_message: str,
    ) -> list[dict[str, str]]:
        """通过 ContextAssembler 组装完整上下文（CANON + STATE + SUBCONSCIOUS + 任务）。

        Args:
            task_message: 任务指令（大纲/创作/修订等）

        Returns:
            组装完成的消息列表
        """
        canon_content = self.retriever.query_canon(task_message[:500], top_k=3)
        subconscious_content = self.retriever.query_subconscious(task_message[:500], top_k=2)

        # 从 EventStore 获取近期高压力事件摘要
        event_summary = ""
        if self.event_store:
            high_events = self.event_store.get_high_pressure_events(threshold=0.5)
            if high_events:
                event_lines = [
                    f"- [{e.event_type}] {e.description} (pressure={e.causal_pressure})"
                    for e in high_events[-10:]  # 最近 10 条
                ]
                event_summary = "\n".join(event_lines)

        if event_summary:
            task_message = f"### 近期高因果压力事件\n{event_summary}\n\n{task_message}"

        return assemble_context(
            project_root=self.project_root,
            task_message=task_message,
            prompt_path=self.prompt_path,
            canon_content=canon_content,
            subconscious_content=subconscious_content,
            strategy=ContextStrategy.STANDARD,
        )

    def _build_think_task_message(
        self,
        chapter_id: str,
        chapter_outline_hint: str,
        previous_summary: str,
    ) -> str:
        """构建思考阶段的任务消息（不含设定/状态，由 ContextAssembler 注入）。"""
        return f"""## 思考任务

请为章节 `{chapter_id}` 进行深度思考规划，输出结构化 JSON 大纲。

### 大纲提示
{chapter_outline_hint}

### 创作方向
{self.creative_direction or "无特殊要求"}

### 目标字数
{self.words_per_chapter} 字

### 前文摘要
{previous_summary or "这是第一章，无前文"}

请输出合法的 JSON 对象，格式如下：
{{
  "chapter_id": "{chapter_id}",
  "title": "章节标题",
  "summary": "本章概要（200字以内）",
  "scenes": [
    {{
      "scene_id": "scene_1",
      "description": "场景描述",
      "characters_involved": ["char_001"],
      "emotional_tone": "情绪基调",
      "estimated_words": 800
    }}
  ],
  "character_arcs": {{"char_001": "情绪变化描述"}},
  "key_plot_points": ["关键情节节点"],
  "narrative_rhythm": "叙事节奏描述",
  "target_words": {self.words_per_chapter}
}}"""

    def _build_write_task_message(
        self,
        chapter_id: str,
        outline: ChapterOutline,
        previous_chapter_text: str,
        feedback: str = "",
    ) -> str:
        """构建创作阶段的任务消息（不含设定/状态，由 ContextAssembler 注入）。"""
        scenes_text = "\n".join(
            f"- 场景 {s.scene_id}: {s.description} ({s.estimated_words}字, {s.emotional_tone})"
            for s in outline.scenes
        )
        arcs_text = "\n".join(f"- {cid}: {desc}" for cid, desc in outline.character_arcs.items())
        plot_text = "\n".join(f"- {p}" for p in outline.key_plot_points)

        revise_note = ""
        if feedback:
            # 检测是否为锚定反馈（包含原文引用）
            if "原文:" in feedback:
                revise_note = f"""

### 修订反馈（精确修改指引）
{feedback}

请根据以上定位指引精确修改：
1. 先在正文中找到「原文」引用的位置
2. 针对性地修改该段落，不要重写全章
3. 保持已有优点，只修正标注的问题"""
            else:
                revise_note = f"""

### 修订反馈（请针对性修改以下问题）
{feedback}
请在保持已有优点的基础上，针对上述问题进行修改。不要重写全章。"""

        prev_text = (
            previous_chapter_text[-2000:] if previous_chapter_text else "这是第一章，请从头开始"
        )

        return f"""## 创作任务

请根据以下大纲创作章节 `{chapter_id}` 的正文。

### 章节大纲
- 标题: {outline.title}
- 概要: {outline.summary}
- 目标字数: {outline.target_words}
- 叙事节奏: {outline.narrative_rhythm}

### 场景分解
{scenes_text}

### 角色情绪弧线
{arcs_text}

### 关键情节节点
{plot_text}

### 创作方向
{self.creative_direction or "无特殊要求"}

### 前文结尾
{prev_text}{revise_note}

请直接输出小说正文，不要输出任何元数据、注释或解释。以 `# {outline.title}` 作为开头。"""

    def _parse_outline_from_text(self, text: str, chapter_id: str) -> ChapterOutline:
        """从 LLM 输出中解析 ChapterOutline JSON。"""
        # 清理 markdown 代码块标记
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)
        data["chapter_id"] = chapter_id
        return ChapterOutline(**data)

    def think(
        self,
        chapter_id: str,
        chapter_outline_hint: str,
        previous_summary: str = "",
    ) -> ChapterOutline:
        """思考规划阶段：分析要素，输出结构化大纲。

        Args:
            chapter_id: 章节 ID (如 "ch_001")
            chapter_outline_hint: 大纲文件中本章的描述
            previous_summary: 前一章的摘要

        Returns:
            ChapterOutline 结构化大纲
        """
        task_message = self._build_think_task_message(
            chapter_id,
            chapter_outline_hint,
            previous_summary,
        )
        messages = self._build_context(task_message)

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.llm_bus.chat(messages, temperature=0.7)
                text = response.choices[0].message.content
                if not text:
                    raise ValueError("LLM 返回空文本")
                outline = self._parse_outline_from_text(text, chapter_id)
                logger.info("Writer 思考完成: %s, %d 个场景", chapter_id, len(outline.scenes))
                return outline
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                last_error = e
                logger.warning(
                    "Writer 思考 JSON 解析失败 (尝试 %d/%d): %s", attempt + 1, MAX_RETRIES + 1, e
                )
                if attempt < MAX_RETRIES:
                    messages.append(
                        {"role": "assistant", "content": text if "text" in dir() else ""}
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"你的输出 JSON 格式有误: {e}\n请重新输出合法的 JSON 对象。",
                        }
                    )

        raise RuntimeError(f"Writer 思考失败，已重试 {MAX_RETRIES} 次: {last_error}")

    def think_variations(
        self,
        chapter_id: str,
        chapter_outline_hint: str,
        previous_summary: str = "",
        n_variants: int = 3,
        variation_mode: str = "exploratory",
        corrective_feedback: str = "",
    ) -> list[ChapterOutline]:
        """盲目变异：生成多个叙事方向的大纲方案。

        探索型变异：不同 temperature 生成多样化方向。
        纠错型变异：将 Critic 反馈作为负向约束注入。

        Args:
            chapter_id: 章节 ID
            chapter_outline_hint: 大纲文件中本章的描述
            previous_summary: 前一章的摘要
            n_variants: 生成方案数量
            variation_mode: "exploratory"（探索型）或 "corrective"（纠错型）
            corrective_feedback: 纠错模式下的 Critic 反馈

        Returns:
            大纲方案列表（长度 = n_variants）
        """
        temperatures = [0.5, 0.7, 0.9][:n_variants]
        # 补齐温度列表
        while len(temperatures) < n_variants:
            temperatures.append(temperatures[-1] + 0.2)

        direction_hints = [
            "请尝试一个出人意料的叙事方向，打破读者预期。",
            "请尝试一个以角色内心成长为核心的叙事方向。",
            "请尝试一个以世界观揭示或秘密揭露为核心的叙事方向。",
        ]

        outlines: list[ChapterOutline] = []
        for i in range(n_variants):
            # 构建任务消息
            task_message = self._build_think_task_message(
                chapter_id,
                chapter_outline_hint,
                previous_summary,
            )

            # 探索型：添加方向提示
            if variation_mode == "exploratory":
                hint = direction_hints[i % len(direction_hints)]
                task_message += f"\n\n### 创作方向提示（方案 {i + 1}）\n{hint}"

            # 纠错型：注入负向约束
            if variation_mode == "corrective" and corrective_feedback:
                task_message += (
                    f"\n\n### 前章问题（请在本方案中避免以下问题）\n"
                    f"{corrective_feedback}\n"
                    f"请尝试一种与前章不同的修复策略。"
                )

            messages = self._build_context(task_message)

            last_error = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    response = self.llm_bus.chat(
                        messages,
                        temperature=temperatures[i],
                    )
                    text = response.choices[0].message.content
                    if not text:
                        raise ValueError("LLM 返回空文本")
                    outline = self._parse_outline_from_text(text, chapter_id)
                    outlines.append(outline)
                    logger.info(
                        "Writer 变异方案 %d/%d: %s, %d 个场景 (T=%.1f)",
                        i + 1,
                        n_variants,
                        chapter_id,
                        len(outline.scenes),
                        temperatures[i],
                    )
                    break
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    last_error = e
                    logger.warning(
                        "Writer 变异方案 %d 解析失败 (尝试 %d/%d): %s",
                        i + 1,
                        attempt + 1,
                        MAX_RETRIES + 1,
                        e,
                    )
                    if attempt < MAX_RETRIES:
                        messages.append(
                            {"role": "assistant", "content": text if "text" in dir() else ""}
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"你的输出 JSON 格式有误: {e}\n请重新输出合法的 JSON 对象。"
                                ),
                            }
                        )
            else:
                raise RuntimeError(
                    f"Writer 变异方案 {i + 1} 失败，已重试 {MAX_RETRIES} 次: {last_error}"
                )

        return outlines

    def write(
        self,
        chapter_id: str,
        outline: ChapterOutline,
        previous_chapter_text: str = "",
    ) -> str:
        """创作阶段：根据大纲创作章节正文。

        Args:
            chapter_id: 章节 ID
            outline: 思考阶段输出的大纲
            previous_chapter_text: 前一章正文

        Returns:
            章节正文 (纯文本)
        """
        task_message = self._build_write_task_message(
            chapter_id,
            outline,
            previous_chapter_text,
        )
        messages = self._build_context(task_message)

        response = self.llm_bus.chat(messages, temperature=0.8, max_tokens=4000)
        text = response.choices[0].message.content
        if not text:
            raise RuntimeError("Writer 创作返回空文本")

        logger.info("Writer 创作完成: %s, %d 字", chapter_id, len(text))
        return text.strip()

    def revise(
        self,
        chapter_id: str,
        outline: ChapterOutline,
        current_text: str,
        feedback: str,
    ) -> str:
        """修订阶段：根据 Critic 反馈修改章节。

        Args:
            chapter_id: 章节 ID
            outline: 原始大纲
            current_text: 当前章节正文
            feedback: Critic 的反馈

        Returns:
            修订后的章节正文
        """
        task_message = self._build_write_task_message(
            chapter_id,
            outline,
            "",
            feedback=feedback,
        )
        messages = self._build_context(task_message)

        # 追加当前正文供修订
        messages.append(
            {
                "role": "user",
                "content": f"以下是当前章节正文，请根据上面的反馈进行修订：\n\n{current_text}",
            }
        )

        response = self.llm_bus.chat(messages, temperature=0.7, max_tokens=4000)
        text = response.choices[0].message.content
        if not text:
            raise RuntimeError("Writer 修订返回空文本")

        logger.info("Writer 修订完成: %s, %d 字", chapter_id, len(text))
        return text.strip()
