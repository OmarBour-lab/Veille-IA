# Learning Log

## Informations generales

- Projet : Assistant Autonome de Veille sur les Frameworks IA
- Membres : Omar BOUREZGUI, Wassim RHAZZAL
- Cours : Agent IA et Prompt Ingenierie
- Periode : mai 2026
- Version du prototype : agents LLM GitHub Models, RAG ChromaDB, n8n, MCP, Streamlit

## Entree 1 - Cadrage du sujet

Objectif : comprendre le besoin et transformer le sujet en architecture realisable.

Travail realise :

- Analyse du sujet : surveiller les tendances des frameworks IA.
- Identification de la base interne comme source de contextualisation.
- Definition des livrables : README, rapport, learning log, notebooks, TOML, source, demo.
- Choix d'un prototype simple/intermediaire mais extensible.

Apprentissage :

Un projet agentique ne doit pas etre seulement un prompt. Il faut penser en flux de donnees, roles, outils, logs et points de controle.

## Entree 2 - Modelisation multi-agents

Objectif : decomposer le systeme en agents specialises.

Travail realise :

- Creation de six agents : collecteur, filtreur, RAG, analyste, redacteur, evaluateur.
- Attribution d'un role clair a chaque agent.
- Ajout de logs dedies par agent dans `logs/`.
- Redaction des prompts systeme dans `docs/system_prompts_agents.md`.

Apprentissage :

La decomposition agentique rend le systeme plus explicable et plus facile a tester qu'un seul grand prompt.

## Entree 3 - Base interne et pipeline RAG

Objectif : croiser les tendances externes avec les connaissances internes.

Travail realise :

- Creation d'une base interne simulee dans `data/knowledge_base_interne/`.
- Chunking avec `langchain-text-splitters`.
- Mise en place de ChromaDB comme base vectorielle persistante.
- Ajout d'embeddings locaux deterministes pour eviter les couts API.
- Conservation d'un fallback lexical avec NumPy.

Apprentissage :

Le RAG sert ici a contextualiser une decision, pas seulement a repondre a une question. Le fallback est important pour garantir une demonstration stable.

## Entree 4 - Collecte, fallback et robustesse

Objectif : rendre la collecte fiable malgre les erreurs reseau ou API.

Travail realise :

- Collecte via GitHub API lorsque disponible.
- Fallback automatique vers `manual_seed.json`.
- Logs des echecs API dans `agent_collecteur.log`.
- Validation de schema simple pour corriger les champs manquants.

Apprentissage :

Un systeme autonome doit savoir continuer proprement lorsqu'une source externe echoue. Il ne doit pas inventer les donnees manquantes.

## Entree 5 - Rapport et export

Objectif : produire des sorties exploitables par une equipe technique.

Travail realise :

- Generation automatique d'un rapport Markdown.
- Creation de rapports horodates pour conserver l'historique.
- Conservation d'un fichier `rapport_veille.md` comme dernier rapport.
- Export CSV compatible Google Sheets dans `data/exports/`.

Apprentissage :

Un rapport de veille doit separer les faits, les sources, le contexte interne et les recommandations.

## Entree 6 - Dashboard Streamlit

Objectif : rendre le prototype demonstrable et lisible.

Travail realise :

- Creation d'un dashboard Streamlit.
- Affichage des KPIs, priorites, scores, rapports, logs et exports.
- Ajout d'une validation humaine Human-in-the-Loop.
- Amelioration du theme visuel et du contraste.

Apprentissage :

Une interface de supervision rend les logs et resultats plus comprehensibles pendant la soutenance.

## Entree 7 - Integration n8n

Objectif : respecter la couche d'orchestration demandee dans le bac a sable technologique.

Travail realise :

- Creation d'une API FastAPI pour piloter la pipeline.
- Creation d'un workflow n8n importable.
- Ajout de declenchement manuel, planification, appel pipeline, export, validation et fallback.
- Documentation de l'usage dans `docs/integration_n8n_mcp_agentique.md`.

Apprentissage :

n8n est utile pour orchestrer les evenements, declencher la pipeline et preparer la diffusion. Il ne remplace pas forcement les agents, mais il structure leur execution.

## Entree 8 - Integration MCP

Objectif : ajouter une couche d'interoperabilite standardisee.

Travail realise :

- Creation d'un serveur MCP dans `source/mcp_server.py`.
- Exposition d'outils : execution de veille, statut, rapports, logs, validation.
- Ajout d'une demo client dans `source/mcp_client_demo.py`.

Apprentissage :

MCP permet de separer la logique de l'agent des sources et outils. Cela rend le systeme plus modulaire qu'une integration hardcodee.

## Entree 9 - Tests et verification

Objectif : verifier que les pieces principales fonctionnent ensemble.

Tests realises :

