"""Web UI — FastAPI + HTML 前端。

启动方式:
    python -m src.cli launch
"""

import os as _os

import uvicorn

from .server import app


def start_server(port: int = 7860, host: str = "127.0.0.1"):
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        _os.environ.pop(key, None)
    _os.environ["no_proxy"] = "127.0.0.1,localhost"

    uvicorn.run(app, host=host, port=port, log_level="info")
