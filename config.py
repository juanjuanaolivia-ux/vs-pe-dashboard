"""
VS Analytics — Configuración central
=====================================
Único lugar donde tocar cuando agregás un rubro nuevo o cambiás colores/constantes.
"""

from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

# ── Encoding helpers ─────────────────────────────────────────────────────────
def garble(s: str) -> str:
    """UTF-8 → CP437 (formato de almacenamiento en la DB)."""
    try:
        return s.encode("utf-8").decode("cp437")
    except Exception:
        return s

def ungarble(s) -> str:
    """CP437 → UTF-8 (para mostrar al usuario)."""
    if not s:
        return s
    try:
        return s.encode("cp437").decode("utf-8")
    except Exception:
        return s

# ── Períodos especiales (Hot Sale, Black Friday, etc.) ───────────────────────
SPECIAL = {
    "2024-11": "Black Friday ⚡",
    "2024-12": "Navidad 🎄",
    "2025-05": "Hot Sale 🔥",
    "2025-11": "Black Friday ⚡",
    "2025-12": "Navidad 🎄",
    "2026-05": "Hot Sale 🔥",
}

# ── Rubros disponibles ────────────────────────────────────────────────────────
# Para agregar un rubro nuevo: copiar la estructura de "pe", cambiar los campos,
# asegurarse de que el .db.gz esté en BASE_DIR. Eso es todo.
RUBROS: dict[str, dict] = {
    "pe": {
        "label":    "Pequeños Electrodomésticos",
        "short":    "PE",
        "icon":     "🏠",
        "db_gz":    BASE_DIR / "vs_pe.db.gz",
        "db_path":  BASE_DIR / "vs_pe.db",
        "rubro_db": garble("Pequeños Electrodomésticos"),
    },
    # Ejemplo para cuando agregues Televisores:
    # "tv": {
    #     "label":    "Televisores",
    #     "short":    "TV",
    #     "icon":     "📺",
    #     "db_gz":    BASE_DIR / "vs_tv.db.gz",
    #     "db_path":  BASE_DIR / "vs_tv.db",
    #     "rubro_db": garble("Televisores"),
    # },
}

# ── Formatters ────────────────────────────────────────────────────────────────
def fmt_usd(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    v = float(v)
    if v >= 1_000_000:
        return f"USD {v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"USD {v / 1_000:.1f}K"
    return f"USD {v:.0f}"

def fmt_num(v) -> str:
    if v is None:
        return "—"
    return f"{int(v):,}".replace(",", ".")

def fmt_pct(v) -> str:
    if v is None:
        return "—"
    return f"{float(v):.1f}%"

def delta_pct(curr, prev) -> float | None:
    if not prev or prev == 0:
        return None
    return round((curr - prev) / prev * 100, 1)

def prev_periodo(p: str, offset: int = 1) -> str:
    """Retorna el período YYYY-MM `offset` meses atrás."""
    if not p or len(p) < 7:
        return ""
    y, m = int(p[:4]), int(p[5:7])
    for _ in range(offset):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return f"{y}-{m:02d}"

def yoy_periodo(p: str) -> str:
    """Mismo mes, año anterior."""
    if not p or len(p) < 7:
        return ""
    return f"{int(p[:4]) - 1}-{p[5:7]}"

# ── Paleta de colores ─────────────────────────────────────────────────────────
COLORS = {
    "accent":  "#7c6af7",
    "accent2": "#4f8ef7",
    "green":   "#4ade80",
    "red":     "#f87171",
    "yellow":  "#fbbf24",
    "blue":    "#60a5fa",
    "purple":  "#a78bfa",
    "muted":   "#6b7a99",
    "surface": "#161625",
    "surface2":"#1e1e32",
    "border":  "#252538",
}

BRAND_PALETTE = [
    "#7c6af7", "#4f8ef7", "#fbbf24", "#4ade80", "#f87171",
    "#a78bfa", "#60a5fa", "#fb923c", "#34d399", "#e879f9",
]

FIN_COLORS = {
    "Sin cuotas":   "#94a3b8",
    "3 cuotas":     "#4ade80",
    "6 cuotas":     "#7c6af7",
    "9 cuotas":     "#4f8ef7",
    "12 cuotas":    "#fbbf24",
    "Interés bajo": "#f87171",
}

# ── Plotly base layout ────────────────────────────────────────────────────────
PLOTLY_BASE = dict(
    template="plotly_dark",
    paper_bgcolor="#161625",
    plot_bgcolor="#161625",
    font=dict(color="#e2e8f0", size=10),
    margin=dict(l=10, r=10, t=36, b=40),
)
GRID_COLOR  = "#252538"
GRID_COLOR0 = "rgba(0,0,0,0)"
