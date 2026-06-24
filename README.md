<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/L.O.O.M.-Living%20Organic%20Outline%20Machine-8B5CF6?style=for-the-badge&logo=markdown&logoColor=white&labelColor=1a1a2e">
    <img alt="L.O.O.M." src="https://img.shields.io/badge/L.O.O.M.-Living%20Organic%20Outline%20Machine-8B5CF6?style=for-the-badge&logo=markdown&logoColor=white&labelColor=1a1a2e">
  </picture>
</p>

<p align="center">
  <b>本地优先的长篇小说叙事操作系统</b><br>
  <i>作者只写 Markdown，系统维护世界观的严丝合缝</i>
</p>

<p align="center">
  <a href="https://github.com/Yaemikoreal/LOOM/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/Yaemikoreal/LOOM?color=8B5CF6&style=flat-square" alt="MIT License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=ffd343" alt="Python 3.10+">
  </a>
  <a href="https://github.com/Yaemikoreal/LOOM/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/Yaemikoreal/LOOM/ci.yml?branch=main&style=flat-square&label=CI" alt="CI">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/badge/code%20style-ruff-261230?style=flat-square" alt="Ruff">
  </a>
  <a href="https://github.com/Yaemikoreal/LOOM/releases">
    <img src="https://img.shields.io/github/v/release/Yaemikoreal/LOOM?style=flat-square&color=8B5CF6" alt="Latest Release">
  </a>
</p>

---

## 简介

**L.O.O.M.** 是面向长篇小说创作的叙事操作系统。它不是"一键生成小说"的玩具，而是写作者的数字织机与记忆外脑。

> 你写故事，L.O.O.M. 记住故事的每一个细节。

传统写作工具要么过于简单（纯文本编辑器），要么过于复杂（项目管理式写作软件）。L.O.O.M. 走了第三条路：

- **Human Layer** — 作者只写纯 Markdown，兼容 Obsidian、VSCode 等任意编辑器
- **Machine Shadow** — AI 在后台自动提取角色状态、追踪事件因果、维护设定一致性
- **Semantic Layer** — 向量引擎将历史文本转化为可召回的语义记忆

---

## 特性

**四 Agent 自主创作** — Writer 负责思考规划与沉浸式创作，Critic 进行五维百分制评分与锚定反馈，Manager 自动提取角色状态变更，Director 全局叙事分析并注入策略指导。单章最多 5 次重试，确保质量。

**盲目变异** — 关键章节自动生成 3 个叙事方向的大纲方案，Critic 预审评分后选择最佳方案。支持探索型（最大化差异性）和纠错型（带着问题去变异）两种模式。

**锚定反馈** — Critic 的评审意见锚定到具体原文段落，Writer 的修订指令精确到"找到引用位置，针对性修改"，而非模糊的"改一下这里"。

**零信任安全** — AI 只能提议，人类拥有最终否决权。`loom commit` 强制 Diff 审阅，`loom rollback` 一键回滚到任意历史快照。

**模型无关** — 通过 LiteLLM 总线连接任意 LLM（OpenAI / Anthropic / DeepSeek / Ollama / 本地模型）。Writer、Critic、Manager、Director 可独立配置不同模型。

**MCP Server 集成** — 暴露 4 个 MCP Tools 供 Claude Code 等 AI Agent 调用，stdio 传输，开箱即用。

**纯本地优先** — 所有数据存储在本地 SQLite + Markdown 文件中，可被 git 追踪、Obsidian 打开，无需注册、无需云账号。

---

## 快速开始

### 安装

```bash
# 推荐：使用 pipx 隔离安装
pipx install loom-narrative

# 或使用 pip
pip install loom-narrative

# 从源码安装
git clone https://github.com/Yaemikoreal/LOOM.git
cd LOOM
pip install -e ".[dev]"
```

### 交互式创作

```bash
# 初始化项目
loom init ./my-novel

# 编辑角色文件 (characters/char_001.md)
# 编辑世界观设定 (canon/world_rules.md)
# 编辑大纲 (outlines/outline.md)

# 开始写作（AI 续写循环）
loom write ./my-novel/draft/ch_001.md

# 存入灵感碎片
loom stash "深渊不会主动吞噬你——它只是让你自己跳下去。" --tag 金句

# 审阅状态变更（5 步流程：快照 → 提取 → Diff → 确认 → 固化）
loom commit ./my-novel/draft/ch_001.md
```

### 全自动创作（推荐）

全自动创作是 L.O.O.M. 的核心能力。准备好大纲、角色、世界观后，一条命令即可生成完整小说。

**第一步：初始化项目**

```bash
loom init ./my-novel
cd my-novel
```

**第二步：配置 `loom.yaml`**

