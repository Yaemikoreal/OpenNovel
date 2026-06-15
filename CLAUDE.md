# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

**L.O.O.M. (Living Organic Outline Machine) V1.0.1** — 本地优先的长篇小说叙事操作系统。CLI 驱动，Markdown 创作，AI 辅助。

> **当前状态**：设计冻结，Core 层骨架已搭建，检索/向量模块为 TODO 桩代码。所有代码必须遵循 `设计文档/` 中的 PRD 和技术方案。

## 快速命令

```bash
# 安装
pip install -e ".[dev]"        # 安装项目 + 开发依赖

# 测试
pytest                         # 运行全部测试
pytest -v --tb=short           # 详细输出
pytest tests/test_parser.py    # 单文件测试
pytest --cov=loom --cov-report=term-missing  # 覆盖率

# 代码质量
ruff check loom/ tests/        # 静态检查
ruff format loom/ tests/       # 格式化

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
| `loom stash` | 存入灵感潜意识池 | ✅ 实现，索引为 TODO |
| `loom commit` | 提取状态并固化（强制快照+Diff审阅） | ✅ 实现 |
| `loom rollback` | 回滚错误 commit | ✅ 实现 |
| `loom diff` | 正文与 Shadow 一致性校验 | ⏳ 桩代码 |
| `loom doctor` | 世界线健康度诊断 | ⏳ 桩代码 |

## 架构三层解耦

```
Human Layer (创作层)          → 纯 Markdown 文件
Machine Shadow (状态层)       → YAML Frontmatter + SQLite 事件账本 + Snapshots
Semantic Layer (语义层)       → LlamaIndex + BGE-M3 向量索引 (TODO)
```

### 四条防爆铁律

1. **ID 即锚点** — 全局强制 Canonical IDs（`char_001`、`loc_london`），严禁用角色名做关联
2. **权威分级** — `[CANON] > [STATE MEMORY] > [SUBCONSCIOUS]`，灵感不可作为设定执行
3. **人工审核关口** — AI 只能提议，人类否决权（`loom commit` 的 Diff Review）
4. **操作可逆** — 破坏性写入前必须生成 Snapshot，支持 `loom rollback`

## 模块结构

```
loom/
├── cli/                     # Typer CLI 命令入口
│   ├── main.py              # 根命令 (init/rollback/diff/doctor)
│   ├── write.py             # loom write
│   ├── commit.py            # loom commit (5 步审阅流程)
│   └── stash.py             # loom stash
├── core/                    # 核心引擎
│   ├── llm.py               # LLMBus: LiteLLM + tenacity 重试
│   ├── context_assembler.py # TokenCounter + 权威分级上下文组装 + 熔断
│   ├── retriever.py         # Retriever: LlamaIndex 路由 (TODO 桩代码)
│   ├── state_manager.py     # StateManager: 快照/回滚/Diff
│   └── parser.py            # Markdown + Frontmatter 读写隔离
├── agents/                  # 代理人格
│   ├── actor.py             # Actor: 沉浸式续写
│   └── auditor.py           # Auditor: 状态提取 + Pydantic 校验
├── storage/                 # 存储适配
│   ├── sqlite.py            # EventStore: SQLModel 事件账本
│   └── vector.py            # VectorStore: BGE-M3 向量索引 (TODO 桩代码)
├── schemas/                 # Pydantic / SQLModel 模型
│   ├── character.py         # CharacterFrontmatter, PhysicalState, EmotionalState
│   └── event.py             # EventLog, EventCreate, EventDiff, SnapshotMeta
└── prompts/                 # Prompt 即资产 (核心产品逻辑)
    ├── actor.v1.md          # Actor 人格 Prompt (冲突降级规则)
    └── auditor.v1.md        # Auditor 人格 Prompt (提取规则)
```

## 关键代码模式

### Markdown + Frontmatter 双区隔离

角色/章节文件 = Markdown 正文 + YAML Frontmatter。作者只写正文，AI 只写 Frontmatter，`python-frontmatter` 物理隔离读写。详见 `core/parser.py`。

### Token 熔断机制

`context_assembler.py` 中的 `assemble_actor_context()` 按权威分级注入上下文：
- 人格注入 → CANON(20%) → STATE MEMORY(30%) → SUBCONSCIOUS(10%) → 近期正文(40%)
- 总预算 8000 Tokens（预留 2000 输出）
- 超限按权威层级从低到高截断

### commit 5 步审阅流程

`cli/commit.py` 的 `commit()`:
1. 快照生成 (Snapshot) → 2. Auditor 提取事件 → 3. Diff 展示 → 4. 人工确认 → 5. 写入固化

### 测试模式

测试按模块分组，以 `TestClassName` 组织，使用 pytest fixture。数据库测试用 `tmp_path` 创建临时 SQLite 文件。示例见 `tests/test_parser.py` 和 `tests/test_storage.py`。

## 已知 TODO / 桩代码

- `core/retriever.py` — 全部检索方法返回空字符串（`query_canon`、`query_subconscious`）
- `storage/vector.py` — 全部索引操作为注释代码
- `cli/main.py:diff/doctor` — 仅打印占位文字
- BGE-M3 嵌入模型依赖 `sentence-transformers` (optional dependency `local-embedding`)

## 依赖管理

### 主依赖
```
typer rich litellm tenacity llama-index pydantic sqlmodel
python-frontmatter tiktoken orjson networkx
```

### 开发依赖
```
pytest pytest-cov ruff mypy
```

### 可选依赖
```
sentence-transformers  # 本地嵌入 (local-embedding)
```

## 设计文档

详见 `设计文档/`：
- `设计方案文档.md` — 技术架构方案
- `设计需求文档.md` — 产品需求文档（已冻结）
