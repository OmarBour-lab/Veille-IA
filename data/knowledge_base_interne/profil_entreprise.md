# Profil interne simule de l'entreprise

## Contexte general

L'entreprise developpe des solutions IA pour des equipes produit et support client. Elle privilegie les technologies open-source, auditables et compatibles avec un deploiement local ou cloud prive.

## Stack actuelle

- Python pour les prototypes IA.
- FastAPI pour les APIs internes.
- PostgreSQL pour les donnees relationnelles.
- ChromaDB pour les experimentations RAG locales.
- GitHub Actions pour l'integration continue.
- Notebooks Jupyter pour les preuves de concept.

## Contraintes

- Les donnees internes sensibles ne doivent pas etre envoyees vers des services externes sans anonymisation.
- Les recommandations doivent etre sourcees.
- Les couts LLM doivent rester maitrises.
- Les frameworks choisis doivent etre maintenables par une petite equipe.

## Experience passee

- LangChain a ete teste pour l'orchestration RAG, mais certaines chaines etaient difficiles a deboguer.
- LlamaIndex a donne de bons resultats pour l'indexation documentaire et la recherche contextuelle.
- Haystack est considere robuste pour des pipelines RAG plus industriels.
- CrewAI est juge interessant pour expliquer et demontrer une architecture multi-agents.

