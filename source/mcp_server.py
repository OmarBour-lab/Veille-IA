from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

SOURCE_DIR = Path(__file__).resolve().parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from veille_agents import (
    COLLECTED_DIR,
    LOG_DIR,
    REPORT_DIR,
    get_human_validation,
    llm_configured,
    run_pipeline,
    set_human_validation,
)


mcp = FastMCP("assistant-veille-frameworks-ia")


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


@mcp.tool()
def run_market_watch(use_live: bool = True, use_llm: bool = True) -> dict:
    """Execute la pipeline de veille IA avec agents LLM et genere un nouveau rapport horodate."""
    return run_pipeline(use_live=use_live, use_llm=use_llm)


@mcp.tool()
def get_pipeline_status() -> dict:
    """Retourne un etat synthetique de la derniere execution."""
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
        "llm_configured": llm_configured(),
        "human_validation": get_human_validation(),
    }


@mcp.tool()
def get_llm_status() -> dict:
    """Retourne l'etat de configuration des agents LLM GitHub Models."""
    return {
        "enabled": True,
        "configured": llm_configured(),
        "provider": "github_models",
    }


@mcp.tool()
def list_generated_reports() -> list[dict]:
    """Liste les rapports de veille disponibles."""
    reports = sorted(REPORT_DIR.glob("rapport_veille*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "name": path.name,
            "path": str(path),
            "size": path.stat().st_size,
        }
        for path in reports
    ]


@mcp.tool()
def get_latest_report() -> str:
    """Retourne le contenu Markdown du dernier rapport de veille."""
    path = REPORT_DIR / "rapport_veille.md"
    if not path.exists():
        return "Aucun rapport disponible. Lancez d'abord la pipeline."
    return path.read_text(encoding="utf-8")


@mcp.tool()
def get_agent_logs(agent_name: str, limit: int = 20) -> list[dict]:
    """Retourne les logs recents d'un agent."""
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


@mcp.tool()
def set_report_validation(status: str, reviewer: str = "humain", comment: str = "") -> dict:
    """Enregistre une validation humaine du dernier rapport avant diffusion."""
    return set_human_validation(status, reviewer=reviewer, comment=comment)


if __name__ == "__main__":
    mcp.run()
