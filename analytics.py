"""
analytics.py - Calculs de turnover et statistiques RH.

Formule de référence :
  Taux de turnover = (Nb départs sur la période / Effectif moyen) × 100
  Effectif moyen   = (Effectif début de période + Effectif fin de période) / 2
"""

import calendar
from datetime import date, datetime

from data_loader import get_connection


# ---------------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------------

def _parse_date(d):
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def _headcount_at(conn, ref_date):
    """Nombre d'employés présents à une date donnée (embauche ≤ date et pas encore partis)."""
    return conn.execute("""
        SELECT COUNT(*) FROM employees e
        WHERE e.hire_date <= ?
          AND (
              e.status = 'active'
              OR EXISTS (
                  SELECT 1 FROM exits ex
                  WHERE ex.employee_id = e.id AND ex.exit_date > ?
              )
          )
    """, (ref_date, ref_date)).fetchone()[0]


def _headcount_at_dept(conn, ref_date, department):
    """Idem, filtré par département."""
    return conn.execute("""
        SELECT COUNT(*) FROM employees e
        JOIN departments d ON d.id = e.department_id
        WHERE e.hire_date <= ?
          AND d.name = ?
          AND (
              e.status = 'active'
              OR EXISTS (
                  SELECT 1 FROM exits ex
                  WHERE ex.employee_id = e.id AND ex.exit_date > ?
              )
          )
    """, (ref_date, department, ref_date)).fetchone()[0]


# ---------------------------------------------------------------------------
# Calcul du taux de turnover
# ---------------------------------------------------------------------------

def turnover_rate(start_date, end_date, department=None, db_path=None):
    """
    Calcule le taux de turnover pour une période et un département optionnel.

    Retourne un dict :
        rate      – taux en %
        exits     – nombre de départs
        headcount – effectif de début de période
    """
    conn = get_connection(db_path)
    try:
        start = str(start_date)
        end = str(end_date)

        if department:
            exits = conn.execute("""
                SELECT COUNT(*) FROM exits ex
                JOIN employees e ON e.id = ex.employee_id
                JOIN departments d ON d.id = e.department_id
                WHERE ex.exit_date BETWEEN ? AND ? AND d.name = ?
            """, (start, end, department)).fetchone()[0]

            headcount = _headcount_at_dept(conn, start, department)
        else:
            exits = conn.execute("""
                SELECT COUNT(*) FROM exits ex
                WHERE ex.exit_date BETWEEN ? AND ?
            """, (start, end)).fetchone()[0]

            headcount = _headcount_at(conn, start)

        rate = round((exits / headcount) * 100, 2) if headcount else 0.0
        return {"rate": rate, "exits": exits, "headcount": headcount}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Analyses par dimension
# ---------------------------------------------------------------------------

def turnover_by_department(start_date, end_date, db_path=None):
    """
    Taux de turnover par département pour la période donnée.
    Retourne une liste triée par taux décroissant.
    """
    conn = get_connection(db_path)
    departments = [
        r[0] for r in conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
    ]
    conn.close()

    results = []
    for dept in departments:
        data = turnover_rate(start_date, end_date, department=dept, db_path=db_path)
        data["department"] = dept
        results.append(data)

    return sorted(results, key=lambda x: x["rate"], reverse=True)


def monthly_trend(year, db_path=None):
    """
    Taux de turnover mois par mois pour une année donnée.
    Retourne une liste de 12 entrées.
    """
    result = []
    for m in range(1, 13):
        last_day = calendar.monthrange(year, m)[1]
        start = f"{year}-{m:02d}-01"
        end = f"{year}-{m:02d}-{last_day:02d}"
        data = turnover_rate(start, end, db_path=db_path)
        data["month"] = m
        data["month_name"] = calendar.month_abbr[m]
        result.append(data)
    return result


