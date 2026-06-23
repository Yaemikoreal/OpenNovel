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
  <a href="https://codecov.io/gh/Yaemikoreal/LOOM">
    <img src="https://img.shields.io/codecov/c/github/Yaemikoreal/LOOM?style=flat-square&token=YOUR_TOKEN" alt="Coverage">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/badge/code%20style-ruff-261230?style=flat-square" alt="Ruff">
  </a>
  <a href="https://github.com/Yaemikoreal/LOOM/blob/main/CODE_OF_CONDUCT.md">
    <img src="https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa?style=flat-square" alt="Code of Conduct">
  </a>
  <a href="https://github.com/Yaemikoreal/LOOM/releases">
    <img src="https://img.shields.io/github/v/release/Yaemikoreal/LOOM?style=flat-square&color=8B5CF6" alt="Latest Release">
  </a>
</p>

<p align="center">
  <a href="#-特性">特性</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-CLI-命令">CLI 命令</a> •
  <a href="#-架构">架构</a> •
  <a href="#-贡献">贡献</a> •
  <a href="#-许可证">许可证</a>
</p>

---

## 🔍 简介

**L.O.O.M.** 不是"一键生成小说"的玩具——它是写作者的**数字织机**与**记忆外脑**。

> 你写故事，L.O.O.M. 记住故事的每一个细节。

传统写作工具要么过于简单（纯文本编辑器），要么过于复杂（项目管理式写作软件）。L.O.O.M. 走了第三条路：

- **Human Layer**: 你只写纯 Markdown，就像在 Obsidian 或 VSCode 中一样自在
- **Machine Shadow**: AI 在后台自动提取状态、追踪事件、维护设定一致性
- **Semantic Layer**: 向量引擎让"我记得某章写过…"成为可搜索的语义记忆

### 为何叫 L.O.O.M.?

"Loom" 意为织布机——正如织工将经纬线交织成布，L.O.O.M. 将你的灵感丝线编织成有机生长的故事。

---

## ✨ 特性

<table>
<tr>
<td width="50%">

### 📝 纯 Markdown 创作
- 用你最喜欢的编辑器写故事
- YAML Frontmatter 由系统自动管理
- 零学习成本，零格式污染
</td>
<td width="50%">

### 🤖 三 Agent 自主创作
- Writer 思考规划 + 沉浸式创作
- Critic 五维 100 分制评分（≥80 分通过）
- Manager 自动提取角色状态变更
- 单章最多 5 次重试，确保质量
</td>
</tr>
<tr>
<td width="50%">

### 🔐 零信任安全
- AI 只能提议，你才是最终决策者
- `loom commit` 强制 Diff 审阅
- 一键回滚恢复任何错误
</td>
<td width="50%">

### 🔄 模型无关
- 通过 LiteLLM 总线连接任何 LLM
- 支持 OpenAI / Anthropic / DeepSeek / Ollama / 本地模型
- 支持 Writer/Critic/Manager 独立配置模型
</td>
</tr>
<tr>
<td width="50%">

### 🌱 有机生长
- 灵感碎片自动汇入潜意识池
- 世界在你写作中自然扩展
- 支持增量快照、因果压强追踪
</td>
<td width="50%">

### 🔌 MCP Server 集成
- 暴露 4 个 MCP Tools 供 Claude Code 等 Agent 调用
- `init_project` / `get_status` / `write_chapter` / `auto_create`
- stdio 传输，开箱即用
</td>
</tr>
<tr>
<td width="50%">

### 📦 纯本地优先
- 所有数据在本地 SQLite + Markdown
- 可被 git 追踪、Obsidian 打开
- 无需注册、无需云账号、零数据泄漏
</td>
<td width="50%">

### 🎯 全自动模式
- `loom auto` 一键自主创作整部小说
- 输入大纲 + 角色 + 世界观 → 输出完整章节
- 自动记录创作日志和角色状态变更
</td>
</tr>
</table>

---

## ⚡ 快速开始

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

### 五分钟体验

```bash
# 1. 创建新小说项目
loom init ./my-epic

# 2. 添加角色
echo "---
char_001:
  name: 林夜
  role: protagonist
---
林夜站在废弃的观象台上，风呼啸着穿过断裂的穹顶。" > ./my-epic/characters/char_001.md

# 3. 开始写作
loom write ./my-epic/draft/ch_001.md

# 4. 存入灵感（可选）
loom stash "深渊不会主动吞噬你——它只是让你自己跳下去。" --tag 金句 --tag 哲学

# 5. 审阅状态变更
loom commit ./my-epic/draft/ch_001.md
```

### 全自动创作

