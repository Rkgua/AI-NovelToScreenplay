"""流水线编排器 — 串联全部 AI 转换阶段。"""

from __future__ import annotations

from typing import Callable

from ..config import AppConfig
from ..llm.base import BaseLLMAdapter, LLMError, create_adapter
from ..parser.chapter import Chapter
from ..schema.screenplay import Screenplay
from ..schema.validator import save_screenplay
from .assembler import assemble_screenplay
from .character import extract_characters
from .scene import detect_scenes
from .summary import summarize_chapter
from .dialogue import extract_beats


ProgressCallback = Callable[[str, int, int], None]


def run_pipeline(
    chapters: list[Chapter],
    config: AppConfig,
    *,
    meta: dict | None = None,
    progress: ProgressCallback | None = None,
) -> Screenplay:
    """执行完整的 AI 转换流水线。

    Args:
        chapters: 解析好的章节列表
        config: 应用配置（包含 LLM 配置）
        meta: 剧本元信息（title, author 等）
        progress: 进度回调 (phase: str, current: int, total: int)

    Returns:
        完整的 Screenplay 对象
    """
    if not chapters:
        raise ValueError("章节列表为空")

    meta = meta or {}
    adapter = create_adapter(config.llm)
    total_chapters = len(chapters)

    # ── 阶段 1: 角色识别 ──
    _report(progress, "角色识别", 0, total_chapters)
    try:
        characters_raw = extract_characters(adapter, chapters)
    except LLMError as e:
        raise LLMError(f"角色识别失败: {e}") from e
    _report(progress, "角色识别完成", 0, total_chapters)

    # ── 阶段 2-4: 逐章处理 ──
    chapters_data: list[dict] = []
    summaries: list[str] = []

    for i, chapter in enumerate(chapters):
        _report(progress, f"处理章节 {i + 1}/{total_chapters}: {chapter.title}", i + 1, total_chapters)

        # 2. 生成章节摘要
        prev_summary = summaries[-1] if summaries else ""
        summary = summarize_chapter(adapter, chapter, characters_raw, prev_summary)
        summaries.append(summary)

        # 3. 分场
        scenes_raw = detect_scenes(adapter, chapter, characters_raw, prev_summary)

        # 4. 逐场提取节拍
        chapter_text = chapter.full_text
        for sc in scenes_raw:
            _report(progress, f"  └ 提取场次节拍: {sc.get('summary', '')[:30]}...", i + 1, total_chapters)
            scene_text_prompt = (
                f"请为以下场次提取节拍：\n\n"
                f"场次信息：{sc.get('location_type', 'INT')} - {sc.get('location', '')} - {sc.get('time', '')}\n"
                f"场次概要：{sc.get('summary', '')}\n\n"
                f"章节原文供参考：\n{chapter_text}"
            )
            beats = extract_beats(adapter, scene_text_prompt, characters_raw)
            sc["beats"] = beats

        chapters_data.append({
            "chapter_title": chapter.title,
            "scenes": scenes_raw,
        })

        _report(progress, f"完成章节 {i + 1}/{total_chapters}", i + 1, total_chapters)

    # ── 阶段 5: 组装 ──
    _report(progress, "组装剧本", total_chapters, total_chapters)
    screenplay = assemble_screenplay(
        meta=meta,
        characters_raw=characters_raw,
        chapters_data=chapters_data,
    )
    _report(progress, "完成", total_chapters, total_chapters)

    return screenplay


def run_and_save(
    chapters: list[Chapter],
    config: AppConfig,
    output_path: str,
    *,
    meta: dict | None = None,
    progress: ProgressCallback | None = None,
) -> Screenplay:
    """执行流水线并保存为 YAML。"""
    screenplay = run_pipeline(chapters, config, meta=meta, progress=progress)
    save_screenplay(screenplay, output_path)
    return screenplay


def _report(cb: ProgressCallback | None, msg: str, cur: int, total: int) -> None:
    if cb:
        cb(msg, cur, total)
