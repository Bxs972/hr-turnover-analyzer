"""
data_loader.py - Gestion de la base de données SQLite et import CSV.

Fonctionnalités :
- Initialisation du schéma
- CRUD complet sur les employés et les départements
- Import en masse depuis CSV avec validation et rapport d'erreurs
- Pagination et filtres pour gérer >100 collaborateurs
"""

import csv
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "hr_data.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

VALID_STATUSES = ("active", "inactive")
VALID_REASONS = ("resignation", "dismissal", "retirement", "end_of_contract", "other")

REASON_LABELS = {
    "resignation": "Démission",
    "dismissal": "Licenciement",
    "retirement": "Retraite",
    "end_of_contract": "Fin de contrat",
    "other": "Autre",
}


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def get_connection(db_path=None):
    """Retourne une connexion SQLite avec foreign keys activées."""
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # meilleures perfs en lecture/écriture concurrentes
    return conn


def init_db(db_path=None):
    """Crée les tables et index à partir du schéma SQL."""
    target = db_path or DB_PATH
    conn = get_connection(target)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Base de données initialisée : {target}")


# ---------------------------------------------------------------------------
# Départements
# ---------------------------------------------------------------------------

def get_or_create_department(conn, name):
    """Retourne l'id du département (le crée si absent)."""
    name = name.strip()
    row = conn.execute("SELECT id FROM departments WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO departments (name) VALUES (?)", (name,))
    return cur.lastrowid


def list_departments(db_path=None):
    """Retourne la liste des départements avec le nombre d'actifs."""
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT d.id,
               d.name,
               COUNT(e.id) AS employee_count
        FROM departments d
        LEFT JOIN employees e
               ON e.department_id = d.id AND e.status = 'active'
        GROUP BY d.id
        ORDER BY d.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_department(name, db_path=None):
    """Supprime un département (les employés rattachés sont désassociés)."""
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM departments WHERE name = ?", (name,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Validation employé
# ---------------------------------------------------------------------------

def _validate_employee(data):
    errors = []
    for field in ("employee_id", "first_name", "last_name", "hire_date"):
        if not str(data.get(field, "")).strip():
            errors.append(f"Champ obligatoire manquant : {field}")
    if data.get("status") and data["status"] not in VALID_STATUSES:
        errors.append(f"Statut invalide : '{data['status']}'. Valeurs : {VALID_STATUSES}")
    if data.get("hire_date"):
        try:
            datetime.strptime(str(data["hire_date"]).strip(), "%Y-%m-%d")
        except ValueError:
            errors.append(f"Format hire_date invalide : '{data['hire_date']}' (attendu YYYY-MM-DD)")
    return errors


# ---------------------------------------------------------------------------
# CRUD Employés
# ---------------------------------------------------------------------------

