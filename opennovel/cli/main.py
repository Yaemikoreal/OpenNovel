"""OpenNovel CLI 根命令 - Typer 命令路由入口。

命令矩阵:
- novel init      : 初始化小说项目目录
- novel write     : Actor 交互式写作循环
- novel stash     : 存入灵感潜意识池
- novel commit    : 提取状态并固化
- novel rollback  : 回滚错误 commit
- novel diff      : 检查正文与 Shadow 一致性
- novel doctor    : 诊断世界线健康度
- novel auto      : 四 Agent 自主创作循环
- novel list      : 列出工作区所有小说项目
- novel config    : 查看/设置全局配置
- novel foreshadow: 查看/管理伏笔追踪
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")  # noqa: E402

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from opennovel.cli.auto import auto_app
from opennovel.cli.commit import commit_app
from opennovel.cli.stash import stash_app
from opennovel.cli.write import write_app

console = Console()

app = typer.Typer(
    name="novel",
    help="OpenNovel (Living Organic Outline Machine) - 本地优先的长篇小说叙事操作系统",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# 注册子命令
app.add_typer(write_app, name="write")
app.add_typer(commit_app, name="commit")
app.add_typer(stash_app, name="stash")
app.add_typer(auto_app, name="auto")


@app.command()
def init(
    name: str = typer.Argument(
        None,
        help="项目名称（不指定时交互式输入）。传入 . 则在当前目录创建（不使用 workspace）",
    ),
) -> None:
    """初始化小说项目目录，生成标准 ID 模板。

    如果提供项目名称，在 workspace 目录下创建（如 novels/my-story/）。
    如果传入 ".", 在当前目录创建（传统模式）。
    """
    from pathlib import Path

    from opennovel.core.global_config import GlobalConfig
    from opennovel.storage.yaml_storage import YAMLStorage

    # 确定项目根目录
    if name == "." or name is None and Path.cwd() == GlobalConfig._find_project_root():
        # 传统模式：在当前目录创建
        project_root = Path.cwd().resolve()
    elif name is None:
        # 交互式（TODO: 简化处理，使用默认名）
        project_root = Path.cwd().resolve()
        rprint("[yellow]提示: 使用 'novel init <项目名>' 在 workspace 下创建项目[/yellow]")
    else:
        # workspace 模式
        global_cfg = GlobalConfig.load()
        ws_dir = global_cfg.workspace_dir
        ws_dir.mkdir(parents=True, exist_ok=True)
        project_root = (ws_dir / name).resolve()
        rprint(f"[dim]工作区: {ws_dir}[/dim]")

    if project_root.exists() and (project_root / "novel.yaml").exists():
        rprint(f"[yellow]⚠ 项目已存在: {project_root}[/yellow]")
        return

    project_root.mkdir(parents=True, exist_ok=True)
    rprint(f"[bold cyan]OpenNovel[/bold cyan] 正在初始化项目: [bold]{project_root}[/bold]")
    storage = YAMLStorage()

    # 创建标准目录结构
    directories = [
        "canon",
        "characters",
        "draft",
        "outlines",
        "subconscious",
        "foreshadowing",
        "summaries",
        "timeline",
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

    # 生成 novel.yaml 配置（使用全局默认模型）
    import yaml

    from opennovel.core.global_config import GlobalConfig

    global_cfg = GlobalConfig.load()
    config = {
        "version": "1.0.1",
        "model": global_cfg.default_model,
        "token_budget": 8000,
        "output_reserve": 2000,
    }
    config_path = project_root / "novel.yaml"
    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        rprint(f"  [green]✓[/green] 创建配置文件: novel.yaml (model: {global_cfg.default_model})")

    rprint("[bold green]项目初始化完成！[/bold green]")
    rprint("使用 [bold]novel write[/bold] 开始创作，[bold]novel commit[/bold] 提取状态。")


@app.command()
def list_projects() -> None:
    """列出工作区中的所有小说项目。"""
    from pathlib import Path

    from opennovel.core.global_config import GlobalConfig

    global_cfg = GlobalConfig.load()
    ws_dir = global_cfg.workspace_dir

    if not ws_dir.exists():
        rprint(f"[yellow]工作区不存在: {ws_dir}[/yellow]")
        rprint("使用 [bold]novel init <项目名>[/bold] 创建第一个项目。")
        return

    projects: list[Path] = []
    for entry in sorted(ws_dir.iterdir()):
        if entry.is_dir() and (entry / "novel.yaml").exists():
            projects.append(entry)

    if not projects:
        rprint(f"[dim]工作区为空: {ws_dir}[/dim]")
        rprint("使用 [bold]novel init <项目名>[/bold] 创建新项目。")
        return

    table = Table(title=f"📚 小说工作区 ({len(projects)} 个项目)")
    table.add_column("项目名", style="cyan")
    table.add_column("模型", style="green")
    table.add_column("章节数", style="yellow")
    table.add_column("字数", style="dim")
    table.add_column("路径", style="dim")

    for proj in projects:
        name = proj.name
        config_path = proj / "novel.yaml"
        try:
            import yaml

            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            model = cfg.get("model", "未设置")
        except Exception:
            model = "读取失败"

        # 统计章节
        draft_dir = proj / "draft"
        if draft_dir.exists():
            chapters = len(list(draft_dir.glob("ch_*.md")))
        else:
            chapters = 0

        # 统计字数
        total_words = 0
        if draft_dir.exists():
            for ch_file in sorted(draft_dir.glob("ch_*.md")):
                try:
                    total_words += len(ch_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

        table.add_row(
            f"[link=file:///{proj}]{name}[/link]",
            str(model),
            str(chapters),
            str(total_words) if total_words > 0 else "-",
            str(proj),
        )

    console.print(table)
    console.print(f"\n[dim]工作区路径: {ws_dir}[/dim]")


@app.command()
def config(
    show: bool = typer.Option(True, "--show", help="显示当前全局配置"),
    set_model: str | None = typer.Option(None, "--set-model", help="设置全局默认模型"),
    set_workspace: str | None = typer.Option(None, "--set-workspace", help="设置工作区目录"),
) -> None:
    """查看/设置 OpenNovel 全局配置。"""

    import yaml
    from rich.panel import Panel

    from opennovel.core.global_config import GLOBAL_CONFIG_FILENAME, GlobalConfig

    # 找到或创建全局配置文件
    project_root = GlobalConfig._find_project_root()
    config_path = project_root / GLOBAL_CONFIG_FILENAME

    # 读取当前配置
    current: dict = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                current = yaml.safe_load(f) or {}
        except Exception:
            current = {}

    changed = False

    if set_model is not None:
        current["default_model"] = set_model
        changed = True
        rprint(f"[green]✓[/green] 设置默认模型: {set_model}")

    if set_workspace is not None:
        current["workspace_dir"] = set_workspace
        changed = True
        rprint(f"[green]✓[/green] 设置工作区目录: {set_workspace}")

    if changed:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(current, f, allow_unicode=True, default_flow_style=False)
            rprint(f"[green]✓[/green] 全局配置已保存: {config_path}")
        except Exception as e:
            rprint(f"[red]✗[/red] 保存失败: {e}")
        return

    # 显示当前配置
    if show:
        cfg = GlobalConfig.load()
        info_lines = [
            f"[bold]配置文件:[/bold] {cfg.source or '未找到'}",
            "",
            f"[bold]默认模型:[/bold] {cfg.default_model}",
            f"[bold]默认 API 端点:[/bold] {cfg.default_api_base or '(未设置)'}",
            f"[bold]工作区目录:[/bold] {cfg.workspace_dir}",
            "",
            "[dim]修改配置: novel config --set-model <模型名>[/dim]",
            "[dim]       or: novel config --set-workspace <路径>[/dim]",
        ]
        console.print(Panel("\n".join(info_lines), title="⚙ OpenNovel 全局配置"))
        if current:
            rprint("\n[dim]配置文件内容:[/dim]")
            for k, v in current.items():
                rprint(f"  [dim]{k}:[/dim] {v}")


@app.command()
def rollback(
    snapshot_id: str = typer.Argument(..., help="要回滚的快照 ID"),
    path: str = typer.Argument(".", help="项目路径"),
) -> None:
    """回滚错误 commit，从快照恢复状态。"""
    from pathlib import Path

    from opennovel.core.state_manager import StateManager

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

    from opennovel.core.diff_checker import DiffChecker, Severity

    project_root = Path(path).resolve()
    rprint("[bold cyan]OpenNovel diff[/bold cyan] - 一致性校验\n")

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

    from opennovel.core.doctor import DiagnosticLevel, Doctor

    project_root = Path(path).resolve()
    rprint("[bold cyan]OpenNovel doctor[/bold cyan] - 世界线诊断\n")

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


@app.command()
def foreshadow(
    list_items: bool = typer.Option(True, "--list", help="展示伏笔列表"),
    add: str | None = typer.Option(None, "--add", help="手动添加伏笔描述（用于人工补充 Director 未检测到的伏笔）"),
    path: str = typer.Argument(".", help="项目路径"),
) -> None:
    """查看或管理伏笔追踪表。

    Director 每 3-5 章分析时会自动检测伏笔并更新状态。
    此命令用于手动查看和补充伏笔。
    """
    from pathlib import Path

    from rich.table import Table

    from opennovel.storage.foreshadowing import ForeshadowStore

    project_root = Path(path).resolve()
    store = ForeshadowStore(project_root)

    if add:
        import json

        from opennovel.schemas.foreshadowing import ForeshadowItem, ForeshadowStatus, ForeshadowType

        state = store.load()
        max_num = 0
        for item in state.items:
            if item.foreshadow_id.startswith("F"):
                try:
                    num = int(item.foreshadow_id[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    continue
        new_id = f"F{max_num + 1:03d}"
        new_item = ForeshadowItem(
            foreshadow_id=new_id,
            type=ForeshadowType.PLOT,
            description=add,
            buried_chapter="manual",
            status=ForeshadowStatus.BURIED,
        )
        state.items.append(new_item)
        store.save(state)
        rprint(f"[green]✓[/green] 已添加伏笔: {new_id}")
        return

    # 展示伏笔列表
    state = store.load()
    if not state.items:
        rprint("[dim]当前无伏笔记录。Director 会在章节分析时自动检测。[/dim]")
        return

    table = Table(title=f"伏笔追踪表 ({len(state.items)} 条)")
    table.add_column("ID", style="cyan")
    table.add_column("类型", style="blue")
    table.add_column("描述")
    table.add_column("埋设", style="dim")
    table.add_column("状态", style="yellow")
    table.add_column("关联角色", style="dim")

    for item in state.items:
        status_style = {
            "buried": "yellow",
            "in_progress": "cyan",
            "closed": "green",
        }.get(item.status.value, "white")
        chars = ", ".join(item.related_character_ids) if item.related_character_ids else "-"
        table.add_row(
            item.foreshadow_id,
            item.type.value,
            item.description[:80],
            item.buried_chapter,
            f"[{status_style}]{item.status.value}[/{status_style}]",
            chars,
        )

    console.print(table)
    rprint(f"\n[dim]伏笔文件: {store.file_path}[/dim]")
    rprint("[dim]新增伏笔: novel foreshadow --add \"描述...\"[/dim]")


if __name__ == "__main__":
    app()
