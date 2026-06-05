"""LLM 统一接口 — 多模型适配层。

用法:
    from src.llm import create_adapter
    from src.config import AppConfig

    cfg = AppConfig.from_env("openai")
    adapter = create_adapter(cfg.llm)
    result = adapter.complete("你好")
"""

from .base import BaseLLMAdapter, LLMError, build_structured_schema, create_adapter

__all__ = [
    "BaseLLMAdapter",
    "LLMError",
    "build_structured_schema",
    "create_adapter",
]
