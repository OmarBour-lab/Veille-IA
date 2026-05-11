from __future__ import annotations

import json
import math
import os
import re
import time
import hashlib
import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    import numpy as np
except Exception:
    np = None

try:
    import requests
except Exception:
    requests = None

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:
    RecursiveCharacterTextSplitter = None

try:
    import chromadb
except Exception:
    chromadb = None


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
KB_DIR = DATA_DIR / "knowledge_base_interne"
COLLECTED_DIR = DATA_DIR / "donnees_collectees"
REPORT_DIR = DATA_DIR / "rapports_generes"
VECTOR_DIR = DATA_DIR / "vector_db"
EXPORT_DIR = DATA_DIR / "exports"
VALIDATION_DIR = DATA_DIR / "validation"


def load_env_file(path: Path | None = None) -> None:
    path = path or ROOT / ".env"
    if load_dotenv:
        load_dotenv(path)
        return
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def ensure_dirs() -> None:
    for path in [LOG_DIR, KB_DIR, COLLECTED_DIR, REPORT_DIR, VECTOR_DIR, EXPORT_DIR, VALIDATION_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(agent: str, message: str, payload: dict | None = None) -> None:
    ensure_dirs()
    record = {"timestamp": now_iso(), "agent": agent, "message": message}
    if payload:
        record["payload"] = payload
    with (LOG_DIR / f"{agent}.log").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_dict_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\w+-]{3,}", text.lower(), flags=re.UNICODE)


def stable_embedding(text: str, dimensions: int = 128) -> list[float]:
    tokens = tokenize(text)
    if np is None:
        vector = [0.0] * dimensions
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector
    vector = np.zeros(dimensions, dtype=float)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = np.linalg.norm(vector)
    return (vector / norm).tolist() if norm else vector.tolist()


def read_internal_documents() -> list[dict]:
    docs = []
    for path in sorted(KB_DIR.glob("*.md")):
        docs.append({"path": str(path), "text": path.read_text(encoding="utf-8")})
    log("agent_rag", "Base interne chargee", {"documents": len(docs)})
    return docs


def chunk_document(doc: dict, chunk_size: int = 120, overlap: int = 25) -> list[dict]:
    if RecursiveCharacterTextSplitter:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 7,
            chunk_overlap=overlap * 7,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        parts = splitter.split_text(doc["text"])
        return [
            {
                "source": doc["path"],
                "chunk_id": f"{Path(doc['path']).stem}-{idx + 1}",
                "text": part,
            }
            for idx, part in enumerate(parts)
            if part.strip()
        ]
    words = doc["text"].split()
    chunks = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(words), step):
        part = words[start : start + chunk_size]
        if not part:
            continue
        chunks.append(
            {
                "source": doc["path"],
                "chunk_id": f"{Path(doc['path']).stem}-{len(chunks) + 1}",
                "text": " ".join(part),
            }
        )
    return chunks


def build_chunks(chunk_size: int = 120, overlap: int = 25) -> list[dict]:
    chunks = []
    for doc in read_internal_documents():
        chunks.extend(chunk_document(doc, chunk_size=chunk_size, overlap=overlap))
    log("agent_rag", "Chunks generes", {"chunks": len(chunks), "chunk_size": chunk_size, "overlap": overlap})
    return chunks


