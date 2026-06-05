"""CLI 入口。"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .config import AppConfig
from .parser import parse_file
from .pipeline import run_and_save

app = typer.Typer(name="novel2script", help="AI 辅助小说转剧本工具")
console = Console(force_terminal=False, legacy_windows=False)


@app.command()
def convert(
    source: str = typer.Argument(..., help="小说文件路径 (epub / txt / md)"),
    output: str = typer.Option("output/screenplay.yaml", "--output", "-o", help="输出 YAML 文件路径"),
    model: str = typer.Option("deepseek", "--model", "-m", help="LLM 服务商 (openai / deepseek / claude / ollama)"),
    title: str = typer.Option("", "--title", "-t", help="剧本标题（默认取自文件名）"),
    author: str = typer.Option("", "--author", "-a", help="原作者"),
    chapters: str = typer.Option("", "--chapters", "-c", help="指定章节范围，如 1-5"),
) -> None:
    """将小说章节转换为结构化 YAML 剧本。"""
    source_path = Path(source)
    if not source_path.exists():
        console.print(f"[red]文件不存在: {source}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Source:[/bold] {source}")
    console.print(f"[bold]Model:[/bold] {model}")

    with console.status("[bold green]Parsing file...[/bold green]"):
        all_chapters = parse_file(source_path)

    if not all_chapters:
        console.print("[red]No chapters detected[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Chapters: {len(all_chapters)}[/bold]")

    selected = _filter_chapters(all_chapters, chapters)
    if len(selected) < 3:
        console.print(f"[yellow]Warning: only {len(selected)} chapters, suggest at least 3[/yellow]")

    config = AppConfig.from_env(model)

    meta = {
        "title": title or source_path.stem,
        "source": source_path.name,
        "author": author,
    }

    console.print("[bold]Starting AI conversion...[/bold]")

    def progress_cb(phase: str, cur: int, total: int) -> None:
        console.print(f"  {phase}")

    try:
        screenplay = run_and_save(
            selected, config, output,
            meta=meta,
            progress=progress_cb,
        )
    except Exception as e:
        console.print(f"[red]Conversion failed: {e}[/red]")
        raise typer.Exit(1)

    total_scenes = sum(len(a.scenes) for a in screenplay.structure.acts)
    total_beats = sum(len(s.beats) for a in screenplay.structure.acts for s in a.scenes)
    dialogue_count = sum(
        1 for a in screenplay.structure.acts
        for s in a.scenes for b in s.beats
        if b.type == "dialogue"
    )

    console.print()
    console.print("[bold green]Done![/bold green]")
    console.print(f"[bold]Output:[/bold] {output}")
    console.print(f"[bold]Stats:[/bold] {len(screenplay.characters)} chars, "
                   f"{len(screenplay.structure.acts)} acts, {total_scenes} scenes, "
                   f"{total_beats} beats ({dialogue_count} dialogues)")


@app.command()
def validate(
    screenplay: str = typer.Argument(..., help="YAML 剧本文件路径"),
) -> None:
    """校验已有 YAML 剧本是否符合 Schema。"""
    from .schema.validator import validate_screenplay

    result = validate_screenplay(screenplay)

    if result.valid:
        console.print("[bold green]PASS[/bold green]")
    else:
        console.print("[bold red]FAIL[/bold red]")
        for err in result.errors:
            console.print(f"  [red]- {err}[/red]")

    if result.warnings:
        for w in result.warnings:
            console.print(f"  [yellow]* {w}[/yellow]")


@app.command()
def launch(
    share: bool = typer.Option(False, "--share", help="生成公开分享链接"),
    port: int = typer.Option(7860, "--port", "-p", help="监听端口"),
) -> None:
    """启动 Gradio Web UI。"""
    import os as _os
    for _key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        _os.environ.pop(_key, None)
    _os.environ["no_proxy"] = "127.0.0.1,localhost"

    from .web import create_ui

    ui = create_ui()
    console.print(f"[bold]Web UI starting at: http://127.0.0.1:{port}[/bold]")
    ui.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=share,
        inbrowser=False,
    )


def _filter_chapters(all_chapters, spec: str):
    if not spec:
        return all_chapters
    parts = spec.split("-")
    if len(parts) == 2:
        try:
            start = int(parts[0]) - 1
            end = int(parts[1])
            return all_chapters[start:end]
        except (ValueError, IndexError):
            pass
    return all_chapters


if __name__ == "__main__":
    app()
