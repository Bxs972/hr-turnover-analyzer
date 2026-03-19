"""
report_generator.py - Génération de rapports HTML avec graphiques embarqués.

Les graphiques sont convertis en base64 pour produire un fichier HTML
autonome (aucune dépendance externe au moment de l'ouverture).
"""

import base64
import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend non-interactif
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path(__file__).parent / "output"

REASON_LABELS = {
    "resignation": "Démission",
    "dismissal": "Licenciement",
    "retirement": "Retraite",
    "end_of_contract": "Fin de contrat",
    "other": "Autre",
}

# Palette cohérente pour toutes les visualisations
PALETTE_BLUE = "#2563EB"
PALETTE_RED = "#DC2626"
PALETTE_GREEN = "#16A34A"


# ---------------------------------------------------------------------------
# Helpers graphiques
# ---------------------------------------------------------------------------

def _fig_to_base64(fig):
    """Convertit une figure matplotlib en chaîne base64 PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=130)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def _apply_style():
    sns.set_theme(style="whitegrid", font_scale=1.05)
    plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white"})


# ---------------------------------------------------------------------------
# Graphiques individuels
# ---------------------------------------------------------------------------

def chart_monthly_trend(monthly_data):
    """Histogramme du taux de turnover mensuel."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(11, 4))

    months = [d["month_name"] for d in monthly_data]
    rates = [d["rate"] for d in monthly_data]
    colors = [PALETTE_RED if r >= 5 else PALETTE_BLUE for r in rates]

    bars = ax.bar(months, rates, color=colors, width=0.6, edgecolor="white")
    ax.set_title("Taux de turnover mensuel", fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Turnover (%)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_ylim(0, max(rates) * 1.3 + 1 if any(r > 0 for r in rates) else 10)

    for bar, rate in zip(bars, rates):
        if rate > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                f"{rate:.1f}%",
                ha="center", va="bottom", fontsize=8, color="#374151",
            )

    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_by_department(dept_data):
    """Graphique horizontal de turnover par département."""
    if not dept_data:
        return None

    _apply_style()
    n = len(dept_data)
    fig, ax = plt.subplots(figsize=(10, max(3.5, n * 0.55)))

    departments = [d["department"] for d in dept_data]
    rates = [d["rate"] for d in dept_data]

    # Dégradé rouge → vert selon le taux
    max_rate = max(rates) if rates else 1
    colors = [
        plt.cm.RdYlGn_r(r / max_rate) if max_rate > 0 else (0.2, 0.6, 0.8, 1)
        for r in rates
    ]

    bars = ax.barh(departments, rates, color=colors, height=0.6, edgecolor="white")
    ax.set_title("Turnover par département (%)", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Turnover (%)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter())
    ax.invert_yaxis()

    for bar, rate, headcount in zip(bars, rates, [d["headcount"] for d in dept_data]):
        ax.text(
            bar.get_width() + 0.1,
            bar.get_y() + bar.get_height() / 2,
            f"{rate:.1f}%  (n={headcount})",
            va="center", fontsize=8, color="#374151",
        )

    ax.set_xlim(0, max(rates) * 1.35 + 1 if rates else 10)
    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_exit_reasons(reasons_data):
    """Camembert des motifs de départ."""
    if not reasons_data:
        return None

    _apply_style()
    fig, ax = plt.subplots(figsize=(6, 5))

    labels = [REASON_LABELS.get(d["reason"], d["reason"]) for d in reasons_data]
    sizes = [d["count"] for d in reasons_data]
    colors = sns.color_palette("Set2", len(labels))

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.1f%%",
        colors=colors, startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.set_title("Motifs de départs", fontsize=14, fontweight="bold", pad=16)
    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_headcount_by_dept(headcount_data):
    """Barres de l'effectif actif par département."""
    by_dept = headcount_data.get("by_department", [])
    if not by_dept:
        return None

    _apply_style()
    fig, ax = plt.subplots(figsize=(10, max(3.5, len(by_dept) * 0.5)))

    depts = [d["department"] for d in by_dept]
    counts = [d["count"] for d in by_dept]

    bars = ax.barh(depts, counts, color=PALETTE_BLUE, height=0.6, edgecolor="white")
    ax.set_title("Effectif actif par département", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Nombre d'employés")
    ax.invert_yaxis()

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va="center", fontsize=9, color="#374151",
        )

    ax.set_xlim(0, max(counts) * 1.2 + 1 if counts else 10)
    fig.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# Génération du rapport complet
# ---------------------------------------------------------------------------

def generate_report(data, output_path=None):
    """
    Génère un rapport HTML autonome à partir du dict retourné par analytics.full_report_data().

    Paramètres
    ----------
    data        : dict – résultat de analytics.full_report_data()
    output_path : str | Path | None – chemin de sortie (auto-généré si None)

    Retourne le chemin du fichier HTML généré.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Génération des graphiques
    charts = {
        "trend": chart_monthly_trend(data["monthly_trend"]),
        "dept": chart_by_department(data["by_department"]),
        "reasons": chart_exit_reasons(data["exit_reasons"]),
        "headcount": chart_headcount_by_dept(data["headcount"]),
    }

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("report_template.html")

    html = template.render(
        generated_at=datetime.now().strftime("%d/%m/%Y à %H:%M"),
        reason_labels=REASON_LABELS,
        charts=charts,
        **data,
    )

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"rapport_{data['year']}_{ts}.html"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return str(output_path)