```yaml
model: openai/gpt-4o
creative_direction: |
  末世生存题材，聚焦情感与生存的悖论。
  风格克制、内敛，用细节和动作传递情感。
target_chapters: 7
words_per_chapter: 3000
outline: outlines/outline.md

# 每个 Agent 可独立配置模型
agents:
  writer:
    model: openai/gpt-4o
  critic:
    model: openai/gpt-4o
  manager:
    model: openai/gpt-4o
  director:
    model: openai/gpt-4o
```

**第三步：编写大纲 (`outlines/outline.md`)**

```markdown
# 小说标题

## 第一章：开篇描述

本章的场景、角色、情节要点。

## 第二章：发展描述

...
```

**第四步：创建角色档案 (`characters/char_001.md`)**

```markdown
---
id: char_001
name: 陈远
location: loc_gas_station
emotional:
  grief: 0.6
  anger: 0.3
  fear: 0.4
  joy: 0.1
  determination: 0.7
inventory:
  - 女儿的蜡笔画（心锚）
  - 老旧瑞士军刀
---

# 陈远

三十五岁的前物流工人，沉默寡言，行动派...
```

**第五步：运行自主创作**

```bash
loom auto . --chapters 7
```

系统将自动执行四 Agent 流水线：

1. **Writer** 思考规划（生成结构化大纲）→ 沉浸式创作（输出章节正文）
2. **Critic** 五维评分（文笔/情节/角色/节奏/情感，每项 20 分，满分 100）
3. 评分 < 80 分时，Writer 根据 Critic 的锚定反馈修订，最多重试 5 次
4. **Manager** 从合格章节中提取角色状态变更，写入 YAML Frontmatter 和 SQLite 事件账本
5. **Director** 分析全局叙事状态（评分趋势、因果压力、角色弧线），注入策略指导到下一章
6. 关键章节（高潮/转折）触发盲目变异：生成 3 个大纲方案，Critic 预审选择最佳

每章写入前自动创建快照，写入后运行一致性校验。全部完成后生成 `run_log.md` 创作日志。

**实际输出示例**

《最后的信号》— 由四 Agent 流水线自主生成的 7 章末世生存小说：

- 总字数：31,933
- 平均评分：84.4 / 100
- 章节评分范围：81 – 88
- 创作耗时：约 50 分钟（含 Director 分析和盲目变异）

---

## CLI 命令

| 命令 | 功能 |
|:---|:---|
| `loom init <path>` | 初始化小说项目目录 |
| `loom write <file>` | 沉浸式 AI 续写循环 |
| `loom auto <path>` | 四 Agent 全自动创作 |
| `loom stash <text>` | 存入灵感潜意识池 |
| `loom commit <file>` | 5 步审阅流程固化状态 |
| `loom rollback <snapshot>` | 回滚到指定快照 |
| `loom diff <file>` | 正文与 Shadow 一致性校验 |
| `loom doctor <path>` | 世界线健康度诊断 |

详细文档：`loom --help` 或查看 [CLAUDE.md](CLAUDE.md)。

---

## MCP Server 集成

L.O.O.M. 提供 MCP (Model Context Protocol) Server，让 Claude Code 等 AI Agent 通过标准协议调用创作能力。

### 工具列表

| Tool | 功能 | 输入 | 输出 |
|:---|:---|:---|:---|
| `init_project` | 初始化小说项目 | `path`: 项目路径 | 目录结构和模板文件 |
| `get_status` | 读取项目状态 | `path`: 项目路径 | 配置、角色、章节、大纲信息 |
| `write_chapter` | 单章创作 | `path`, `chapter_id`, `chapter_hint` | 章节正文 + 五维评分 + 维度详情 |
| `auto_create` | 全自动创作 | `path`, `chapters?`: 章节数 | 完整小说 + 创作日志 |

### 配置方式

在项目根目录或全局 Claude Code 配置中添加 `.mcp.json`：

```json
{
  "mcpServers": {
    "loom": {
      "command": "loom-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

### 使用场景

在 Claude Code 中直接调用：

```
# 初始化一个新小说项目
请用 loom 初始化一个项目到 ./my-novel

# 查看项目状态
请查看 ./my-novel 的当前状态

