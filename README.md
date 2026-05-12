# Assistant Autonome de Veille sur les Frameworks IA

Projet realise par Omar BOUREZGUI et Wassim RHAZZAL pour le cours "Agent IA et Prompt Ingenierie".

## Objectif

Ce projet propose un systeme autonome capable de surveiller les tendances autour des frameworks IA, de croiser les informations collectees avec une base de connaissances interne simulee, puis de generer un rapport de synthese source, horodate et actionnable.

Le prototype couvre les frameworks suivants : LangChain, LlamaIndex, LangGraph, CrewAI, AutoGen, Haystack, DSPy et Smolagents.

## Architecture en bref

- Pipeline multi-agents en Python : collecte, filtrage, RAG, analyse, redaction et evaluation.
- RAG avec chunking LangChain, base vectorielle ChromaDB et fallback lexical.
- Dashboard Streamlit pour piloter la pipeline, consulter les rapports, lire les logs et effectuer une validation humaine.
- API FastAPI pour integrer le projet dans un workflow n8n.
- Serveur MCP local pour exposer les outils de veille a des clients ou agents externes.

## Livrables

- `README.md` : presentation et instructions d'execution.
- `rapport.md` : rapport principal du projet.
- `learning_log.md` : journal d'apprentissage et de realisation.
- `config.toml` : configuration des agents, sources, RAG et fallback.
- `source/*.ipynb` : notebooks de collecte, RAG, pipeline, tests et generation du rapport.
- `source/veille_agents.py` : moteur reutilisable du prototype.
- `dashboard/app.py` : dashboard web Streamlit.
- `source/api_server.py` : API HTTP pour integrer n8n.
- `source/mcp_server.py` : serveur MCP local pour exposer les outils de veille.
- `source/mcp_client_demo.py` : demonstration simple d'un client MCP externe.
- `n8n/workflow_veille_frameworks_ia.json` : workflow n8n importable.
- `docs/` : details du workflow, de la pipeline RAG, des prompts agents et des strategies de fiabilite.
- `logs/` : logs des agents conserves comme preuves d'execution.
- `data/knowledge_base_interne/` : base de connaissances interne simulee.
- `data/donnees_collectees/manual_seed.json` : jeu de donnees local utilise en fallback.

Les dossiers `data/rapports_generes/`, `data/vector_db/`, `data/exports/` et `data/validation/` sont generes automatiquement a l'execution.

## Installation rapide avec uv

Depuis la racine du projet :

```powershell
uv venv .venv
```

Installer les dependances :

```powershell
uv pip install -r requirements.txt --python .venv\Scripts\python.exe
```

Copier `.env.example` vers `.env`, puis renseigner les cles API necessaires. Le prototype peut fonctionner sans appel externe grace au fichier de fallback `data/donnees_collectees/manual_seed.json`.

## Execution de la pipeline

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

Chaque execution ajoute un nouveau rapport horodate dans `data/rapports_generes/`.

## Dashboard web

Lancer le dashboard Streamlit :

```powershell
.venv\Scripts\streamlit.exe run dashboard\app.py --server.port 8501
```

Puis ouvrir :

```text
http://localhost:8501
```

Le dashboard permet de :

- relancer la pipeline avec ou sans collecte GitHub live ;
- consulter les indicateurs de collecte, filtrage, analyse et generation ;
- visualiser les priorites de veille et les scores par framework ;
- lire le dernier rapport et les rapports horodates ;
- consulter les logs recents de chaque agent ;
- valider ou rejeter humainement le dernier rapport ;
- telecharger les exports Markdown et CSV.

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

Dans un autre terminal, lancer la demonstration client :

```powershell
.venv\Scripts\python.exe source\mcp_client_demo.py
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

Les logs produits par ces agents sont disponibles dans `logs/` et servent de preuves d'execution pour le rapport.

## Securite des cles API

Les cles doivent rester dans `.env`. Le fichier `.gitignore` exclut `.env`, `*.env`, la base vectorielle, les exports, les validations locales et les rapports generes.

Les fichiers `logs/*.log` sont volontairement conserves dans le depot, car ils font partie des preuves demandees dans les consignes du projet. Ne jamais y ecrire de secrets.

## Bibliotheques utilisees

- `numpy` : calcul numerique et scoring.
- `pandas` : dedoublonnage, filtrage et affichage tabulaire.
- `requests` : appels HTTP vers GitHub API.
- `python-dotenv` : chargement des variables depuis `.env`.
- `langchain-text-splitters` : decoupage des documents internes en chunks.
- `chromadb` : base vectorielle persistante pour le RAG.
- `jupyter` : execution des notebooks.
- `streamlit` : dashboard web.
- `fastapi` et `uvicorn` : API HTTP pour n8n.
- `mcp` : serveur MCP local pour l'interoperabilite agentique.
