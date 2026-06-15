"""上下文权威组装器与 Token 熔断 - Actor 代理的心脏。

负责将三层数据按权威分级打包送入 LLM：
1. 人格注入 (最高优先级，不可裁剪)
2. [CANON | IMMUTABLE] 设定 (20% 预算)
3. [STATE MEMORY | MEDIUM] 角色状态 (30% 预算)
4. [SUBCONSCIOUS | LOW] 灵感碎片 (10% 预算，最易被裁剪)
5. 近期正文 (40% 预算)

熔断机制：总预算 8000 Tokens (预留 2000 给输出)，超限时按权威层级从低到高截断。
"""

import logging
from enum import IntEnum
from pathlib import Path
from typing import Optional

import tiktoken

from loom.schemas.character import AuthorityLevel
from loom.storage.yaml_storage import YAMLStorage

logger = logging.getLogger(__name__)

# Token 预算常量
TOTAL_TOKEN_BUDGET = 8000
OUTPUT_RESERVE = 2000
INPUT_TOKEN_BUDGET = TOTAL_TOKEN_BUDGET - OUTPUT_RESERVE

# 各层级预算占比
BUDGET_RATIOS = {
    AuthorityLevel.CANON: 0.20,
    AuthorityLevel.STATE_MEMORY: 0.30,
    AuthorityLevel.SUBCONSCIOUS: 0.10,
    "recent_text": 0.40,
}

# 权威层级优先级排序（从低到高，裁剪时从最低开始）
TRUNCATION_ORDER = [
    AuthorityLevel.SUBCONSCIOUS,
    AuthorityLevel.STATE_MEMORY,
    AuthorityLevel.CANON,
]


class TokenCounter:
    """Token 计数器，基于 tiktoken 实现精确的 Token 预算计算。"""

    def __init__(self, model: str = "cl100k_base") -> None:
        """初始化 Token 计数器。

        Args:
            model: tiktoken 编码模型名称，默认使用 cl100k_base (GPT-4 系列)
        """
        try:
            self._encoding = tiktoken.get_encoding(model)
        except KeyError:
            logger.warning("未找到编码模型 %s，回退到 cl100k_base", model)
            self._encoding = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        """计算文本的 Token 数量。

        Args:
            text: 待计算的文本

        Returns:
            Token 数量
        """
        return len(self._encoding.encode(text))

    def truncate_to_budget(self, text: str, max_tokens: int) -> str:
        """将文本截断至指定 Token 预算内。

        Args:
            text: 待截断的文本
            max_tokens: 最大 Token 数

        Returns:
            截断后的文本
        """
        tokens = self._encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated_tokens = tokens[:max_tokens]
        return self._encoding.decode(truncated_tokens)


class ContextMessage:
    """上下文消息单元，携带权威层级标签。"""

    def __init__(
        self,
        role: str,
        content: str,
        authority: Optional[AuthorityLevel] = None,
    ) -> None:
        """初始化上下文消息。

        Args:
            role: 消息角色 (system/user/assistant)
            content: 消息内容
            authority: 权威层级标签，None 表示不可裁剪（如人格注入）
        """
        self.role = role
        self.content = content
        self.authority = authority
        self.token_count = 0  # 由组装器填充

    def to_dict(self) -> dict[str, str]:
        """转换为 LLM API 消息格式。"""
        return {"role": self.role, "content": self.content}


def load_prompt(prompt_path: Path) -> str:
    """加载外置 Prompt 文件。

    Args:
        prompt_path: Prompt Markdown 文件路径

    Returns:
        Prompt 文本内容

    Raises:
        FileNotFoundError: Prompt 文件不存在
    """
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def wrap_with_authority_tag(content: str, authority: AuthorityLevel) -> str:
    """为内容包裹权威层级标签。

    LLM 必须严格遵守冲突降级逻辑：Canon > State > Memory > Subconscious。

    Args:
        content: 原始内容
        authority: 权威层级

    Returns:
        带标签的内容文本
    """
    tag_map = {
        AuthorityLevel.CANON: "[CANON | IMMUTABLE | HIGH AUTHORITY]",
        AuthorityLevel.STATE_MEMORY: "[STATE MEMORY | MEDIUM AUTHORITY]",
        AuthorityLevel.SUBCONSCIOUS: "[SUBCONSCIOUS FRAGMENT | LOW AUTHORITY | OPTIONAL]",
    }
    tag = tag_map.get(authority, "")
    return f"{tag}\n{content}"


