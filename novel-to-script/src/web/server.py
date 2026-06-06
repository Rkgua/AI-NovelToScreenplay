"""FastAPI 后端 — 小说转剧本 Web 服务。"""

from __future__ import annotations

import tempfile
import traceback
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from ..config import AppConfig
from ..parser import parse_file
from ..pipeline import run_pipeline
from ..schema.validator import save_screenplay, validate_screenplay

_BASE_DIR = Path(__file__).resolve().parent
_OUTPUT_DIR = Path("output")

app = FastAPI(title="Novel2Script API")

# Load template
_TEMPLATE = (_BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=_TEMPLATE)


@app.post("/api/convert")
def api_convert(
    file: UploadFile = File(...),
    model: str = Form("deepseek"),
    title: str = Form(""),
    author: str = Form(""),
):
    if not file.filename:
        raise HTTPException(400, "请上传文件")

    suffix = Path(file.filename).suffix.lower()
    tmp = Path(tempfile.gettempdir()) / f"_n2s_{file.filename}"
    try:
        tmp.write_bytes(file.file.read())
    except Exception as e:
        raise HTTPException(500, f"文件保存失败: {e}")

    try:
        chapters = parse_file(tmp)
        config = AppConfig.from_env(model)
        meta = {"title": title or Path(file.filename).stem, "source": file.filename, "author": author}
        sp = run_pipeline(chapters, config, meta=meta)

        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = _OUTPUT_DIR / f"{Path(file.filename).stem}_screenplay.yaml"
        save_screenplay(sp, out)
        yaml_text = out.read_text(encoding="utf-8")

        total_scenes = sum(len(a.scenes) for a in sp.structure.acts)
        total_beats = sum(len(s.beats) for a in sp.structure.acts for s in a.scenes)
        dialogue_count = sum(
            1 for a in sp.structure.acts for s in a.scenes for b in s.beats
            if b.type == "dialogue"
        )

        return {
            "ok": True,
            "yaml": yaml_text,
            "stats": {
                "characters": len(sp.characters),
                "acts": len(sp.structure.acts),
                "scenes": total_scenes,
                "beats": total_beats,
                "dialogues": dialogue_count,
            },
            "output_path": str(out),
        }
    except Exception as e:
        return {"ok": False, "error": traceback.format_exc()}
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


@app.post("/api/validate")
async def api_validate(request: Request):
    body = await request.json()
    yaml_text = body.get("yaml", "")
    if not yaml_text.strip():
        return {"ok": True, "valid": True, "errors": [], "warnings": []}

    tmp = Path(tempfile.gettempdir()) / "_n2s_validate.yaml"
    tmp.write_text(yaml_text, encoding="utf-8")
    result = validate_screenplay(tmp)

    return {
        "ok": True,
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
    }


@app.post("/api/save")
async def api_save(request: Request):
    body = await request.json()
    yaml_text = body.get("yaml", "")
    filename = body.get("filename", "screenplay_edited")
    if not yaml_text.strip():
        raise HTTPException(400, "YAML 为空")

    name = Path(filename).stem or "screenplay_edited"
    out = _OUTPUT_DIR / f"{name}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml_text, encoding="utf-8")

    return {"ok": True, "path": str(out), "filename": out.name}


@app.get("/api/download/{filename}")
def api_download(filename: str):
    name = Path(filename).name
    fp = _OUTPUT_DIR / name
    if not fp.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(fp, filename=name, media_type="application/x-yaml")
