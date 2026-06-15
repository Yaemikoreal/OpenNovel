"""loom commit / rollback 命令 - 状态审阅与固化。

核心功能：
- loom commit: 提取状态并固化（强制 Diff Review + 前置快照）
- 审阅流程：快照生成 → Auditor 提取 → Diff 展示 → 人工确认 → 写入固化

铁律 3：AI 只能提议状态变更，人类拥有绝对否决权。
铁律 4：任何破坏性写入前必须生成 Snapshot。
"""

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from loom.core.llm import LLMBus
from loom.core.state_manager import StateManager

commit_app = typer.Typer(help="状态审阅与固化")
console = Console()


@commit_app.callback(invoke_without_command=True)
def commit(
    chapter: str = typer.Argument(..., help="章节文件路径（相对于 draft/ 目录）"),
    path: str = typer.Argument(".", help="项目路径"),
    model: str = typer.Option("gpt-4", "--model", "-m", help="LLM 模型名称"),
) -> None:
    """提取章节状态并固化，强制 Diff Review + 前置快照。"""
    from pathlib import Path

    from loom.agents.auditor import Auditor
    from loom.storage.yaml_storage import YAMLStorage
    from loom.core.retriever import Retriever

    project_root = Path(path).resolve()
    chapter_path = project_root / "draft" / chapter

    if not chapter_path.exists():
        rprint(f"[bold red]章节文件不存在:[/bold red] {chapter_path}")
        raise typer.Exit(1)

    rprint(f"[bold cyan]L.O.O.M. commit[/bold cyan] - 状态审阅与固化")
    rprint(f"章节: [bold]{chapter}[/bold]\n")

    # 初始化存储
    storage = YAMLStorage()

    # Step 1: 生成快照（铁律 4）
    rprint("[bold]Step 1/5[/bold] 生成快照...")
    manager = StateManager(project_root)
    chapter_meta, body = storage.read_markdown_file(chapter_path)
    chapter_id = chapter_meta.get("id", chapter.replace(".md", ""))

    # 确定受影响的文件（章节 + 活跃角色）
    active_chars = storage.extract_active_characters(chapter_path)
    affected_files = [chapter_path]
    for char_id in active_chars:
        char_path = project_root / "characters" / f"{char_id}.md"
        if char_path.exists():
            affected_files.append(char_path)

    snapshot = manager.create_snapshot(chapter_id, affected_files=affected_files)
    rprint(f"  [green]✓[/green] 快照已创建: {snapshot.snapshot_id}\n")

    # Step 2: Auditor 提取事件
    rprint("[bold]Step 2/5[/bold] Auditor 提取事件...")
    llm_bus = LLMBus(model=model)
    retriever = Retriever(project_root)
    auditor = Auditor(
        llm_bus=llm_bus, state_manager=manager, project_root=project_root
    )

    events = auditor.extract_events(chapter_id, body, active_chars)

    if not events:
        rprint("[yellow]未检测到状态变更事件[/yellow]")
        return

    rprint(f"  [green]✓[/green] 提取到 {len(events)} 个事件\n")

    # Step 3: Diff 展示（铁律 3）
    rprint("[bold]Step 3/5[/bold] 变更预览:")
    diffs = auditor.generate_diffs(events)
    diff_text = manager.generate_diff_text(diffs)

    diff_panel = Panel(
        Text(diff_text, style="bold"),
        title="状态变更 Diff",
        border_style="cyan",
    )
    console.print(diff_panel)

    # Step 4: 人工守门（铁律 3）
    rprint("\n[bold]Step 4/5[/bold] 人工审阅")
    choice = typer.prompt("Apply these changes? [y/n/edit]", default="n")

    if choice.lower() == "n":
        rprint("[yellow]已取消，状态未变更[/yellow]")
        return

    if choice.lower() == "edit":
        rprint("[dim]手动编辑功能开发中...[/dim]")
        return

    if choice.lower() != "y":
        rprint("[yellow]已取消，状态未变更[/yellow]")
        return

    # Step 5: 写入固化
    rprint("\n[bold]Step 5/5[/bold] 写入固化...")
    event_ids = auditor.apply_confirmed_events(events, chapter_id)

    # 更新快照的 after 状态（只更新受影响的文件）
    manager.update_snapshot_after(snapshot.snapshot_id, affected_files, event_ids)

    rprint(f"[bold green]✓ 已固化 {len(event_ids)} 个事件[/bold green]")
