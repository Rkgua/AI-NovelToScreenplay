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

        saved_path_state = gr.State("")

        with gr.Row(equal_height=False):
            with gr.Column(scale=2, min_width=320):
                gr.Markdown("### 输入")

                file_input = gr.File(
                    label="上传小说文件",
                    file_types=[".txt", ".md", ".epub"],
                    file_count="single",
                )

                model_choice = gr.Dropdown(
                    choices=["deepseek", "openai", "claude", "ollama"],
                    value="deepseek",
                    label="LLM 服务商",
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

                convert_btn = gr.Button("开始转换", variant="primary", size="lg")

            with gr.Column(scale=3, min_width=480):
                gr.Markdown("### 输出")

                status_box = gr.Textbox(
                    label="状态",
                    value="等待开始 — 请上传小说文件并点击「开始转换」",
                    lines=3,
                    interactive=False,
                )

                stats_md = gr.Markdown("")

                yaml_preview = gr.Code(
                    label="YAML 剧本预览（点击编辑按钮后可修改）",
                    language="yaml",
                    lines=22,
                    elem_classes=["yaml-preview"],
                    interactive=False,
                )

                with gr.Row():
                    edit_btn = gr.Button("编辑", variant="secondary", size="sm", visible=False)
                    validate_btn = gr.Button("校验", variant="secondary", size="sm", visible=False)
                    save_btn = gr.Button("保存修改并导出", variant="primary", size="sm", visible=False)

                with gr.Row():
                    validate_result_box = gr.Textbox(
                        label="校验结果",
                        interactive=False,
                        visible=False,
                    )
                    download_btn = gr.DownloadButton(
                        label="下载 YAML",
                        variant="secondary",
                        visible=False,
                    )

        convert_btn.click(
            fn=_run_conversion,
            inputs=[file_input, model_choice, title_input, author_input],
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
    title: str,
    author: str,
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
        gr.Warning("请先上传小说文件")
        return ("请先上传小说文件", "", "", *hide)

    file_path = Path(file_obj.name)
    progress(0.0, desc="正在解析文件...")

    try:
        all_chapters = parse_file(file_path)
    except Exception as e:
        gr.Warning(f"文件解析失败: {e}")
        return (f"解析失败: {e}", "", "", *hide)

    if not all_chapters:
        gr.Warning("未检测到任何章节")
        return ("未检测到任何章节", "", "", *hide)

    selected = all_chapters
    progress(0.05, desc=f"检测到 {len(all_chapters)} 个章节...")

    if len(selected) < 3:
        gr.Info(f"仅 {len(selected)} 个章节，建议至少 3 章以获得较好的结果")

    config = AppConfig.from_env(model)

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
        return (f"转换失败: {e}", "", "", *hide)

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
        f"### 统计\n"
        f"| 角色 | 幕 | 场次 | 节拍 | 对白 |\n"
        f"|------|-----|------|------|------|\n"
        f"| {len(screenplay.characters)} | {len(screenplay.structure.acts)} "
        f"| {total_scenes} | {total_beats} | {dialogue_count} |"
    )

    status = f"转换完成！已保存至: `{output_path}`"

    yaml_text = output_path.read_text(encoding="utf-8")

    return (
        status,
        stats,
        yaml_text,
        gr.DownloadButton(label="下载 YAML", value=str(output_path), visible=True),
        str(output_path),
        gr.Button(visible=True),
        gr.Button(visible=True),
        gr.Button(visible=True),
        gr.Textbox(visible=False),
    )


def _enable_edit(yaml_text: str):
    """启用编辑模式。"""
    return (
        gr.Code(value=yaml_text, interactive=True, label="YAML 剧本（编辑模式）"),
        gr.Button(visible=False),
        gr.Button(visible=True),
        gr.Button(visible=True),
        gr.Textbox(visible=False),
    )


def _validate_edited_yaml(yaml_text: str):
    """校验编辑后的 YAML。"""
    tmp = Path(tempfile.gettempdir()) / "_n2s_validate.yaml"
    tmp.write_text(yaml_text, encoding="utf-8")
    result = validate_screenplay(tmp)

    if result.valid:
        msg = "校验通过"
    else:
        msg = "校验失败\n" + "\n".join(result.errors)

    if result.warnings:
        msg += "\n\n警告:\n" + "\n".join(result.warnings)

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
        f"已保存: `{out_path}`",
        gr.DownloadButton(label="下载修改后的 YAML", value=str(out_path), visible=True),
        gr.Code(value=yaml_text, interactive=False, label="YAML 剧本预览"),
        gr.Button(visible=False),
        gr.Button(visible=False),
        gr.Button(visible=False),
        gr.Textbox(visible=False),
    )
