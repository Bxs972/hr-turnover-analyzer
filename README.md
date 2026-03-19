# HR Turnover Analyzer

Outil d'analyse automatique du turnover RH — gestion des collaborateurs, calculs de métriques et génération de rapports HTML à partir de données CSV.

Conçu pour gérer une entreprise d'une **centaine de collaborateurs** répartis sur plusieurs départements.

## Fonctionnalités

- **Import CSV** : chargement en masse des employés et des départs avec validation ligne par ligne
- **Base de données SQLite** : stockage structuré avec index optimisés pour les requêtes analytiques
- **CRUD complet** : ajout, modification, suppression et recherche d'employés
- **Pagination & filtres** : navigation dans de grandes listes (par département, statut, nom…)
- **Calculs de turnover** : global, par département, mensuel et trimestriel
- **Rapport HTML autonome** : graphiques embarqués (base64), aucune dépendance externe à l'ouverture
- **Interface CLI** : toutes les opérations accessibles en ligne de commande

## Technologies

- **Python 3.11+**
- **SQLite** — base de données locale (WAL mode, foreign keys, index)
- **pandas** — manipulation de données
- **matplotlib / seaborn** — visualisations (graphiques base64)
- **Jinja2** — template HTML

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation rapide

```bash
# 1. Initialiser la base de données
python main.py init

# 2. Importer les données
python main.py import employees sample_data/employees.csv
python main.py import exits sample_data/exits.csv

# 3. Statistiques dans le terminal
python main.py stats --year 2024

# 4. Générer un rapport HTML
python main.py report --year 2024
```

## Toutes les commandes

```
python main.py init                                         # Créer la BDD
python main.py import employees <fichier.csv>              # Importer employés
python main.py import exits <fichier.csv>                  # Importer départs

python main.py employee list [--department RH] [--status active] [--search dupont] [--page 2]
python main.py employee add --id EMP101 --first-name Lucie --last-name Martin --hire-date 2024-03-01 --department Finance --position Comptable
python main.py employee show EMP101
python main.py employee update EMP101 --position "Responsable comptable"
python main.py employee delete EMP101

python main.py exit add --id EMP042 --date 2024-09-15 --reason resignation
python main.py exits list --year 2024 [--department Ventes]

python main.py departments                                  # Effectif par département
python main.py stats [--year 2024]                         # Statistiques console
python main.py report [--year 2024] [--output mon_rapport.html]
```

## Structure du projet

```
hr-turnover-analyzer/
├── main.py                     # Point d'entrée CLI (argparse)
├── data_loader.py              # CRUD + import CSV → SQLite
├── analytics.py                # Calculs de turnover (global, depts, tendances)
├── report_generator.py         # Génération de rapport HTML avec graphiques
├── schema.sql                  # Schéma de la base de données
├── requirements.txt            # Dépendances Python
├── templates/
│   └── report_template.html   # Template Jinja2
├── sample_data/
│   ├── employees.csv           # 100 collaborateurs fictifs
│   └── exits.csv              # 18 départs fictifs (2024-2025)
└── output/
    └── (rapports HTML générés)
```

## Format des fichiers CSV

**employees.csv** — colonnes obligatoires : `employee_id`, `first_name`, `last_name`, `hire_date`
Colonnes optionnelles : `email`, `department`, `position`, `status` (active/inactive)

**exits.csv** — colonnes obligatoires : `employee_id`, `exit_date`, `reason`
Valeurs acceptées pour `reason` : `resignation`, `dismissal`, `retirement`, `end_of_contract`, `other`
Colonne optionnelle : `notes`

Dates au format **YYYY-MM-DD**.

## Métriques calculées

| Métrique | Description |
|---|---|
| Taux de turnover | `(départs / effectif début de période) × 100` |
| Turnover par département | Même formule filtrée par service |
| Tendance mensuelle | Taux mois par mois sur l'année |
| Bilan trimestriel | Taux par trimestre |
| Ancienneté moyenne | Moyenne des durées (en années) des actifs |
| Nouvelles embauches | Nombre de recrutements sur la période |

---

**Auteur** : BXS7
**Date de création** : 07/02/2025
**Licence** : MIT