```bash
# 准备大纲文件 (outlines/outline.md) 和 loom.yaml 配置
# 然后一键生成整部小说
loom auto ./my-epic --chapters 5

# Writer → Critic → Manager 循环，全程无人工干预
# 每章经过五维评分，≥80 分通过，最多 5 次重试
```

---

## 📟 CLI 命令

| 命令 | 功能 | 状态 |
|:---|:---|:---|
| `loom init <path>` | 初始化小说项目目录 | ✅ |
| `loom write <file>` | 沉浸式 AI 续写循环 | ✅ |
| `loom auto <path>` | 三 Agent 全自动创作 | ✅ |
| `loom stash <text>` | 存入灵感潜意识池 | ✅ |
| `loom commit <file>` | 5 步审阅流程固化状态 | ✅ |
| `loom rollback <snapshot>` | 回滚到指定快照 | ✅ |
| `loom diff <file>` | 正文 / Shadow 一致性校验 | ✅ |
| `loom doctor <path>` | 世界线健康度诊断 | ✅ |

详细命令文档：`loom --help` 或查看 [CLAUDE.md](CLAUDE.md)。

---

## 🏗️ 架构

```
╔══════════════════════════════════╗
║        Human Layer (创作层)       ║  ← 你只写 Markdown
╠══════════════════════════════════╣
║       Machine Shadow (状态层)     ║  ← AI 自动提取
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

### 四条防爆铁律

```
铁律 1: ID 即锚点     → 全局 Canonical IDs，绑定不绑定名
铁律 2: 权威分级       → CANON > STATE MEMORY > SUBCONSCIOUS
铁律 3: 人工审核关口   → AI 只提议，人类决定
铁律 4: 操作可逆       → 破坏前快照，出错可回滚
```

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

## 🧪 开发

```bash
# 克隆
git clone https://github.com/Yaemikoreal/LOOM.git
cd LOOM

# 虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest -v --tb=short

# 带覆盖率
pytest --cov=loom --cov-report=term-missing

# 代码检查
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
│   ├── auto.py              # loom auto (三 Agent 全自动)
│   ├── commit.py            # loom commit & rollback
│   └── stash.py             # loom stash
├── core/                    # 核心引擎
│   ├── llm.py               # LiteLLM 封装
│   ├── auto_runner.py       # 三 Agent 编排器
│   ├── context_assembler.py # 上下文组装 & Token 熔断
│   ├── retriever.py         # 检索路由
│   ├── state_manager.py     # 快照/回滚/Diff
│   ├── config.py            # 项目配置管理
│   └── parser.py            # Markdown/Frontmatter 解析
├── agents/                  # 代理人格
│   ├── actor.py             # Actor 沉浸式续写
│   ├── auditor.py           # Auditor 状态提取
│   ├── writer.py            # Writer Agent (思考+创作+修改)
│   ├── critic.py            # Critic Agent (五维评分)
│   └── manager.py           # Manager Agent (状态提取)
├── storage/                 # 存储适配
│   ├── sqlite.py            # SQLite 事件账本
│   ├── yaml_storage.py      # YAML Frontmatter 安全读写
│   └── vector.py            # 向量索引
├── schemas/                 # 数据模型
│   ├── character.py         # 角色档案模型
│   ├── event.py             # 事件账本模型
│   ├── outline.py           # Writer 结构化大纲
│   ├── evaluation.py        # Critic 评分模型
│   └── manager_update.py    # Manager 状态更新模型
├── prompts/                 # Prompt 即资产
│   ├── actor.v1.md          # Actor 人格 Prompt
│   ├── auditor.v1.md        # Auditor 人格 Prompt
│   ├── writer.v1.md         # Writer Agent Prompt
│   ├── critic.v1.md         # Critic Agent Prompt
│   └── manager.v1.md        # Manager Agent Prompt
└── mcp_server.py            # MCP Server (Claude Code 集成)
```

---

## 🤝 贡献

欢迎各种形式的贡献！无论是 Bug 报告、功能建议、文档改进还是代码提交。

1. 阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发流程
2. 查看 [Issues](https://github.com/Yaemikoreal/LOOM/issues) 寻找想解决的问题
3. 阅读 [CLAUDE.md](CLAUDE.md) 了解架构约定
4. Fork 并提交 Pull Request

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。  
请遵守 [行为准则](CODE_OF_CONDUCT.md) 参与社区交流。

---

<p align="center">
  <sub>以 Markdown 为笔，以 LLM 为线，编织你的叙事世界。</sub>
  <br>
  <sub>Built with ❤️ for writers who care about consistency.</sub>
</p>