def add_employee(data, db_path=None):
    """Ajoute un nouvel employé. Lève ValueError si les données sont invalides."""
    errors = _validate_employee(data)
    if errors:
        raise ValueError("\n".join(errors))

    conn = get_connection(db_path)
    try:
        dept_id = get_or_create_department(conn, data["department"]) if data.get("department") else None
        conn.execute("""
            INSERT INTO employees
                (employee_id, first_name, last_name, email, department_id, position, hire_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["employee_id"].strip(),
            data["first_name"].strip(),
            data["last_name"].strip(),
            data.get("email", "").strip() or None,
            dept_id,
            data.get("position", "").strip() or None,
            data["hire_date"].strip(),
            data.get("status", "active"),
        ))
        conn.commit()
    finally:
        conn.close()


def update_employee(employee_id, updates, db_path=None):
    """Met à jour les champs fournis pour un employé existant."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM employees WHERE employee_id = ?", (employee_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Employé introuvable : {employee_id}")

        fields, values = [], []
        mapping = {
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "email",
            "position": "position",
            "status": "status",
            "hire_date": "hire_date",
        }
        for key, col in mapping.items():
            if key in updates:
                if key == "status" and updates[key] not in VALID_STATUSES:
                    raise ValueError(f"Statut invalide : '{updates[key]}'")
                fields.append(f"{col} = ?")
                values.append(updates[key])

        if "department" in updates:
            dept_id = get_or_create_department(conn, updates["department"])
            fields.append("department_id = ?")
            values.append(dept_id)

        if not fields:
            return

        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat(timespec="seconds"))
        values.append(employee_id)

        conn.execute(
            f"UPDATE employees SET {', '.join(fields)} WHERE employee_id = ?", values
        )
        conn.commit()
    finally:
        conn.close()


def delete_employee(employee_id, db_path=None):
    """Supprime définitivement un employé (et ses sorties via CASCADE)."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM employees WHERE employee_id = ?", (employee_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Employé introuvable : {employee_id}")
        conn.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
        conn.commit()
    finally:
        conn.close()


def get_employee(employee_id, db_path=None):
    """Retourne les détails complets d'un employé ou None."""
    conn = get_connection(db_path)
    row = conn.execute("""
        SELECT e.*, d.name AS department_name
        FROM employees e
        LEFT JOIN departments d ON d.id = e.department_id
        WHERE e.employee_id = ?
    """, (employee_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_employees(department=None, status=None, search=None,
                   page=1, page_size=20, db_path=None):
    """
    Retourne (liste_employés, total) avec pagination et filtres.

    Paramètres
    ----------
    department : str, optionnel – filtre par nom de département (LIKE)
    status     : str, optionnel – 'active' ou 'inactive'
    search     : str, optionnel – recherche dans prénom, nom, ID
    page       : int            – numéro de page (commence à 1)
    page_size  : int            – nombre d'entrées par page
    """
    conn = get_connection(db_path)

    base = """
        FROM employees e
        LEFT JOIN departments d ON d.id = e.department_id
        WHERE 1=1
    """
    params = []

    if department:
        base += " AND d.name LIKE ?"
        params.append(f"%{department}%")
    if status:
        base += " AND e.status = ?"
        params.append(status)
    if search:
        base += " AND (e.first_name LIKE ? OR e.last_name LIKE ? OR e.employee_id LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    total = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]

    query = f"""
        SELECT e.employee_id, e.first_name, e.last_name, e.email,
               d.name AS department, e.position, e.hire_date, e.status
        {base}
        ORDER BY e.last_name, e.first_name
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(query, params + [page_size, (page - 1) * page_size]).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


# ---------------------------------------------------------------------------
# Départs (Exits)
# ---------------------------------------------------------------------------

def add_exit(data, db_path=None):
    """
    Enregistre un départ et passe l'employé en statut 'inactive'.

    data doit contenir : employee_id, exit_date (YYYY-MM-DD), reason.
    """
    if data.get("reason") not in VALID_REASONS:
        raise ValueError(
            f"Raison invalide : '{data.get('reason')}'. Valeurs : {VALID_REASONS}"
        )
    try:
        datetime.strptime(str(data.get("exit_date", "")), "%Y-%m-%d")
    except ValueError:
        raise ValueError("Format exit_date invalide. Attendu : YYYY-MM-DD")

    conn = get_connection(db_path)
    try:
        emp = conn.execute(
            "SELECT id FROM employees WHERE employee_id = ?", (data["employee_id"],)
        ).fetchone()
        if not emp:
            raise ValueError(f"Employé introuvable : {data['employee_id']}")

        conn.execute("""
            INSERT INTO exits (employee_id, exit_date, reason, notes)
            VALUES (?, ?, ?, ?)
        """, (emp["id"], data["exit_date"], data["reason"], data.get("notes", "") or None))

        conn.execute("""
            UPDATE employees
            SET status = 'inactive', updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(timespec="seconds"), emp["id"]))

        conn.commit()
    finally:
        conn.close()


def list_exits(start_date=None, end_date=None, department=None,
               page=1, page_size=20, db_path=None):
    """Liste les départs avec filtres optionnels."""
    conn = get_connection(db_path)

    base = """
        FROM exits ex
        JOIN employees e ON e.id = ex.employee_id
        LEFT JOIN departments d ON d.id = e.department_id
        WHERE 1=1
    """
    params = []
    if start_date:
        base += " AND ex.exit_date >= ?"
        params.append(start_date)
    if end_date:
        base += " AND ex.exit_date <= ?"
        params.append(end_date)
    if department:
        base += " AND d.name LIKE ?"
        params.append(f"%{department}%")

    total = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]

    query = f"""
        SELECT e.employee_id, e.first_name, e.last_name,
               d.name AS department, ex.exit_date, ex.reason, ex.notes
        {base}
        ORDER BY ex.exit_date DESC
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(query, params + [page_size, (page - 1) * page_size]).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


# ---------------------------------------------------------------------------
# Import CSV
# ---------------------------------------------------------------------------

def import_employees_csv(filepath, db_path=None):
    """
    Importe des employés depuis un fichier CSV.

    Colonnes attendues : employee_id, first_name, last_name, hire_date
    Colonnes optionnelles : email, department, position, status

    Retourne (nb_importés, liste_lignes_ignorées).
    """
    conn = get_connection(db_path)
    imported, skipped = 0, []

    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                row = {k.strip(): v.strip() for k, v in row.items() if k}

                errors = _validate_employee(row)
                if errors:
                    skipped.append({"row": i, "errors": errors, "data": row})
                    continue

                try:
                    dept_id = (
                        get_or_create_department(conn, row["department"])
                        if row.get("department")
                        else None
                    )
                    conn.execute("""
                        INSERT OR IGNORE INTO employees
                            (employee_id, first_name, last_name, email,
                             department_id, position, hire_date, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row["employee_id"],
                        row["first_name"],
                        row["last_name"],
                        row.get("email") or None,
                        dept_id,
                        row.get("position") or None,
                        row["hire_date"],
                        row.get("status", "active"),
                    ))
                    imported += 1
                except Exception as exc:
                    skipped.append({"row": i, "errors": [str(exc)], "data": row})

        conn.commit()
    finally:
        conn.close()

    return imported, skipped


