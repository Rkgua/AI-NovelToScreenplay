"""Gradio Web UI — 小说转剧本交互界面。"""

from __future__ import annotations

import re
import tempfile
import traceback
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
        gr.Markdown("# Novel2Script\n将 3 章以上的小说文本自动转换为结构化 YAML 剧本")

        saved_path_state = gr.State("")
        is_valid_state = gr.State(True)

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 输入")

                file_input = gr.File(label="上传小说文件", file_types=[".txt", ".md", ".epub"])
                model_choice = gr.Dropdown(
                    choices=["deepseek", "openai", "claude", "ollama"],
                    value="deepseek", label="LLM 服务商",
                )
                title_input = gr.Textbox(label="剧本标题", placeholder="默认取自文件名")
                author_input = gr.Textbox(label="原作者", placeholder="选填")
                convert_btn = gr.Button("开始转换", variant="primary", size="lg")

            with gr.Column(scale=3):
                gr.Markdown("### 输出")

                status_box = gr.Textbox(
                    label="状态",
                    value="等待开始 — 请上传文件并点击「开始转换」",
                    lines=3,
                )

                with gr.Row():
                    validate_btn = gr.Button("校验", variant="secondary", size="sm")
                    save_btn = gr.Button("保存修改并导出", variant="primary", size="sm")
                    download_btn = gr.File(label="下载 YAML", visible=False)

                yaml_preview = gr.Code(
                    label="YAML 剧本（可直接修改）",
                    language="yaml", lines=18, interactive=True,
                )

                annotated_view = gr.HTML(value="", visible=False)
                validation_status = gr.HTML(value="")

        # ── 事件 ──
        convert_btn.click(
            fn=_run_conversion,
            inputs=[file_input, model_choice, title_input, author_input],
            outputs=[status_box, yaml_preview, download_btn, saved_path_state,
                     validation_status, annotated_view, is_valid_state],
        )

        validate_btn.click(
            fn=_do_validate,
            inputs=[yaml_preview],
            outputs=[validation_status, annotated_view, is_valid_state],
        )

        save_btn.click(
            fn=_do_save,
            inputs=[yaml_preview, saved_path_state, is_valid_state],
            outputs=[status_box, download_btn, validation_status, annotated_view],
        )

    return app


# ── 回调 ──────────────────────────────────────────────

def _run_conversion(file_obj, model, title, author):
    if file_obj is None:
        return ("请先上传小说文件", "", gr.File(visible=False), "",
                gr.HTML(value=""), gr.HTML(value=""), gr.update(value=True))

    try:
        fp = Path(file_obj) if isinstance(file_obj, str) else Path(file_obj.name)
        chapters = parse_file(fp)
        config = AppConfig.from_env(model)
        meta = {"title": title or fp.stem, "source": fp.name, "author": author}
        sp = run_pipeline(chapters, config, meta=meta)

        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = _OUTPUT_DIR / f"{fp.stem}_screenplay.yaml"
        save_screenplay(sp, out)
        yaml_text = out.read_text(encoding="utf-8")

        total_scenes = sum(len(a.scenes) for a in sp.structure.acts)
        total_beats = sum(len(s.beats) for a in sp.structure.acts for s in a.scenes)
        dialogue_count = sum(
            1 for a in sp.structure.acts for s in a.scenes for b in s.beats
            if b.type == "dialogue"
        )

        stats_line = (
            f"角色:{len(sp.characters)} 幕:{len(sp.structure.acts)} "
            f"场:{total_scenes} 节拍:{total_beats} 对白:{dialogue_count}"
        )

        return (
            f"转换完成！{stats_line}\n文件: {out}",
            yaml_text,
            gr.File(value=str(out), visible=True, label="下载 YAML"),
            str(out),
            gr.HTML(value="", visible=False),
            gr.HTML(value="", visible=False),
            gr.update(value=True),
        )
    except Exception as e:
        return (
            f"转换失败:\n{traceback.format_exc()}",
            "", gr.File(visible=False), "",
            gr.HTML(value=""), gr.HTML(value=""),
            gr.update(value=True),
        )


def _do_validate(yaml_text):
    if not yaml_text.strip():
        return (gr.HTML(value=""), gr.HTML(value=""), gr.update(value=True))

    tmp = Path(tempfile.gettempdir()) / "_n2s_validate.yaml"
    tmp.write_text(yaml_text, encoding="utf-8")
    result = validate_screenplay(tmp)

    if result.valid:
        return (
            _html('<div style="background:#e8f5e9;padding:8px;border-radius:6px;color:#2e7d32;font-weight:bold;">校验通过</div>'),
            gr.HTML(value="", visible=False),
            gr.update(value=True),
        )

    items = _find_error_lines(yaml_text, result.errors)
    return (
        _html(f'<div style="background:#ffebee;padding:8px;border-radius:6px;color:#c62828;font-weight:bold;">{len(items)} 处错误</div>'),
        gr.HTML(value=_build_annotated_view(yaml_text, items), visible=True),
        gr.update(value=False),
    )


