"""CLI 入口。"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import AppConfig
from .parser import parse_file
from .pipeline import run_and_save

app = typer.Typer(name="novel2script", help="AI 辅助小说转剧本工具")
console = Console()


@app.command()
def convert(
    source: str = typer.Argument(..., help="小说文件路径 (epub / txt / md)"),
    output: str = typer.Option("output/screenplay.yaml", "--output", "-o", help="输出 YAML 文件路径"),
    model: str = typer.Option("openai", "--model", "-m", help="LLM 服务商 (openai / claude / ollama)"),
    title: str = typer.Option("", "--title", "-t", help="剧本标题（默认取自文件名）"),
    author: str = typer.Option("", "--author", "-a", help="原作者"),
    chapters: str = typer.Option("", "--chapters", "-c", help="指定章节范围，如 1-5"),
) -> None:
    """将小说章节转换为结构化 YAML 剧本。"""
    source_path = Path(source)
    if not source_path.exists():
        console.print(f"[red]文件不存在: {source}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]📖 源文件:[/bold] {source}")
    console.print(f"[bold]🤖 模型:[/bold] {model}")

    # 解析
    with console.status("[bold green]正在解析文件...[/bold green]"):
        all_chapters = parse_file(source_path)

    if not all_chapters:
        console.print("[red]未检测到任何章节[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]📑 检测到 {len(all_chapters)} 个章节[/bold]")

    # 章节筛选
    selected = _filter_chapters(all_chapters, chapters)
    if len(selected) < 3:
        console.print(f"[yellow]⚠ 仅 {len(selected)} 个章节，建议至少 3 章以获得较完整的结果[/yellow]")

    # 配置
    config = AppConfig.from_env(model)

    # 元信息
    meta = {
        "title": title or source_path.stem,
        "source": source_path.name,
        "author": author,
    }

    # 转换
    console.print("[bold]🚀 开始 AI 转换...[/bold]")

    def progress_cb(phase: str, cur: int, total: int) -> None:
        console.print(f"  {phase}")

    try:
        screenplay = run_and_save(
            selected, config, output,
            meta=meta,
            progress=progress_cb,
        )
    except Exception as e:
        console.print(f"[red]转换失败: {e}[/red]")
        raise typer.Exit(1)

    total_scenes = sum(len(a.scenes) for a in screenplay.structure.acts)
    total_beats = sum(len(s.beats) for a in screenplay.structure.acts for s in a.scenes)
    dialogue_count = sum(
        1 for a in screenplay.structure.acts
        for s in a.scenes for b in s.beats
        if b.type == "dialogue"
    )

    console.print()
    console.print("[bold green]✅ 转换完成![/bold green]")
    console.print(f"[bold]📄 输出:[/bold] {output}")
    console.print(f"[bold]📊 统计:[/bold] {len(screenplay.characters)} 个角色, "
                   f"{len(screenplay.structure.acts)} 幕, {total_scenes} 场, "
                   f"{total_beats} 个节拍 ({dialogue_count} 句对白)")


@app.command()
def validate(
    screenplay: str = typer.Argument(..., help="YAML 剧本文件路径"),
) -> None:
    """校验已有 YAML 剧本是否符合 Schema。"""
    from .schema.validator import validate_screenplay

    result = validate_screenplay(screenplay)

    if result.valid:
        console.print("[bold green]✅ 校验通过[/bold green]")
    else:
        console.print("[bold red]❌ 校验失败[/bold red]")
        for err in result.errors:
            console.print(f"  [red]✗ {err}[/red]")

    if result.warnings:
        for w in result.warnings:
            console.print(f"  [yellow]⚠ {w}[/yellow]")


@app.command()
def launch(
    share: bool = typer.Option(False, "--share", help="生成公开分享链接"),
    port: int = typer.Option(7860, "--port", "-p", help="监听端口"),
) -> None:
    """启动 Gradio Web UI。"""
    from .web import create_ui

    ui = create_ui()
    console.print(f"[bold]🌐 启动 Web UI [link=http://127.0.0.1:{port}]http://127.0.0.1:{port}[/link][/bold]")
    ui.launch(
        server_port=port,
        share=share,
        inbrowser=True,
        css=(
            ".yaml-preview textarea {"
            "  font-family: 'Cascadia Code', 'Consolas', monospace !important;"
            "  font-size: 13px;"
            "}"
        ),
        theme="soft",
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
