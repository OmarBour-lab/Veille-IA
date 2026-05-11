# Projets IA internes simules

## Assistant documentaire RH

Objectif : repondre aux questions des collaborateurs a partir de documents internes.

Contraintes :
- Traçabilite des reponses.
- Citations obligatoires.
- Reponse "je ne sais pas" si les sources ne suffisent pas.

Technologies testees :
- LlamaIndex pour l'ingestion documentaire.
- ChromaDB pour le stockage vectoriel.
- OpenAI GPT-4o-mini pour la synthese.

## Agent support technique

Objectif : analyser des tickets et proposer des reponses preliminaires.

Contraintes :
- Validation humaine obligatoire.
- Logs de raisonnement synthetiques.
- Detection des demandes hors perimetre.

Technologies testees :
- CrewAI pour la separation des roles.
- LangChain pour quelques connecteurs.

## Veille technologique

Objectif : produire un rapport hebdomadaire sur les frameworks IA.

Critere de decision :
- Maturite du framework.
- Qualite de la documentation.
- Activite GitHub.
- Simplicite d'integration.
- Risque de verrouillage fournisseur.

