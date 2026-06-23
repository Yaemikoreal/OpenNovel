"""Writer Agent - 沉浸式创作代理。

负责思考规划（输出结构化大纲）和文学创作（输出章节正文）。
两阶段工作流: think → write/revise。
"""

import json
import logging
from pathlib import Path

from loom.core.llm import LLMBus
from loom.core.retriever import Retriever
from loom.schemas.outline import ChapterOutline

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
    ) -> None:
        self.llm_bus = llm_bus
        self.retriever = retriever
        self.project_root = project_root
        self.prompt_path = prompt_path or (
            Path(__file__).parent.parent / "prompts" / "writer.v1.md"
        )
        self.creative_direction = creative_direction
        self.words_per_chapter = words_per_chapter

    def _load_prompt(self) -> str:
        """加载 Writer Prompt，文件不存在时返回硬编码兜底。"""
        if not self.prompt_path.exists():
            logger.warning("Writer Prompt 文件不存在: %s", self.prompt_path)
            return "你是一位专业的小说创作者。根据大纲和角色状态进行创作。"
        return self.prompt_path.read_text(encoding="utf-8")

    def _build_think_messages(
        self,
        chapter_id: str,
        chapter_outline_hint: str,
        previous_summary: str,
        canon_content: str,
        state_content: str,
    ) -> list[dict[str, str]]:
        """组装思考阶段的消息列表。"""
        prompt = self._load_prompt()

        user_content = f"""## 思考任务

请为章节 `{chapter_id}` 进行深度思考规划，输出结构化 JSON 大纲。

### 大纲提示
{chapter_outline_hint}

### 创作方向
{self.creative_direction or "无特殊要求"}

### 目标字数
{self.words_per_chapter} 字

### 世界观设定
{canon_content or "无"}

### 角色当前状态
{state_content or "无"}

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

        return [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ]

    def _build_write_messages(
        self,
        chapter_id: str,
        outline: ChapterOutline,
        previous_chapter_text: str,
        canon_content: str,
        state_content: str,
        feedback: str = "",
    ) -> list[dict[str, str]]:
        """组装创作阶段的消息列表。"""
        prompt = self._load_prompt()

        scenes_text = "\n".join(
            f"- 场景 {s.scene_id}: {s.description} ({s.estimated_words}字, {s.emotional_tone})"
            for s in outline.scenes
        )
        arcs_text = "\n".join(
            f"- {cid}: {desc}" for cid, desc in outline.character_arcs.items()
        )
        plot_text = "\n".join(f"- {p}" for p in outline.key_plot_points)

        revise_note = ""
        if feedback:
            revise_note = f"""

### 修订反馈（请针对性修改以下问题）
{feedback}
请在保持已有优点的基础上，针对上述问题进行修改。不要重写全章。"""

        user_content = f"""## 创作任务

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

### 世界观设定
{canon_content or "无"}

### 角色当前状态
{state_content or "无"}

### 前文结尾
{previous_chapter_text[-2000:] if previous_chapter_text else "这是第一章，请从头开始"}{revise_note}

请直接输出小说正文，不要输出任何元数据、注释或解释。以 `# {outline.title}` 作为开头。"""

        return [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ]

    def _parse_outline_from_text(self, text: str, chapter_id: str) -> ChapterOutline:
        """从 LLM 输出中解析 ChapterOutline JSON。"""
        # 清理 markdown 代码块标记
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
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
        # 获取 CANON 和角色状态
        canon_content = self.retriever.query_canon(chapter_outline_hint, top_k=3)
        state_content = self._get_state_summary()

        messages = self._build_think_messages(
            chapter_id, chapter_outline_hint, previous_summary,
            canon_content, state_content,
        )

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
                logger.warning("Writer 思考 JSON 解析失败 (尝试 %d/%d): %s",
                               attempt + 1, MAX_RETRIES + 1, e)
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": text if 'text' in dir() else ""})
                    messages.append({
                        "role": "user",
                        "content": f"你的输出 JSON 格式有误: {e}\n请重新输出合法的 JSON 对象。",
                    })

        raise RuntimeError(f"Writer 思考失败，已重试 {MAX_RETRIES} 次: {last_error}")

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
        canon_content = self.retriever.query_canon(outline.summary, top_k=3)
        state_content = self._get_state_summary()

        messages = self._build_write_messages(
            chapter_id, outline, previous_chapter_text,
            canon_content, state_content,
        )

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
        canon_content = self.retriever.query_canon(outline.summary, top_k=3)
        state_content = self._get_state_summary()

        messages = self._build_write_messages(
            chapter_id, outline, "",
            canon_content, state_content,
            feedback=feedback,
        )

        # 追加当前正文供修订
        messages.append({
            "role": "user",
            "content": f"以下是当前章节正文，请根据上面的反馈进行修订：\n\n{current_text}",
        })

        response = self.llm_bus.chat(messages, temperature=0.7, max_tokens=4000)
        text = response.choices[0].message.content
        if not text:
            raise RuntimeError("Writer 修订返回空文本")

        logger.info("Writer 修订完成: %s, %d 字", chapter_id, len(text))
        return text.strip()

    def _get_state_summary(self) -> str:
        """获取所有角色当前状态的文本摘要。"""
        from loom.storage.yaml_storage import YAMLStorage

        storage = YAMLStorage()
        chars_dir = self.project_root / "characters"
        if not chars_dir.exists():
            return ""

        summaries = []
        for char_file in sorted(chars_dir.glob("char_*.md")):
            try:
                char = storage.read_character_file(char_file)
                fm = char.frontmatter
                summary_parts = [
                    f"角色: {fm.name} (ID: {fm.id})",
                    f"  位置: {fm.location or '未知'}",
                    f"  情绪: 悲伤={fm.emotional.grief} 愤怒={fm.emotional.anger} "
                    f"恐惧={fm.emotional.fear} 快乐={fm.emotional.joy} "
                    f"决心={fm.emotional.determination}",
                    f"  物品: {', '.join(fm.inventory) if fm.inventory else '无'}",
                ]
                if fm.physical.injuries:
                    summary_parts.append(f"  伤势: {', '.join(fm.physical.injuries)}")
                summaries.append("\n".join(summary_parts))
            except Exception as e:
                logger.warning("读取角色文件失败 %s: %s", char_file, e)

        return "\n\n".join(summaries)
