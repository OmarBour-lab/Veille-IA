# Assistant Autonome de Veille sur les Frameworks IA

Projet realise par Omar BOUREZGUI et Wassim RHAZZAL pour le cours "Agent IA et Prompt Ingenierie".

## Objectif

Ce projet propose un systeme autonome capable de surveiller les tendances autour des frameworks IA, de croiser les informations collectees avec une base de connaissances interne simulee, puis de generer un rapport de synthese source et actionnable.

Le prototype couvre les frameworks suivants : LangChain, LlamaIndex, LangGraph, CrewAI, AutoGen, Haystack, DSPy et Smolagents.

## Livrables

- `README.md` : presentation et instructions d'execution.
- `rapport.md` : rapport principal du projet.
- `learning_log.md` : journal d'apprentissage et de realisation.
- `config.toml` : configuration des agents, sources, RAG et fallback.
- `source/*.ipynb` : notebooks de collecte, RAG, pipeline, tests et generation du rapport.
- `source/veille_agents.py` : moteur reutilisable du prototype.
- `dashboard/app.py` : dashboard web minimaliste avec Streamlit.
- `source/api_server.py` : API HTTP pour integrer n8n.
- `source/mcp_server.py` : serveur MCP local pour exposer les outils de veille.
- `source/mcp_client_demo.py` : demonstration simple d'un client externe.
- `n8n/workflow_veille_frameworks_ia.json` : workflow n8n importable.
- `docs/system_prompts_agents.md` : prompts systeme des agents.
- `docs/` : details du workflow, de la pipeline RAG et des strategies de fiabilite.
- `logs/` : logs generes automatiquement par les agents.
- `data/` : base interne simulee, donnees collectees et rapports generes.

## Installation rapide avec uv

1. Creer l'environnement virtuel :

```powershell
uv venv .venv
```

2. Installer les dependances :

```powershell
uv pip install -r requirements.txt --python .venv\Scripts\python.exe
```

3. Copier `.env.example` vers `.env` et renseigner les cles API.
4. Verifier que `.env` n'est jamais publie. Il est deja ignore par `.gitignore`.

Le prototype fonctionne aussi en mode fallback avec le fichier `data/donnees_collectees/manual_seed.json`.

## Execution

Execution complete depuis un terminal :

```powershell
.venv\Scripts\python.exe source\run_demo.py
```

Execution pedagogique depuis Jupyter :

1. `source/01_collecte_donnees.ipynb`
2. `source/02_construction_base_rag.ipynb`
3. `source/03_pipeline_multi_agents.ipynb`
4. `source/04_tests_logs_evaluation.ipynb`
5. `source/05_generation_rapport.ipynb`

Le rapport genere se trouve dans `data/rapports_generes/rapport_veille.md`.

## Dashboard web

Lancer le dashboard Streamlit :

```powershell
.venv\Scripts\streamlit.exe run dashboard\app.py --server.port 8501
```

Puis ouvrir :

```text
http://localhost:8501
```

Le dashboard affiche :

- les indicateurs de collecte et d'analyse ;
- les scores par framework ;
- le tableau des recommandations ;
- le dernier rapport et les anciens rapports horodates ;
- les logs recents de chaque agent ;
- un bouton pour relancer la pipeline.
- une validation humaine du dernier rapport ;
- un export CSV compatible Google Sheets.

## Integration n8n

Lancer l'API locale :

```powershell
.venv\Scripts\uvicorn.exe source.api_server:app --host 127.0.0.1 --port 8000
```

Tester l'API :

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
```

Importer ensuite le workflow suivant dans n8n :

```text
n8n/workflow_veille_frameworks_ia.json
```

Le workflow contient un declenchement manuel, une planification hebdomadaire, un appel `POST /pipeline/run`, la recuperation du dernier rapport, une preparation d'export Google Sheets, une validation humaine et une branche fallback/correction.

Si n8n tourne dans Docker, garder `http://host.docker.internal:8000`. Si n8n tourne directement sur Windows, remplacer par `http://127.0.0.1:8000`.

## Integration MCP

Lancer le serveur MCP :

```powershell
.venv\Scripts\python.exe source\mcp_server.py
```

Le serveur expose des outils standardises :

- `run_market_watch`
- `get_pipeline_status`
- `list_generated_reports`
- `get_latest_report`
- `get_agent_logs`
- `set_report_validation`

Un client compatible MCP peut utiliser ces outils sans connaitre les details internes du code Python.

## Architecture agents

- Agent collecteur : collecte les signaux externes depuis GitHub ou le fallback local.
- Agent filtreur : deduplique et filtre les items pertinents.
- Agent RAG : interroge la base vectorielle ChromaDB construite a partir de la base interne simulee.
- Agent analyste : calcule l'impact et formule une recommandation.
- Agent redacteur : genere le rapport final.
- Agent evaluateur : controle les sources, les logs et les risques d'hallucination.

## Securite des cles API

Les cles doivent rester dans `.env`. Le fichier `.gitignore` exclut `.env`, `*.env`, les logs et les rapports generes afin de reduire le risque de fuite.

## Bibliotheques utilisees

- `numpy` : calcul de similarite cosinus pour le retrieval.
- `requests` : appels HTTP vers GitHub API.
- `python-dotenv` : chargement des cles depuis `.env`.
- `langchain-text-splitters` : decoupage des documents internes en chunks.
- `pandas` : disponible pour l'analyse tabulaire dans les notebooks.
- `chromadb` : base vectorielle persistante pour le RAG.
- `langchain-text-splitters` : decoupage des documents internes.
- `jupyter` : execution des notebooks.
- `streamlit` : dashboard web minimaliste.
- `fastapi` et `uvicorn` : API HTTP pour n8n.
- `mcp` : serveur MCP local pour interoperabilite agentique.
