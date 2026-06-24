# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

**L.O.O.M. (Living Organic Outline Machine) V1.0.1** — 本地优先的长篇小说叙事操作系统。CLI 驱动，Markdown 创作，AI 辅助。

> **当前状态**：设计冻结，Core 层 + 语义层 + 三 Agent 自主创作系统已实现。

## 快速命令

```bash
# 安装
pip install -e ".[dev]"        # 安装项目 + 开发依赖

# 测试
pytest                         # 运行全部测试
pytest -v --tb=short           # 详细输出
pytest tests/test_parser.py    # 单文件测试
pytest -k "test_name"          # 按名称过滤测试
pytest --cov=loom --cov-report=term-missing  # 覆盖率

# 代码质量
ruff check loom/ tests/        # 静态检查
ruff format loom/ tests/       # 格式化
ruff format --check loom/ tests/  # 检查格式差异

# 类型检查
mypy loom/                     # 类型注解校验

# CLI 入口
loom --help                    # 查看所有命令
```

## CLI 命令矩阵

| 命令 | 功能 | 实现状态 |
|:---|:---|:---|
| `loom init` | 初始化小说项目目录 | ✅ 完成 |
| `loom write` | Actor 交互式写作循环 | ✅ 实现，依赖 LLM |
| `loom stash` | 存入灵感潜意识池 | ✅ 实现，向量索引已接入 |
| `loom commit` | 提取状态并固化（强制快照+Diff审阅） | ✅ 实现 |
| `loom rollback` | 回滚错误 commit | ✅ 实现 |
| `loom diff` | 正文与 Shadow 一致性校验 | ✅ 实现（规则检测） |
| `loom doctor` | 世界线健康度诊断 | ✅ 实现（基础检测） |

## 架构三层解耦

```
Human Layer (创作层)          → 纯 Markdown 文件 (canon/ characters/ draft/)
Machine Shadow (状态层)       → YAML Frontmatter + SQLite 事件账本 + Snapshots
Semantic Layer (语义层)       → LlamaIndex + BGE-M3 向量索引（可选 sentence-transformers）
```

### 四条防爆铁律

1. **ID 即锚点** — 全局强制 Canonical IDs（`char_001`、`loc_london`），严禁用角色名做关联
2. **权威分级** — `[CANON] > [STATE MEMORY] > [SUBCONSCIOUS]`，灵感不可作为设定执行
3. **人工审核关口** — AI 只能提议，人类否决权（`loom commit` 的 Diff Review）
4. **操作可逆** — 破坏性写入前必须生成 Snapshot，支持 `loom rollback`

### 三级上下文策略

`context_assembler.py` 根据模型上下文窗口自动映射策略（详见 `docs/adr/0002-three-tier-context-strategy.md`）：

- **FRUGAL** (< 32K)：8K 预算，按比例分配各层级，仅注入 POV 角色状态
- **STANDARD** (32K–128K)：48K 预算，注入全部活跃角色状态（`active_characters`），更多空间给设定和潜意识
- **PANORAMIC** (> 128K)：128K 软限，全量设定 + 全量潜意识 + 全部活跃角色状态，不做截断

使用方式：
```python
from loom.core.context_assembler import assemble_actor_context, ContextStrategy, detect_strategy

# 自动检测策略
strategy = detect_strategy(model_max_window)  # e.g. 128000 → STANDARD

# 手动指定策略
messages = assemble_actor_context(
    chapter_path, project_root, current_text,
    strategy=ContextStrategy.STANDARD,
)
```

## 模块结构