def import_exits_csv(filepath, db_path=None):
    """
    Importe des départs depuis un fichier CSV.

    Colonnes attendues : employee_id, exit_date, reason
    Colonnes optionnelles : notes

    Retourne (nb_importés, liste_lignes_ignorées).
    """
    conn = get_connection(db_path)
    imported, skipped = 0, []

    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                row = {k.strip(): v.strip() for k, v in row.items() if k}

                if row.get("reason") not in VALID_REASONS:
                    skipped.append({
                        "row": i,
                        "errors": [f"Raison invalide : '{row.get('reason')}'"],
                        "data": row,
                    })
                    continue

                try:
                    datetime.strptime(row.get("exit_date", ""), "%Y-%m-%d")
                except ValueError:
                    skipped.append({
                        "row": i,
                        "errors": [f"Format exit_date invalide : '{row.get('exit_date')}'"],
                        "data": row,
                    })
                    continue

                try:
                    emp = conn.execute(
                        "SELECT id FROM employees WHERE employee_id = ?",
                        (row["employee_id"],),
                    ).fetchone()
                    if not emp:
                        skipped.append({
                            "row": i,
                            "errors": [f"Employé introuvable : {row['employee_id']}"],
                            "data": row,
                        })
                        continue

                    conn.execute("""
                        INSERT OR IGNORE INTO exits (employee_id, exit_date, reason, notes)
                        VALUES (?, ?, ?, ?)
                    """, (emp["id"], row["exit_date"], row["reason"], row.get("notes") or None))

                    conn.execute("""
                        UPDATE employees
                        SET status = 'inactive', updated_at = ?
                        WHERE id = ?
                    """, (datetime.now().isoformat(timespec="seconds"), emp["id"]))

                    imported += 1
                except Exception as exc:
                    skipped.append({"row": i, "errors": [str(exc)], "data": row})

        conn.commit()
    finally:
        conn.close()

    return imported, skipped
