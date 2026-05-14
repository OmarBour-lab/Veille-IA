# Logigramme du flux de donnees

```mermaid
flowchart TD
    A["Declenchement manuel, n8n ou MCP"] --> LG["Graphe LangGraph"]
    LG --> B["Agent collecteur LLM"]
    B --> C["Sources externes: GitHub/API"]
    B --> D["Fallback local: manual_seed.json"]
    C --> E["Items collectes"]
    D --> E
    E --> F["Agent filtreur LLM"]
    F --> G["Items dedupliques et classes"]
    H["Base interne simulee"] --> I["Chunking avec overlap"]
    I --> J["Index vectoriel ChromaDB"]
    I --> S["Fallback lexical NumPy"]
    G --> K["Agent RAG"]
    J --> K
    S --> K
    K --> L["Contexte interne pertinent"]
    L --> M["Agent analyste LLM"]
    G --> M
    M --> N["Scores, priorites, recommandations"]
    N --> O["Agent redacteur LLM"]
    O --> P["Rapport Markdown"]
    N --> Q["Agent evaluateur LLM"]
    P --> Q
    Q --> R["Logs et controle anti-hallucination"]
```

## Description courte

Le systeme collecte des signaux externes, les nettoie, recupere les informations internes pertinentes avec une pipeline RAG, puis genere une synthese priorisee. Chaque agent produit des logs horodates.
