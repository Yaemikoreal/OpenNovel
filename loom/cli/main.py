"""L.O.O.M. CLI 根命令 - Typer 命令路由入口。

命令矩阵:
- loom init    : 初始化小说项目目录
- loom write   : Actor 交互式写作循环
- loom stash   : 存入灵感潜意识池
- loom commit  : 提取状态并固化
- loom rollback: 回滚错误 commit
- loom diff    : 检查正文与 Shadow 一致性
- loom doctor  : 诊断世界线健康度
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")  # noqa: E402

import typer
from rich import print as rprint
from rich.console import Console

from loom.cli.commit import commit_app
from loom.cli.stash import stash_app
from loom.cli.write import write_app

console = Console()

app = typer.Typer(
    name="loom",
    help="L.O.O.M. (Living Organic Outline Machine) - 本地优先的长篇小说叙事操作系统",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# 注册子命令
app.add_typer(write_app, name="write")
app.add_typer(commit_app, name="commit")
app.add_typer(stash_app, name="stash")


@app.command()
def init(
    path: str = typer.Argument(".", help="项目初始化路径，默认为当前目录"),
) -> None:
    """初始化小说项目目录，生成标准 ID 模板。"""
    from pathlib import Path

    from loom.storage.yaml_storage import YAMLStorage

    project_root = Path(path).resolve()
    rprint(f"[bold cyan]L.O.O.M.[/bold cyan] 正在初始化项目: {project_root}")
    storage = YAMLStorage()

    # 创建标准目录结构
    directories = [
        "canon",
        "characters",
        "draft",
        "outlines",
        "subconscious",
        ".snapshots",
    ]
    for dir_name in directories:
        dir_path = project_root / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        rprint(f"  [green]✓[/green] 创建目录: {dir_name}/")

    # 生成角色模板
    char_template = {
        "id": "char_001",
        "name": "角色名",
        "aliases": [],
        "location": None,
        "physical": {"injuries": [], "buffs": [], "debuffs": []},
        "emotional": {"grief": 0.0, "anger": 0.0, "fear": 0.0, "joy": 0.0, "determination": 0.0},
        "inventory": [],
        "knowledge": [],
    }
    char_path = project_root / "characters" / "char_001.md"
    if not char_path.exists():
        storage.write_markdown_file(
            char_path,
            char_template,
            "# 角色背景\n\n在此自由书写角色的背景故事...",
        )
        rprint("  [green]✓[/green] 创建角色模板: characters/char_001.md")

    # 生成设定模板
    canon_template = {
        "id": "canon_world_rules",
        "type": "world_rules",
    }
    canon_path = project_root / "canon" / "world_rules.md"
    if not canon_path.exists():
        storage.write_markdown_file(
            canon_path,
            canon_template,
            "# 世界观设定\n\n在此书写不可违反的世界观规则...",
        )
        rprint("  [green]✓[/green] 创建设定模板: canon/world_rules.md")

    # 生成章节模板
    chapter_template = {
        "id": "ch_001",
        "title": "第一章",
        "pov": "char_001",
        "active_characters": ["char_001"],
    }
    chapter_path = project_root / "draft" / "ch_001.md"
    if not chapter_path.exists():
        storage.write_markdown_file(
            chapter_path,
            chapter_template,
            "# 第一章\n\n",
        )
        rprint("  [green]✓[/green] 创建章节模板: draft/ch_001.md")

    # 生成 loom.yaml 配置
    import yaml

    config = {
        "version": "1.0.1",
        "model": "gpt-4",
        "token_budget": 8000,
        "output_reserve": 2000,
    }
    config_path = project_root / "loom.yaml"
    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        rprint("  [green]✓[/green] 创建配置文件: loom.yaml")

    rprint("[bold green]项目初始化完成！[/bold green]")
    rprint("使用 [bold]loom write[/bold] 开始创作，[bold]loom commit[/bold] 提取状态。")


@app.command()
def rollback(
    snapshot_id: str = typer.Argument(..., help="要回滚的快照 ID"),
    path: str = typer.Argument(".", help="项目路径"),
) -> None:
    """回滚错误 commit，从快照恢复状态。"""
    from pathlib import Path

    from loom.core.state_manager import StateManager

    project_root = Path(path).resolve()
    manager = StateManager(project_root)

    rprint(f"[bold yellow]正在回滚快照:[/bold yellow] {snapshot_id}")
    success = manager.rollback_snapshot(snapshot_id)

    if success:
        rprint("[bold green]回滚成功！[/bold green] 状态已恢复到快照时间点。")
    else:
        rprint("[bold red]回滚失败！[/bold red] 快照不存在或恢复出错。")


@app.command()
def diff(
    chapter: str = typer.Argument(None, help="章节文件路径（相对于 draft/），不指定则扫描全部"),
    path: str = typer.Argument(".", help="项目路径"),
) -> None:
    """检查正文与 Shadow 状态的一致性，暴露逻辑漏洞。"""
    from pathlib import Path

    from rich.table import Table

    from loom.core.diff_checker import DiffChecker, Severity

    project_root = Path(path).resolve()
    rprint("[bold cyan]L.O.O.M. diff[/bold cyan] - 一致性校验\n")

    checker = DiffChecker(project_root)

    if chapter:
        chapter_path = project_root / "draft" / chapter
        if not chapter_path.exists():
            rprint(f"[bold red]章节文件不存在:[/bold red] {chapter_path}")
            raise typer.Exit(1)
        mismatches = checker.check_chapter(chapter_path)
    else:
        mismatches = checker.check_all()

    if not mismatches:
        rprint("[bold green]✓ 未检测到不一致[/bold green]")
        return

    # 渲染结果表格
    table = Table(title=f"检测到 {len(mismatches)} 项不一致")
    table.add_column("严重程度", style="bold", width=10)
    table.add_column("类别", width=12)
    table.add_column("角色", width=12)
    table.add_column("描述")
    table.add_column("来源", style="dim")

    for m in mismatches:
        severity_style = "red" if m.severity == Severity.WARNING else "yellow"
        table.add_row(
            f"[{severity_style}]{m.severity.value}[/{severity_style}]",
            m.category,
            m.character_id or "-",
            m.message,
            m.source,
        )

    console.print(table)

    # 汇总
    warnings = sum(1 for m in mismatches if m.severity == Severity.WARNING)
    infos = sum(1 for m in mismatches if m.severity == Severity.INFO)
    rprint(f"\n[dim]共 {warnings} 个 WARNING, {infos} 个 INFO[/dim]")


@app.command()
def doctor(
    path: str = typer.Argument(".", help="项目路径"),
) -> None:
    """诊断世界线健康度（基础检测：孤立角色、悬空引用、ID 一致性、脏标记）。"""
    from pathlib import Path

    from rich.table import Table

    from loom.core.doctor import DiagnosticLevel, Doctor

    project_root = Path(path).resolve()
    rprint("[bold cyan]L.O.O.M. doctor[/bold cyan] - 世界线诊断\n")

    doc = Doctor(project_root)
    items = doc.diagnose()

    if not items:
        rprint("[bold green]✓ 项目健康，未检测到问题[/bold green]")
        return

    # 渲染结果表格
    table = Table(title=f"诊断完成，共 {len(items)} 项")
    table.add_column("级别", style="bold", width=10)
    table.add_column("类别", width=18)
    table.add_column("描述")
    table.add_column("详情", style="dim")

    for item in items:
        level_style = {
            DiagnosticLevel.ERROR: "red",
            DiagnosticLevel.WARNING: "yellow",
            DiagnosticLevel.OK: "green",
            DiagnosticLevel.INFO: "cyan",
        }.get(item.level, "white")

        table.add_row(
            f"[{level_style}]{item.level.value}[/{level_style}]",
            item.category,
            item.message,
            item.details,
        )

    console.print(table)

    # 汇总
    errors = sum(1 for i in items if i.level == DiagnosticLevel.ERROR)
    warnings = sum(1 for i in items if i.level == DiagnosticLevel.WARNING)
    oks = sum(1 for i in items if i.level in (DiagnosticLevel.OK, DiagnosticLevel.INFO))
    rprint(f"\n[dim]共 {errors} 个 ERROR, {warnings} 个 WARNING, {oks} 个 OK/INFO[/dim]")


if __name__ == "__main__":
    app()
