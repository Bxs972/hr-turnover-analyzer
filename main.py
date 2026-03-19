#!/usr/bin/env python3
"""
HR Turnover Analyzer - Point d'entrée principal.

Usage :
    python main.py init
    python main.py import employees sample_data/employees.csv
    python main.py import exits sample_data/exits.csv
    python main.py employee list [--department RH] [--status active] [--search dupont]
    python main.py employee add --id EMP001 --first-name Jean --last-name Dupont --hire-date 2023-01-15
    python main.py employee show EMP001
    python main.py employee update EMP001 --position "Chef de projet"
    python main.py employee delete EMP001
    python main.py exit add --id EMP001 --date 2024-06-30 --reason resignation
    python main.py exits list [--year 2024] [--department Ventes]
    python main.py stats [--year 2024]
    python main.py report [--year 2024] [--output rapport.html]
    python main.py departments
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import data_loader as dl
import analytics as an
import report_generator as rg


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------

def _print_table(headers, rows, widths):
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*[str(v)[:w] for v, w in zip(row, widths)]))


def _ok(msg):
    print(f"[OK] {msg}")


def _err(msg):
    print(f"[ERREUR] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------

def cmd_init(args):
    dl.init_db()
    _ok("Base de données prête.")


# ---- Import ----------------------------------------------------------------

def cmd_import(args):
    filepath = Path(args.file)
    if not filepath.exists():
        _err(f"Fichier introuvable : {filepath}")
        sys.exit(1)

    if args.type == "employees":
        imported, skipped = dl.import_employees_csv(filepath)
        _ok(f"{imported} employé(s) importé(s).")
    else:
        imported, skipped = dl.import_exits_csv(filepath)
        _ok(f"{imported} départ(s) importé(s).")

    if skipped:
        print(f"  {len(skipped)} ligne(s) ignorée(s) :")
        for s in skipped:
            print(f"    Ligne {s['row']} — {'; '.join(s['errors'])}")


# ---- Employés --------------------------------------------------------------

def cmd_employee_list(args):
    employees, total = dl.list_employees(
        department=args.department,
        status=args.status,
        search=args.search,
        page=args.page,
        page_size=args.page_size,
    )
    if not employees:
        print("Aucun employé trouvé.")
        return

    headers = ["ID", "Nom", "Prénom", "Département", "Poste", "Embauche", "Statut"]
    widths = [10, 18, 16, 22, 24, 12, 10]
    rows = [
        (
            e["employee_id"],
            e["last_name"],
            e["first_name"],
            e["department"] or "-",
            e["position"] or "-",
            e["hire_date"],
            e["status"],
        )
        for e in employees
    ]
    _print_table(headers, rows, widths)
    total_pages = (total + args.page_size - 1) // args.page_size
    print(f"\n  {len(employees)}/{total} employé(s) — page {args.page}/{total_pages}")


def cmd_employee_add(args):
    dl.add_employee({
        "employee_id": args.id,
        "first_name": args.first_name,
        "last_name": args.last_name,
        "email": args.email or "",
        "department": args.department or "",
        "position": args.position or "",
        "hire_date": args.hire_date,
        "status": args.status or "active",
    })
    _ok(f"Employé {args.id} ajouté.")


def cmd_employee_update(args):
    updates = {}
    for attr in ("first_name", "last_name", "email", "department", "position", "status", "hire_date"):
        val = getattr(args, attr, None)
        if val:
            updates[attr] = val
    dl.update_employee(args.id, updates)
    _ok(f"Employé {args.id} mis à jour.")


def cmd_employee_delete(args):
    answer = input(f"Supprimer définitivement {args.id} ? [o/N] : ").strip().lower()
    if answer != "o":
        print("Annulé.")
        return
    dl.delete_employee(args.id)
    _ok(f"Employé {args.id} supprimé.")


def cmd_employee_show(args):
    emp = dl.get_employee(args.id)
    if not emp:
        _err(f"Employé introuvable : {args.id}")
        sys.exit(1)
    print(f"\n=== Fiche employé : {args.id} ===")
    labels = {
        "employee_id": "Identifiant",
        "first_name": "Prénom",
        "last_name": "Nom",
        "email": "Email",
        "department_name": "Département",
        "position": "Poste",
        "hire_date": "Date d'embauche",
        "status": "Statut",
        "created_at": "Créé le",
        "updated_at": "Modifié le",
    }
    for key, label in labels.items():
        if key in emp:
            print(f"  {label:<20} : {emp[key] or '-'}")


def cmd_employee(args):
    dispatch = {
        "list": cmd_employee_list,
        "add": cmd_employee_add,
        "update": cmd_employee_update,
        "delete": cmd_employee_delete,
        "show": cmd_employee_show,
    }
    dispatch[args.action](args)


# ---- Départs ---------------------------------------------------------------

def cmd_exit_add(args):
    dl.add_exit({
        "employee_id": args.id,
        "exit_date": args.date,
        "reason": args.reason,
        "notes": args.notes or "",
    })
    _ok(f"Départ de {args.id} enregistré ({args.reason}).")


def cmd_exits_list(args):
    start = f"{args.year}-01-01" if args.year else None
    end = f"{args.year}-12-31" if args.year else None
    exits, total = dl.list_exits(
        start_date=start,
        end_date=end,
        department=args.department,
        page=args.page,
        page_size=args.page_size,
    )
    if not exits:
        print("Aucun départ trouvé.")
        return

    labels = dl.REASON_LABELS
    headers = ["ID", "Nom", "Département", "Date départ", "Motif"]
    widths = [10, 22, 22, 14, 20]
    rows = [
        (
            e["employee_id"],
            f"{e['last_name']} {e['first_name']}",
            e["department"] or "-",
            e["exit_date"],
            labels.get(e["reason"], e["reason"]),
        )
        for e in exits
    ]
    _print_table(headers, rows, widths)
    total_pages = (total + args.page_size - 1) // args.page_size
    print(f"\n  {len(exits)}/{total} départ(s) — page {args.page}/{total_pages}")


def cmd_exit(args):
    dispatch = {"add": cmd_exit_add, "list": cmd_exits_list}
    dispatch[args.action](args)


# ---- Statistiques ----------------------------------------------------------

def cmd_stats(args):
    year = args.year or date.today().year
    start = f"{year}-01-01"
    end = f"{year}-12-31"

    g = an.turnover_rate(start, end)
    hc = an.headcount_summary()
    tenure = an.average_tenure()
    new = an.new_hires(start, end)
    reasons = an.exit_reasons_breakdown(start, end)

    print(f"\n{'='*55}")
    print(f"  Statistiques RH — Année {year}")
    print(f"{'='*55}")
    print(f"  Effectif actif         : {hc['total']}")
    print(f"  Nouvelles embauches    : {new}")
    print(f"  Ancienneté moyenne     : {tenure} ans")
    print(f"  Turnover annuel        : {g['rate']:.1f}%  "
          f"({g['exits']} départs / {g['headcount']} employés début de période)")

    by_dept = an.turnover_by_department(start, end)
    print(f"\n  {'Département':<28} {'Turnover':>8}  {'Départs':>7}  {'Effectif':>8}")
    print(f"  {'-'*56}")
    for d in by_dept:
        bar = "█" * min(int(d["rate"]), 30)
        print(f"  {d['department']:<28} {d['rate']:>7.1f}%  {d['exits']:>7}  {d['headcount']:>8}  {bar}")

    if reasons:
        labels = dl.REASON_LABELS
        print(f"\n  Motifs de départs :")
        for r in reasons:
            pct = (r["count"] / g["exits"] * 100) if g["exits"] else 0
            print(f"    {labels.get(r['reason'], r['reason']):<20} : {r['count']:>3}  ({pct:.0f}%)")

    print()


# ---- Rapport HTML ----------------------------------------------------------

def cmd_report(args):
    year = args.year or date.today().year
    print(f"Génération du rapport {year}...")

    data = an.full_report_data(year)
    output = rg.generate_report(data, output_path=args.output)
    _ok(f"Rapport généré : {output}")


# ---- Départements ----------------------------------------------------------

def cmd_departments(args):
    depts = dl.list_departments()
    if not depts:
        print("Aucun département trouvé.")
        return
    headers = ["Département", "Effectif actif"]
    widths = [30, 15]
    rows = [(d["name"], d["employee_count"]) for d in depts]
    _print_table(headers, rows, widths)
    total = sum(d["employee_count"] for d in depts)
    print(f"\n  Total actifs : {total}")


# ---------------------------------------------------------------------------
# Parsing des arguments
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="hr-analyzer",
        description="HR Turnover Analyzer — Gestion RH et analyse du turnover",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- init ---
    p = sub.add_parser("init", help="Initialiser la base de données")
    p.set_defaults(func=cmd_init)

    # --- import ---
    p = sub.add_parser("import", help="Importer des données depuis un CSV")
    p.add_argument("type", choices=["employees", "exits"])
    p.add_argument("file", help="Chemin vers le fichier CSV")
    p.set_defaults(func=cmd_import)

    # --- employee ---
    p_emp = sub.add_parser("employee", help="Gérer les employés")
    p_emp.set_defaults(func=cmd_employee)
    emp_sub = p_emp.add_subparsers(dest="action", required=True)

    # employee list
    p_l = emp_sub.add_parser("list", help="Lister les employés")
    p_l.add_argument("--department", help="Filtrer par département")
    p_l.add_argument("--status", choices=["active", "inactive"], help="Filtrer par statut")
    p_l.add_argument("--search", help="Recherche (nom, prénom, ID)")
    p_l.add_argument("--page", type=int, default=1)
    p_l.add_argument("--page-size", dest="page_size", type=int, default=25)

    # employee add
    p_a = emp_sub.add_parser("add", help="Ajouter un employé")
    p_a.add_argument("--id", required=True, help="Identifiant unique (ex: EMP042)")
    p_a.add_argument("--first-name", dest="first_name", required=True)
    p_a.add_argument("--last-name", dest="last_name", required=True)
    p_a.add_argument("--hire-date", dest="hire_date", required=True, help="YYYY-MM-DD")
    p_a.add_argument("--email")
    p_a.add_argument("--department")
    p_a.add_argument("--position")
    p_a.add_argument("--status", choices=["active", "inactive"], default="active")

    # employee update
    p_u = emp_sub.add_parser("update", help="Modifier un employé")
    p_u.add_argument("id", help="Identifiant de l'employé")
    p_u.add_argument("--first-name", dest="first_name")
    p_u.add_argument("--last-name", dest="last_name")
    p_u.add_argument("--email")
    p_u.add_argument("--department")
    p_u.add_argument("--position")
    p_u.add_argument("--status", choices=["active", "inactive"])
    p_u.add_argument("--hire-date", dest="hire_date")

    # employee delete
    p_d = emp_sub.add_parser("delete", help="Supprimer un employé")
    p_d.add_argument("id", help="Identifiant de l'employé")

    # employee show
    p_s = emp_sub.add_parser("show", help="Afficher la fiche d'un employé")
    p_s.add_argument("id", help="Identifiant de l'employé")

    # --- exit ---
    p_ex = sub.add_parser("exit", help="Gérer les départs")
    p_ex.set_defaults(func=cmd_exit)
    ex_sub = p_ex.add_subparsers(dest="action", required=True)

    # exit add
    p_ea = ex_sub.add_parser("add", help="Enregistrer un départ")
    p_ea.add_argument("--id", required=True, help="Identifiant de l'employé")
    p_ea.add_argument("--date", required=True, help="Date de départ YYYY-MM-DD")
    p_ea.add_argument(
        "--reason", required=True,
        choices=["resignation", "dismissal", "retirement", "end_of_contract", "other"],
    )
    p_ea.add_argument("--notes", help="Commentaire optionnel")

    # exit list
    p_el = ex_sub.add_parser("list", help="Lister les départs")
    p_el.add_argument("--year", type=int)
    p_el.add_argument("--department")
    p_el.add_argument("--page", type=int, default=1)
    p_el.add_argument("--page-size", dest="page_size", type=int, default=25)

    # --- stats ---
    p = sub.add_parser("stats", help="Afficher les statistiques RH")
    p.add_argument("--year", type=int, help="Année (défaut : année courante)")
    p.set_defaults(func=cmd_stats)

    # --- report ---
    p = sub.add_parser("report", help="Générer un rapport HTML")
    p.add_argument("--year", type=int, help="Année (défaut : année courante)")
    p.add_argument("--output", help="Chemin du fichier HTML de sortie")
    p.set_defaults(func=cmd_report)

    # --- departments ---
    p = sub.add_parser("departments", help="Lister les départements et effectifs")
    p.set_defaults(func=cmd_departments)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except ValueError as exc:
        _err(str(exc))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrompu.")
        sys.exit(0)
    except Exception as exc:
        _err(f"Erreur inattendue : {exc}")
        raise


if __name__ == "__main__":
    main()
