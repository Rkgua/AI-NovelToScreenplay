"""Ollama 本地模型适配器。"""

from __future__ import annotations

import json
from typing import Any

from ollama import Client

from ..config import LLMConfig
from .base import BaseLLMAdapter, LLMError


class OllamaAdapter(BaseLLMAdapter):
    """Ollama 本地模型适配器。"""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._client = Client(host=config.api_base)

    def complete(self, prompt: str, *, system: str = "", max_tokens: int | None = None) -> str:
        try:
            resp = self._client.generate(
                model=self.config.model,
                prompt=prompt,
                system=system,
                options={
                    "temperature": self.config.temperature,
                    "num_predict": max_tokens or self.config.max_tokens,
                },
            )
        except Exception as e:
            raise LLMError(f"Ollama 调用失败: {e}") from e

        self._tokens_in += resp.prompt_eval_count or 0
        self._tokens_out += resp.eval_count or 0

        return resp.response

    def complete_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system: str = "",
    ) -> dict[str, Any]:
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        structured_prompt = (
            f"{prompt}\n\n"
            f"你必须严格按以下 JSON Schema 输出 JSON，不要输出任何额外内容：\n"
            f"```json\n{schema_str}\n```\n"
            f"输出："
        )

        for _ in range(3):
            try:
                raw = self.complete(structured_prompt, system=system)
                # 提取 JSON 块
                raw = _extract_json(raw)
                return json.loads(raw)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                raise LLMError(f"Ollama 结构化调用失败: {e}") from e

        raise LLMError("Ollama 结构化调用失败：3次尝试均无法解析JSON")

    def count_tokens(self, text: str) -> int:
        return len(text) // 2


def _extract_json(raw: str) -> str:
    """从模型输出中提取 JSON 块。"""
    if "```json" in raw:
        start = raw.index("```json") + 7
        end = raw.index("```", start)
        return raw[start:end].strip()
    if "```" in raw:
        start = raw.index("```") + 3
        end = raw.index("```", start)
        return raw[start:end].strip()
    # 尝试取首尾大括号之间的内容
    s = raw.find("{")
    e = raw.rfind("}")
    if s != -1 and e != -1:
        return raw[s:e + 1]
    return raw
