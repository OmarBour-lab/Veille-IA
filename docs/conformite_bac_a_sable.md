# Verification de conformite - Bac a Sable Technologique

## Synthese

Le projet couvre maintenant les quatre couches demandees dans le document :

- orchestration n8n via workflow importable et API locale ;
- couche cognitive multi-agents LLM avec prompts dedies et orchestration LangGraph ;
- base de connaissance vectorielle ChromaDB ;
- action et resilience via MCP, export CSV, validation humaine, fallback et logs.

La seule reserve importante est que les agents LLM sont executes dans le graphe LangGraph via GitHub Models, puis declenches par n8n via API. Les noeuds Advanced AI natifs n8n restent optionnels si l'environnement n8n du groupe les fournit.

## Matrice de conformite

| Exigence | Etat actuel | Evaluation | Suggestion |
|---|---|---|---|
| SMA interconnecte et automatise | Agents LLM orchestres par LangGraph + API + dashboard + n8n | Conforme prototype | Montrer les logs agents pendant la soutenance |
| n8n comme workflow visuel et triggers | Workflow importable avec trigger manuel et hebdomadaire | Conforme prototype | Importer dans n8n et faire une capture |
| Minimum 3 agents IA | Agents LLM collecteur, filtreur, analyste, redacteur et evaluateur via GitHub Models | Conforme prototype | Montrer les logs "Appel LLM reussi" |
| System prompts specifiques | `docs/system_prompts_agents.md` | Conforme | Coller ces prompts dans n8n si possible |
| Gestion Context Window | chunking, top-k, rapports synthetiques, logs courts | Conforme | Expliquer les valeurs chunk/top-k |
| Vector DB | ChromaDB persistant dans `data/vector_db` | Conforme prototype | Utiliser embeddings OpenAI/HuggingFace en version production |
| Interrogation semantique | Agent RAG interroge ChromaDB | Conforme prototype | Ajouter benchmark retrieval si temps disponible |
| Outil bureautique/cloud | Export CSV compatible Google Sheets + n8n | Partiel | Brancher un vrai noeud Google Sheets si compte disponible |
| MCP | Serveur MCP avec outils de veille | Conforme | Demontrer `source/mcp_server.py` |
| Client MCP | `source/mcp_client_demo.py` comme demo de consommation externe | Conforme prototype | Utiliser un vrai client MCP si disponible |
| Observation & fallback | logs d'erreur, fallback donnees locales, fallback RAG lexical | Conforme | Montrer `agent_collecteur.log` |
| Human-in-the-Loop | validation Streamlit + API + branche n8n | Conforme prototype | Faire une capture de l'approbation |
| Logs de raisonnement/tests | logs par agent + notebook evaluation | Conforme | Ajouter captures de logs dans rapport final |
| JSON invalide/self-correction | validateur schema + correction champs manquants | Conforme prototype | Remplacer par Pydantic strict si besoin |
| Tool usage autonome vs orchestration | architecture hybride transparente | Conforme prototype | Expliquer que n8n orchestre, MCP expose les outils, Python execute les agents LLM |

## Corrections restantes recommandees

1. Importer le workflow dans n8n et capturer le schema.
2. Si n8n Advanced AI est disponible, ajouter en option des noeuds AI Agent natifs n8n pour comparer avec l'orchestration LangGraph.
3. Connecter l'export CSV a Google Sheets dans n8n.
4. Faire une capture du dashboard montrant la validation humaine.
5. Montrer le serveur MCP ou expliquer les outils exposes.

## Formulation recommandee

Notre solution est une architecture agentique hybride. n8n gere l'orchestration evenementielle externe, LangGraph orchestre les agents LLM internes, MCP expose les outils de veille de maniere standardisee, ChromaDB fournit la memoire vectorielle, et les agents LLM realisent les taches cognitives avec logs, fallback, validation de schema et validation humaine.
