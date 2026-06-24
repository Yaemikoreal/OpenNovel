"""三 Agent 自主创作编排器。

协调 Writer → Critic → Manager 的创作循环，
管理重试逻辑、快照、日志和进度输出。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from loom.agents.critic import Critic
from loom.agents.manager import Manager
from loom.agents.writer import Writer
from loom.core.config import LoomConfig
from loom.core.diff_checker import DiffChecker, Mismatch
from loom.core.llm import LLMBus
from loom.core.retriever import Retriever
from loom.core.state_manager import StateManager
from loom.schemas.evaluation import ChapterEvaluation
from loom.schemas.outline import ChapterOutline
from loom.storage.yaml_storage import YAMLStorage

logger = logging.getLogger(__name__)

MAX_CHAPTER_RETRIES = 5

console = Console()


@dataclass
class ChapterResult:
    """单章创作结果。"""

    chapter_id: str
    outline: ChapterOutline
    chapter_text: str
    evaluation: ChapterEvaluation
    retry_count: int
    manager_summary: str = ""
    word_count: int = 0
    mismatches: list[Mismatch] = field(default_factory=list)


@dataclass
class RunReport:
    """完整创作运行报告。"""

    chapters: list[ChapterResult] = field(default_factory=list)
    total_chapters: int = 0
    successful_chapters: int = 0
    failed_chapters: int = 0
    start_time: str = ""
    end_time: str = ""
    log_lines: list[str] = field(default_factory=list)
    all_mismatches: list[Mismatch] = field(default_factory=list)


class AutoRunner:
    """三 Agent 自主创作编排器。

    使用方式:
        runner = AutoRunner(project_root=Path("."), config=config)
        report = runner.run(outline_text)
    """

    def __init__(self, project_root: Path, config: LoomConfig) -> None:
        self.project_root = project_root
        self.config = config
        self.storage = YAMLStorage()
        self.log_lines: list[str] = []

        # 初始化三个 Agent 的 LLMBus
        writer_cfg = config.get_agent_llm_config("writer")
        critic_cfg = config.get_agent_llm_config("critic")
        manager_cfg = config.get_agent_llm_config("manager")

        self.writer_bus = LLMBus(
            model=writer_cfg["model"] or config.model,
            api_base=writer_cfg["api_base"] or config.api_base,
            api_key=writer_cfg["api_key"] or config.api_key,
        )
        self.critic_bus = LLMBus(
            model=critic_cfg["model"] or config.model,
            api_base=critic_cfg["api_base"] or config.api_base,
            api_key=critic_cfg["api_key"] or config.api_key,
        )
        self.manager_bus = LLMBus(
            model=manager_cfg["model"] or config.model,
            api_base=manager_cfg["api_base"] or config.api_base,
            api_key=manager_cfg["api_key"] or config.api_key,
        )

        # 初始化组件
        retriever = Retriever(project_root)
        self.state_manager = StateManager(project_root)
        self.diff_checker = DiffChecker(project_root, self.storage)

        # EventStore（懒加载，数据库可能尚不存在）
        from loom.storage.sqlite import EventStore

        db_path = project_root / ".loom.db"
        event_store = EventStore(db_path) if db_path.exists() else None

        self.writer = Writer(
            llm_bus=self.writer_bus,
            retriever=retriever,
            project_root=project_root,
            creative_direction=config.creative_direction,
            words_per_chapter=config.words_per_chapter,
            event_store=event_store,
        )
        self.critic = Critic(
            llm_bus=self.critic_bus,
            project_root=project_root,
            retriever=retriever,
            event_store=event_store,
        )
        self.manager = Manager(
            llm_bus=self.manager_bus,
            state_manager=self.state_manager,
            project_root=project_root,
        )

        # Director Agent（可选）
        self.director = None
        if config.director_enabled:
            from loom.agents.director import Director

            director_cfg = config.get_agent_llm_config("director")
            director_bus = LLMBus(
                model=director_cfg["model"] or config.model,
                api_base=director_cfg["api_base"] or config.api_base,
                api_key=director_cfg["api_key"] or config.api_key,
            )
            self.director = Director(
                llm_bus=director_bus,
                project_root=project_root,
                event_store=event_store,
            )

    def _log(self, message: str, level: str = "info") -> None:
        """输出日志到终端和日志列表。"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        self.log_lines.append(log_line)

        style_map = {"info": "dim", "success": "green", "warning": "yellow", "error": "red"}
        style = style_map.get(level, "dim")
        console.print(f"  [{style}]{log_line}[/{style}]")

    def _parse_outline(self, outline_text: str) -> list[tuple[str, str]]:
        """解析大纲文本，返回 [(chapter_id, chapter_hint), ...] 列表。"""
        chapters = []
        current_title = None
        current_lines = []

        for line in outline_text.split("\n"):
            if line.startswith("## "):
                if current_title is not None:
                    chapters.append((current_title, "\n".join(current_lines).strip()))
                current_title = line[3:].strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_title is not None:
            chapters.append((current_title, "\n".join(current_lines).strip()))

        # 生成 chapter_id
        result = []
        for i, (title, hint) in enumerate(chapters, 1):
            chapter_id = f"ch_{i:03d}"
            result.append((chapter_id, f"{title}\n{hint}"))

        return result

    def _get_previous_summary(self, chapter_index: int, results: list[ChapterResult]) -> str:
        """获取前一章的摘要。"""
        if chapter_index <= 0 or not results:
            return ""
        return results[-1].manager_summary

    def _get_previous_chapter_text(self, chapter_index: int, results: list[ChapterResult]) -> str:
        """获取前一章的正文末尾。"""
        if chapter_index <= 0 or not results:
            return ""
        text = results[-1].chapter_text
        return text[-2000:] if len(text) > 2000 else text

    def _get_active_characters(self) -> list[str]:
        """获取所有角色 ID。"""
        chars_dir = self.project_root / "characters"
        if not chars_dir.exists():
            return []
        return sorted([f.stem for f in chars_dir.glob("char_*.md")])

    def _should_generate_variations(
        self,
        chapter_hint: str,
        previous_result: ChapterResult | None,
    ) -> tuple[bool, str, str]:
        """判断是否需要多方案生成。

        Returns:
            (是否需要, 模式 "exploratory"/"corrective", 纠错反馈)
        """
        # 用户强制
        if "<!-- multi -->" in chapter_hint:
            return True, "exploratory", ""

        # 纠错型：前章评分 < 80
        if previous_result and previous_result.evaluation.total_score < 80:
            issues = previous_result.evaluation.issues
            feedback = "\n".join(f"- {i}" for i in issues) if issues else "评分偏低，请调整方向"
            return True, "corrective", feedback

        # 探索型：仅高潮关键词触发（短 hint 不自动触发）
        climax_keywords = ["转折", "高潮", "climax", "决战", "大结局", "finale"]
        hint_lower = chapter_hint.lower()
        is_climax = any(kw in hint_lower for kw in climax_keywords)

        if is_climax:
            return True, "exploratory", ""

        return False, "", ""

    def run_chapter(
        self,
        chapter_id: str,
        chapter_hint: str,
        previous_summary: str = "",
        previous_text: str = "",
        results: list[ChapterResult] | None = None,
    ) -> ChapterResult:
        """执行单章创作循环: think → write → evaluate → (revise if needed) → update。

        Args:
            chapter_id: 章节 ID
            chapter_hint: 大纲中本章的描述
            previous_summary: 前一章摘要
            previous_text: 前一章正文末尾

        Returns:
            ChapterResult
        """
        # Step 1: Writer 思考（含盲目变异）
        console.print(f"\n[bold]📝 Writer 思考规划[/bold] {chapter_id}")

        # 获取前一章结果用于触发判断
        prev_result = results[-1] if results else None
        should_multi, mode, feedback = self._should_generate_variations(
            chapter_hint, prev_result,
        )

        if should_multi:
            # 多方案生成 → Critic 预审 → 选择最佳
            n_variants = 3
            self._log(
                f"盲目变异触发: {mode} 模式, {n_variants} 个方案",
                "info",
            )
            outlines = self.writer.think_variations(
                chapter_id, chapter_hint, previous_summary,
                n_variants=n_variants,
                variation_mode=mode,
                corrective_feedback=feedback,
            )

            # Critic 预审每个方案
            evaluations = []
            for idx, o in enumerate(outlines):
                eval_result = self.critic.evaluate_outline(
                    chapter_id, o, previous_summary,
                )
                evaluations.append(eval_result)
                self._log(
                    f"方案 {idx+1}: {eval_result.total_score} 分 "
                    f"(情节{eval_result.dimensions[0].score} "
                    f"角色{eval_result.dimensions[1].score} "
                    f"节奏{eval_result.dimensions[2].score})",
                    "info",
                )

            # 选择最佳方案
            best_idx = max(
                range(len(evaluations)),
                key=lambda i: evaluations[i].total_score,
            )
            outline = outlines[best_idx]
            self._log(
                f"选择方案 {best_idx+1}/{n_variants} "
                f"({evaluations[best_idx].total_score} 分): {outline.title}",
                "success",
            )
        else:
            outline = self.writer.think(chapter_id, chapter_hint, previous_summary)

        self._log(
            f"Writer 思考完成: {len(outline.scenes)} 个场景, 目标 {outline.target_words} 字",
            "success",
        )

        # Step 2-3: 创作 → 评分循环
        best_text = ""
        best_evaluation = None
        retry_count = 0

        # 首次创作
        console.print(f"[bold]✍️  Writer 创作[/bold] {chapter_id}")
        chapter_text = self.writer.write(chapter_id, outline, previous_text)
        word_count = len(chapter_text)
        self._log(f"Writer 创作完成: {word_count} 字", "success")

        for attempt in range(MAX_CHAPTER_RETRIES + 1):
            # Critic 评分
            console.print(f"[bold]📊 Critic 评分[/bold] (第 {attempt + 1} 次)")
            evaluation = self.critic.evaluate(chapter_id, chapter_text, outline)
            d = evaluation.dimensions
            score_str = (
                f"{evaluation.total_score} 分 "
                f"(文笔{d[0].score} 情节{d[1].score} 角色{d[2].score} "
                f"节奏{d[3].score} 情感{d[4].score})"
            )
            self._log(f"Critic 评分: {score_str}", "success" if evaluation.is_pass else "warning")

            if evaluation.is_pass:
                best_text = chapter_text
                best_evaluation = evaluation
                retry_count = attempt
                status = "✓ 优秀" if evaluation.is_excellent else "✓ 合格"
                console.print(f"[bold green]{status}[/bold green] {score_str}")
                break

            # 不合格：记录最佳版本
            if best_evaluation is None or evaluation.total_score > best_evaluation.total_score:
                best_text = chapter_text
                best_evaluation = evaluation

            if attempt >= MAX_CHAPTER_RETRIES:
                self._log(f"已达最大重试次数 ({MAX_CHAPTER_RETRIES})，取最高分版本", "warning")
                retry_count = attempt
                break

            # Writer 修订（优先使用锚定反馈）
            if evaluation.has_anchored_issues:
                parts = []
                for issue in evaluation.anchored_issues:
                    parts.append(
                        f"[{issue.severity.upper()}] [{issue.dimension}]\n"
                        f'  原文: "{issue.quote}"\n'
                        f"  问题: {issue.problem}\n"
                        f"  建议: {issue.suggestion}"
                    )
                feedback = "不合格原因及修改指引:\n" + "\n".join(parts)
            else:
                issues_text = "\n".join(f"- {i}" for i in evaluation.issues)
                suggestions_text = "\n".join(f"- {s}" for s in evaluation.suggestions)
                feedback = f"不合格原因:\n{issues_text}\n\n改进建议:\n{suggestions_text}"

            console.print(
                f"[bold yellow]↩️  退回 Writer 修订[/bold yellow] (第 {attempt + 1} 次重试)"
            )
            self._log(f"不合格 ({evaluation.total_score} 分)，退回修订", "warning")

            chapter_text = self.writer.revise(chapter_id, outline, chapter_text, feedback)
            word_count = len(chapter_text)
            self._log(f"Writer 修订完成: {word_count} 字", "success")

        assert best_evaluation is not None

        # Step 4: Manager 更新
        console.print(f"[bold]🔄 Manager 更新状态[/bold] {chapter_id}")
        active_chars = self._get_active_characters()
        manager_result = None
        try:
            manager_result = self.manager.update(chapter_id, best_text, active_chars)
            self._log(
                f"Manager 更新: {len(manager_result.character_updates)} 个角色变更, "
                f"{len(manager_result.events)} 个事件",
                "success",
            )
            manager_summary = manager_result.chapter_summary
        except Exception as e:
            self._log(f"Manager 更新失败: {e}", "error")
            manager_summary = ""

        # Step 5: 快照 + 写入 + 一致性校验
        chapter_path = self.project_root / "draft" / f"{chapter_id}.md"

        # 构建受影响文件列表（章节文件 + 活跃角色文件）
        affected_files = [chapter_path]
        for char_id in active_chars:
            char_path = self.project_root / "characters" / f"{char_id}.md"
            if char_path.exists():
                affected_files.append(char_path)

        # 写入前快照（铁律 4：操作可逆）
        snapshot = self.state_manager.create_snapshot(chapter_id, affected_files)
        self._log(f"快照已创建: {snapshot.snapshot_id}", "info")

        # 写入章节文件
        chapter_meta = {
            "id": chapter_id,
            "title": outline.title,
            "pov": outline.scenes[0].characters_involved[0] if outline.scenes else "",
            "active_characters": active_chars,
        }
        self.storage.write_markdown_file(chapter_path, chapter_meta, best_text)
        self._log(f"章节已写入: {chapter_path}", "success")

        # 完成快照（记录 fm_after + 事件 ID）
        event_ids = [e.event_id for e in manager_result.events] if manager_result else []
        self.state_manager.update_snapshot_after(
            snapshot.snapshot_id,
            affected_files,
            event_ids,
        )

        # 一致性校验
        chapter_mismatches = self.diff_checker.check_chapter(chapter_path)
        if chapter_mismatches:
            for m in chapter_mismatches:
                self._log(f"[{m.severity}] {m.message}", "warning")
        else:
            self._log("一致性校验通过", "success")

        return ChapterResult(
            chapter_id=chapter_id,
            outline=outline,
            chapter_text=best_text,
            evaluation=best_evaluation,
            retry_count=retry_count,
            manager_summary=manager_summary,
            word_count=word_count,
            mismatches=chapter_mismatches,
        )

    def run(self, outline_text: str) -> RunReport:
        """执行完整创作循环。

        Args:
            outline_text: 大纲文本 (Markdown 格式)

        Returns:
            RunReport 完整运行报告
        """
        report = RunReport(start_time=datetime.now().isoformat())
        chapters = self._parse_outline(outline_text)

        # 限制章节数
        max_chapters = self.config.target_chapters
        if len(chapters) > max_chapters:
            chapters = chapters[:max_chapters]

        report.total_chapters = len(chapters)
        console.print(
            Panel(
                f"[bold cyan]L.O.O.M. Auto[/bold cyan] - 三 Agent 自主创作\n"
                f"章节数: {len(chapters)} | 每章目标: {self.config.words_per_chapter} 字\n"
                f"创作方向: {self.config.creative_direction or '无特殊要求'}",
                border_style="cyan",
            )
        )

        results: list[ChapterResult] = []
        for i, (chapter_id, chapter_hint) in enumerate(chapters):
            console.print(f"\n{'=' * 60}")
            console.print(f"[bold cyan]📖 第 {i + 1}/{len(chapters)} 章: {chapter_id}[/bold cyan]")
            console.print(f"{'=' * 60}")

            previous_summary = self._get_previous_summary(i, results)
            previous_text = self._get_previous_chapter_text(i, results)

            try:
                result = self.run_chapter(
                    chapter_id,
                    chapter_hint,
                    previous_summary,
                    previous_text,
                    results=results,
                )
                results.append(result)
                report.successful_chapters += 1

                # Director 全局分析（每章结束后，非最后一章时执行）
                if self.director and i < len(chapters) - 1:
                    try:
                        analysis = self.director.analyze(
                            results, chapters[i + 1][1],
                        )
                        # 注入策略指导到下一章 hint
                        if analysis.strategic_guidance:
                            next_id, next_hint = chapters[i + 1]
                            chapters[i + 1] = (
                                next_id,
                                f"{next_hint}\n\n### 导演策略指导\n{analysis.strategic_guidance}",
                            )
                            self._log(
                                f"Director 指导: {analysis.strategic_guidance[:80]}...",
                                "info",
                            )
                        # 注入创作方向调整
                        if analysis.creative_direction_adjustment:
                            self.writer.creative_direction += (
                                f"\n{analysis.creative_direction_adjustment}"
                            )
                        # 记录警告
                        for warning in analysis.warnings:
                            self._log(f"Director 警告: {warning}", "warning")
                    except Exception as e:
                        self._log(f"Director 分析失败（不影响创作）: {e}", "warning")

            except Exception as e:
                self._log(f"章节 {chapter_id} 创作失败: {e}", "error")
                report.failed_chapters += 1

        report.chapters = results
        report.end_time = datetime.now().isoformat()
        report.log_lines = self.log_lines
        report.all_mismatches = [m for r in results for m in r.mismatches]

        # 写入日志文件
        self._write_log(report)

        # 输出最终报告
        self._print_report(report)

        return report

    def _write_log(self, report: RunReport) -> None:
        """写入运行日志到 run_log.md。"""
        log_path = self.project_root / "run_log.md"
        lines = [
            "# 自主创作日志\n",
            f"开始时间: {report.start_time}",
            f"结束时间: {report.end_time}",
            (
                f"总章节: {report.total_chapters} | "
                f"成功: {report.successful_chapters} | "
                f"失败: {report.failed_chapters}\n"
            ),
        ]

        for result in report.chapters:
            lines.append(f"## {result.chapter_id}: {result.outline.title}")
            lines.append(f"- 字数: {result.word_count}")
            lines.append(f"- 评分: {result.evaluation.total_score} 分")
            lines.append(f"- 重试: {result.retry_count} 次")
            if result.manager_summary:
                lines.append(f"- 摘要: {result.manager_summary}")
            if result.mismatches:
                lines.append(f"- 一致性问题: {len(result.mismatches)} 个")
                for m in result.mismatches:
                    lines.append(f"  - [{m.severity}] {m.message}")
            else:
                lines.append("- 一致性校验: ✓ 通过")
            lines.append("")

        # 全局一致性汇总
        total_mismatches = len(report.all_mismatches)
        if total_mismatches > 0:
            lines.append("## 一致性校验汇总")
            lines.append(f"共 {total_mismatches} 个问题\n")
            for m in report.all_mismatches:
                lines.append(f"- [{m.severity}] [{m.category}] {m.message}")
            lines.append("")

        lines.append("---")
        lines.append("## 完整日志")
        lines.extend(self.log_lines)

        try:
            log_path.write_text("\n".join(lines), encoding="utf-8")
            console.print(f"\n[dim]日志已写入: {log_path}[/dim]")
        except Exception as e:
            logger.error("日志写入失败: %s", e)

    def _print_report(self, report: RunReport) -> None:
        """输出最终报告。"""
        console.print(f"\n{'=' * 60}")
        console.print("[bold cyan]📊 创作完成报告[/bold cyan]")
        console.print(f"{'=' * 60}")

        for result in report.chapters:
            score = result.evaluation.total_score
            status = (
                "[green]优秀[/green]"
                if score >= 90
                else "[yellow]合格[/yellow]"
                if score >= 80
                else "[red]待审[/red]"
            )
            console.print(
                f"  {result.chapter_id}: {result.outline.title} | "
                f"{score} 分 {status} | {result.word_count} 字 | "
                f"重试 {result.retry_count} 次"
            )

        total_words = sum(r.word_count for r in report.chapters)
        avg_score = (
            sum(r.evaluation.total_score for r in report.chapters) / len(report.chapters)
            if report.chapters
            else 0
        )

        console.print(f"\n  总字数: {total_words}")
        console.print(f"  平均分: {avg_score:.1f}")
        console.print(f"  成功率: {report.successful_chapters}/{report.total_chapters}")

        if report.all_mismatches:
            warnings = sum(1 for m in report.all_mismatches if m.severity.value == "WARNING")
            infos = sum(1 for m in report.all_mismatches if m.severity.value == "INFO")
            console.print(
                f"  一致性问题: [yellow]{warnings}[/yellow] 警告, [dim]{infos}[/dim] 信息"
            )
        else:
            console.print("  一致性校验: [green]全部通过[/green]")
