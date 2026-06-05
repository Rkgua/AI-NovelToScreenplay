"""Gradio Web UI — 小说转剧本交互界面。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import gradio as gr

from ..config import AppConfig
from ..parser import parse_file
from ..pipeline import run_pipeline
from ..schema.validator import save_screenplay, validate_screenplay

_OUTPUT_DIR = Path("output")


def create_ui() -> gr.Blocks:
    """构建 Gradio 界面。"""
    with gr.Blocks(title="Novel2Script - AI 小说转剧本") as app:
        gr.Markdown(
            "# Novel2Script\n"
            "将 3 章以上的小说文本自动转换为结构化 YAML 剧本"
        )

        # ── 隐藏的状态 ──
        saved_path_state = gr.State("")

        with gr.Row(equal_height=False):
            with gr.Column(scale=2, min_width=320):
                gr.Markdown("### Input")

                file_input = gr.File(
                    label="Upload Novel",
                    file_types=[".txt", ".md", ".epub"],
                    file_count="single",
                )

                model_choice = gr.Dropdown(
                    choices=["deepseek", "openai", "claude", "ollama"],
                    value="deepseek",
                    label="LLM Provider",
                )

                model_name = gr.Textbox(
                    label="Model Name (optional)",
                    placeholder="Leave blank for default",
                    value="",
                )

                with gr.Row():
                    title_input = gr.Textbox(
                        label="Title",
                        placeholder="Default from filename",
                        scale=2,
                    )
                    author_input = gr.Textbox(
                        label="Author",
                        placeholder="Optional",
                        scale=1,
                    )

                chapter_range = gr.Textbox(
                    label="Chapter Range",
                    placeholder="e.g. 1-5 (blank = all)",
                )

                convert_btn = gr.Button("Start Conversion", variant="primary", size="lg")

            with gr.Column(scale=3, min_width=480):
                gr.Markdown("### Output")

                status_box = gr.Textbox(
                    label="Status",
                    value="Waiting — upload a file and click Start Conversion",
                    lines=3,
                    interactive=False,
                )

                stats_md = gr.Markdown("")

                yaml_preview = gr.Code(
                    label="YAML Preview (click edit button to modify)",
                    language="yaml",
                    lines=22,
                    elem_classes=["yaml-preview"],
                    interactive=False,
                )

                with gr.Row():
                    edit_btn = gr.Button("Edit", variant="secondary", size="sm", visible=False)
                    validate_btn = gr.Button("Validate", variant="secondary", size="sm", visible=False)
                    save_btn = gr.Button("Save Edits & Export", variant="primary", size="sm", visible=False)

                with gr.Row():
                    validate_result_box = gr.Textbox(
                        label="Validation Result",
                        interactive=False,
                        visible=False,
                    )
                    download_btn = gr.DownloadButton(
                        label="Download YAML",
                        variant="secondary",
                        visible=False,
                    )

        # ── 事件绑定 ──
        convert_btn.click(
            fn=_run_conversion,
            inputs=[file_input, model_choice, model_name, title_input, author_input, chapter_range],
            outputs=[status_box, stats_md, yaml_preview, download_btn, saved_path_state,
                     edit_btn, validate_btn, save_btn, validate_result_box],
        )

        edit_btn.click(
            fn=_enable_edit,
            inputs=[yaml_preview],
            outputs=[yaml_preview, edit_btn, save_btn, validate_btn, validate_result_box],
        )

        validate_btn.click(
            fn=_validate_edited_yaml,
            inputs=[yaml_preview],
            outputs=[validate_result_box],
        )

        save_btn.click(
            fn=_save_edited_yaml,
            inputs=[yaml_preview, saved_path_state],
            outputs=[status_box, download_btn, yaml_preview, edit_btn, save_btn, validate_btn, validate_result_box],
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
    hide = (
        gr.DownloadButton(visible=False),
        "",
        gr.Button(visible=False),
        gr.Button(visible=False),
        gr.Button(visible=False),
        gr.Textbox(visible=False),
    )

    if file_obj is None:
        gr.Warning("Please upload a file")
        return ("No file uploaded", "", "", *hide)

    file_path = Path(file_obj.name)
    progress(0.0, desc="Parsing file...")

    try:
        all_chapters = parse_file(file_path)
    except Exception as e:
        gr.Warning(f"Parse failed: {e}")
        return (f"Parse failed: {e}", "", "", *hide)

    if not all_chapters:
        gr.Warning("No chapters detected")
        return ("No chapters detected", "", "", *hide)

    selected = _filter_by_range(all_chapters, chapter_range)
    progress(0.05, desc=f"Found {len(all_chapters)} chapters, processing {len(selected)}...")

    if len(selected) < 3:
        gr.Info(f"Only {len(selected)} chapters, 3+ recommended for best results")

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
        gr.Warning(f"Conversion failed: {e}")
        return (f"Conversion failed: {e}", "", "", *hide)

    progress(0.95, desc="Generating YAML...")

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _OUTPUT_DIR / f"{file_path.stem}_screenplay.yaml"
    save_screenplay(screenplay, output_path)

    progress(1.0, desc="Done!")

    total_scenes = sum(len(a.scenes) for a in screenplay.structure.acts)
    total_beats = sum(len(s.beats) for a in screenplay.structure.acts for s in a.scenes)
    dialogue_count = sum(
        1 for a in screenplay.structure.acts
        for s in a.scenes for b in s.beats
        if b.type == "dialogue"
    )

    stats = (
        f"### Stats\n"
        f"| Chars | Acts | Scenes | Beats | Dialogues |\n"
        f"|-------|------|--------|-------|-----------|\n"
        f"| {len(screenplay.characters)} | {len(screenplay.structure.acts)} "
        f"| {total_scenes} | {total_beats} | {dialogue_count} |"
    )

    status = f"Done! Saved to: `{output_path}`"

    yaml_text = output_path.read_text(encoding="utf-8")

    return (
        status,
        stats,
        yaml_text,
        gr.DownloadButton(label="Download YAML", value=str(output_path), visible=True),
        str(output_path),
        gr.Button(visible=True),           # edit_btn
        gr.Button(visible=True),           # validate_btn
        gr.Button(visible=True),           # save_btn
        gr.Textbox(visible=False),         # validate_result_box (hidden)
    )


def _enable_edit(yaml_text: str):
    """启用编辑模式。"""
    return (
        gr.Code(value=yaml_text, interactive=True, label="YAML (editing mode)"),
        gr.Button(visible=False),  # edit_btn
        gr.Button(visible=True),   # save_btn
        gr.Button(visible=True),   # validate_btn
        gr.Textbox(visible=False),  # validate_result_box
    )


def _validate_edited_yaml(yaml_text: str):
    """校验编辑后的 YAML。"""
    tmp = Path(tempfile.gettempdir()) / "_n2s_validate.yaml"
    tmp.write_text(yaml_text, encoding="utf-8")
    result = validate_screenplay(tmp)

    if result.valid:
        msg = "PASS"
    else:
        msg = "FAIL\n" + "\n".join(result.errors)

    if result.warnings:
        msg += "\n\nWarnings:\n" + "\n".join(result.warnings)

    return gr.Textbox(value=msg, visible=True)


def _save_edited_yaml(yaml_text: str, saved_path: str):
    """保存编辑后的 YAML 并返回下载。"""
    if saved_path:
        out = Path(saved_path)
        stem = out.stem
        out_path = out.parent / f"{stem}_edited.yaml"
    else:
        out_path = _OUTPUT_DIR / "screenplay_edited.yaml"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml_text, encoding="utf-8")

    return (
        f"Saved: `{out_path}`",
        gr.DownloadButton(label="Download Edited YAML", value=str(out_path), visible=True),
        gr.Code(value=yaml_text, interactive=False, label="YAML Preview"),
        gr.Button(visible=False),  # edit_btn
        gr.Button(visible=False),  # save_btn
        gr.Button(visible=False),  # validate_btn
        gr.Textbox(visible=False),  # validate_result_box
    )


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