- Execution de `source/run_demo.py`.
- Verification de l'index ChromaDB.
- Verification de l'export CSV.
- Test de l'API `/health` et `/pipeline/status`.
- Compilation des fichiers Python.
- Verification du workflow n8n JSON.

Resultat :

La pipeline s'execute correctement avec `evaluation: OK`.

## Entree 10 - Difficultes et decisions

Difficultes rencontrees :

- Certaines APIs externes peuvent etre bloquees par le reseau.
- Les composants Streamlit ont necessite des ajustements CSS pour garder un bon contraste.
- L'utilisation de noeuds Advanced AI natifs dans n8n depend de l'environnement n8n disponible ; l'orchestration interne retenue est LangGraph.

Decisions prises :

- Garder un fallback local pour garantir la demonstration.
- Utiliser ChromaDB avec embeddings locaux pour eviter les couts et les cles API.
- Presenter l'architecture comme hybride : n8n declenche le workflow, LangGraph orchestre les agents LLM, MCP expose les outils.

## Entree 11 - Limites restantes

Limites :

- La base interne reste simulee.
- Les noeuds Advanced AI natifs n8n restent optionnels ; le coeur multi-agent est deja orchestre par LangGraph.
- L'export Google Sheets est fourni sous forme CSV, pas encore connecte a un compte Google.
- Les embeddings locaux sont suffisants pour la demonstration, mais moins performants que des embeddings specialises.

Ameliorations possibles :

- Brancher un vrai noeud Google Sheets dans n8n.
- Utiliser des embeddings OpenAI ou HuggingFace.
- Ajouter un benchmark de pertinence RAG.
- Ajouter un vrai client MCP pendant la soutenance.
- Ajouter une boucle de self-correction LLM plus avancee avec Pydantic.

## Entree 12 - Consolidation finale des livrables

Objectif : verifier que les fichiers de rendu restent coherents avec la version actuelle du prototype.

Travail realise :

- Relecture et harmonisation du `README.md`.
- Verification du `rapport.md`, du logigramme, de la documentation RAG et des strategies de fallback.
- Correction du logigramme pour representer ChromaDB comme base vectorielle principale et NumPy comme fallback lexical.
- Clarification de la configuration : GitHub et le fallback local sont actifs, arXiv reste hors perimetre du prototype actuel.
- Verification que les logs agents restent conserves comme preuves d'execution, tandis que les rapports generes, exports, validations et bases vectorielles restent ignores par Git.

Apprentissage :

La documentation doit suivre l'evolution du code. Quand on ajoute n8n, MCP, Streamlit ou ChromaDB, il faut mettre a jour le rapport, le learning log et les schemas pour eviter de presenter une architecture differente de celle qui tourne vraiment.

## Entree 13 - Passage aux agents LLM

Objectif : remplacer les agents logiques deterministes par des agents LLM appeles via GitHub Models.

Travail realise :

- Ajout de `langchain-openai` pour appeler GitHub Models avec une API compatible OpenAI.
- Ajout de la configuration `GITHUB_MODELS_TOKEN`, `GITHUB_API_KEY`, `GITHUB_MODELS_MODEL` et `GITHUB_MODELS_BASE_URL`.
- Transformation du collecteur, filtreur, analyste, redacteur et evaluateur en agents LLM par defaut.
- Conservation du RAG avec ChromaDB pour fournir le contexte interne aux agents LLM.
- Garantie que le texte de recommandation est produit par l'agent analyste LLM et trace avec `recommendation_source="llm"`.
- Mise a jour de FastAPI, MCP, n8n et Streamlit pour lancer la pipeline avec `use_llm=true`.
- Conservation d'un fallback deterministe uniquement si l'appel LLM ou une API externe echoue.

Apprentissage :

Un agent LLM doit avoir un role clair, un schema de sortie controle et des logs. Le fallback reste necessaire, mais il ne doit pas remplacer le chemin principal : il sert a rendre la demonstration robuste quand l'API ou le reseau est indisponible.

## Entree 14 - Orchestration LangGraph

Objectif : remplacer l'orchestration lineaire manuelle par un graphe multi-agent explicite.

Travail realise :

- Ajout de `langgraph` aux dependances.
- Creation d'un `PipelineState` partage par les noeuds du graphe.
- Transformation de la pipeline en noeuds LangGraph : preparation RAG, collecteur LLM, filtreur LLM, analyste LLM, redacteur LLM, export CSV et evaluateur LLM.
- Optimisation de l'agent analyste LLM en mode batch pour eviter un appel API par item et accelerer la demonstration.
- Conservation d'un fallback d'orchestration Python si LangGraph est indisponible.
- Ajout du champ `orchestrator` dans le resultat de pipeline pour prouver que l'execution passe par LangGraph.

Apprentissage :

LangGraph rend l'orchestration plus explicite : les agents ne sont plus seulement appeles dans une fonction lineaire, ils sont organises comme un graphe d'etats. C'est plus lisible pour expliquer la coordination dans un systeme multi-agent.
