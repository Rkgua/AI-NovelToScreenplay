"""Gradio Web UI。

启动方式:
    python -m src.cli launch
"""

import gradio as gr

from .app import create_ui

__all__ = ["create_ui"]
