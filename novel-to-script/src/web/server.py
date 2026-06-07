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

import yaml as _yaml

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


@app.post("/api/filter")
async def api_filter(request: Request):
    """根据配置过滤 YAML 字段。"""
    body = await request.json()
    yaml_text = body.get("yaml", "")
    config = body.get("config", {})
    if not yaml_text.strip():
        raise HTTPException(400, "YAML 为空")

    try:
        data = _yaml.safe_load(yaml_text)
        data = _filter_dict(data, config)
        filtered = _yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return {"ok": True, "yaml": filtered}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _filter_dict(data: dict, config: dict) -> dict:
    """递归过滤 YAML 数据。"""
    if not isinstance(data, dict):
        return data

    result = dict(data)  # shallow copy

    # meta
    if "title" in result and "format" in result:
        keep = set(config.get("meta", []))
        keep.add("title")
        result = {k: v for k, v in result.items() if k in keep or k == "title"}

    # characters
    if result.get("characters") is not None and isinstance(result.get("characters"), list):
        keep_char = set(config.get("character", []))
        keep_char.update(["id", "name"])
        result["characters"] = [
            {k: v for k, v in c.items() if k in keep_char}
            for c in result["characters"]
        ]

    # structure
    if "structure" in result:
        result["structure"] = _filter_dict(result["structure"], config)

    # acts
    if "acts" in result:
        keep_act = set(config.get("act", []))
        keep_act.add("act_number")
        keep_scene = set(config.get("scene", []))
        keep_scene.add("scene_number")
        keep_scene.add("heading")
        keep_scene.add("beats")
        new_acts = []
        for act in result.get("acts", []):
            new_act = {k: v for k, v in act.items() if k in keep_act}
            if "act_number" not in new_act:
                new_act["act_number"] = act.get("act_number", 1)
            if "scenes" in act:
                scenes = []
                for sc in act["scenes"]:
                    new_sc = {k: v for k, v in sc.items() if k in keep_scene or k == "scene_number"}
                    if "heading" in sc:
                        new_heading = {}
                        if "location_type" in keep_scene:
                            new_heading["location_type"] = sc["heading"]["location_type"]
                        if "location" in keep_scene:
                            new_heading["location"] = sc["heading"]["location"]
                        if "time" in keep_scene:
                            new_heading["time"] = sc["heading"]["time"]
                        if new_heading:
                            new_sc["heading"] = new_heading
                    if "beats" in sc:
                        keep_beat = set(config.get("beat", []))
                        new_beats = []
                        for b in sc["beats"]:
                            if b.get("type") not in keep_beat:
                                continue
                            new_b = {"type": b["type"]}
                            if b["type"] == "action":
                                new_b["description"] = b.get("description", "")
                            elif b["type"] == "dialogue":
                                new_b["character"] = b.get("character", "")
                                new_b["line"] = b.get("line", "")
                                if "parenthetical" in keep_beat and b.get("parenthetical"):
                                    new_b["parenthetical"] = b["parenthetical"]
                            elif b["type"] == "transition":
                                new_b["transition"] = b.get("transition", "")
                            new_beats.append(new_b)
                        new_sc["beats"] = new_beats
                    scenes.append(new_sc)
                new_act["scenes"] = scenes
            new_acts.append(new_act)
        result["acts"] = new_acts

    return result


@app.get("/api/download/{filename}")
def api_download(filename: str):
    name = Path(filename).name
    fp = _OUTPUT_DIR / name
    if not fp.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(fp, filename=name, media_type="application/x-yaml")