def assemble_actor_context(
    chapter_path: Path,
    project_root: Path,
    current_text: str,
    prompt_path: Optional[Path] = None,
    canon_content: str = "",
    subconscious_content: str = "",
    yaml_storage: Optional[YAMLStorage] = None,
) -> list[dict[str, str]]:
    """组装 Actor 代理的完整上下文，带 Token 熔断与权威分级。

    这是 Actor 代理的心脏方法，负责将三层数据按权威分级打包送入 LLM。
    超过 Token 预算时，按权威层级从低到高截断。

    Args:
        chapter_path: 当前章节 Markdown 文件路径
        project_root: 项目根目录路径
        current_text: 当前正文文本（近期续写锚点）
        prompt_path: Actor 人格 Prompt 文件路径
        canon_content: 从检索引擎获取的设定内容
        subconscious_content: 从潜意识池检索的灵感碎片

    Returns:
        组装完成的消息列表，可直接传入 LLM API
    """
    counter = TokenCounter()
    messages: list[ContextMessage] = []
    total_tokens = 0

    # 1. 人格注入 (最高优先级，不可裁剪)
    if prompt_path and prompt_path.exists():
        prompt_text = load_prompt(prompt_path)
        msg = ContextMessage(role="system", content=prompt_text, authority=None)
        msg.token_count = counter.count(prompt_text)
        messages.append(msg)
        total_tokens += msg.token_count

    # 2. 设定 (CANON | IMMUTABLE)
    canon_budget = int(INPUT_TOKEN_BUDGET * BUDGET_RATIOS[AuthorityLevel.CANON])
    if canon_content:
        canon_text = wrap_with_authority_tag(canon_content, AuthorityLevel.CANON)
        canon_tokens = counter.count(canon_text)
        if canon_tokens > canon_budget:
            canon_text = counter.truncate_to_budget(canon_text, canon_budget)
            canon_tokens = canon_budget
        msg = ContextMessage(role="system", content=canon_text, authority=AuthorityLevel.CANON)
        msg.token_count = canon_tokens
        messages.append(msg)
        total_tokens += canon_tokens

    # 3. 角色状态 (STATE MEMORY | MEDIUM)
    state_budget = int(INPUT_TOKEN_BUDGET * BUDGET_RATIOS[AuthorityLevel.STATE_MEMORY])
    storage = yaml_storage or YAMLStorage()
    pov_id = storage.extract_pov_character_id(chapter_path)
    if pov_id:
        char_path = project_root / "characters" / f"{pov_id}.md"
        if char_path.exists():
            char_file = storage.read_character_file(char_path)
            state_text = wrap_with_authority_tag(
                char_file.frontmatter.model_dump_json(indent=2),
                AuthorityLevel.STATE_MEMORY,
            )
            state_tokens = counter.count(state_text)
            if state_tokens > state_budget:
                state_text = counter.truncate_to_budget(state_text, state_budget)
                state_tokens = state_budget
            msg = ContextMessage(
                role="system", content=state_text, authority=AuthorityLevel.STATE_MEMORY
            )
            msg.token_count = state_tokens
            messages.append(msg)
            total_tokens += state_tokens

    # 4. 潜意识 (SUBCONSCIOUS | LOW)
    sub_budget = int(INPUT_TOKEN_BUDGET * BUDGET_RATIOS[AuthorityLevel.SUBCONSCIOUS])
    if subconscious_content:
        sub_text = wrap_with_authority_tag(
            subconscious_content, AuthorityLevel.SUBCONSCIOUS
        )
        sub_tokens = counter.count(sub_text)
        if sub_tokens > sub_budget:
            sub_text = counter.truncate_to_budget(sub_text, sub_budget)
            sub_tokens = sub_budget
        msg = ContextMessage(
            role="system", content=sub_text, authority=AuthorityLevel.SUBCONSCIOUS
        )
        msg.token_count = sub_tokens
        messages.append(msg)
        total_tokens += sub_tokens

    # 5. 近期正文
    text_budget = int(INPUT_TOKEN_BUDGET * BUDGET_RATIOS["recent_text"])
    remaining_budget = INPUT_TOKEN_BUDGET - total_tokens
    actual_text_budget = min(text_budget, remaining_budget)
    if actual_text_budget > 0 and current_text:
        text_tokens = counter.count(current_text)
        if text_tokens > actual_text_budget:
            current_text = counter.truncate_to_budget(current_text, actual_text_budget)
        msg = ContextMessage(role="user", content=f"[Previous Text]\n{current_text}\n\nCONTINUE:")
        msg.token_count = counter.count(current_text)
        messages.append(msg)

    # 熔断检查：如果总 Token 超限，按权威层级从低到高截断
    messages = _apply_circuit_breaker(messages, counter, INPUT_TOKEN_BUDGET)

    return [m.to_dict() for m in messages]


def _apply_circuit_breaker(
    messages: list[ContextMessage],
    counter: TokenCounter,
    budget: int,
) -> list[ContextMessage]:
    """应用 Token 熔断机制，超限时按权威层级从低到高截断。

    Args:
        messages: 待检查的消息列表
        counter: Token 计数器
        budget: 总 Token 预算

    Returns:
        裁剪后的消息列表
    """
    total = sum(m.token_count for m in messages)
    if total <= budget:
        return messages

    logger.warning("Token 超限 (%d > %d)，开始按权威层级裁剪", total, budget)

    # 按裁剪优先级（从低权威到高权威）逐层截断
    for authority_level in TRUNCATION_ORDER:
        if total <= budget:
            break
        for msg in messages:
            if msg.authority == authority_level and msg.token_count > 0:
                # 计算需要减少的 Token 数
                excess = total - budget
                new_token_count = max(0, msg.token_count - excess)
                if new_token_count == 0:
                    # 完全移除该消息
                    total -= msg.token_count
                    msg.token_count = 0
                    msg.content = ""
                else:
                    # 截断内容
                    msg.content = counter.truncate_to_budget(msg.content, new_token_count)
                    total -= msg.token_count - new_token_count
                    msg.token_count = new_token_count

    # 过滤掉空消息
    messages = [m for m in messages if m.token_count > 0 or m.authority is None]
    return messages
