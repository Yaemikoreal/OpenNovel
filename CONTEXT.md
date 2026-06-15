# L.O.O.M.

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
当 `loom commit` 中 Auditor 三次提取均失败且用户选择脏提交时，在章节 Frontmatter 中强制写入 `dirty_flag: extraction_failed`，标记该章节状态不可信。
_Avoid_: 静默跳过

### 流程

**Commit 审阅流**:
`loom commit` 的 5 步流程：①快照生成 → ②Auditor 提取（含最多 3 次自省纠偏）→ ③Diff 展示 → ④人工确认 → ⑤写入固化。若 Auditor 连续 3 次失败则进入人类急救模式：编辑残次 JSON / 脏提交 / 终止。

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
`loom commit` 前自动生成的文件级增量快照（`.snapshots/*.snapshot.json`），仅记录被本次 commit 涉及的文件的 `fm_before` 和 `fm_after`。回滚时按文件逐条覆写，覆写前校验当前文件与 `fm_after` 是否一致（防止覆盖人类在间隙中的手动修改）。不涉及的文件绝不触碰。
_Avoid_: 全局全量 dump、field_path 级 JSON Patch
