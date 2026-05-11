# Description de la pipeline RAG

## 1. Ingestion

Les documents internes sont stockes dans `data/knowledge_base_interne/`. Ils representent une base de connaissances d'entreprise simulee : stack actuelle, projets IA, contraintes et retours d'experience.

## 2. Chunking

Chaque document est decoupe avec `RecursiveCharacterTextSplitter` de LangChain. Le recouvrement evite de perdre le contexte lorsqu'une idee se trouve a la frontiere entre deux chunks.

## 3. Vector DB

Les chunks sont indexes dans ChromaDB sous `data/vector_db/`.

Pour rester executable sans cout API, le prototype utilise des embeddings locaux deterministes bases sur un hachage stable des tokens. Cela permet de demontrer une vraie base vectorielle persistante. En production, ces embeddings peuvent etre remplaces par OpenAI, HuggingFace ou un modele local specialise.

## 4. Retrieval

Pour chaque item externe, une requete est construite avec :

- nom du framework ;
- resume de la tendance ;
- categorie de l'item.

Le systeme interroge ChromaDB et recupere les `top_k` chunks les plus proches.

## 5. Fallback lexical

Si ChromaDB est indisponible, le systeme bascule vers une recherche lexicale :

- tokenisation en mots ;
- comptage des frequences ;
- similarite cosinus avec NumPy.

## 6. Generation augmentee

L'agent analyste utilise les passages retrouves pour produire :

- un score d'impact ;
- une priorite ;
- une recommandation ;
- une justification interne.

## 7. Controle qualite

Chaque analyse passe par un validateur de schema simple. Si un champ obligatoire manque, le systeme le corrige avec une valeur par defaut et journalise l'action dans les logs de l'agent evaluateur.

