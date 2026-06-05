"""LLM 抽象基类与适配器工厂。"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any

from ..config import LLMConfig


class LLMError(Exception):
    """LLM 调用错误。"""


class BaseLLMAdapter(ABC):
    """LLM 适配器抽象基类。"""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._tokens_in: int = 0
        self._tokens_out: int = 0

    @property
    def total_tokens(self) -> int:
        return self._tokens_in + self._tokens_out

    @abstractmethod
    def complete(self, prompt: str, *, system: str = "", max_tokens: int | None = None) -> str:
        """发送 prompt，返回纯文本回复。"""

    @abstractmethod
    def complete_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system: str = "",
    ) -> dict[str, Any]:
        """发送 prompt，返回按 JSON Schema 约束的结构化数据。"""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """估算文本 token 数。"""

    def complete_with_retry(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int | None = None,
        retries: int = 3,
        backoff: float = 1.0,
    ) -> str:
        """带重试的 complete。"""
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                return self.complete(prompt, system=system, max_tokens=max_tokens)
            except LLMError:
                raise
            except Exception as e:
                last_err = e
                if attempt < retries - 1:
                    time.sleep(backoff * (2**attempt))
        raise LLMError(f"调用失败（{retries}次重试后）: {last_err}") from last_err

    def complete_structured_with_retry(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system: str = "",
        retries: int = 3,
        backoff: float = 1.0,
    ) -> dict[str, Any]:
        """带重试的 complete_structured。"""
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                return self.complete_structured(prompt, schema, system=system)
            except LLMError:
                raise
            except Exception as e:
                last_err = e
                if attempt < retries - 1:
                    time.sleep(backoff * (2**attempt))
        raise LLMError(f"结构化调用失败（{retries}次重试后）: {last_err}") from last_err


def create_adapter(config: LLMConfig) -> BaseLLMAdapter:
    """根据 LLMConfig 创建对应的适配器实例。"""
    match config.provider:
        case "openai" | "deepseek":
            from .openai_adapter import OpenAIAdapter

            return OpenAIAdapter(config)
        case "claude":
            from .claude_adapter import ClaudeAdapter

            return ClaudeAdapter(config)
        case "ollama":
            from .ollama_adapter import OllamaAdapter

            return OllamaAdapter(config)
        case _:
            raise ValueError(f"不支持的 LLM 提供商: {config.provider}")


def build_structured_schema(
    properties: dict[str, Any],
    required: list[str] | None = None,
    *,
    title: str = "structured_output",
) -> dict[str, Any]:
    """快速构建 JSON Schema 定义。

    properties 格式:
        {"field_name": {"type": "string", "description": "..."}, ...}

    返回标准的 JSON Schema dict，可直接传给 complete_structured()。
    """
    schema: dict[str, Any] = {
        "type": "object",
        "title": title,
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema
