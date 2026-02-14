# 📊 HR Turnover Analyzer

Outil d'analyse automatique du turnover RH - Génération de rapports à partir de données CSV.

## 🎯 Objectif du projet

Automatiser l'analyse du turnover de l'entreprise en :
- Important des données d'employés et de départs depuis des fichiers CSV
- Stockant les données dans une base SQLite
- Calculant le turnover global et par département
- Générant un rapport HTML avec graphiques interactifs

## 🚀 Statut du projet

**Phase actuelle** : Initialisation (Semaine 1)

- [x] Repository créé
- [ ] Modèle de données conçu
- [ ] Base de données SQLite créée
- [ ] Import CSV fonctionnel
- [ ] Calculs de turnover implémentés
- [ ] Génération de rapport HTML

## 🛠️ Technologies utilisées

- **Python 3.11+** : Langage principal
- **SQLite** : Base de données locale
- **pandas** : Manipulation de données
- **matplotlib/seaborn** : Visualisations
- **Jinja2** : Génération de rapports HTML

## 📋 Structure prévue du projet
```
hr-turnover-analyzer/
├── README.md                   # Ce fichier
├── requirements.txt            # Dépendances Python
├── schema.sql                  # Schéma de la base de données
├── main.py                     # Point d'entrée principal
├── data_loader.py             # Import CSV → SQLite
├── analytics.py               # Calculs de turnover
├── report_generator.py        # Génération rapport HTML
├── templates/
│   └── report_template.html   # Template Jinja2
├── sample_data/
│   ├── employees.csv          # Données exemple
│   └── exits.csv              # Données de départs
└── output/
    └── (rapports générés)
```

## 🎓 Contexte d'apprentissage

Ce projet fait partie de ma roadmap de montée en compétences techniques en tant que consultant SIRH.

**Objectif d'apprentissage** : Maîtriser Python, SQL, manipulation de données et génération de rapports automatiques.

## 📅 Timeline

- **Semaine 1** : Setup et modélisation de données
- **Semaine 2** : Développement core (import + calculs)
- **Semaine 3** : Visualisation et finalisation

## 📝 Notes

Projet pédagogique en cours de développement. Les données utilisées sont fictives.

---

**Auteur** : [BXS7]  
**Date de création** : 07/02/2025  
**License** : MIT
