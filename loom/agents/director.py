"""Director Agent - 创作总监代理。

从全局视角分析已完成章节的叙事状态，
输出策略指导用于调整后续章节的创作方向。
"""

import json
import logging
from pathlib import Path

from loom.core.context_assembler import ContextStrategy, assemble_context
from loom.core.llm import LLMBus
from loom.schemas.director import DirectorAnalysis
from loom.storage.sqlite import EventStore

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class Director:
    """Director Agent — 创作总监。

    使用方式:
        director = Director(llm_bus=bus, project_root=root, event_store=es)
        analysis = director.analyze(results, "下一章大纲提示")
        print(analysis.strategic_guidance)
    """

    def __init__(
        self,
        llm_bus: LLMBus,
        project_root: Path,
        event_store: EventStore | None = None,
        prompt_path: Path | None = None,
    ) -> None:
        self.llm_bus = llm_bus
        self.project_root = project_root
        self.event_store = event_store
        self.prompt_path = prompt_path or (
            Path(__file__).parent.parent / "prompts" / "director.v1.md"
        )

    def _load_prompt(self) -> str:
        """加载 Director Prompt。"""
        if not self.prompt_path.exists():
            logger.warning("Director Prompt 文件不存在: %s", self.prompt_path)
            return "你是创作总监。分析叙事状态，输出策略指导。"
        return self.prompt_path.read_text(encoding="utf-8")

    def _build_analysis_data(self, results: list) -> str:
        """从已完成章节结果中提取分析数据。"""
        lines = []

        # 评分趋势
        lines.append("### 评分趋势")
        for i, r in enumerate(results):
            score = r.evaluation.total_score
            status = (
                "优秀" if score >= 90
                else "合格" if score >= 80
                else "待审"
            )
            lines.append(
                f"- 第{i+1}章 ({r.chapter_id}): {r.evaluation.total_score}分 {status}, "
                f"{r.word_count}字, 重试{r.retry_count}次"
            )

        # 维度详情（最近 3 章）
        lines.append("\n### 维度评分详情（最近章节）")
        for r in results[-3:]:
            dims = r.evaluation.dimensions
            lines.append(
                f"- {r.chapter_id}: 文笔{dims[0].score} 情节{dims[1].score} "
                f"角色{dims[2].score} 节奏{dims[3].score} 情感{dims[4].score}"
            )

        # 章节摘要
        lines.append("\n### 章节摘要")
        for r in results:
            if r.manager_summary:
                lines.append(f"- {r.chapter_id}: {r.manager_summary}")

        # 一致性问题汇总
        all_mismatches = [m for r in results for m in r.mismatches]
        if all_mismatches:
            lines.append(f"\n### 一致性问题 ({len(all_mismatches)} 个)")
            for m in all_mismatches[-5:]:
                lines.append(f"- [{m.severity}] {m.message}")

        return "\n".join(lines)

    def _build_event_data(self) -> str:
        """从 EventStore 提取事件分析数据。"""
        if not self.event_store:
            return "无事件数据"

        lines = []

        # 高压力事件
        high_events = self.event_store.get_high_pressure_events(threshold=0.7)
        if high_events:
            lines.append("### 高因果压力事件 (≥0.7)")
            for e in high_events[-10:]:
                lines.append(
                    f"- [{e.event_type}] {e.description} "
                    f"(pressure={e.causal_pressure}, chapter={e.chapter_id})"
                )
        else:
            lines.append("### 高因果压力事件: 无")

        # 全部事件统计
        all_events = self.event_store.get_all_events()
        lines.append(f"\n### 事件总数: {len(all_events)}")

        # 按章节统计
        chapter_event_counts: dict[str, int] = {}
        for e in all_events:
            chapter_event_counts[e.chapter_id] = chapter_event_counts.get(e.chapter_id, 0) + 1
        if chapter_event_counts:
            lines.append("### 每章事件数")
            for ch, count in sorted(chapter_event_counts.items()):
                lines.append(f"- {ch}: {count} 个事件")

        return "\n".join(lines)

    def _build_task_message(
        self,
        results: list,
        upcoming_chapter_hint: str,
    ) -> str:
        """构建 Director 分析任务消息。"""
        analysis_data = self._build_analysis_data(results)
        event_data = self._build_event_data()

        return f"""## 全局叙事分析任务

请分析已完成章节的叙事状态，为下一章提供策略指导。

### 已完成章节数据
{analysis_data}

### 事件时间线
{event_data}

### 下一章大纲
{upcoming_chapter_hint}

请输出合法的 JSON 对象，包含以下字段：
pacing_assessment、tension_curve、character_arc_status、
strategic_guidance、creative_direction_adjustment、warnings。"""

    def analyze(
        self,
        results: list,
        upcoming_chapter_hint: str,
    ) -> DirectorAnalysis:
        """分析已完成章节的全局叙事状态，输出策略指导。

        Args:
            results: 已完成的 ChapterResult 列表
            upcoming_chapter_hint: 下一章的大纲提示

        Returns:
            DirectorAnalysis 分析结果
        """
        if not results:
            return DirectorAnalysis(
                pacing_assessment="无数据",
                tension_curve="无数据",
                character_arc_status={},
                strategic_guidance="",
            )

        task_message = self._build_task_message(results, upcoming_chapter_hint)
        messages = assemble_context(
            project_root=self.project_root,
            task_message=task_message,
            prompt_path=self.prompt_path,
            strategy=ContextStrategy.STANDARD,
        )

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.llm_bus.chat(messages, temperature=0.3)
                text = response.choices[0].message.content
                if not text:
                    raise ValueError("LLM 返回空文本")
                analysis = self._parse_analysis_from_text(text)
                logger.info(
                    "Director 分析完成: %s, 张力=%s",
                    analysis.pacing_assessment, analysis.tension_curve,
                )
                return analysis
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                last_error = e
                logger.warning(
                    "Director 分析 JSON 解析失败 (尝试 %d/%d): %s",
                    attempt + 1, MAX_RETRIES + 1, e,
                )
                if attempt < MAX_RETRIES:
                    messages.append(
                        {"role": "assistant", "content": text if "text" in dir() else ""}
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"你的输出 JSON 格式有误: {e}\n"
                                "请重新输出合法的 JSON 对象。"
                            ),
                        }
                    )

        raise RuntimeError(f"Director 分析失败，已重试 {MAX_RETRIES} 次: {last_error}")

    def _parse_analysis_from_text(self, text: str) -> DirectorAnalysis:
        """从 LLM 输出中解析 DirectorAnalysis JSON。"""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)
        return DirectorAnalysis(**data)
