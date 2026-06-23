"""Critic Agent - 文学评判代理。

负责对 Writer 产出的章节进行五维百分制评分。
80 分以上合格，90 分以上优秀。
"""

import json
import logging
from pathlib import Path

from loom.core.llm import LLMBus
from loom.schemas.evaluation import ChapterEvaluation
from loom.schemas.outline import ChapterOutline

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class Critic:
    """Critic Agent — 文学评判员。

    使用方式:
        critic = Critic(llm_bus=llm_bus, project_root=project_root)
        evaluation = critic.evaluate("ch_001", chapter_text, outline)
        if evaluation.is_pass:
            print(f"合格! {evaluation.total_score} 分")
    """

    def __init__(
        self,
        llm_bus: LLMBus,
        project_root: Path,
        prompt_path: Path | None = None,
    ) -> None:
        self.llm_bus = llm_bus
        self.project_root = project_root
        self.prompt_path = prompt_path or (
            Path(__file__).parent.parent / "prompts" / "critic.v1.md"
        )

    def _load_prompt(self) -> str:
        """加载 Critic Prompt，文件不存在时返回硬编码兜底。"""
        if not self.prompt_path.exists():
            logger.warning("Critic Prompt 文件不存在: %s", self.prompt_path)
            return "你是一位文学评判员。对章节进行百分制评分。"
        return self.prompt_path.read_text(encoding="utf-8")

    def _build_messages(
        self,
        chapter_id: str,
        chapter_text: str,
        outline: ChapterOutline,
    ) -> list[dict[str, str]]:
        """组装评分消息列表。"""
        prompt = self._load_prompt()

        scenes_text = "\n".join(
            f"- {s.scene_id}: {s.description} ({s.emotional_tone})"
            for s in outline.scenes
        )

        user_content = f"""## 评分任务

请对章节 `{chapter_id}` 进行专业评分。

### 章节大纲 (参考标准)
- 标题: {outline.title}
- 概要: {outline.summary}
- 场景分解:
{scenes_text}
- 叙事节奏: {outline.narrative_rhythm}

### 章节正文

{chapter_text}

请按照五维评分标准（文笔质量20分 + 情节逻辑20分 + 角色一致性20分 + 节奏把控20分 + 情感表达20分 = 100分）进行评分。

输出合法的 JSON 对象：
{{
  "total_score": 85,
  "dimensions": [
    {{"dimension": "文笔质量", "score": 18, "comment": "评语"}},
    {{"dimension": "情节逻辑", "score": 17, "comment": "评语"}},
    {{"dimension": "角色一致性", "score": 17, "comment": "评语"}},
    {{"dimension": "节奏把控", "score": 16, "comment": "评语"}},
    {{"dimension": "情感表达", "score": 17, "comment": "评语"}}
  ],
  "summary": "总体评价",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}}"""

        return [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ]

    def _parse_evaluation_from_text(self, text: str) -> ChapterEvaluation:
        """从 LLM 输出中解析 ChapterEvaluation JSON。"""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)
        return ChapterEvaluation(**data)

    def evaluate(
        self,
        chapter_id: str,
        chapter_text: str,
        outline: ChapterOutline,
    ) -> ChapterEvaluation:
        """评估章节质量。

        Args:
            chapter_id: 章节 ID
            chapter_text: 章节正文
            outline: 章节大纲 (评分参考)

        Returns:
            ChapterEvaluation 评分结果
        """
        messages = self._build_messages(chapter_id, chapter_text, outline)

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.llm_bus.chat(messages, temperature=0.2)
                text = response.choices[0].message.content
                if not text:
                    raise ValueError("LLM 返回空文本")
                evaluation = self._parse_evaluation_from_text(text)
                logger.info(
                    "Critic 评分完成: %s, %d 分 (%s)",
                    chapter_id, evaluation.total_score,
                    "合格" if evaluation.is_pass else "不合格",
                )
                return evaluation
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                last_error = e
                logger.warning("Critic 评分 JSON 解析失败 (尝试 %d/%d): %s",
                               attempt + 1, MAX_RETRIES + 1, e)
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": text if 'text' in dir() else ""})
                    messages.append({
                        "role": "user",
                        "content": f"你的输出 JSON 格式有误: {e}\n请重新输出合法的 JSON 对象。",
                    })

        raise RuntimeError(f"Critic 评分失败，已重试 {MAX_RETRIES} 次: {last_error}")
