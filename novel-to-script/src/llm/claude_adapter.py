"""Anthropic Claude 适配器。"""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from ..config import LLMConfig
from .base import BaseLLMAdapter, LLMError


class ClaudeAdapter(BaseLLMAdapter):
    """Claude API 适配器。"""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._client = Anthropic(api_key=config.api_key)

    def complete(self, prompt: str, *, system: str = "", max_tokens: int | None = None) -> str:
        try:
            resp = self._client.messages.create(
                model=self.config.model,
                system=system if system else None,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
            )
        except Exception as e:
            raise LLMError(f"Claude 调用失败: {e}") from e

        self._tokens_in += resp.usage.input_tokens
        self._tokens_out += resp.usage.output_tokens

        content = resp.content[0]
        return content.text if hasattr(content, "text") else str(content)

    def complete_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system: str = "",
    ) -> dict[str, Any]:
        tool = _schema_to_tool(schema)

        try:
            resp = self._client.messages.create(
                model=self.config.model,
                system=system if system else None,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        except Exception as e:
            raise LLMError(f"Claude 结构化调用失败: {e}") from e

        self._tokens_in += resp.usage.input_tokens
        self._tokens_out += resp.usage.output_tokens

        for block in resp.content:
            if block.type == "tool_use":
                return block.input or {}

        raise LLMError("Claude 未返回结构化结果")

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 2


def _schema_to_tool(schema: dict[str, Any]) -> dict[str, Any]:
    """将 JSON Schema 转为 Claude Tool 定义。"""
    return {
        "name": schema.get("title", "structured_output"),
        "description": "输出结构化数据",
        "input_schema": {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        },
    }
