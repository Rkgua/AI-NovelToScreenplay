import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


def _load_dotenv_once() -> None:
    load_dotenv()


_load_dotenv_once()


@dataclass
class LLMConfig:
    """LLM 模型配置。"""

    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    api_base: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096

    @classmethod
    def from_env(cls, provider: str | None = None) -> "LLMConfig":
        provider = provider or os.getenv("N2S_LLM_PROVIDER", "openai")
        match provider:
            case "openai":
                return cls(
                    provider="openai",
                    model=os.getenv("N2S_OPENAI_MODEL", "gpt-4o"),
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                    api_base=os.getenv("OPENAI_API_BASE", ""),
                )
            case "claude":
                return cls(
                    provider="claude",
                    model=os.getenv("N2S_CLAUDE_MODEL", "claude-sonnet-4-20250514"),
                    api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                )
            case "deepseek":
                return cls(
                    provider="deepseek",
                    model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                    api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                    api_base="https://api.deepseek.com",
                )
            case "ollama":
                return cls(
                    provider="ollama",
                    model=os.getenv("N2S_OLLAMA_MODEL", "qwen3"),
                    api_base=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                )
            case _:
                raise ValueError(f"Unknown LLM provider: {provider}")


@dataclass
class PipelineConfig:
    """转换流水线配置。"""

    chunk_size: int = 8000
    chunk_overlap: int = 500
    chapter_summary_tokens: int = 512
    temperature: float = 0.3
    max_retries: int = 3


@dataclass
class AppConfig:
    """全局应用配置。"""

    llm: LLMConfig = field(default_factory=LLMConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    output_dir: str = "output"

    @classmethod
    def from_env(cls, provider: str | None = None) -> "AppConfig":
        return cls(
            llm=LLMConfig.from_env(provider),
            pipeline=PipelineConfig(),
            output_dir=os.getenv("N2S_OUTPUT_DIR", "output"),
        )