# 全自动创作
请用 loom 为 ./my-novel 自主创作 7 章
```

---

## 架构

```
╔══════════════════════════════════╗
║        Human Layer (创作层)       ║  ← 作者只写 Markdown
╠══════════════════════════════════╣
║       Machine Shadow (状态层)     ║  ← AI 自动提取状态
╠══════════════════════════════════╣
║      Semantic Layer (语义层)      ║  ← 向量检索记忆
╚══════════════════════════════════╝
```

### 三层解耦

| 层级 | 内容 | 技术 |
|:---|:---|:---|
| **Human Layer** | `canon/` `characters/` `draft/` 中的纯 Markdown | 任意文本编辑器 |
| **Machine Shadow** | YAML Frontmatter + SQLite 事件账本 + Snapshots | `python-frontmatter` + `SQLModel` |
| **Semantic Layer** | LlamaIndex + BGE-M3 向量索引 | `LlamaIndex` + `sentence-transformers` |

### 设计原则

- **ID 即锚点** — 全局 Canonical IDs（`char_001`、`loc_london`），严禁用角色名做关联
- **权威分级** — `[CANON] > [STATE MEMORY] > [SUBCONSCIOUS]`，灵感不可作为设定执行
- **人工审核关口** — AI 只能提议，人类拥有最终否决权
- **操作可逆** — 破坏性写入前必须生成 Snapshot，支持 `loom rollback` 秒级恢复

### 技术栈

| 组件 | 技术 | 用途 |
|:---|:---|:---|
| CLI 框架 | `Typer` + `Rich` | 命令路由、终端富文本 |
| LLM 总线 | `LiteLLM` + `tenacity` | 统一模型调用、重试容错 |
| 检索引擎 | `LlamaIndex` | 文档解析、向量索引 |
| 向量化 | `BGE-M3`（可选） | 本地语义检索 |
| 数据校验 | `Pydantic V2` + `SQLModel` | 强类型状态校验 |
| 状态账本 | `SQLite` | 因果事件日志 |
| 文件解析 | `python-frontmatter` | Markdown/YAML 安全隔离 |
| Token 控制 | `tiktoken` | 上下文预算熔断 |

---

## 开发

```bash
git clone https://github.com/Yaemikoreal/LOOM.git
cd LOOM

python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

pip install -e ".[dev]"

# 测试
pytest -v --tb=short
pytest --cov=loom --cov-report=term-missing

# 代码质量
ruff check loom/ tests/
ruff format --check loom/ tests/
mypy loom/
```

### 项目结构

```
loom/
├── cli/                     # Typer CLI 命令入口
│   ├── main.py              # loom 根命令
│   ├── write.py             # loom write
│   ├── auto.py              # loom auto (四 Agent 全自动)
│   ├── commit.py            # loom commit & rollback
│   └── stash.py             # loom stash
├── core/                    # 核心引擎
│   ├── llm.py               # LiteLLM 封装
│   ├── auto_runner.py       # 四 Agent 编排器
│   ├── context_assembler.py # 上下文组装 & Token 熔断
│   ├── retriever.py         # 检索路由
│   ├── state_manager.py     # 快照/回滚/Diff
│   ├── config.py            # 项目配置管理
│   └── parser.py            # Markdown/Frontmatter 解析
├── agents/                  # 代理人格
│   ├── actor.py             # Actor 沉浸式续写
│   ├── auditor.py           # Auditor 状态提取
│   ├── writer.py            # Writer (思考+创作+修改+变异)
│   ├── critic.py            # Critic (五维评分+大纲评审+锚定反馈)
│   ├── manager.py           # Manager (状态提取)
│   └── director.py          # Director (全局叙事分析+策略指导)
├── storage/                 # 存储适配
│   ├── sqlite.py            # SQLite 事件账本
│   ├── yaml_storage.py      # YAML Frontmatter 安全读写
│   └── vector.py            # 向量索引
├── schemas/                 # 数据模型
│   ├── character.py         # 角色档案模型
│   ├── event.py             # 事件账本模型
│   ├── outline.py           # Writer 结构化大纲
│   ├── evaluation.py        # Critic 评分模型 (含 AnchoredIssue)
│   ├── outline_evaluation.py # 大纲三维评审模型
│   ├── director.py          # Director 分析输出模型
│   └── manager_update.py    # Manager 状态更新模型
├── prompts/                 # Prompt 即资产
│   ├── actor.v1.md          # Actor 人格 Prompt
│   ├── auditor.v1.md        # Auditor 人格 Prompt
│   ├── writer.v1.md         # Writer Agent Prompt
│   ├── critic.v1.md         # Critic Agent Prompt
│   ├── critic_outline.v1.md # Critic 大纲评审 Prompt
│   ├── manager.v1.md        # Manager Agent Prompt
│   └── director.v1.md       # Director Agent Prompt
└── mcp_server.py            # MCP Server (Claude Code 集成)
```

---

## 贡献

欢迎各种形式的贡献。

1. 阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发流程
2. 查看 [Issues](https://github.com/Yaemikoreal/LOOM/issues) 寻找想解决的问题
3. 阅读 [CLAUDE.md](CLAUDE.md) 了解架构约定
4. Fork 并提交 Pull Request

---

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
请遵守 [行为准则](CODE_OF_CONDUCT.md) 参与社区交流。
