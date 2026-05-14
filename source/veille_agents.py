from __future__ import annotations

import json
import math
import os
import re
import time
import hashlib
import csv
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TypedDict

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
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None

warnings.filterwarnings(
    "ignore",
    message="The default value of `allowed_objects` will change in a future version.*",
    category=Warning,
)

try:
    from langgraph.graph import END, START, StateGraph
except Exception:
    END = None
    START = None
    StateGraph = None

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

LLM_MODEL_DEFAULT = "openai/gpt-4o"
LLM_BASE_URL_DEFAULT = "https://models.github.ai/inference"
LLM_AGENT_TEMPERATURE = 0.2


class PipelineState(TypedDict, total=False):
    use_live: bool
    use_llm: bool
    chunks: list[dict]
    vector_index: bool
    collected: list[dict]
    filtered: list[dict]
    analyses: list[dict]
    report: str
    export_path: str
    evaluation: dict


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


def llm_configured() -> bool:
    load_env_file()
    token = os.getenv("GITHUB_MODELS_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_KEY")
    return bool(ChatOpenAI and token)


def build_llm() -> ChatOpenAI:
    load_env_file()
    if ChatOpenAI is None:
        raise RuntimeError("langchain-openai n'est pas installe.")
    token = os.getenv("GITHUB_MODELS_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_KEY")
    if not token:
        raise RuntimeError("Aucun token GitHub Models trouve: definir GITHUB_MODELS_TOKEN, GITHUB_API_KEY ou GITHUB_TOKEN.")
    return ChatOpenAI(
        model=os.getenv("GITHUB_MODELS_MODEL", LLM_MODEL_DEFAULT),
        api_key=token,
        base_url=os.getenv("GITHUB_MODELS_BASE_URL", LLM_BASE_URL_DEFAULT),
        temperature=LLM_AGENT_TEMPERATURE,
        timeout=45,
        max_retries=1,
    )


def compact_json(data, max_chars: int = 24000) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...TRONQUE_POUR_CONTEXT_WINDOW..."


def extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_candidates = [idx for idx in [text.find("{"), text.find("[")] if idx != -1]
        if not start_candidates:
            raise
        start = min(start_candidates)
        end = max(text.rfind("}"), text.rfind("]"))
        if end <= start:
            raise
        return json.loads(text[start : end + 1])


def call_llm_agent(agent: str, system_prompt: str, payload: dict, output: str = "json"):
    llm = build_llm()
    if output == "json":
        instruction = (
            "Retourne uniquement du JSON valide, sans markdown. "
            "N'invente aucune URL, aucune source et aucune metrique absente du payload."
        )
    else:
        instruction = (
            "Retourne uniquement le contenu Markdown final. "
            "N'invente aucune URL, aucune source et separe clairement faits et recommandations."
        )
    messages = [
        ("system", f"{system_prompt}\n\n{instruction}"),
        ("human", compact_json(payload)),
    ]
    response = llm.invoke(messages)
    content = getattr(response, "content", str(response))
    log(agent, "Appel LLM reussi", {"model": os.getenv("GITHUB_MODELS_MODEL", LLM_MODEL_DEFAULT), "output": output})
    return extract_json(content) if output == "json" else content.strip()


def log_llm_fallback(agent: str, exc: Exception) -> None:
    log(
        agent,
        "Fallback deterministe active apres erreur LLM",
        {"error": str(exc), "llm_configured": llm_configured()},
    )


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


def deterministic_collect_market_items(use_live: bool = True) -> list[dict]:
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
    return items


def collect_market_items(use_live: bool = True, use_llm: bool = True) -> list[dict]:
    raw_items = deterministic_collect_market_items(use_live=use_live)
    if use_llm:
        try:
            llm_items = call_llm_agent(
                "agent_collecteur",
                (
                    "Tu es l'agent collecteur LLM d'une cellule de veille IA. "
                    "A partir des signaux bruts fournis, normalise les items, retire les donnees hors sujet "
                    "et conserve uniquement des tendances liees aux frameworks IA surveilles. "
                    "Chaque item doit contenir: framework, title, source, url, date, summary, category, metrics. "
                    "Tu dois conserver les URL et metriques d'origine sans invention. "
                    "Si les signaux bruts sont deja pertinents, conserve-les: ne retourne jamais une liste vide "
                    "lorsque raw_items contient des items valides."
                ),
                {"use_live": use_live, "raw_items": raw_items},
            )
            if isinstance(llm_items, dict):
                llm_items = llm_items.get("items", [])
            if not isinstance(llm_items, list):
                raise ValueError("L'agent collecteur LLM n'a pas retourne une liste JSON.")
            items = [validate_collected_item(item) for item in llm_items if isinstance(item, dict)]
            if not items and raw_items:
                items = [validate_collected_item(item) for item in raw_items if isinstance(item, dict)]
                log("agent_collecteur", "Sortie LLM vide corrigee avec les signaux bruts", {"items": len(items)})
            save_json(COLLECTED_DIR / "items_collectes.json", items)
            log("agent_collecteur", "Collecte LLM terminee", {"items": len(items), "live": use_live})
            return items
        except Exception as exc:
            log_llm_fallback("agent_collecteur", exc)
    save_json(COLLECTED_DIR / "items_collectes.json", raw_items)
    log("agent_collecteur", "Collecte deterministe terminee", {"items": len(raw_items), "live": use_live})
    return raw_items


def validate_collected_item(item: dict) -> dict:
    defaults = {
        "framework": "Inconnu",
        "title": "Titre non disponible",
        "source": "source_non_precisee",
        "url": "",
        "date": now_iso()[:10],
        "summary": "Synthese non disponible",
        "category": "non_classee",
        "metrics": {},
    }
    normalized = {**defaults, **item}
    if not isinstance(normalized.get("metrics"), dict):
        normalized["metrics"] = {}
    return normalized


def deterministic_filter_items(items: Iterable[dict], keywords: Iterable[str] | None = None) -> list[dict]:
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
    return filtered


def filter_items(items: Iterable[dict], keywords: Iterable[str] | None = None, use_llm: bool = True) -> list[dict]:
    items = list(items)
    keywords = list(keywords or ["agent", "rag", "release", "github", "orchestration", "benchmark"])
    if use_llm:
        try:
            filtered = call_llm_agent(
                "agent_filtreur",
                (
                    "Tu es l'agent filtreur LLM. Selectionne les items pertinents pour une veille "
                    "sur les frameworks IA, supprime les doublons et ajoute un champ relevance_score entre 0 et 5. "
                    "Ne conserve pas les items sans rapport avec RAG, agents, orchestration, releases, benchmarks, "
                    "evaluation, securite ou adoption marche. Si les items d'entree sont pertinents, conserve-les: "
                    "ne retourne jamais une liste vide lorsque des items valides existent."
                ),
                {"keywords": keywords, "items": items},
            )
            if isinstance(filtered, dict):
                filtered = filtered.get("items", [])
            if not isinstance(filtered, list):
                raise ValueError("L'agent filtreur LLM n'a pas retourne une liste JSON.")
            filtered = [validate_collected_item(item) for item in filtered if isinstance(item, dict)]
            if not filtered and items:
                filtered = deterministic_filter_items(items, keywords)
                log("agent_filtreur", "Sortie LLM vide corrigee par filtrage local", {"output": len(filtered)})
            save_json(COLLECTED_DIR / "items_filtres.json", filtered)
            log("agent_filtreur", "Filtrage LLM termine", {"input": len(items), "output": len(filtered)})
            return filtered
        except Exception as exc:
            log_llm_fallback("agent_filtreur", exc)
    filtered = deterministic_filter_items(items, keywords)
    save_json(COLLECTED_DIR / "items_filtres.json", filtered)
    log("agent_filtreur", "Filtrage deterministe termine", {"input": len(items), "output": len(filtered)})
    return filtered


def deterministic_analyze_item(item: dict, chunks: list[dict], context: list[dict] | None = None) -> dict:
    query = f"{item.get('framework')} {item.get('summary')} {item.get('category')}"
    context = context if context is not None else retrieve(query, chunks, top_k=4)
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
        "recommendation_source": "fallback_deterministe",
    }
    result = validate_analysis_schema(result)
    return result


def generate_llm_recommendation(item: dict, context: list[dict], baseline: dict) -> str:
    result = call_llm_agent(
        "agent_analyste",
        (
            "Tu es l'agent analyste LLM charge uniquement de produire une recommandation. "
            "Genere une recommandation courte, concrete et actionnable pour l'equipe technique. "
            "Elle doit etre basee uniquement sur le signal externe, le contexte interne RAG et la baseline fournis. "
            "Ne mentionne pas de source absente et n'invente pas de faits."
        ),
        {"item": item, "internal_context": context, "baseline": baseline},
    )
    if isinstance(result, dict):
        recommendation = result.get("recommendation")
    else:
        recommendation = None
    if not isinstance(recommendation, str) or not recommendation.strip():
        raise ValueError("L'agent analyste LLM n'a pas genere de recommandation valide.")
    return recommendation.strip()


def analyze_item(item: dict, chunks: list[dict], use_llm: bool = True) -> dict:
    query = f"{item.get('framework')} {item.get('summary')} {item.get('category')}"
    context = retrieve(query, chunks, top_k=4)
    baseline = deterministic_analyze_item(item, chunks, context=context)
    if use_llm:
        try:
            llm_result = call_llm_agent(
                "agent_analyste",
                (
                    "Tu es l'agent analyste LLM. Croise un signal de marche externe avec le contexte interne RAG. "
                    "Retourne un objet JSON avec impact_score entre 0 et 5, priority parmi haute/moyenne/basse, "
                    "recommendation actionnable, summary enrichie et justification courte. "
                    "Le champ recommendation est obligatoire et doit etre redige par toi, pas copie depuis la baseline. "
                    "Tu dois citer uniquement les informations presentes dans item, internal_context ou baseline."
                ),
                {"item": item, "internal_context": context, "baseline": baseline},
            )
            if not isinstance(llm_result, dict):
                raise ValueError("L'agent analyste LLM n'a pas retourne un objet JSON.")
            recommendation = llm_result.get("recommendation")
            if not isinstance(recommendation, str) or not recommendation.strip():
                recommendation = generate_llm_recommendation(item, context, baseline)
            result = validate_analysis_schema(
                {
                    **item,
                    **llm_result,
                    "recommendation": recommendation.strip(),
                    "recommendation_source": "llm",
                    "internal_context": context,
                }
            )
            log(
                "agent_analyste",
                "Item analyse par LLM",
                {"framework": result.get("framework"), "priority": result.get("priority"), "score": result.get("impact_score")},
            )
            return result
        except Exception as exc:
            log_llm_fallback("agent_analyste", exc)
    log(
        "agent_analyste",
        "Item analyse par fallback deterministe",
        {"framework": baseline.get("framework"), "priority": baseline.get("priority"), "score": baseline.get("impact_score")},
    )
    return baseline


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


def analyze_items(items: list[dict], chunks: list[dict], use_llm: bool = True) -> list[dict]:
    prepared = []
    for item in items:
        query = f"{item.get('framework')} {item.get('summary')} {item.get('category')}"
        context = retrieve(query, chunks, top_k=4)
        baseline = deterministic_analyze_item(item, chunks, context=context)
        prepared.append({"item": item, "internal_context": context, "baseline": baseline})

    if use_llm and prepared:
        try:
            llm_results = call_llm_agent(
                "agent_analyste",
                (
                    "Tu es l'agent analyste LLM. Analyse chaque item fourni en batch. "
                    "Retourne uniquement une liste JSON, avec un objet par item et dans le meme ordre. "
                    "Chaque objet doit contenir: framework, impact_score entre 0 et 5, priority parmi haute/moyenne/basse, "
                    "summary, justification et recommendation. Le champ recommendation est obligatoire et doit etre "
                    "redige par toi, pas copie depuis la baseline. Base-toi uniquement sur item, internal_context et baseline."
                ),
                {"items": prepared},
            )
            if isinstance(llm_results, dict):
                llm_results = llm_results.get("items", llm_results.get("analyses", []))
            if not isinstance(llm_results, list):
                raise ValueError("L'agent analyste LLM batch n'a pas retourne une liste JSON.")
            results = []
            for prepared_item, llm_result in zip(prepared, llm_results):
                if not isinstance(llm_result, dict):
                    raise ValueError("Une analyse LLM batch n'est pas un objet JSON.")
                recommendation = llm_result.get("recommendation")
                if not isinstance(recommendation, str) or not recommendation.strip():
                    recommendation = generate_llm_recommendation(
                        prepared_item["item"],
                        prepared_item["internal_context"],
                        prepared_item["baseline"],
                    )
                result = validate_analysis_schema(
                    {
                        **prepared_item["item"],
                        **llm_result,
                        "recommendation": recommendation.strip(),
                        "recommendation_source": "llm",
                        "internal_context": prepared_item["internal_context"],
                    }
                )
                results.append(result)
            if len(results) != len(prepared):
                raise ValueError("Le nombre d'analyses LLM ne correspond pas au nombre d'items.")
            save_json(COLLECTED_DIR / "items_analyses.json", results)
            log("agent_analyste", "Analyse batch LLM terminee", {"items": len(results)})
            return results
        except Exception as exc:
            log_llm_fallback("agent_analyste", exc)

    results = []
    for prepared_item in prepared:
        baseline = prepared_item["baseline"]
        log(
            "agent_analyste",
            "Item analyse par fallback deterministe",
            {
                "framework": baseline.get("framework"),
                "priority": baseline.get("priority"),
                "score": baseline.get("impact_score"),
            },
        )
        results.append(baseline)
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
                "recommendation_source": item.get("recommendation_source", "non_precisee"),
            }
        )
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "framework",
                "priority",
                "impact_score",
                "category",
                "recommendation",
                "source_url",
                "recommendation_source",
            ],
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


def save_report(report: str, analyses_count: int) -> str:
    ensure_dirs()
    generated_at = datetime.now()
    timestamp = generated_at.strftime("%Y%m%d_%H%M%S")
    dated_path = REPORT_DIR / f"rapport_veille_{timestamp}.md"
    latest_path = REPORT_DIR / "rapport_veille.md"
    dated_path.write_text(report, encoding="utf-8")
    latest_path.write_text(report, encoding="utf-8")
    log(
        "agent_redacteur",
        "Rapport genere",
        {"path": str(dated_path), "latest_path": str(latest_path), "items": analyses_count},
    )
    return report


def deterministic_generate_report(analyses: list[dict]) -> str:
    analyses = sorted(analyses, key=lambda x: x.get("impact_score", 0), reverse=True)
    generated_at = datetime.now()
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
    return "\n".join(lines)


def generate_report(analyses: list[dict], use_llm: bool = True) -> str:
    analyses = sorted(analyses, key=lambda x: x.get("impact_score", 0), reverse=True)
    if use_llm:
        try:
            report = call_llm_agent(
                "agent_redacteur",
                (
                    "Tu es l'agent redacteur LLM. Redige un rapport Markdown professionnel en francais "
                    "pour une veille sur les frameworks IA. Structure obligatoire: titre, date, resume executif, "
                    "priorites, analyse detaillee, contexte interne RAG, risques, recommandations, controle anti-hallucination. "
                    "Chaque fait externe doit garder son URL source. Les recommandations doivent etre distinctes des faits."
                ),
                {
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "analyses": analyses,
                    "top_frameworks": top_framework_summaries(analyses, limit=5),
                },
                output="markdown",
            )
            if not report.startswith("#"):
                report = "# Rapport de veille - Frameworks IA\n\n" + report
            log("agent_redacteur", "Rapport redige par LLM", {"items": len(analyses), "chars": len(report)})
            return save_report(report, len(analyses))
        except Exception as exc:
            log_llm_fallback("agent_redacteur", exc)
    report = deterministic_generate_report(analyses)
    log("agent_redacteur", "Rapport redige par fallback deterministe", {"items": len(analyses), "chars": len(report)})
    return save_report(report, len(analyses))


def deterministic_evaluate_outputs(analyses: list[dict]) -> dict:
    missing_sources = [a.get("title") for a in analyses if not a.get("url")]
    missing_context = [a.get("title") for a in analyses if not a.get("internal_context")]
    return {
        "items_evalues": len(analyses),
        "missing_sources": missing_sources,
        "missing_internal_context": missing_context,
        "human_validation": get_human_validation(),
        "status": "OK" if not missing_sources else "A_CORRIGER",
    }