```
loom/
├── cli/                     # Typer CLI 命令入口
│   ├── main.py              # 根命令 (init/rollback/diff/doctor)
│   ├── write.py             # loom write (Gen1 交互式)
│   ├── auto.py              # loom auto (Gen2 自主创作)
│   ├── commit.py            # loom commit (5 步审阅流程)
│   └── stash.py             # loom stash
├── core/                    # 核心引擎
│   ├── llm.py               # LLMBus: LiteLLM + tenacity 重试
│   ├── context_assembler.py # TokenCounter + 权威分级上下文组装 + 熔断（所有 Agent 通用）（所有 Agent 通用）
│   ├── auto_runner.py       # AutoRunner: Gen2 三 Agent 自主编排器
│   ├── retriever.py         # Retriever: 双索引语义检索路由 (canon + subconscious)
│   ├── state_manager.py     # StateManager: 快照/回滚/Diff
│   ├── parser.py            # Markdown 场景切分 + Token 计数
│   ├── config.py            # 项目配置管理 (loom.yaml 读写)
│   ├── diff_checker.py      # 正文与 Shadow 一致性校验
│   └── doctor.py            # 世界线健康度诊断
├── agents/                  # 代理人格
│   ├── actor.py             # Actor: Gen1 沉浸式续写
│   ├── auditor.py           # Auditor: Gen1 状态提取 + Pydantic 校验 + 重试纠偏
│   ├── writer.py            # Writer: Gen2 创作代理 (think → write/revise, think_variations)
│   ├── critic.py            # Critic: Gen2 五维评分 + 锚定反馈 + 大纲评审
│   ├── manager.py           # Manager: Gen2 状态提取 + 角色更新
│   └── director.py          # Director: 全局叙事分析 + 策略指导注入
├── storage/                 # 存储适配
│   ├── sqlite.py            # EventStore: SQLModel 事件账本
│   ├── yaml_storage.py      # YAMLStorage: Frontmatter 安全读写 + 原子写入
│   └── vector.py            # VectorStore: LlamaIndex 向量索引（可选 BGE-M3 本地 embedding）
├── schemas/                 # Pydantic / SQLModel 模型
│   ├── character.py         # CharacterFrontmatter, PhysicalState, EmotionVector
│   ├── event.py             # EventLog, EventCreate, EventDiff, SnapshotMeta
│   ├── evaluation.py        # ChapterEvaluation, DimensionScore, AnchoredIssue
│   ├── outline.py           # ChapterOutline, SceneBreakdown
│   ├── outline_evaluation.py # OutlineEvaluation (大纲三维评审)
│   ├── director.py          # DirectorAnalysis (导演策略分析)
│   └── manager_update.py    # ManagerUpdateResult, CharacterUpdate, EventRecord
└── prompts/                 # Prompt 即资产 (核心产品逻辑)
    ├── actor.v1.md          # Actor 人格 Prompt (冲突降级规则)
    ├── auditor.v1.md        # Auditor 人格 Prompt (提取规则)
    ├── writer.v1.md         # Writer 人格 Prompt (创作 + 修订 + 变异)
    ├── critic.v1.md         # Critic 人格 Prompt (五维评分 + 锚定反馈)
    ├── critic_outline.v1.md # Critic 大纲评审 Prompt (三维评分)
    ├── manager.v1.md        # Manager 人格 Prompt (状态提取)
    └── director.v1.md       # Director 人格 Prompt (全局叙事分析)
```

### 项目初始化后的目录结构

`loom init` 生成的标准小说项目：

```
<project>/
├── canon/              # 不可变世界观设定 (CANON 层)
│   └── world_rules.md
├── characters/         # 角色档案 (Markdown + Frontmatter)
│   └── char_001.md
├── draft/              # 章节正文
│   └── ch_001.md
├── outlines/           # 大纲
├── subconscious/       # 灵感潜意识池 (SUBCONSCIOUS 层)
├── .snapshots/         # 文件级增量快照
├── .index/             # 向量索引持久化 (canon/ + subconscious/)
├── .loom.db            # SQLite 事件账本
└── loom.yaml           # 项目配置 (model/token_budget)
```

## 关键代码模式

### Markdown + Frontmatter 双区隔离

角色/章节文件 = Markdown 正文 + YAML Frontmatter。作者只写正文，AI 只写 Frontmatter，`python-frontmatter` 物理隔离读写。所有 Frontmatter 操作通过 `YAMLStorage` 进行，其他模块不得直接操作文件系统。详见 `storage/yaml_storage.py`。

### 原子写入防损坏

`YAMLStorage._atomic_write()` 使用 `tmpfile + os.replace()` 原子写入，防止断电/崩溃导致文件损坏。

### safe_merge 冲突检测

