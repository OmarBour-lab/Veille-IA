# Strategies de fallback, hallucination et context window

## Fallback

Le systeme applique plusieurs niveaux de fallback :

1. Si GitHub Models repond, les agents LLM traitent collecte, filtrage, analyse, redaction et evaluation.
2. Si un appel LLM echoue, l'erreur est loggee et le fallback deterministe correspondant est active.
3. Si GitHub API repond, les donnees live sont ajoutees.
4. Si GitHub API echoue, l'erreur est loggee.
5. Le fichier `manual_seed.json` garantit une base de demonstration.
6. La generation du rapport continue sans blocage.

## Anti-hallucination

- Les faits externes sont lies a une URL.
- Les recommandations sont separees des observations.
- Le rapport cite les passages internes retrouves.
- Les erreurs API sont journalisees au lieu d'etre masquees.
- Le systeme n'invente pas de donnees live si une source echoue.

## Gestion de la context window

- Chunking des documents internes.
- Selection `top_k` des passages pertinents.
- Analyse des items en batch lorsque l'agent analyste LLM est disponible, avec fallback item par item en cas d'erreur.
- Rapport final synthetique.
- Logs courts au format JSON.

## Confidentialite

- Les cles API sont dans `.env`.
- `.env` est ignore par Git.
- Seuls les chunks internes top-k utiles sont envoyes a GitHub Models pendant l'analyse LLM ; les cles et fichiers `.env` ne sont jamais envoyes.
- Le chemin principal utilise les agents LLM, mais le prototype conserve un fallback deterministe pour les demonstrations sans reseau ou sans quota.
