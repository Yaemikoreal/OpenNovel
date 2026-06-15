# L.O.O.M. (Living Organic Outline Machine) V1.0.1

本地优先的长篇小说叙事操作系统。

L.O.O.M. 不是"一键生成小说"的玩具，而是作者的"数字织机"与"记忆外脑"。核心目标：让作者只专注于用自然语言创作，由系统在底层维护世界观的严丝合缝。

## 核心设计原则

1. **Human-first (人类主导)** — 作者只写纯文本 Markdown，严禁要求填写 YAML 配置
2. **Memory-as-shadow (记忆如影)** — YAML/SQLite 是 AI 自动提取的影子，不作为输入层
3. **Zero-Trust AI (零信任输出)** — AI 提取的状态变更必须经过人工 Diff 审阅才可固化，支持一键回滚
4. **Model Agnostic (模型无关)** — 通过 LiteLLM 总线屏蔽底层模型差异

## 安装

```bash
# 克隆项目
cd E:\Pythonproject\LOOM

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -e .

# 开发依赖
pip install -e ".[dev]"
```

## 使用

```bash
# 初始化小说项目
loom init ./my-novel

# 启动交互式写作
loom write ch_001.md --path ./my-novel

# 存入灵感碎片
loom stash "深渊不收我" --tag 金句 --tag 绝望 --path ./my-novel

# 提取状态并审阅
loom commit ch_001.md --path ./my-novel

# 回滚错误 commit
loom rollback ch_001_1698765432 --path ./my-novel

# 一致性校验
loom diff --path ./my-novel

# 世界线诊断
loom doctor --path ./my-novel
```

## 项目结构

```
loom/
├── cli/                     # CLI 命令入口
│   ├── main.py              # loom 根命令 (Typer)
│   ├── write.py             # loom write
│   ├── commit.py            # loom commit & rollback
│   └── stash.py             # loom stash
├── core/                    # 核心引擎
│   ├── llm.py               # LiteLLM 封装 & tenacity 重试
│   ├── context_assembler.py # 上下文权威组装器 & Token 熔断
│   ├── retriever.py         # LlamaIndex 检索路由
│   ├── state_manager.py     # YAML/SQLite 读写 & Diff 生成
│   └── parser.py            # Markdown/Frontmatter 解析
├── agents/                  # 代理人格与逻辑
│   ├── actor.py             # Actor 续写代理
│   └── auditor.py           # Auditor 审阅代理
├── storage/                 # 存储适配层
│   ├── sqlite.py            # SQLite 事件账本
│   └── vector.py            # 向量索引存储
├── prompts/                 # Prompt 即资产 (外置)
│   ├── actor.v1.md          # Actor 人格 Prompt
│   └── auditor.v1.md        # Auditor 人格 Prompt
└── schemas/                 # Pydantic/SQLModel 数据模型
    ├── event.py             # 事件账本模型
    └── character.py         # 角色档案模型
```

## 测试

```bash
# 运行全部测试
pytest

# 运行指定模块测试
pytest tests/test_schemas.py
pytest tests/test_parser.py
pytest tests/test_storage.py

# 带覆盖率
pytest --cov=loom
```

## 技术栈

| 层级 | 技术 | 用途 |
|:---|:---|:---|
| CLI 壳 | `Typer`, `Rich` | 命令路由、终端富文本/Diff 渲染 |
| LLM 总线 | `LiteLLM`, `tenacity` | 统一模型调用、限流与重试容错 |
| 检索引擎 | `LlamaIndex` | 文档解析、向量索引、语义路由 |
| 向量化 | `BGE-M3` (本地) | 高质量中英文向量化，防数据泄漏 |
| 数据校验 | `Pydantic V2`, `SQLModel` | 状态结构强类型校验，ORM 映射 |
| 状态账本 | `SQLite` | 全局因果事件日志存储 |
| 文件解析 | `python-frontmatter` | Markdown 与 YAML 的安全读写隔离 |
| Token 熔断 | `tiktoken` | 上下文预算精确计算 |
| 序列化 | `orjson` | 快照与状态高速读写 |
| 图网络预留 | `networkx` | (Phase 2) 因果图与伏笔网 |

## 四条防爆铁律

- **铁律 1：ID 即锚点** — 全局强制使用 Canonical IDs（`char_001`, `loc_london`），严禁用角色名做系统关联
- **铁律 2：权威分级** — `[CANON] > [STATE MEMORY] > [SUBCONSCIOUS]`，灵感绝不可作为设定执行
- **铁律 3：人工审核关口** — AI 只能提议状态变更，人类拥有绝对否决权（`loom commit` 的 Diff Review）
- **铁律 4：操作可逆** — 任何破坏性写入前必须生成 Snapshot，支持 `loom rollback`
