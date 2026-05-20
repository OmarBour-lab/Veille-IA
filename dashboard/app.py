from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from veille_agents import (
    COLLECTED_DIR,
    EXPORT_DIR,
    LATEST_RUN_PATH,
    LOG_DIR,
    REPORT_DIR,
    deduplicate_analyses_by_framework,
    get_human_validation,
    llm_configured,
    run_pipeline,
    set_human_validation,
)


st.set_page_config(page_title="Veille Frameworks IA", page_icon="", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --bg-soft: #eef5ff;
        --panel: #ffffff;
        --panel-soft: #f8fbff;
        --ink: #10203f;
        --muted: #52627a;
        --line: #d8e4f5;
        --accent: #3157d5;
        --accent-soft: #e8eeff;
        --teal: #067a75;
        --teal-soft: #e6fffb;
        --good: #087443;
        --good-soft: #ecfdf3;
        --warn: #b54708;
        --warn-soft: #fff4dc;
        --bad: #b42318;
        --bad-soft: #fff1f0;
    }
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    [data-testid="stMain"],
    section.main {
        background:
            radial-gradient(circle at 12% 8%, rgba(49, 87, 213, 0.12), transparent 28%),
            linear-gradient(135deg, #f7fbff 0%, #eef5ff 48%, #f8f5ff 100%) !important;
        color: var(--ink) !important;
    }
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1400px;
        background: transparent;
        color: var(--ink);
    }
    .block-container p,
    .block-container span,
    .block-container label,
    .block-container div {
        color: inherit;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #eff6ff 100%);
        border-right: 1px solid #c9d9f0;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] code {
        color: #111827;
    }
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] textarea {
        color: #111827;
        background: #ffffff;
    }
    [data-testid="stSidebar"] pre {
        background: #e8eeff;
        border: 1px solid #c9d5ff;
    }
    [data-testid="stSidebar"] code {
        background: #fff4dc !important;
        color: #8a3f00 !important;
        border: 1px solid #ffd58a;
        border-radius: 6px;
        padding: 2px 7px;
        font-weight: 650;
    }
    [data-testid="stSidebar"] pre code {
        background: transparent !important;
        color: #10203f !important;
        border: 0;
        padding: 0;
        font-weight: 500;
    }
    h1, h2, h3 {
        letter-spacing: 0;
        color: var(--ink) !important;
    }
    .hero {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 22px 24px;
        background:
            linear-gradient(120deg, rgba(255,255,255,0.96) 0%, rgba(239,246,255,0.96) 100%),
            linear-gradient(90deg, #3157d5, #067a75);
        box-shadow: 0 12px 30px rgba(49, 87, 213, 0.10);
        margin-bottom: 18px;
    }
    .hero-title {
        font-size: 30px;
        line-height: 1.15;
        font-weight: 750;
        color: var(--ink);
        margin: 0 0 6px 0;
    }
    .hero-subtitle {
        color: var(--muted);
        font-size: 15px;
        margin: 0;
    }
    .status-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
    }
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 6px 10px;
        font-size: 13px;
        color: var(--ink);
        background: #fff;
    }
    .pill.good { border-color: #9ce2bd; color: var(--good); background: var(--good-soft); }
    .pill.warn { border-color: #ffd58a; color: var(--warn); background: var(--warn-soft); }
    .pill.bad { border-color: #ffb8b1; color: var(--bad); background: var(--bad-soft); }
    .section-title {
        font-size: 18px;
        font-weight: 700;
        color: var(--ink);
        margin: 10px 0 4px 0;
    }
    .section-note {
        font-size: 13px;
        color: var(--muted);
        margin-bottom: 10px;
    }
    .agent-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin: 8px 0 12px 0;
    }
    .agent-box {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 12px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
        min-height: 96px;
        box-shadow: 0 8px 18px rgba(16, 32, 63, 0.05);
    }
    .agent-box strong {
        color: var(--ink);
        display: block;
        margin-bottom: 4px;
    }
    .agent-box span {
        color: var(--muted);
        font-size: 13px;
    }
    .priority-high { color: #b42318; font-weight: 700; }
    .priority-mid { color: #b54708; font-weight: 700; }
    .priority-low { color: #087443; font-weight: 700; }
    div[data-testid="stMetric"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px 16px;
        background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
        color: var(--ink) !important;
        box-shadow: 0 8px 18px rgba(16, 32, 63, 0.05);
    }
    div[data-testid="stMetric"] * {
        color: var(--ink) !important;
    }
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"] {
        color: var(--muted) !important;
    }
    div[data-testid="stMetricValue"] *,
    div[data-testid="stMetricValue"] {
        color: var(--ink) !important;
        font-weight: 750 !important;
    }
    .priority-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 8px 18px rgba(16, 32, 63, 0.05);
    }
    .priority-table th {
        background: #e8eeff;
        color: var(--ink);
        font-weight: 750;
        text-align: left;
        padding: 12px;
        border-bottom: 1px solid var(--line);
        font-size: 13px;
    }
    .priority-table td {
        color: var(--ink);
        padding: 12px;
        border-bottom: 1px solid #edf2fb;
        vertical-align: top;
        font-size: 13px;
        background: #ffffff;
    }
    .priority-table tr:last-child td {
        border-bottom: 0;
    }
    .priority-table a {
        color: var(--accent);
        font-weight: 650;
        text-decoration: none;
    }
    .score-track {
        min-width: 96px;
        height: 8px;
        border-radius: 999px;
        background: #e5eaf5;
        overflow: hidden;
        margin-top: 6px;
    }
    .score-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #067a75, #3157d5);
    }
    .priority-badge {
        display: inline-flex;
        border-radius: 999px;
        padding: 4px 8px;
        font-weight: 750;
        font-size: 12px;
    }
    .priority-badge.haute { background: var(--bad-soft); color: var(--bad); border: 1px solid #ffb8b1; }
    .priority-badge.moyenne { background: var(--warn-soft); color: var(--warn); border: 1px solid #ffd58a; }
    .priority-badge.basse { background: var(--good-soft); color: var(--good); border: 1px solid #9ce2bd; }
    div[data-testid="stMarkdownContainer"] {
        color: var(--ink);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px 8px 0 0;
        color: var(--ink) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
        background: var(--accent-soft);
        border-color: #b9c8ff;
    }
    .stButton > button {
        background: linear-gradient(135deg, #3157d5 0%, #2649bd 100%);
        color: #ffffff !important;
        border: 1px solid #1f3ea5;
        border-radius: 8px;
        font-weight: 650;
    }
    .stButton > button * {
        color: #ffffff !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2649bd 0%, #1f3ea5 100%);
        border-color: #1b347f;
        color: #ffffff !important;
    }
    .stDownloadButton > button {
        background: #ffffff !important;
        color: var(--ink) !important;
        border: 1px solid #b9c8ff !important;
        border-radius: 8px;
        font-weight: 650;
    }
    .stDownloadButton > button * {
        color: var(--ink) !important;
    }
    .stDownloadButton > button:hover {
        background: #e8eeff !important;
        color: var(--ink) !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: #ffffff;
        color: #10203f !important;
        border: 1px solid #b9c8ff;
    }
    [data-testid="stSidebar"] .stButton > button * {
        color: #111827 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #e8eeff;
    }
    [data-testid="stSidebar"] [data-baseweb="checkbox"] span {
        color: #10203f !important;
    }
    [data-testid="stSidebar"] [data-baseweb="checkbox"] div {
        color: #10203f !important;
    }
    .stAlert {
        border-radius: 8px;
        border: 1px solid var(--line);
        background: #ffffff;
    }
    .stAlert * {
        color: var(--ink) !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border-color: #b9c8ff !important;
        color: var(--ink) !important;
    }
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] svg {
        color: var(--ink) !important;
        fill: var(--ink) !important;
    }
    ul[role="listbox"],
    div[role="listbox"] {
        background-color: #ffffff !important;
        color: var(--ink) !important;
    }
    li[role="option"],
    div[role="option"] {
        background-color: #ffffff !important;
        color: var(--ink) !important;
    }
    li[role="option"]:hover,
    div[role="option"]:hover {
        background-color: #e8eeff !important;
        color: var(--ink) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def load_log(path: Path, limit: int = 20) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["timestamp", "agent", "message", "payload"])
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(rows)


def load_latest_watch_state() -> dict:
    latest_run = load_json(LATEST_RUN_PATH, {})
    if isinstance(latest_run, dict) and latest_run.get("analyses"):
        latest_run["analyses"] = deduplicate_analyses_by_framework(latest_run.get("analyses", []))
        return latest_run
    return {
        "generated_at": "",
        "latest_report": "",
        "collected": load_json(COLLECTED_DIR / "items_collectes.json", []),
        "filtered": load_json(COLLECTED_DIR / "items_filtres.json", []),
        "analyses": deduplicate_analyses_by_framework(load_json(COLLECTED_DIR / "items_analyses.json", [])),
    }


def priority_badge(priority: str) -> str:
    value = str(priority).lower()
    if value == "haute":
        return "Haute"
    if value == "moyenne":
        return "Moyenne"
    return "Basse"


def validation_class(status: str) -> str:
    if status == "approved":
        return "good"
    if status == "rejected":
        return "bad"
    return "warn"


def evaluation_label(value: str) -> str:
    return "OK" if value == "OK" else "A verifier"


def render_priority_table(dataframe: pd.DataFrame) -> str:
    rows = []
    for _, row in dataframe.iterrows():
        framework = escape(str(row.get("framework", "")))
        priority = escape(str(row.get("priority", "basse")).lower())
        priority_label = escape(priority_badge(priority))
        score = float(row.get("impact_score", 0) or 0)
        score_width = max(0, min(100, score / 5 * 100))
        category = escape(str(row.get("category", "")))
        recommendation = escape(str(row.get("recommendation", "")))
        url = escape(str(row.get("url", "")))
        source = f'<a href="{url}" target="_blank">Source</a>' if url else "Non disponible"
        rows.append(
            "<tr>"
            f"<td><strong>{framework}</strong></td>"
            f'<td><span class="priority-badge {priority}">{priority_label}</span></td>'
            f"<td><strong>{score:.2f}</strong>"
            f'<div class="score-track"><div class="score-fill" style="width:{score_width:.0f}%"></div></div></td>'
            f"<td>{category}</td>"
            f"<td>{recommendation}</td>"
            f"<td>{source}</td>"
            "</tr>"
        )
    return (
        '<table class="priority-table">'
        "<thead>"
        "<tr>"
        "<th>Framework</th>"
        "<th>Priorite</th>"
        "<th>Score</th>"
        "<th>Categorie</th>"
        "<th>Recommandation</th>"
        "<th>Lien</th>"
        "</tr>"
        "</thead>"
        "<tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def get_langgraph_visual() -> dict:
    png_path = EXPORT_DIR / "orchestration_langgraph.png"
    mermaid_path = EXPORT_DIR / "orchestration_langgraph.mmd"
    if png_path.exists() and mermaid_path.exists():
        return {
            "png_exists": True,
            "png_path": str(png_path),
            "mermaid_path": str(mermaid_path),
            "mermaid": mermaid_path.read_text(encoding="utf-8"),
        }
    try:
        import veille_agents

        if hasattr(veille_agents, "export_langgraph_visual"):
            return veille_agents.export_langgraph_visual()
    except Exception as exc:
        return {
            "png_exists": False,
            "png_path": str(png_path),
            "mermaid_path": str(mermaid_path),
            "mermaid": mermaid_path.read_text(encoding="utf-8") if mermaid_path.exists() else "",
            "error": str(exc),
        }
    return {
        "png_exists": png_path.exists(),
        "png_path": str(png_path),
        "mermaid_path": str(mermaid_path),
        "mermaid": mermaid_path.read_text(encoding="utf-8") if mermaid_path.exists() else "",
        "error": "La fonction de generation LangGraph n'est pas disponible dans le module charge.",
    }


latest_state = load_latest_watch_state()
analyses = latest_state.get("analyses", [])
collected = latest_state.get("collected", [])
filtered = latest_state.get("filtered", [])
validation = get_human_validation()
export_path = EXPORT_DIR / "recommendations_google_sheets.csv"

evaluation_log = load_log(LOG_DIR / "agent_evaluateur.log", limit=1)
evaluation_status = "OK"
if not evaluation_log.empty:
    payload = evaluation_log.iloc[-1].get("payload", {})
    if isinstance(payload, dict):
        evaluation_status = payload.get("status", "OK")

df = pd.DataFrame(analyses)
if not df.empty:
    df["impact_score"] = pd.to_numeric(df["impact_score"], errors="coerce").fillna(0)
    df["priorite"] = df["priority"].apply(priority_badge)
    df = (
        df.sort_values(["recommendation_source", "impact_score"], ascending=[False, False])
        .drop_duplicates(subset=["framework"], keep="first")
        .sort_values("impact_score", ascending=False)
    )

with st.sidebar:
    st.title("Pilotage")
    st.caption("Controle de la pipeline, validation humaine et interoperabilite.")

    st.subheader("Execution")
    use_live = st.toggle("Collecte GitHub live", value=True)
    use_llm = st.toggle("Agents LLM GitHub Models", value=True)
    st.caption("LLM pret" if llm_configured() else "LLM non configure: fallback si execution lancee")
    if st.button("Relancer la pipeline", type="primary", width="stretch"):
        with st.spinner("Execution de la pipeline en cours..."):
            result = run_pipeline(use_live=use_live, use_llm=use_llm)
        st.success("Pipeline terminee")
        with st.expander("Resultat technique"):
            st.json(result)
        st.rerun()

    st.subheader("Validation humaine")
    st.markdown(f"Statut actuel : `{validation.get('status', 'pending')}`")
    reviewer = st.text_input("Validateur", value="Omar/Wassim")
    comment = st.text_area("Commentaire", value="", height=80)
    approve_col, reject_col = st.columns(2)
    if approve_col.button("Approuver", width="stretch"):
        set_human_validation("approved", reviewer=reviewer, comment=comment)
        st.rerun()
    if reject_col.button("Rejeter", width="stretch"):
        set_human_validation("rejected", reviewer=reviewer, comment=comment)
        st.rerun()

    st.subheader("Interop")
    st.code("n8n: http://127.0.0.1:8000", language=None)
    st.code("MCP: source/mcp_server.py", language=None)

st.markdown(
    f"""
    <div class="hero">
      <div class="hero-title">Assistant de veille sur les frameworks IA</div>
      <p class="hero-subtitle">
        Surveillance des tendances, contextualisation RAG, recommandations et supervision humaine.
      </p>
      <div class="status-row">
        <span class="pill {'good' if evaluation_status == 'OK' else 'bad'}">Evaluation : {evaluation_label(evaluation_status)}</span>
        <span class="pill {validation_class(validation.get('status', 'pending'))}">Validation : {validation.get('status', 'pending')}</span>
        <span class="pill">RAG : ChromaDB + fallback lexical</span>
        <span class="pill">n8n + MCP actifs</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(4)
metric_cols[0].metric("Items collectes", len(collected))
metric_cols[1].metric("Items filtres", len(filtered))
metric_cols[2].metric("Analyses", len(analyses))
metric_cols[3].metric("Rapports", len(list(REPORT_DIR.glob("rapport_veille*.md"))))

st.markdown('<div class="section-title">Architecture agentique</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="agent-grid">
      <div class="agent-box"><strong>Collecte</strong><span>GitHub API, fallback local, normalisation des signaux.</span></div>
      <div class="agent-box"><strong>RAG</strong><span>Chunking LangChain, index ChromaDB, retrieval top-k.</span></div>
      <div class="agent-box"><strong>Analyse</strong><span>Scoring d'impact, priorisation, recommandation.</span></div>
      <div class="agent-box"><strong>Redaction</strong><span>Rapports horodates, synthese et citations internes.</span></div>
      <div class="agent-box"><strong>Evaluation</strong><span>Controle schema, hallucination, sources et logs.</span></div>
      <div class="agent-box"><strong>Interop</strong><span>n8n pour orchestration, MCP pour exposition d'outils.</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">Priorites de veille</div>', unsafe_allow_html=True)
st.markdown('<div class="section-note">Classement des frameworks par score d impact et action recommandee.</div>', unsafe_allow_html=True)
if df.empty:
    st.info("Aucune analyse disponible. Lance la pipeline depuis la barre laterale.")
else:
    display = df.sort_values("impact_score", ascending=False).copy()
    st.markdown(render_priority_table(display), unsafe_allow_html=True)

st.markdown('<div class="section-title">Scores par framework</div>', unsafe_allow_html=True)
st.markdown('<div class="section-note">Meilleur signal conserve pour chaque framework.</div>', unsafe_allow_html=True)
if df.empty:
    st.info("Aucun score a afficher.")
else:
    chart_df = (
        df.sort_values("impact_score", ascending=False)
        .drop_duplicates(subset=["framework"])
        [["framework", "impact_score"]]
    )
    st.bar_chart(chart_df, x="framework", y="impact_score", height=300)

tabs = st.tabs(["Rapports", "Logs agents", "Donnees et exports", "Graphe d'Orchestration"])

with tabs[0]:
    reports = sorted(REPORT_DIR.glob("rapport_veille*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        st.info("Aucun rapport genere.")
    else:
        report_actions, report_preview = st.columns([0.35, 0.65])
        with report_actions:
            latest_report_path = Path(str(latest_state.get("latest_report", "")))
            default_report_index = reports.index(latest_report_path) if latest_report_path in reports else 0
            selected_report = st.selectbox("Rapport", reports, index=default_report_index, format_func=lambda p: p.name)
            st.download_button(
                "Telecharger Markdown",
                selected_report.read_text(encoding="utf-8"),
                file_name=selected_report.name,
                mime="text/markdown",
                width="stretch",
            )
            if export_path.exists():
                st.download_button(
                    "Telecharger CSV Sheets",
                    export_path.read_text(encoding="utf-8"),
                    file_name=export_path.name,
                    mime="text/csv",
                    width="stretch",
                )
        with report_preview:
            with st.container(height=520):
                st.markdown(selected_report.read_text(encoding="utf-8"))

with tabs[1]:
    log_files = sorted(LOG_DIR.glob("agent_*.log"))
    if not log_files:
        st.info("Aucun log disponible.")
    else:
        selected_log = st.selectbox("Agent", log_files, format_func=lambda p: p.stem)
        log_df = load_log(selected_log, limit=20)
        if log_df.empty:
            st.info("Log vide.")
        else:
            compact = log_df.copy()
            if "payload" in compact.columns:
                compact["payload"] = compact["payload"].apply(lambda value: json.dumps(value, ensure_ascii=False))
            st.dataframe(compact, width="stretch", hide_index=True)

with tabs[2]:
    data_cols = st.columns(3)
    data_cols[0].info(f"Base vectorielle : `{ROOT / 'data' / 'vector_db'}`")
    data_cols[1].info(f"Export Sheets : `{export_path.name if export_path.exists() else 'non genere'}`")
    data_cols[2].info(f"Validation : `{validation.get('status', 'pending')}`")
    if export_path.exists():
        st.dataframe(pd.read_csv(export_path), width="stretch", hide_index=True)

with tabs[3]:
    st.markdown('<div class="section-title">Graphe d\'Orchestration</div>', unsafe_allow_html=True)
    visual = get_langgraph_visual()
    if visual.get("png_exists"):
        st.image(visual["png_path"], caption="Graphe LangGraph genere depuis la pipeline reelle.", width="stretch")
    else:
        st.warning("Image PNG indisponible. Affichage du graphe Mermaid genere par LangGraph.")
        st.code(visual.get("mermaid", ""), language="mermaid")
        if visual.get("error"):
            st.caption(visual["error"])
    st.markdown("**Execution actuelle**")
    latest_orchestrator = load_log(LOG_DIR / "orchestrateur_langgraph.log", limit=1)
    if latest_orchestrator.empty:
        st.info("Aucune execution LangGraph journalisee pour le moment.")
    else:
        compact = latest_orchestrator.copy()
        if "payload" in compact.columns:
            compact["payload"] = compact["payload"].apply(lambda value: json.dumps(value, ensure_ascii=False))
        st.dataframe(compact, width="stretch", hide_index=True)
