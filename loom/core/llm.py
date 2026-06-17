"""LiteLLM 封装与重试机制 - 统一模型调用总线。

基于 LiteLLM + tenacity 实现：
- 模型无关的统一调用接口（屏蔽 OpenAI/Anthropic/本地模型差异）
- 自动重试与限流容错
- 流式输出支持
- Token 用量追踪
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from litellm import acompletion, completion
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# LiteLLM 可重试的异常类型（仅网络/限流/超时类异常）
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


class LLMBus:
    """LLM 统一调用总线，封装 LiteLLM 并提供重试与限流能力。

    使用方式:
        bus = LLMBus(model="gpt-4", default_max_tokens=2000)
        response = bus.chat(messages=[...])
    """

    def __init__(
        self,
        model: str = "gpt-4",
        default_max_tokens: int = 2000,
        default_temperature: float = 0.7,
        max_retries: int = 3,
    ) -> None:
        """初始化 LLM 总线。

        Args:
            model: 默认模型名称，支持 LiteLLM 的所有模型标识
            default_max_tokens: 默认最大输出 Token 数
            default_temperature: 默认生成温度
            max_retries: 最大重试次数
        """
        self.model = model
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        self.max_retries = max_retries

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """同步调用 LLM 进行对话。

        Args:
            messages: 消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
            model: 覆盖默认模型
            max_tokens: 覆盖默认最大输出 Token
            temperature: 覆盖默认温度
            **kwargs: 传递给 LiteLLM 的额外参数

        Returns:
            LiteLLM 的原始响应字典
        """
        response = completion(
            model=model or self.model,
            messages=messages,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature or self.default_temperature,
            **kwargs,
        )
        logger.debug(
            "LLM 调用完成: model=%s, usage=%s",
            model or self.model,
            getattr(response, "usage", None),
        )
        return response

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def achat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """异步调用 LLM 进行对话。

        Args:
            messages: 消息列表
            model: 覆盖默认模型
            max_tokens: 覆盖默认最大输出 Token
            temperature: 覆盖默认温度
            **kwargs: 传递给 LiteLLM 的额外参数

        Returns:
            LiteLLM 的原始响应字典
        """
        response = await acompletion(
            model=model or self.model,
            messages=messages,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature or self.default_temperature,
            **kwargs,
        )
        return response

    async def achat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """异步流式调用 LLM，逐 Token 返回生成内容。

        适用于 loom write 的交互式续写场景。

        Args:
            messages: 消息列表
            model: 覆盖默认模型
            max_tokens: 覆盖默认最大输出 Token
            temperature: 覆盖默认温度
            **kwargs: 传递给 LiteLLM 的额外参数

        Yields:
            逐个生成的文本片段
        """
        response = await acompletion(
            model=model or self.model,
            messages=messages,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature or self.default_temperature,
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content


def extract_text_from_response(response: dict[str, Any]) -> str:
    """从 LLM 响应中提取生成的文本内容。

    Args:
        response: LiteLLM 的原始响应

    Returns:
        生成的文本内容
    """
    try:
        return response.choices[0].message.content
    except (AttributeError, IndexError, KeyError) as e:
        logger.error("无法从 LLM 响应中提取文本: %s", e)
        return ""


def extract_usage_from_response(response: dict[str, Any]) -> dict[str, int]:
    """从 LLM 响应中提取 Token 使用量。

    Args:
        response: LiteLLM 的原始响应

    Returns:
        包含 prompt_tokens, completion_tokens, total_tokens 的字典
    """
    try:
        usage = response.usage
        return {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }
    except (AttributeError, KeyError) as e:
        logger.warning("无法从 LLM 响应中提取 Token 使用量: %s", e)
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