def quarterly_trend(year, db_path=None):
    """Taux de turnover par trimestre."""
    quarters = [
        (1, f"{year}-01-01", f"{year}-03-31"),
        (2, f"{year}-04-01", f"{year}-06-30"),
        (3, f"{year}-07-01", f"{year}-09-30"),
        (4, f"{year}-10-01", f"{year}-12-31"),
    ]
    result = []
    for q, start, end in quarters:
        data = turnover_rate(start, end, db_path=db_path)
        data["quarter"] = q
        data["label"] = f"T{q} {year}"
        result.append(data)
    return result


# ---------------------------------------------------------------------------
# Motifs de départs
# ---------------------------------------------------------------------------

def exit_reasons_breakdown(start_date, end_date, department=None, db_path=None):
    """Distribution des motifs de départ sur la période."""
    conn = get_connection(db_path)
    dept_clause = ""
    params = [str(start_date), str(end_date)]

    if department:
        dept_clause = """
            JOIN employees e2 ON e2.id = ex.employee_id
            JOIN departments d ON d.id = e2.department_id AND d.name = ?
        """
        params.append(department)

    rows = conn.execute(f"""
        SELECT ex.reason, COUNT(*) AS count
        FROM exits ex
        {dept_clause}
        WHERE ex.exit_date BETWEEN ? AND ?
        GROUP BY ex.reason
        ORDER BY count DESC
    """, params[-2:] if not department else [department] + params[-2:]).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Statistiques générales
# ---------------------------------------------------------------------------

def average_tenure(db_path=None):
    """Ancienneté moyenne (en années) des employés actifs."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT hire_date FROM employees WHERE status = 'active'"
    ).fetchall()
    conn.close()

    today = date.today()
    tenures = []
    for r in rows:
        try:
            start = datetime.strptime(r["hire_date"], "%Y-%m-%d").date()
            tenures.append((today - start).days / 365.25)
        except (ValueError, TypeError):
            pass

    return round(sum(tenures) / len(tenures), 1) if tenures else 0.0


def headcount_summary(db_path=None):
    """Retourne l'effectif actif total et par département."""
    conn = get_connection(db_path)
    total = conn.execute(
        "SELECT COUNT(*) FROM employees WHERE status = 'active'"
    ).fetchone()[0]

    by_dept = conn.execute("""
        SELECT d.name AS department, COUNT(e.id) AS count
        FROM employees e
        JOIN departments d ON d.id = e.department_id
        WHERE e.status = 'active'
        GROUP BY d.name
        ORDER BY count DESC
    """).fetchall()
    conn.close()

    return {"total": total, "by_department": [dict(r) for r in by_dept]}


def top_departments_at_risk(start_date, end_date, top_n=5, db_path=None):
    """Retourne les N départements avec le taux de turnover le plus élevé."""
    all_depts = turnover_by_department(start_date, end_date, db_path=db_path)
    return [d for d in all_depts if d["headcount"] > 0][:top_n]


def new_hires(start_date, end_date, db_path=None):
    """Nombre de nouvelles embauches sur la période."""
    conn = get_connection(db_path)
    count = conn.execute("""
        SELECT COUNT(*) FROM employees
        WHERE hire_date BETWEEN ? AND ?
    """, (str(start_date), str(end_date))).fetchone()[0]
    conn.close()
    return count


def full_report_data(year, db_path=None):
    """
    Agrège toutes les métriques nécessaires pour le rapport HTML.
    Retourne un dict structuré.
    """
    start = f"{year}-01-01"
    end = f"{year}-12-31"

    return {
        "year": year,
        "global_rate": turnover_rate(start, end, db_path=db_path),
        "monthly_trend": monthly_trend(year, db_path=db_path),
        "quarterly_trend": quarterly_trend(year, db_path=db_path),
        "by_department": turnover_by_department(start, end, db_path=db_path),
        "exit_reasons": exit_reasons_breakdown(start, end, db_path=db_path),
        "headcount": headcount_summary(db_path=db_path),
        "avg_tenure": average_tenure(db_path=db_path),
        "new_hires": new_hires(start, end, db_path=db_path),
        "top_at_risk": top_departments_at_risk(start, end, db_path=db_path),
    }
