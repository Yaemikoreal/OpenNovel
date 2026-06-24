# OpenNovel

本地优先的长篇小说叙事操作系统。作者只写纯文本 Markdown，由系统在底层维护世界观的一致性。

## Language

### 架构层

**Context Strategy** (三级上下文策略):
LLMBus 根据模型上下文窗口自动映射的策略：
- **FRUGAL** (<32K)：RAG + 摘要，精打细算
- **STANDARD** (32K–128K)：均衡型，当前章全量
- **PANORAMIC** (>128K)：全景沉浸，全量设定+全量潜意识+历史正文倒序灌注。软限 128K 防延迟/注意力漫游。
_Avoid_: 固定 Token 预算、一刀切的天花板

### 权威体系

**Human Layer**:
作者直接操作的纯 Markdown 文件层（`canon/`, `characters/`, `draft/`）。永远可被 Git 追踪、Obsidian/VSCode 打开。
_Avoid_: 创作层、输入层

**Machine Shadow**:
AI 自动提取的结构化数据**存储层**（容器概念），由 YAML Frontmatter（局部缓存）+ SQLite（全局事件账本）+ Snapshots（时间机器）组成。只关心数据怎么存、存在哪，不关心 LLM 怎么用。
_Avoid_: 状态层、影子层、STATE MEMORY（这是上下文视图，不是存储层）

**Semantic Layer**:
基于 LlamaIndex + BGE-M3 的向量检索引擎，将历史文本转化为可召回的语义记忆。

### 权威体系

**Authority Level**:
上下文消息的权威优先级标签，决定冲突时谁覆盖谁。从高到低：`CANON` > `STATE MEMORY` > `SUBCONSCIOUS`。

**CANON**:
不可变世界观设定。最高权威，LLM 绝对不可违反。例如"魔法消耗寿命"。
_Avoid_: 设定、世界观规则

**STATE MEMORY**:
Machine Shadow 中记录的角色/世界当前状态。中等权威，LLM 必须尊重。例如"左臂骨折"。
_Avoid_: Shadow、状态缓存

**SUBCONSCIOUS**:
灵感碎片池（`subconscious/lines.md`）。最低权威，仅作文风参考，绝不可作为事实执行。
_Avoid_: 潜意识、灵感池

**Dirty Flag**:
当 `novel commit` 中 Auditor 三次提取均失败且用户选择脏提交时，在章节 Frontmatter 中强制写入 `dirty_flag: extraction_failed`，标记该章节状态不可信。
_Avoid_: 静默跳过

### 流程

**Commit 审阅流**:
`novel commit` 的 5 步流程：①快照生成 → ②Auditor 提取（含最多 3 次自省纠偏）→ ③Diff 展示 → ④人工确认 → ⑤写入固化。若 Auditor 连续 3 次失败则进入人类急救模式：编辑残次 JSON / 脏提交 / 终止。

**Rescue Mode**:
Auditor 三次提取均失败后的 fallback。提供三个选项：[E]dit（手动修补 JSON）、[S]kip（脏提交，打 dirty_flag）、[A]bort（终止 commit）。

### 标识与数据

**Canonical ID**:
系统内部关联的全局稳定标识符。格式：`char_001`（角色）、`loc_london`（地点）、`item_sword`（物品）。
_Avoid_: 角色名、自然语言标识

**EmotionVector**:
角色情绪状态，由一组命名维度组成。核心维度：grief, anger, fear, joy, determination（0.0~1.0）。支持自由扩展额外情绪字段。
_Avoid_: EmotionalState, emotion_vector

**Causal Pressure**:
事件对后续叙事影响力的量化指标（0.0~1.0）。>0.7 为高因果压强事件，通常关联关键剧情转折。

**Event Log**:
SQLite 中存储的全局因果事件账本，记录所有经人工确认的状态变更事件。

**Snapshot**:
`novel commit` 前自动生成的文件级增量快照（`.snapshots/*.snapshot.json`），仅记录被本次 commit 涉及的文件的 `fm_before` 和 `fm_after`。回滚时按文件逐条覆写，覆写前校验当前文件与 `fm_after` 是否一致（防止覆盖人类在间隙中的手动修改）。不涉及的文件绝不触碰。
_Avoid_: 全局全量 dump、field_path 级 JSON Patch

### 自主创作系统（Gen2）

**AutoRunner**:
`novel auto` 的编排器（非 Agent），负责解析大纲、按序执行章节流水线（think → write → evaluate → revise → update）、管理重试和日志。纯调度逻辑，不做叙事判断。
_Avoid_: 导演、Orchestrator

**Director Agent**（规划中）:
创作总监 Agent，负责 AutoRunner 无法胜任的叙事决策：章节调度（合并/插入/删除）、动态创作策略调整、全局叙事状态感知。与 AutoRunner 的边界：AutoRunner 执行，Director 决策。Director 可提议修改大纲，但需用户确认。
_Avoid_: 导演 Agent、协调 Agent

**Anchored Issue**:
Critic 反馈的结构化升级。从 `list[str]` 升级为包含文本定位信息的结构化对象：`dimension`（维度）、`severity`（critical/major/minor）、`quote`（原文引用，20-50 字）、`problem`（问题描述）、`suggestion`（修改建议）、`location_hint`（位置提示）。让反馈从"评价意见"变成"可执行的补丁"。实现于 `schemas/evaluation.py` 的 `AnchoredIssue` 模型。

**Exploratory Variation**:
盲目变异的探索模式。在高潮关键词（转折/高潮/climax/决战/大结局/finale）触发，不同 temperature（0.5/0.7/0.9）生成多样化方向。与 Corrective Variation 对应。实现于 `agents/writer.py` 的 `think_variations()` 方法。

**Corrective Variation**:
盲目变异的纠错模式。在前章评分 <80 时触发，将 Critic 的低分原因作为负向约束注入 Writer 的多方案生成 Prompt，每个方案尝试不同的修复策略。实现于 `agents/writer.py` 的 `think_variations(variation_mode="corrective")`。

**Outline Evaluation**:
Critic 对大纲方案的三维评审（情节逻辑/角色一致性/节奏设计），每维 20 分，满分 60 分。用于盲目变异流程中的多方案预审选择。实现于 `agents/critic.py` 的 `evaluate_outline()` 方法和 `schemas/outline_evaluation.py`。

**Director Agent**:
创作总监 Agent，从全局视角分析已完成章节的叙事状态（评分趋势、因果压力曲线、角色弧线），输出策略指导注入下一章的 `chapter_hint`。实现于 `agents/director.py`。通过 `novel.yaml` 的 `director_enabled` 配置开关控制。

**Checkpoint**:
`novel auto` 的事后保护机制。每章写入前自动创建快照（`StateManager.create_snapshot()`），写入后完成快照并运行 `DiffChecker.check_chapter()` 进行一致性校验。校验结果记入 `run_log.md`，支持 `novel rollback` 回滚到任意章节。实现于 `core/auto_runner.py`。
