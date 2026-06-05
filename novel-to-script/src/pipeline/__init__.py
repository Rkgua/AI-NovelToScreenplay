"""AI 转换流水线 — 角色识别、分场、对话提取、剧本组装。

用法:
    from src.pipeline import run_pipeline
    from src.config import AppConfig
    from src.parser import parse_file

    chapters = parse_file("novel.txt")
    config = AppConfig.from_env("openai")
    screenplay = run_pipeline(chapters, config, meta={"title": "我的剧本"})
"""

from .assembler import assemble_screenplay
from .character import extract_characters
from .pipeline import run_and_save, run_pipeline
from .scene import detect_scenes
from .summary import summarize_chapter

__all__ = [
    "assemble_screenplay",
    "detect_scenes",
    "extract_characters",
    "run_and_save",
    "run_pipeline",
    "summarize_chapter",
]
