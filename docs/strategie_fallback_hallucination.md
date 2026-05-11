# Strategies de fallback, hallucination et context window

## Fallback

Le systeme applique plusieurs niveaux de fallback :

1. Si GitHub API repond, les donnees live sont ajoutees.
2. Si GitHub API echoue, l'erreur est loggee.
3. Le fichier `manual_seed.json` garantit une base de demonstration.
4. La generation du rapport continue sans blocage.

## Anti-hallucination

- Les faits externes sont lies a une URL.
- Les recommandations sont separees des observations.
- Le rapport cite les passages internes retrouves.
- Les erreurs API sont journalisees au lieu d'etre masquees.
- Le systeme n'invente pas de donnees live si une source echoue.

## Gestion de la context window

- Chunking des documents internes.
- Selection `top_k` des passages pertinents.
- Analyse item par item.
- Rapport final synthetique.
- Logs courts au format JSON.

## Confidentialite

- Les cles API sont dans `.env`.
- `.env` est ignore par Git.
- Les donnees internes ne sont pas envoyees a une API externe dans la version actuelle.
- Le prototype peut fonctionner sans LLM.