def normalize_evaluation_result(result: dict, baseline: dict) -> dict:
    result = {**baseline, **result, "human_validation": get_human_validation()}
    result["items_evalues"] = baseline["items_evalues"]
    if not isinstance(result.get("missing_sources"), list):
        result["missing_sources"] = baseline["missing_sources"]
    if not isinstance(result.get("missing_internal_context"), list):
        result["missing_internal_context"] = baseline["missing_internal_context"]
    if result.get("status") not in {"OK", "A_CORRIGER"}:
        result["status"] = baseline["status"]
    risks = result.get("hallucination_risks", [])
    if not isinstance(risks, (list, dict)):
        result["hallucination_risks"] = []
    return result


def evaluate_outputs(analyses: list[dict], use_llm: bool = True) -> dict:
    baseline = deterministic_evaluate_outputs(analyses)
    if use_llm:
        try:
            result = call_llm_agent(
                "agent_evaluateur",
                (
                    "Tu es l'agent evaluateur LLM. Controle les sources, le risque d'hallucination, "
                    "la presence du contexte interne RAG et la validation humaine. Retourne un objet JSON avec: "
                    "items_evalues, missing_sources, missing_internal_context, hallucination_risks, human_validation, status. "
                    "Le status vaut OK si les sources critiques sont presentes, sinon A_CORRIGER."
                ),
                {"analyses": analyses, "baseline": baseline, "human_validation": get_human_validation()},
            )
            if not isinstance(result, dict):
                raise ValueError("L'agent evaluateur LLM n'a pas retourne un objet JSON.")
            result = normalize_evaluation_result(result, baseline)
            log("agent_evaluateur", "Evaluation LLM terminee", result)
            return result
        except Exception as exc:
            log_llm_fallback("agent_evaluateur", exc)
    log("agent_evaluateur", "Evaluation fallback deterministe terminee", baseline)
    return baseline


def graph_prepare_rag(state: PipelineState) -> PipelineState:
    chunks = build_chunks()
    vector_index = build_vector_index(chunks)
    return {"chunks": chunks, "vector_index": vector_index}


def graph_collect(state: PipelineState) -> PipelineState:
    collected = collect_market_items(use_live=state.get("use_live", True), use_llm=state.get("use_llm", True))
    return {"collected": collected}


def graph_filter(state: PipelineState) -> PipelineState:
    filtered = filter_items(state.get("collected", []), use_llm=state.get("use_llm", True))
    return {"filtered": filtered}


def graph_analyze(state: PipelineState) -> PipelineState:
    analyses = analyze_items(state.get("filtered", []), state.get("chunks", []), use_llm=state.get("use_llm", True))
    return {"analyses": analyses}


def graph_write_report(state: PipelineState) -> PipelineState:
    report = generate_report(state.get("analyses", []), use_llm=state.get("use_llm", True))
    return {"report": report}


def graph_export(state: PipelineState) -> PipelineState:
    export_path = export_recommendations_csv(state.get("analyses", []))
    return {"export_path": str(export_path)}


def graph_evaluate(state: PipelineState) -> PipelineState:
    evaluation = evaluate_outputs(state.get("analyses", []), use_llm=state.get("use_llm", True))
    return {"evaluation": evaluation}


def build_langgraph_pipeline():
    if StateGraph is None or START is None or END is None:
        raise RuntimeError("langgraph n'est pas installe.")
    graph = StateGraph(PipelineState)
    graph.add_node("rag_prepare", graph_prepare_rag)
    graph.add_node("agent_collecteur_llm", graph_collect)
    graph.add_node("agent_filtreur_llm", graph_filter)
    graph.add_node("agent_analyste_llm", graph_analyze)
    graph.add_node("agent_redacteur_llm", graph_write_report)
    graph.add_node("export_csv", graph_export)
    graph.add_node("agent_evaluateur_llm", graph_evaluate)

    graph.add_edge(START, "rag_prepare")
    graph.add_edge("rag_prepare", "agent_collecteur_llm")
    graph.add_edge("agent_collecteur_llm", "agent_filtreur_llm")
    graph.add_edge("agent_filtreur_llm", "agent_analyste_llm")
    graph.add_edge("agent_analyste_llm", "agent_redacteur_llm")
    graph.add_edge("agent_redacteur_llm", "export_csv")
    graph.add_edge("export_csv", "agent_evaluateur_llm")
    graph.add_edge("agent_evaluateur_llm", END)
    return graph.compile()