def build_vector_index(chunks: list[dict]) -> bool:
    if chromadb is None:
        log("agent_rag", "ChromaDB indisponible, fallback lexical", {"chunks": len(chunks)})
        return False
    ensure_dirs()
    client = chromadb.PersistentClient(path=str(VECTOR_DIR))
    collection = client.get_or_create_collection(name="knowledge_base_interne")
    existing = collection.count()
    if existing:
        collection.delete(ids=collection.get()["ids"])
    ids = [chunk["chunk_id"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [{"source": chunk["source"], "chunk_id": chunk["chunk_id"]} for chunk in chunks]
    embeddings = [stable_embedding(chunk["text"]) for chunk in chunks]
    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    log("agent_rag", "Index ChromaDB construit", {"chunks": len(chunks), "path": str(VECTOR_DIR)})
    return True


def score_text(query: str, text: str) -> float:
    q = Counter(tokenize(query))
    t = Counter(tokenize(text))
    if not q or not t:
        return 0.0
    common = set(q) & set(t)
    if np is not None:
        vocab = sorted(set(q) | set(t))
        q_vec = np.array([q[word] for word in vocab], dtype=float)
        t_vec = np.array([t[word] for word in vocab], dtype=float)
        norm = np.linalg.norm(q_vec) * np.linalg.norm(t_vec)
        return float(np.dot(q_vec, t_vec) / norm) if norm else 0.0
    raw = sum(q[word] * t[word] for word in common)
    norm = math.sqrt(sum(v * v for v in q.values())) * math.sqrt(sum(v * v for v in t.values()))
    return raw / norm if norm else 0.0


def retrieve(query: str, chunks: list[dict], top_k: int = 4) -> list[dict]:
    if chromadb is not None:
        try:
            client = chromadb.PersistentClient(path=str(VECTOR_DIR))
            collection = client.get_collection(name="knowledge_base_interne")
            if collection.count() > 0:
                result = collection.query(query_embeddings=[stable_embedding(query)], n_results=top_k)
                retrieved = []
                ids = result.get("ids", [[]])[0]
                docs = result.get("documents", [[]])[0]
                metadatas = result.get("metadatas", [[]])[0]
                distances = result.get("distances", [[]])[0]
                for chunk_id, text, metadata, distance in zip(ids, docs, metadatas, distances):
                    retrieved.append(
                        {
                            "source": metadata.get("source", ""),
                            "chunk_id": metadata.get("chunk_id", chunk_id),
                            "text": text,
                            "score": round(1 / (1 + float(distance)), 4),
                            "retrieval": "chromadb",
                        }
                    )
                log("agent_rag", "Recherche RAG ChromaDB executee", {"query": query[:120], "results": len(retrieved)})
                return retrieved
        except Exception as exc:
            log("agent_rag", "Fallback retrieval lexical", {"error": str(exc)})
    ranked = []
    for chunk in chunks:
        score = score_text(query, chunk["text"])
        if score > 0:
            ranked.append({**chunk, "score": round(score, 4), "retrieval": "lexical"})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    results = ranked[:top_k]
    log("agent_rag", "Recherche RAG executee", {"query": query[:120], "results": len(results)})
    return results


def fetch_github_repo(framework: str, repo: str, timeout: int = 8) -> dict | None:
    load_env_file()
    url = f"https://api.github.com/repos/{repo}"
    headers = {"User-Agent": "veille-frameworks-ia-student-project"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        if not requests:
            raise RuntimeError("La bibliotheque requests n'est pas installee.")
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return {
            "framework": framework,
            "title": f"Activite GitHub recente pour {framework}",
            "source": "github_api",
            "url": data.get("html_url", url),
            "date": now_iso()[:10],
            "summary": (
                f"{framework} a {data.get('stargazers_count', 'N/A')} stars, "
                f"{data.get('forks_count', 'N/A')} forks, "
                f"derniere mise a jour {data.get('updated_at', 'N/A')}."
            ),
            "category": "github_signal",
            "metrics": {
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "open_issues": data.get("open_issues_count"),
                "updated_at": data.get("updated_at"),
            },
        }
    except Exception as exc:
        log("agent_collecteur", "Fallback GitHub active", {"framework": framework, "error": str(exc)})
        return None


def collect_market_items(use_live: bool = True) -> list[dict]:
    ensure_dirs()
    seed_path = COLLECTED_DIR / "manual_seed.json"
    items = load_json(seed_path)
    repos = {
        "LangChain": "langchain-ai/langchain",
        "LlamaIndex": "run-llama/llama_index",
        "LangGraph": "langchain-ai/langgraph",
        "CrewAI": "crewAIInc/crewAI",
        "AutoGen": "microsoft/autogen",
        "Haystack": "deepset-ai/haystack",
        "DSPy": "stanfordnlp/dspy",
        "Smolagents": "huggingface/smolagents",
    }
    if use_live:
        for framework, repo in repos.items():
            item = fetch_github_repo(framework, repo)
            if item:
                items.append(item)
            time.sleep(0.1)
    save_json(COLLECTED_DIR / "items_collectes.json", items)
    log("agent_collecteur", "Collecte terminee", {"items": len(items), "live": use_live})
    return items


def filter_items(items: Iterable[dict], keywords: Iterable[str] | None = None) -> list[dict]:
    keywords = [k.lower() for k in (keywords or ["agent", "rag", "release", "github", "orchestration", "benchmark"])]
    items = list(items)
    if pd is not None and items:
        df = pd.DataFrame(items).drop_duplicates(subset=["framework", "title", "url"])
        text = (df["title"].fillna("") + " " + df["summary"].fillna("")).str.lower()
        df["relevance_score"] = text.apply(lambda value: sum(1 for keyword in keywords if keyword in value))
        df = df[(df["relevance_score"] > 0) | (df["source"] == "github_api")]
        filtered = df.to_dict(orient="records")
    else:
        seen = set()
        filtered = []
        for item in items:
            key = (item.get("framework"), item.get("title"), item.get("url"))
            if key in seen:
                continue
            seen.add(key)
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            relevance = sum(1 for k in keywords if k in text)
            if relevance > 0 or item.get("source") == "github_api":
                filtered.append({**item, "relevance_score": relevance})
    save_json(COLLECTED_DIR / "items_filtres.json", filtered)
    log("agent_filtreur", "Filtrage termine", {"input": len(items), "output": len(filtered)})
    return filtered


def analyze_item(item: dict, chunks: list[dict]) -> dict:
    query = f"{item.get('framework')} {item.get('summary')} {item.get('category')}"
    context = retrieve(query, chunks, top_k=4)
    internal_match = sum(c["score"] for c in context)
    source_reliability = 2 if item.get("source") in {"github_api", "donnee_de_demo"} else 1
    metrics = item.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    stars = metrics.get("stars") or 0
    market_signal = 2 if stars > 10000 else 1
    impact_score = round(min(5, source_reliability + market_signal + internal_match), 2)
    if impact_score >= 4:
        priority = "haute"
    elif impact_score >= 2.5:
        priority = "moyenne"
    else:
        priority = "basse"
    recommendation = (
        f"Surveiller {item.get('framework')} et realiser un mini-POC cible."
        if priority in {"haute", "moyenne"}
        else f"Conserver {item.get('framework')} dans la veille sans action immediate."
    )
    result = {
        **item,
        "impact_score": impact_score,
        "priority": priority,
        "internal_context": context,
        "recommendation": recommendation,
    }
    result = validate_analysis_schema(result)
    log("agent_analyste", "Item analyse", {"framework": item.get("framework"), "priority": priority, "score": impact_score})
    return result


def validate_analysis_schema(item: dict) -> dict:
    required_defaults = {
        "framework": "Inconnu",
        "title": "Titre non disponible",
        "source": "source_non_precisee",
        "url": "",
        "summary": "Synthese non disponible",
        "category": "non_classee",
        "impact_score": 0.0,
        "priority": "basse",
        "internal_context": [],
        "recommendation": "Aucune recommandation disponible.",
    }
    corrected = False
    for key, default in required_defaults.items():
        if key not in item or item[key] is None:
            item[key] = default
            corrected = True
    if item["priority"] not in {"haute", "moyenne", "basse"}:
        item["priority"] = "basse"
        corrected = True
    try:
        item["impact_score"] = round(float(item["impact_score"]), 2)
    except (TypeError, ValueError):
        item["impact_score"] = 0.0
        corrected = True
    if not isinstance(item["internal_context"], list):
        item["internal_context"] = []
        corrected = True
    if corrected:
        log("agent_evaluateur", "Self-correction schema appliquee", {"framework": item.get("framework")})
    return item


def analyze_items(items: list[dict], chunks: list[dict]) -> list[dict]:
    results = [analyze_item(item, chunks) for item in items]
    save_json(COLLECTED_DIR / "items_analyses.json", results)
    return results


def export_recommendations_csv(analyses: list[dict]) -> Path:
    ensure_dirs()
    path = EXPORT_DIR / "recommendations_google_sheets.csv"
    rows = []
    for item in analyses:
        rows.append(
            {
                "framework": item.get("framework"),
                "priority": item.get("priority"),
                "impact_score": item.get("impact_score"),
                "category": item.get("category"),
                "recommendation": item.get("recommendation"),
                "source_url": item.get("url"),
            }
        )
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["framework", "priority", "impact_score", "category", "recommendation", "source_url"],
        )
        writer.writeheader()
        writer.writerows(rows)
    log("agent_redacteur", "Export CSV genere pour outil bureautique", {"path": str(path), "rows": len(rows)})
    return path


def set_human_validation(status: str, reviewer: str = "humain", comment: str = "") -> dict:
    status = status.lower().strip()
    if status not in {"approved", "rejected", "pending"}:
        status = "pending"
    payload = {
        "status": status,
        "reviewer": reviewer,
        "comment": comment,
        "timestamp": now_iso(),
    }
    save_dict_json(VALIDATION_DIR / "latest_validation.json", payload)
    log("agent_evaluateur", "Validation humaine mise a jour", payload)
    return payload


def get_human_validation() -> dict:
    path = VALIDATION_DIR / "latest_validation.json"
    if not path.exists():
        return {"status": "pending", "reviewer": None, "comment": "", "timestamp": None}
    return json.loads(path.read_text(encoding="utf-8"))


def top_framework_summaries(analyses: list[dict], limit: int = 5) -> list[dict]:
    sorted_items = sorted(analyses, key=lambda x: x.get("impact_score", 0), reverse=True)
    selected = []
    seen_frameworks = set()
    for item in sorted_items:
        framework = item.get("framework")
        if framework in seen_frameworks:
            continue
        selected.append(item)
        seen_frameworks.add(framework)
        if len(selected) == limit:
            break
    return selected


def generate_report(analyses: list[dict]) -> str:
    analyses = sorted(analyses, key=lambda x: x.get("impact_score", 0), reverse=True)
    generated_at = datetime.now()
    timestamp = generated_at.strftime("%Y%m%d_%H%M%S")
    lines = [
        "# Rapport de veille - Frameworks IA",
        "",
        f"Date de generation : {generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Resume executif",
        "",
    ]
    for item in top_framework_summaries(analyses, limit=5):
        lines.append(
            f"- **{item['framework']}** ({item['priority']}, score {item['impact_score']}) : {item['recommendation']}"
        )
    lines.extend(["", "## Analyse detaillee", ""])
    for item in analyses:
        lines.extend(
            [
                f"### {item['framework']} - {item['title']}",
                "",
                f"- Source : [{item['source']}]({item['url']})",
                f"- Categorie : {item.get('category', 'non classee')}",
                f"- Score d'impact : {item['impact_score']} / 5",
                f"- Priorite : {item['priority']}",
                f"- Synthese : {item['summary']}",
                f"- Recommandation : {item['recommendation']}",
                "",
                "Contexte interne retrouve :",
            ]
        )
        contexts = item.get("internal_context") or []
        if contexts:
            for ctx in contexts[:2]:
                lines.append(f"- `{Path(ctx['source']).name}` / {ctx['chunk_id']} : {ctx['text'][:220]}...")
        else:
            lines.append("- Aucun contexte interne suffisamment proche.")
        lines.append("")
    lines.extend(
        [
            "## Controle anti-hallucination",
            "",
            "- Les faits externes sont associes a une URL source.",
            "- Les recommandations sont separees des faits observes.",
            "- En cas d'echec API, le systeme utilise un jeu de donnees manuel de demonstration.",
            "- Les informations non verifiees doivent etre marquees comme hypotheses dans une version production.",
            "- Les sorties d'analyse sont validees par un schema simple avec correction automatique des champs manquants.",
            "- Une validation humaine peut approuver ou rejeter le dernier rapport avant diffusion.",
        ]
    )
    report = "\n".join(lines)
    dated_path = REPORT_DIR / f"rapport_veille_{timestamp}.md"
    latest_path = REPORT_DIR / "rapport_veille.md"
    dated_path.write_text(report, encoding="utf-8")
    latest_path.write_text(report, encoding="utf-8")
    log(
        "agent_redacteur",
        "Rapport genere",
        {"path": str(dated_path), "latest_path": str(latest_path), "items": len(analyses)},
    )
    return report


def evaluate_outputs(analyses: list[dict]) -> dict:
    missing_sources = [a.get("title") for a in analyses if not a.get("url")]
    missing_context = [a.get("title") for a in analyses if not a.get("internal_context")]
    result = {
        "items_evalues": len(analyses),
        "missing_sources": missing_sources,
        "missing_internal_context": missing_context,
        "human_validation": get_human_validation(),
        "status": "OK" if not missing_sources else "A_CORRIGER",
    }
    log("agent_evaluateur", "Evaluation terminee", result)
    return result


def run_pipeline(use_live: bool = True) -> dict:
    ensure_dirs()
    chunks = build_chunks()
    vector_index = build_vector_index(chunks)
    collected = collect_market_items(use_live=use_live)
    filtered = filter_items(collected)
    analyses = analyze_items(filtered, chunks)
    report = generate_report(analyses)
    export_path = export_recommendations_csv(analyses)
    evaluation = evaluate_outputs(analyses)
    return {
        "chunks": len(chunks),
        "vector_index": vector_index,
        "collected": len(collected),
        "filtered": len(filtered),
        "analyses": len(analyses),
        "report_chars": len(report),
        "export_csv": str(export_path),
        "evaluation": evaluation,
    }