`YAMLStorage.safe_merge()` 在写入前比对文件当前 Frontmatter 与预期状态是否一致，不一致则抛出 `ConflictError`。回滚操作依赖此机制防止覆盖人类在间隙中的手动修改。

### Token 熔断机制

`context_assembler.py` 中的 `assemble_context()` 为所有 Agent（Actor/Writer/Critic）按权威分级注入上下文：
- 人格注入 → CANON(20%) → STATE MEMORY(30%) → SUBCONSCIOUS(10%) → 任务消息(40%)
- 总预算 8000 Tokens（预留 2000 输出）
- 超限按权威层级从低到高截断（SUBCONSCIOUS → STATE MEMORY → CANON）

### commit 5 步审阅流程

`cli/commit.py` 的 `commit()`:
1. 快照生成 (Snapshot) → 2. Auditor 提取事件（含最多 3 次自省纠偏） → 3. Diff 展示 → 4. 人工确认 → 5. 写入固化

若 Auditor 连续 3 次提取失败，进入人类急救模式（Rescue Mode）：[E]dit 手动修补 / [S]kip 脏提交（打 dirty_flag） / [A]bort 终止。

### 测试模式

测试按模块分组，以 `TestClassName` 组织，使用 pytest fixture。数据库测试用 `tmp_path` 创建临时 SQLite 文件。Mock 使用 `unittest.mock` 模拟 LLM 响应。示例见 `tests/test_parser.py`、`tests/test_auditor.py` 和 `tests/test_yaml_storage.py`。

## 已知 TODO / 桩代码

- `core/context_assembler.py` — PANORAMIC 模式已注入历史章节正文（`_load_previous_chapters()`）
- BGE-M3 嵌入模型依赖 `sentence-transformers` (optional dependency `local-embedding`)
- `networkx` 因果图与伏笔网（Phase 2 预留，未实现，已移至可选依赖 `phase2`）
- **P4 导演 Agent 增强**（规划中）— 章节调度（合并/插入/删除）能力尚未实现，当前仅支持策略指导注入

## 依赖管理

### 主依赖
```
typer rich litellm tenacity llama-index pydantic sqlmodel
python-frontmatter tiktoken orjson
```

### 开发依赖
```
pytest pytest-cov ruff mypy pre-commit
```

### 可选依赖
```
sentence-transformers  # 本地嵌入 (local-embedding)
networkx              # 因果图 (phase2)
```

## Commit 约定

使用中文，遵循 Conventional Commits 风格：

```
[类型]：精炼概要

- 变更点：（做了什么改动）
- 优化点：（改进了什么）
- 解决问题：（修复了什么）
```

类型：`feat` `fix` `refactor` `test` `docs` `style` `chore`

## 设计文档

- `docs/adr/0001-file-level-incremental-snapshots.md` — 文件级增量快照决策
- `docs/adr/0002-three-tier-context-strategy.md` — 三级上下文策略决策
- `CONTEXT.md` — 项目术语表与命名约定（**必读**，定义了 CANON / STATE MEMORY / SUBCONSCIOUS 等核心术语的精确含义）
- `docs/user-guide.md` — 用户手册（安装、工作流、FAQ）

## 开发约束

- **Python**: >= 3.10（pyproject.toml 声明 3.10/3.11/3.12）
- **行宽**: 100 字符（ruff line-length）
- **缩进**: 4 空格（.editorconfig）
- **类型检查**: mypy strict 模式（`disallow_untyped_defs = true`）— 所有函数必须有类型注解
- **Lint 规则**: ruff select E/F/W/I/N/UP/B/A/SIM，ignore B008（Typer 默认参数）
- **Pre-commit**: ruff lint+format、mypy、trailing-whitespace、end-of-file-fixer、check-yaml、check-toml、大文件检查（500KB 限制）
- **行尾**: LF（.editorconfig 强制）

## demo_novel 项目

`demo_novel/` 包含一个可运行的演示小说项目，`loom.yaml` 配置了 `openai/mimo-v2.5-pro` 模型和 50K token 预算。可用于测试 `loom write` / `loom commit` 等命令的完整流程。