def _do_save(yaml_text, saved_path, is_valid):
    if not yaml_text.strip():
        return ("YAML 为空", gr.File(visible=False),
                gr.HTML(value=""), gr.HTML(value=""))

    status, annotated, valid_state = _do_validate(yaml_text)

    if not valid_state["value"]:
        return ("校验未通过，请修复错误后再保存", gr.File(visible=False), status, annotated)

    out = (Path(saved_path).parent / f"{Path(saved_path).stem}_edited.yaml") if saved_path else _OUTPUT_DIR / "screenplay_edited.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml_text, encoding="utf-8")

    return (
        f"已保存: {out}",
        gr.File(value=str(out), visible=True, label="下载修改后的 YAML"),
        status,
        annotated,
    )


# ── 辅助 ──────────────────────────────────────────────

def _html(content: str) -> gr.HTML:
    return gr.HTML(value=content, visible=True)


def _build_annotated_view(yaml_text: str, error_items: list[tuple[int, str]]) -> str:
    error_lines: dict[int, list[str]] = {}
    for lineno, msg in error_items:
        error_lines.setdefault(lineno, []).append(msg)

    lines = yaml_text.split("\n")
    parts = [
        '<div style="border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;font:12px Consolas,monospace;">',
        f'<div style="background:#ffebee;color:#c62828;padding:6px 12px;font-weight:bold;">{len(error_items)} 处错误</div>',
        '<div style="max-height:400px;overflow-y:auto;background:#fafafa;">',
    ]

    for i, line_text in enumerate(lines, 1):
        errs = error_lines.get(i, [])
        ln_style = 'color:#c62828;font-weight:bold;' if errs else 'color:#bbb;'
        row_style = 'background:#fff0f0;' if errs else ''
        escaped = line_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") or "&nbsp;"
        parts.append(
            f'<div style="{row_style}padding:1px 8px;line-height:1.5;white-space:pre;">'
            f'<span style="display:inline-block;width:42px;text-align:right;{ln_style}">{"▶" if errs else ""}{i}</span>'
            f' {escaped}</div>'
        )
        for msg in errs:
            parts.append(
                f'<div style="background:#ffebee;padding:2px 8px 2px 54px;font-size:11px;color:#c62828;">{msg}</div>'
            )

    parts.append('</div></div>')
    return "\n".join(parts)


def _find_error_lines(yaml_text: str, errors: list[str]) -> list[tuple[int, str]]:
    lines = yaml_text.split("\n")
    return [(_search_line(lines, e), e) for e in errors]


def _search_line(lines: list[str], err: str) -> int:
    m = re.search(r"角色\s*'(.+?)'\s*的关系引用了不存在的角色\s*'(.+?)'", err)
    if m:
        char_id, target = m.group(1), m.group(2)
        for i, line in enumerate(lines, 1):
            if re.search(rf"\b{re.escape(target)}\b", line):
                return i
        loc = _find_char_id_line(lines, char_id)
        return loc or 1

    m = re.search(r"第(\d+)幕第(\d+)场的对白引用了不存在的角色\s*'(.+?)'", err)
    if m:
        return _find_in_scene(lines, int(m.group(2)), m.group(3)) or 1

    m = re.search(r"第(\d+)幕第(\d+)场引用了不存在的角色\s*'(.+?)'", err)
    if m:
        return _find_in_scene(lines, int(m.group(2)), m.group(3)) or 1

    if "重复" in err and ("场次" in err or "场景" in err or "编号" in err):
        seen = set()
        for i, line in enumerate(lines, 1):
            m2 = re.search(r"scene_number:\s*(\d+)", line)
            if m2:
                num = int(m2.group(1))
                if num in seen:
                    return i
                seen.add(num)
        return 1

    m = re.search(r"场景\s*(\d+)\s*后出现场景\s*(\d+)", err)
    if m:
        target = int(m.group(2))
        for i, line in enumerate(lines, 1):
            if re.search(rf"scene_number:\s*{target}\b", line):
                return i
        return 1

    return 1


def _find_in_scene(lines, scene_num, target):
    in_scene = False
    for i, line in enumerate(lines, 1):
        if re.search(rf"scene_number:\s*{scene_num}\b", line):
            in_scene = True
            continue
        if in_scene and re.search(r"scene_number:", line):
            return None
        if in_scene and target in line:
            return i
    return None


def _find_char_id_line(lines, char_id):
    for i, line in enumerate(lines, 1):
        if re.match(rf"\s*- id:\s*{re.escape(char_id)}\s*$", line):
            return i
    return None
