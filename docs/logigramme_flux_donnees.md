# Logigramme du flux de donnees

```mermaid
flowchart TD
    A["Declenchement manuel ou planifie"] --> B["Agent collecteur"]
    B --> C["Sources externes: GitHub/API"]
    B --> D["Fallback local: manual_seed.json"]
    C --> E["Items collectes"]
    D --> E
    E --> F["Agent filtreur"]
    F --> G["Items dedupliques et classes"]
    H["Base interne simulee"] --> I["Chunking avec overlap"]
    I --> J["Index RAG lexical"]
    G --> K["Agent RAG"]
    J --> K
    K --> L["Contexte interne pertinent"]
    L --> M["Agent analyste"]
    G --> M
    M --> N["Scores, priorites, recommandations"]
    N --> O["Agent redacteur"]
    O --> P["Rapport Markdown"]
    N --> Q["Agent evaluateur"]
    P --> Q
    Q --> R["Logs et controle anti-hallucination"]
```

## Description courte

Le systeme collecte des signaux externes, les nettoie, recupere les informations internes pertinentes avec une pipeline RAG, puis genere une synthese priorisee. Chaque agent produit des logs horodates.

