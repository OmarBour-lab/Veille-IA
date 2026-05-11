from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

SOURCE_DIR = Path(__file__).resolve().parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from veille_agents import (
    COLLECTED_DIR,
    EXPORT_DIR,
    LOG_DIR,
    REPORT_DIR,
    get_human_validation,
    run_pipeline,
    set_human_validation,
)


app = FastAPI(
    title="API Veille Frameworks IA",
    description="API HTTP pour piloter la pipeline depuis n8n ou un autre orchestrateur.",
    version="0.1.0",
)


class RunRequest(BaseModel):
    use_live: bool = True


class ValidationRequest(BaseModel):
    status: str
    reviewer: str = "humain"
    comment: str = ""


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "veille-frameworks-ia"}


@app.post("/pipeline/run")
def run_pipeline_endpoint(request: RunRequest) -> dict:
    return run_pipeline(use_live=request.use_live)


@app.get("/pipeline/status")
def pipeline_status() -> dict:
    analyses = read_json(COLLECTED_DIR / "items_analyses.json", [])
    collected = read_json(COLLECTED_DIR / "items_collectes.json", [])
    filtered = read_json(COLLECTED_DIR / "items_filtres.json", [])
    reports = sorted(REPORT_DIR.glob("rapport_veille*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "collected": len(collected),
        "filtered": len(filtered),
        "analyses": len(analyses),
        "reports": len(reports),
        "latest_report": reports[0].name if reports else None,
        "human_validation": get_human_validation(),
    }


@app.get("/reports")
def list_reports() -> list[dict]:
    reports = sorted(REPORT_DIR.glob("rapport_veille*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "name": path.name,
            "path": str(path),
            "size": path.stat().st_size,
            "modified_at": path.stat().st_mtime,
        }
        for path in reports
    ]


@app.get("/reports/latest", response_class=PlainTextResponse)
def latest_report() -> str:
    path = REPORT_DIR / "rapport_veille.md"
    if not path.exists():
        return "Aucun rapport disponible. Lancez d'abord la pipeline."
    return path.read_text(encoding="utf-8")


@app.get("/exports/recommendations")
def recommendations_export() -> dict:
    path = EXPORT_DIR / "recommendations_google_sheets.csv"
    return {
        "exists": path.exists(),
        "path": str(path),
        "name": path.name,
    }


@app.post("/validation")
def validation_endpoint(request: ValidationRequest) -> dict:
    return set_human_validation(request.status, reviewer=request.reviewer, comment=request.comment)


@app.get("/validation")
def validation_status() -> dict:
    return get_human_validation()


@app.get("/logs/{agent_name}")
def get_agent_logs(agent_name: str, limit: int = 20) -> list[dict]:
    safe_name = agent_name if agent_name.startswith("agent_") else f"agent_{agent_name}"
    path = LOG_DIR / f"{safe_name}.log"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows
