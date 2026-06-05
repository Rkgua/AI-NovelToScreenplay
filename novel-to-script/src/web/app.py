"""Gradio Web UI — 小说转剧本交互界面。"""

from __future__ import annotations

from pathlib import Path

import gradio as gr

from ..config import AppConfig
from ..parser import parse_file
from ..pipeline import run_pipeline
from ..schema.validator import save_screenplay

_OUTPUT_DIR = Path("output")


def create_ui() -> gr.Blocks:
    """构建 Gradio 界面。"""
    with gr.Blocks(title="Novel2Script - AI 小说转剧本") as app:
        gr.Markdown(
            "# 🎬 Novel2Script\n"
            "将 3 章以上的小说文本自动转换为结构化 YAML 剧本，支持 EPUB / TXT / Markdown 格式。"
        )

        with gr.Row(equal_height=False):
            with gr.Column(scale=2, min_width=320):
                gr.Markdown("### 📥 输入")

                file_input = gr.File(
                    label="上传小说文件",
                    file_types=[".txt", ".md", ".epub"],
                    file_count="single",
                )

                model_choice = gr.Dropdown(
                    choices=["openai", "claude", "ollama"],
                    value="openai",
                    label="🤖 LLM 服务商",
                )

                model_name = gr.Textbox(
                    label="模型名（可选）",
                    placeholder="留空使用默认模型",
                    value="",
                )

                with gr.Row():
                    title_input = gr.Textbox(
                        label="剧本标题",
                        placeholder="默认取自文件名",
                        scale=2,
                    )
                    author_input = gr.Textbox(
                        label="原作者",
                        placeholder="选填",
                        scale=1,
                    )

                chapter_range = gr.Textbox(
                    label="章节范围",
                    placeholder="如 1-5（留空处理全部章节）",
                )

                convert_btn = gr.Button("🚀 开始转换", variant="primary", size="lg")

            with gr.Column(scale=3, min_width=480):
                gr.Markdown("### 📤 输出")

                status_box = gr.Textbox(
                    label="进度",
                    value="等待开始 — 请上传小说文件并点击「开始转换」",
                    lines=3,
                    interactive=False,
                )

                stats_md = gr.Markdown("")

                yaml_preview = gr.Code(
                    label="YAML 剧本预览",
                    language="yaml",
                    lines=22,
                    elem_classes=["yaml-preview"],
                    interactive=False,
                )

                with gr.Row():
                    download_btn = gr.DownloadButton(
                        label="📥 下载 YAML",
                        variant="secondary",
                        visible=False,
                    )

        convert_btn.click(
            fn=_run_conversion,
            inputs=[file_input, model_choice, model_name, title_input, author_input, chapter_range],
            outputs=[status_box, stats_md, yaml_preview, download_btn],
        )

    return app


def _run_conversion(
    file_obj,
    model: str,
    model_override: str,
    title: str,
    author: str,
    chapter_range: str,
    progress=gr.Progress(),
):
    """执行转换流水线并返回 UI 更新。"""
    if file_obj is None:
        gr.Warning("请先上传小说文件")
        return ("❌ 请先上传小说文件", "", "", gr.DownloadButton(visible=False))

    file_path = Path(file_obj.name)
    progress(0.0, desc="正在解析文件...")

    try:
        all_chapters = parse_file(file_path)
    except Exception as e:
        gr.Warning(f"文件解析失败: {e}")
        return (f"❌ 解析失败: {e}", "", "", gr.DownloadButton(visible=False))

    if not all_chapters:
        gr.Warning("未检测到任何章节")
        return ("❌ 未检测到任何章节", "", "", gr.DownloadButton(visible=False))

    selected = _filter_by_range(all_chapters, chapter_range)
    progress(0.05, desc=f"检测到 {len(all_chapters)} 章，处理 {len(selected)} 章...")

    if len(selected) < 3:
        gr.Info(f"仅 {len(selected)} 个章节，建议至少 3 章以获得较完整的剧本结构")

    config = AppConfig.from_env(model)
    if model_override:
        config.llm.model = model_override

    meta = {
        "title": title or file_path.stem,
        "source": file_path.name,
        "author": author,
    }

    _steps = len(selected) + 1
    _count = 0

    def progress_cb(phase: str, cur: int, total: int) -> None:
        nonlocal _count
        _count += 1
        frac = min(0.9, _count / _steps)
        progress(frac, desc=phase)

    try:
        screenplay = run_pipeline(selected, config, meta=meta, progress=progress_cb)
    except Exception as e:
        gr.Warning(f"转换失败: {e}")
        return (f"❌ 转换失败: {e}", "", "", gr.DownloadButton(visible=False))

    progress(0.95, desc="正在生成 YAML...")

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _OUTPUT_DIR / f"{file_path.stem}_screenplay.yaml"
    save_screenplay(screenplay, output_path)

    progress(1.0, desc="完成!")

    total_scenes = sum(len(a.scenes) for a in screenplay.structure.acts)
    total_beats = sum(len(s.beats) for a in screenplay.structure.acts for s in a.scenes)
    dialogue_count = sum(
        1 for a in screenplay.structure.acts
        for s in a.scenes for b in s.beats
        if b.type == "dialogue"
    )

    stats = (
        f"### 📊 统计\n"
        f"| 角色 | 幕 | 场次 | 节拍 | 对白 |\n"
        f"|------|-----|------|------|------|\n"
        f"| {len(screenplay.characters)} | {len(screenplay.structure.acts)} "
        f"| {total_scenes} | {total_beats} | {dialogue_count} |"
    )

    status = f"✅ 转换完成！文件已保存至: `{output_path}`"

    yaml_text = output_path.read_text(encoding="utf-8")

    download = gr.DownloadButton(
        label="📥 下载 YAML",
        value=str(output_path),
        visible=True,
    )

    return (status, stats, yaml_text, download)


def _filter_by_range(chapters, spec: str):
    if not spec:
        return chapters
    parts = spec.split("-")
    if len(parts) == 2:
        try:
            start = int(parts[0]) - 1
            end = int(parts[1])
            return chapters[start:end]
        except (ValueError, IndexError):
            pass
    return chapters
