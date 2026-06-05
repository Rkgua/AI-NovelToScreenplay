"""OpenAI 兼容适配器（支持 OpenAI / DeepSeek 等兼容接口）。"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from ..config import LLMConfig
from .base import BaseLLMAdapter, LLMError


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI API 适配器。"""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        kwargs: dict[str, Any] = {"api_key": config.api_key}
        if config.api_base:
            kwargs["base_url"] = config.api_base
        self._client = OpenAI(**kwargs)

    def complete(self, prompt: str, *, system: str = "", max_tokens: int | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
            )
        except Exception as e:
            raise LLMError(f"OpenAI 调用失败: {e}") from e

        if resp.usage:
            self._tokens_in += resp.usage.prompt_tokens
            self._tokens_out += resp.usage.completion_tokens

        content = resp.choices[0].message.content
        return content or ""

    def complete_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system: str = "",
    ) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})

        is_deepseek = self.config.provider == "deepseek"

        if is_deepseek:
            schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
            user_message = (
                f"{prompt}\n\n"
                f"你必须严格按以下 JSON Schema 输出 JSON，不要输出任何额外内容：\n"
                f"```json\n{schema_str}\n```"
            )
            messages.append({"role": "user", "content": user_message})
        else:
            messages.append({"role": "user", "content": prompt})

        try:
            kwargs: dict[str, Any] = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
            if is_deepseek:
                kwargs["response_format"] = {"type": "json_object"}
            else:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.get("title", "structured_output"),
                        "strict": True,
                        "schema": schema,
                    },
                }
            resp = self._client.chat.completions.create(**kwargs)
        except Exception as e:
            raise LLMError(f"OpenAI 结构化调用失败: {e}") from e

        if resp.usage:
            self._tokens_in += resp.usage.prompt_tokens
            self._tokens_out += resp.usage.completion_tokens

        content = resp.choices[0].message.content or "{}"
        return json.loads(content)

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            enc = tiktoken.encoding_for_model(self.config.model)
            return len(enc.encode(text))
        except Exception:
            return len(text) // 2
