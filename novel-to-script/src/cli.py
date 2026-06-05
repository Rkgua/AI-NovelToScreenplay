"""CLI 入口。"""

import typer

app = typer.Typer(name="novel2script", help="AI 辅助小说转剧本工具")


@app.command()
def convert(
    source: str = typer.Argument(..., help="小说文件路径 (epub / txt / md)"),
    output: str = typer.Option("output/screenplay.yaml", "--output", "-o", help="输出 YAML 文件路径"),
    model: str = typer.Option("openai", "--model", "-m", help="LLM 服务商 (openai / claude / ollama)"),
    chapters: str = typer.Option("", "--chapters", "-c", help="指定章节范围，如 1-5"),
) -> None:
    """将小说章节转换为结构化 YAML 剧本。"""
    typer.echo(f"📖 正在处理: {source}")
    typer.echo(f"🤖 模型: {model}")
    typer.echo(f"📄 输出: {output}")
    typer.echo("⚠  转换流水线尚未实现，将在后续阶段完成。")


@app.command()
def validate(
    screenplay: str = typer.Argument(..., help="YAML 剧本文件路径"),
) -> None:
    """校验已有 YAML 剧本是否符合 Schema。"""
    typer.echo(f"🔍 正在校验: {screenplay}")
    typer.echo("⚠  校验模块尚未实现，将在后续阶段完成。")


if __name__ == "__main__":
    app()