def export_langgraph_visual() -> dict:
    ensure_dirs()
    app = build_langgraph_pipeline()
    graph = app.get_graph()
    mermaid_path = EXPORT_DIR / "orchestration_langgraph.mmd"
    png_path = EXPORT_DIR / "orchestration_langgraph.png"
    mermaid = graph.draw_mermaid()
    mermaid_path.write_text(mermaid, encoding="utf-8")
    result = {
        "mermaid_path": str(mermaid_path),
        "png_path": str(png_path),
        "png_exists": png_path.exists(),
        "mermaid": mermaid,
    }
    try:
        graph.draw_mermaid_png(output_file_path=str(png_path), background_color="white", padding=16)
        result["png_exists"] = png_path.exists()
        log("orchestrateur_langgraph", "Image du graphe LangGraph generee", {"path": str(png_path)})
    except Exception as exc:
        result["error"] = str(exc)
        log("orchestrateur_langgraph", "Generation image LangGraph indisponible", {"error": str(exc)})
    return result


def run_pipeline_sequential(use_live: bool = True, use_llm: bool = True) -> PipelineState:
    ensure_dirs()
    chunks = build_chunks()
    vector_index = build_vector_index(chunks)
    collected = collect_market_items(use_live=use_live, use_llm=use_llm)
    filtered = filter_items(collected, use_llm=use_llm)
    analyses = analyze_items(filtered, chunks, use_llm=use_llm)
    report = generate_report(analyses, use_llm=use_llm)
    export_path = export_recommendations_csv(analyses)
    evaluation = evaluate_outputs(analyses, use_llm=use_llm)
    return {
        "use_live": use_live,
        "use_llm": use_llm,
        "chunks": chunks,
        "vector_index": vector_index,
        "collected": collected,
        "filtered": filtered,
        "analyses": analyses,
        "report": report,
        "export_path": str(export_path),
        "evaluation": evaluation,
    }


def pipeline_result_from_state(state: PipelineState, orchestrator: str) -> dict:
    report = state.get("report", "")
    return {
        "orchestrator": orchestrator,
        "llm_requested": state.get("use_llm", True),
        "llm_configured": llm_configured(),
        "chunks": len(state.get("chunks", [])),
        "vector_index": state.get("vector_index", False),
        "collected": len(state.get("collected", [])),
        "filtered": len(state.get("filtered", [])),
        "analyses": len(state.get("analyses", [])),
        "report_chars": len(report),
        "export_csv": state.get("export_path", ""),
        "evaluation": state.get("evaluation", {}),
    }


def run_pipeline(use_live: bool = True, use_llm: bool = True) -> dict:
    ensure_dirs()
    initial_state: PipelineState = {"use_live": use_live, "use_llm": use_llm}
    try:
        app = build_langgraph_pipeline()
        final_state = app.invoke(initial_state)
        log(
            "orchestrateur_langgraph",
            "Pipeline LangGraph executee",
            {
                "use_live": use_live,
                "use_llm": use_llm,
                "nodes": [
                    "rag_prepare",
                    "agent_collecteur_llm",
                    "agent_filtreur_llm",
                    "agent_analyste_llm",
                    "agent_redacteur_llm",
                    "export_csv",
                    "agent_evaluateur_llm",
                ],
            },
        )
        return pipeline_result_from_state(final_state, orchestrator="langgraph")
    except Exception as exc:
        log("orchestrateur_langgraph", "Fallback orchestration Python apres erreur LangGraph", {"error": str(exc)})
        final_state = run_pipeline_sequential(use_live=use_live, use_llm=use_llm)
        return pipeline_result_from_state(final_state, orchestrator="python_fallback")
