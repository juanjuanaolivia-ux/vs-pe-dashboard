"""
VS Analytics — Pequeños Electrodomésticos Dashboard
====================================================
Diseño replicado del HTML original: dark mode pro, KPI cards, insights bar,
donuts, concentración, top lists, rankings con thumbnails y pills.
"""

import gzip, shutil, sqlite3, html as html_module
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="VS Analytics — PE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root {
  --bg:#0d0d1a; --surface:#161625; --surface2:#1e1e32;
  --accent:#7c6af7; --accent2:#4f8ef7;
  --text:#e2e8f0; --text-muted:#6b7a99; --text-dim:#8896b3;
  --green:#4ade80; --red:#f87171; --yellow:#fbbf24; --blue:#60a5fa; --purple:#a78bfa;
  --border:#252538; --border-light:#1e1e2e;
  --radius:12px; --radius-sm:8px; --radius-xs:6px;
}
.stApp { background: var(--bg) !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
.block-container { padding-top: 0 !important; padding-left: 0 !important; padding-right: 0 !important; max-width: 100% !important; }
footer, #MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }
div[data-testid="stDecoration"] { display: none !important; }
.stTabs [data-baseweb="tab-list"] { background: var(--surface2) !important; border-radius: 8px !important; padding: 3px !important; gap: 2px !important; border: none !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--text-muted) !important; border-radius: 6px !important; font-size: 11px !important; font-weight: 600 !important; letter-spacing: .3px !important; }
.stTabs [aria-selected="true"] { background: var(--surface) !important; color: var(--accent) !important; box-shadow: 0 1px 4px rgba(0,0,0,.4) !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 12px !important; }
[data-testid="stSidebar"] label { color: var(--text-muted) !important; font-size: 10px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: .5px !important; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div { background: var(--surface2) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: 6px !important; font-size: 12px !important; }
[data-testid="stSidebar"] hr { border-color: var(--border) !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] small { color: var(--text-muted) !important; font-size: 11px !important; }
.stButton > button { background: var(--surface2) !important; border: 1px solid var(--border) !important; color: var(--text-muted) !important; border-radius: 6px !important; font-size: 11px !important; }
.stButton > button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
[data-testid="stDataFrame"] { border: none !important; border-radius: var(--radius) !important; overflow: hidden !important; }
.vs-header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 10px 20px; display: flex; align-items: center; gap: 12px; box-shadow: 0 1px 20px rgba(0,0,0,.5); }
.vs-icon { width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, var(--accent), var(--accent2)); display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
.vs-brand-name { font-size: 13px; font-weight: 700; color: var(--text); line-height: 1.1; }
.vs-brand-sub { font-size: 9px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; }
.vs-scope { margin-left: auto; background: rgba(124,106,247,.12); border: 1px solid rgba(124,106,247,.3); color: var(--accent); border-radius: 20px; padding: 3px 12px; font-size: 11px; font-weight: 600; }
.vs-period { margin-left: 8px; background: var(--surface2); border: 1px solid var(--border); color: var(--text-muted); border-radius: 20px; padding: 3px 10px; font-size: 10px; }
.vs-bc { background: var(--surface); border-bottom: 1px solid var(--border-light); padding: 6px 20px; font-size: 11px; color: var(--text-muted); display: flex; gap: 6px; align-items: center; }
.bc-sep { color: var(--border); }
.bc-active { color: var(--accent); font-weight: 600; }
.insights-panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 16px; margin: 14px 20px 0 20px; display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 8px; }
.insight-item { display: flex; align-items: flex-start; gap: 8px; font-size: 11px; line-height: 1.4; }
.insight-icon { font-size: 15px; flex-shrink: 0; margin-top: 1px; }
.insight-text { color: var(--text-dim); }
.insight-text strong { color: var(--text); font-weight: 700; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 14px 20px 0 20px; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; transition: border-color .2s; }
.kpi-card:hover { border-color: rgba(124,106,247,.35); }
.kpi-lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; color: var(--text-muted); margin-bottom: 8px; }
.kpi-val { font-size: 26px; font-weight: 700; letter-spacing: -.5px; color: var(--text); line-height: 1; margin-bottom: 6px; }
.kpi-up  { font-size: 11px; font-weight: 600; color: var(--green); }
.kpi-dn  { font-size: 11px; font-weight: 600; color: var(--red); }
.kpi-ne  { font-size: 11px; font-weight: 600; color: var(--text-muted); }
.vs-section { padding: 14px 20px; }
.vs-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }
.vs-card:hover { border-color: rgba(124,106,247,.25); transition: border-color .2s; }
.vs-card-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .7px; color: var(--text-muted); margin-bottom: 14px; display: flex; align-items: center; justify-content: space-between; }
.top-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--border-light); }
.top-row:last-child { border-bottom: none; }
.top-n { font-size: 10px; font-weight: 700; color: var(--text-muted); width: 16px; flex-shrink: 0; text-align: center; }
.top-name { flex: 1; font-size: 11px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); }
.top-bar-w { width: 70px; flex-shrink: 0; }
.top-bar-bg { height: 4px; border-radius: 2px; background: var(--surface2); }
.top-bar { height: 4px; border-radius: 2px; background: linear-gradient(90deg, var(--accent), var(--accent2)); }
.top-pct { font-size: 11px; font-weight: 700; color: var(--text); width: 36px; text-align: right; flex-shrink: 0; }
.top-gmv { font-size: 10px; color: var(--text-muted); width: 72px; text-align: right; flex-shrink: 0; }
.conc-row { background: var(--surface2); border-radius: var(--radius-sm); padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.conc-lbl { font-size: 10px; color: var(--text-muted); }
.conc-val { font-size: 15px; font-weight: 700; color: var(--accent); }
.conc-footer { display: flex; gap: 10px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border); }
.conc-foot-item { flex: 1; text-align: center; }
.conc-foot-val { font-size: 13px; font-weight: 700; color: var(--text); }
.conc-foot-lbl { font-size: 9px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; }
.char-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.char-stat { background: var(--surface2); border-radius: var(--radius-sm); padding: 12px; }
.char-val { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 3px; }
.char-lbl { font-size: 10px; color: var(--text-muted); }
.char-sub { font-size: 9px; color: var(--text-dim); margin-top: 2px; }
.pill { display: inline-flex; align-items: center; padding: 2px 6px; border-radius: 20px; font-size: 9px; font-weight: 600; margin-right: 3px; }
.p-full { background: rgba(124,106,247,.15); color: var(--accent); }
.p-free { background: rgba(74,222,128,.12); color: var(--green); }
.p-flex { background: rgba(251,191,36,.12); color: var(--yellow); }
.p-cat  { background: rgba(96,165,250,.12);  color: var(--blue); }
.rank-tbl { width: 100%; border-collapse: collapse; font-size: 11px; }
.rank-tbl th { padding: 8px 10px; font-size: 9px; text-transform: uppercase; letter-spacing: .5px; color: var(--text-muted); background: var(--surface2); border-bottom: 1px solid var(--border); white-space: nowrap; text-align: left; }
.rank-tbl td { padding: 7px 10px; border-bottom: 1px solid var(--border-light); vertical-align: middle; color: var(--text); }
.rank-tbl tr:hover td { background: rgba(124,106,247,.06); }
.rank-tbl .num { text-align: right; font-variant-numeric: tabular-nums; color: var(--text-dim); }
.rb { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 5px; font-size: 10px; font-weight: 700; background: var(--surface2); color: var(--text-muted); }
.rb-g { background: rgba(251,191,36,.15); color: var(--yellow); }
.rb-s { background: rgba(148,163,184,.12); color: #94a3b8; }
.rb-b { background: rgba(180,120,60,.12); color: #c08040; }
.thumb { width: 36px; height: 36px; object-fit: contain; border-radius: 5px; background: var(--surface2); vertical-align: middle; }
.thumb-ph { width: 36px; height: 36px; border-radius: 5px; background: var(--surface2); display: inline-flex; align-items: center; justify-content: center; font-size: 14px; vertical-align: middle; }
.t-title { font-weight: 500; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 320px; display: block; }
.t-sub { font-size: 9px; color: var(--text-muted); }
.donut-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px; }
.donut-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; color: var(--text-muted); text-align: center; margin-bottom: 8px; }
.dleg { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.dleg-row { display: flex; align-items: center; gap: 7px; font-size: 11px; }
.dleg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dleg-name { color: var(--text-dim); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dleg-pct { color: var(--text); font-weight: 700; flex-shrink: 0; }
</style>
""", unsafe_allow_html=True)

DB_GZ = Path(__file__).parent / "vs_pe.db.gz"
DB_PATH = Path(__file__).parent / "vs_pe.db"

def _garble(s: str) -> str:
    try: return s.encode("utf-8").decode("cp437")
    except: return s

def _ungarble(s) -> str:
    if not s: return s
    try: return s.encode("cp437").decode("utf-8")
    except: return s

@st.cache_resource(show_spinner=False)
def ensure_db():
    if DB_PATH.exists() and DB_PATH.stat().st_size > 50_000_000:
        return str(DB_PATH)
    if not DB_GZ.exists():
        st.error("No se encontro vs_pe.db.gz"); st.stop()
    with st.spinner("Descomprimiendo DB..."):
        with gzip.open(DB_GZ, "rb") as fin, open(DB_PATH, "wb") as fout:
            shutil.copyfileobj(fin, fout)
    return str(DB_PATH)

@st.cache_resource(show_spinner=False)
def get_conn():
    db = ensure_db()
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, check_same_thread=False)
    conn.execute("PRAGMA cache_size = -32768")
    conn.execute("PRAGMA mmap_size = 134217728")
    return conn

@st.cache_data(ttl=3600, show_spinner=False)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_conn(), params=params)

RUBRO_DB = _garble("Pequeños Electrodomésticos")

@st.cache_data(ttl=3600, show_spinner=False)
def get_periodos():
    return q("SELECT DISTINCT periodo FROM publicaciones ORDER BY periodo DESC")["periodo"].tolist()

@st.cache_data(ttl=3600, show_spinner=False)
def get_cats(periodo):
    df = q("SELECT DISTINCT subrubro, categoria FROM publicaciones WHERE periodo=? AND rubro=? ORDER BY subrubro,categoria", (periodo, RUBRO_DB))
    df["subrubro"] = df["subrubro"].apply(_ungarble)
    df["categoria"] = df["categoria"].apply(_ungarble)
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def kpis(periodo, subrubro=None, categoria=None):
    w, p = "rubro=? AND periodo=?", [RUBRO_DB, periodo]
    if subrubro: w += " AND subrubro=?"; p.append(_garble(subrubro))
    if categoria: w += " AND categoria=?"; p.append(_garble(categoria))
    dm = q(f"SELECT SUM(gmv) gmv_usd, SUM(sold_quantity) unidades, COUNT(DISTINCT brand_name) marcas FROM marcas WHERE {w}", tuple(p))
    dp = q(f"""SELECT COUNT(DISTINCT item_id) pubs, COUNT(DISTINCT seller_id) vends,
        AVG(CASE WHEN fulfillment='SI' THEN 1.0 ELSE 0 END)*100 pct_full,
        AVG(CASE WHEN free_shipping='SI' THEN 1.0 ELSE 0 END)*100 pct_free,
        AVG(CASE WHEN flex='SI' THEN 1.0 ELSE 0 END)*100 pct_flex,
        AVG(CASE WHEN catalog_listing='SI' THEN 1.0 ELSE 0 END)*100 pct_cat
        FROM publicaciones WHERE {w}""", tuple(p))
    return {
        "gmv": float(dm["gmv_usd"].iloc[0] or 0),
        "units": int(dm["unidades"].iloc[0] or 0),
        "marcas": int(dm["marcas"].iloc[0] or 0),
        "pubs": int(dp["pubs"].iloc[0] or 0),
        "vends": int(dp["vends"].iloc[0] or 0),
        "pct_full": float(dp["pct_full"].iloc[0] or 0),
        "pct_free": float(dp["pct_free"].iloc[0] or 0),
        "pct_flex": float(dp["pct_flex"].iloc[0] or 0),
        "pct_cat":  float(dp["pct_cat"].iloc[0] or 0),
    }

@st.cache_data(ttl=3600, show_spinner=False)
def evolucion(subrubro=None, categoria=None):
    w, p = "rubro=?", [RUBRO_DB]
    if subrubro: w += " AND subrubro=?"; p.append(_garble(subrubro))
    if categoria: w += " AND categoria=?"; p.append(_garble(categoria))
    return q(f"SELECT periodo, SUM(gmv) gmv_usd, SUM(sold_quantity) unidades FROM marcas WHERE {w} GROUP BY periodo ORDER BY periodo", tuple(p))

@st.cache_data(ttl=3600, show_spinner=False)
def top_marcas(periodo, subrubro=None, categoria=None, limit=10):
    w, p = "rubro=? AND periodo=?", [RUBRO_DB, periodo]
    if subrubro: w += " AND subrubro=?"; p.append(_garble(subrubro))
    if categoria: w += " AND categoria=?"; p.append(_garble(categoria))
    df = q(f"SELECT brand_name, SUM(gmv) gmv_usd, SUM(sold_quantity) unidades FROM marcas WHERE {w} GROUP BY brand_name ORDER BY gmv_usd DESC LIMIT ?", tuple(p + [limit]))
    df["brand_name"] = df["brand_name"].apply(_ungarble)
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def top_vends(periodo, subrubro=None, categoria=None, limit=10):
    w, p = "rubro=? AND periodo=?", [RUBRO_DB, periodo]
    if subrubro: w += " AND subrubro=?"; p.append(_garble(subrubro))
    if categoria: w += " AND categoria=?"; p.append(_garble(categoria))
    return q(f"SELECT seller_nickname, seller_type, SUM(gmv) gmv_usd, SUM(sold_quantity) unidades FROM vendedores WHERE {w} GROUP BY seller_nickname ORDER BY gmv_usd DESC LIMIT ?", tuple(p + [limit]))

@st.cache_data(ttl=3600, show_spinner=False)
def top_pubs(periodo, subrubro=None, categoria=None, limit=50):
    w, p = "p.rubro=? AND p.periodo=?", [RUBRO_DB, periodo]
    if subrubro: w += " AND p.subrubro=?"; p.append(_garble(subrubro))
    if categoria: w += " AND p.categoria=?"; p.append(_garble(categoria))
    df = q(f"""SELECT p.title, p.brand, p.seller_nickname, p.categoria,
        COALESCE(p.gmv, p.price*p.sold_quantity,0) gmv_usd, p.sold_quantity unidades, p.price,
        p.fulfillment AS full_delivery, p.free_shipping, p.flex, p.catalog_listing, p.url, p.picture
        FROM publicaciones p WHERE {w} ORDER BY gmv_usd DESC LIMIT ?""", tuple(p + [limit]))
    df["categoria"] = df["categoria"].apply(_ungarble)
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def logistica_breakdown(periodo, subrubro=None, categoria=None):
    w, p = "rubro=? AND periodo=?", [RUBRO_DB, periodo]
    if subrubro: w += " AND subrubro=?"; p.append(_garble(subrubro))
    if categoria: w += " AND categoria=?"; p.append(_garble(categoria))
    return q(f"""SELECT
        SUM(CASE WHEN fulfillment='SI' THEN 1 ELSE 0 END) n_full,
        SUM(CASE WHEN flex='SI' AND fulfillment!='SI' THEN 1 ELSE 0 END) n_flex,
        SUM(CASE WHEN fulfillment!='SI' AND flex!='SI' THEN 1 ELSE 0 END) n_sin,
        SUM(CASE WHEN free_shipping='SI' THEN 1 ELSE 0 END) n_free,
        SUM(CASE WHEN free_shipping!='SI' THEN 1 ELSE 0 END) n_paid,
        COUNT(*) total FROM publicaciones WHERE {w}""", tuple(p)).iloc[0]

@st.cache_data(ttl=3600, show_spinner=False)
def cobertura_pubs(periodo, subrubro=None, categoria=None):
    """GMV publicaciones como % del GMV marcas (mercado real)."""
    w, p = "rubro=? AND periodo=?", [RUBRO_DB, periodo]
    if subrubro: w += " AND subrubro=?"; p.append(_garble(subrubro))
    if categoria: w += " AND categoria=?"; p.append(_garble(categoria))
    gmv_m = q(f"SELECT SUM(gmv) FROM marcas WHERE {w}", tuple(p)).iloc[0, 0] or 0
    gmv_p = q(f"SELECT SUM(gmv) FROM publicaciones WHERE {w}", tuple(p)).iloc[0, 0] or 0
    pct = round(gmv_p / gmv_m * 100, 1) if gmv_m else 0
    return pct, gmv_m, gmv_p

def fmt_usd(v):
    if v is None or (isinstance(v, float) and v != v): return "—"
    v = float(v)
    if v >= 1e6: return f"USD {v/1e6:.2f}M"
    if v >= 1e3: return f"USD {v/1e3:.1f}K"
    return f"USD {v:.0f}"

def fmt_num(v):
    if v is None: return "—"
    return f"{int(v):,}".replace(",", ".")

def fmt_pct(v):
    if v is None: return "—"
    return f"{float(v):.1f}%"

def delta_pct(curr, prev):
    if not prev or prev == 0: return None
    return round((curr - prev) / prev * 100, 1)

def delta_html(d, label="MoM"):
    if d is None: return f'<span class="kpi-ne">— {label}</span>'
    cls = "kpi-up" if d > 0 else "kpi-dn"
    ico = "▲" if d > 0 else "▼"
    return f'<span class="{cls}">{ico} {abs(d):.1f}% {label}</span>'

def prev_per(p):
    if not p or len(p) < 7: return ""
    y, m = int(p[:4]), int(p[5:7])
    m -= 1
    if m == 0: m, y = 12, y - 1
    return f"{y}-{m:02d}"

SPECIAL = {"2025-05": "Hot Sale 🔥", "2025-11": "Black Friday ⚡", "2025-12": "Navidad 🎄",
           "2026-05": "Hot Sale 🔥", "2024-11": "Black Friday ⚡", "2024-12": "Navidad 🎄"}

def esc(s): return html_module.escape(str(s or ""))

with st.sidebar:
    st.markdown("### 🎛 Filtros")
    periodos = get_periodos()
    if not periodos: st.error("Sin datos"); st.stop()
    default_idx = 1 if len(periodos) > 1 else 0
    periodo = st.selectbox("📅 Período", periodos, index=default_idx)
    cats_df = get_cats(periodo)
    subs = ["Todos"] + sorted(cats_df["subrubro"].dropna().unique().tolist())
    sub_sel = st.selectbox("🏷️ Subrubro", subs)
    sub_f = None if sub_sel == "Todos" else sub_sel
    if sub_f:
        cats = cats_df[cats_df["subrubro"] == sub_f]["categoria"].dropna().sort_values().tolist()
    else:
        cats = cats_df["categoria"].dropna().sort_values().tolist()
    cat_sel = st.selectbox(f"📦 Categoría ({len(cats)})", ["Todas"] + cats)
    cat_f = None if cat_sel == "Todas" else cat_sel
    st.divider()
    st.markdown("### ℹ️ Info")
    st.caption(f"Período: **{periodo}**")
    st.caption(f"Subrubro: **{sub_sel}**")
    st.caption(f"Categoría: **{cat_sel}**")
    st.caption(f"Total períodos: **{len(periodos)}** ({periodos[-1]} → {periodos[0]})")
    if SPECIAL.get(periodo):
        st.caption(f"⚠️ **{SPECIAL[periodo]}**")
    if st.button("🔄 Limpiar caché"):
        st.cache_data.clear(); st.rerun()

kpis_curr = kpis(periodo, sub_f, cat_f)
pp = prev_per(periodo)
kpis_prev = kpis(pp, sub_f, cat_f) if pp in periodos else None
scope = sub_sel if sub_sel != "Todos" else "Todo PE"
if cat_sel != "Todas": scope += f" › {cat_sel}"

st.markdown(f"""
<div class="vs-header">
  <div class="vs-icon">📊</div>
  <div><div class="vs-brand-name">VS Analytics</div><div class="vs-brand-sub">Pequeños Electrodomésticos · MLA</div></div>
  <span class="vs-scope">{esc(scope)}</span>
  <span class="vs-period">📅 {periodo}{' · ' + SPECIAL[periodo] if SPECIAL.get(periodo) else ''}</span>
</div>
<div class="vs-bc">
  <span>Pequeños Electrodomésticos</span><span class="bc-sep">›</span>
  <span>{esc(sub_sel)}</span><span class="bc-sep">›</span>
  <span class="bc-active">{esc(cat_sel)}</span>
</div>""", unsafe_allow_html=True)

df_b5 = top_marcas(periodo, sub_f, cat_f, limit=5)
df_v5 = top_vends(periodo, sub_f, cat_f, limit=5)
df_evo = evolucion(sub_f, cat_f)

insights = []
if kpis_prev and kpis_prev["gmv"]:
    d = delta_pct(kpis_curr["gmv"], kpis_prev["gmv"])
    if d is not None:
        ico = "📈" if d > 0 else "📉"
        insights.append((ico, f'<strong>GMV {d:+.1f}% MoM</strong> — {fmt_usd(kpis_prev["gmv"])} → {fmt_usd(kpis_curr["gmv"])}'))
if not df_b5.empty:
    tot = df_b5["gmv_usd"].sum()
    top3 = df_b5.head(3)["gmv_usd"].sum()
    names = ", ".join(df_b5.head(3)["brand_name"].tolist())
    insights.append(("🏆", f'<strong>Top 3 marcas: {top3/tot*100:.1f}%</strong> del mercado — <em>{esc(names)}</em>'))
insights.append(("📦", f'<strong>{kpis_curr["pct_full"]:.1f}% con Envío Full</strong> · {kpis_curr["pct_free"]:.1f}% Envío Gratis'))
if not df_v5.empty:
    tot_v = df_v5["gmv_usd"].sum()
    lider = df_v5.iloc[0]
    insights.append(("🏪", f'<strong>Líder: {esc(lider["seller_nickname"])}</strong> — {lider["gmv_usd"]/tot_v*100:.1f}% del top 5'))
if len(df_evo) >= 12:
    yoy_per = f"{int(periodo[:4])-1}-{periodo[5:7]}"
    yoy_row = df_evo[df_evo["periodo"] == yoy_per]
    if not yoy_row.empty:
        d = delta_pct(kpis_curr["gmv"], yoy_row["gmv_usd"].iloc[0])
        if d is not None:
            insights.append(("📈" if d > 0 else "📉", f'<strong>YoY {d:+.1f}%</strong> vs {yoy_per}'))

items_html = "".join(f'<div class="insight-item"><span class="insight-icon">{ico}</span><span class="insight-text">{txt}</span></div>' for ico, txt in insights)
st.markdown(f'<div class="insights-panel">{items_html}</div>', unsafe_allow_html=True)

ticket = kpis_curr["gmv"] / max(kpis_curr["units"], 1)
ticket_p = (kpis_prev["gmv"] / max(kpis_prev["units"], 1)) if kpis_prev and kpis_prev["units"] else None

def kpi_card(label, value, d_curr, d_prev, fmt_fn=fmt_usd, label2="MoM"):
    d = delta_pct(d_curr, d_prev) if d_prev else None
    return f'<div class="kpi-card"><div class="kpi-lbl">{label}</div><div class="kpi-val">{fmt_fn(value)}</div>{delta_html(d, label2)}</div>'

row1 = "".join([
    kpi_card("GMV (USD)", kpis_curr["gmv"], kpis_curr["gmv"], kpis_prev["gmv"] if kpis_prev else None),
    kpi_card("Unidades", kpis_curr["units"], kpis_curr["units"], kpis_prev["units"] if kpis_prev else None, fmt_num),
    kpi_card("Ticket Promedio", ticket, ticket, ticket_p),
    kpi_card("Publicaciones", kpis_curr["pubs"], kpis_curr["pubs"], kpis_prev["pubs"] if kpis_prev else None, fmt_num),
])
row2 = "".join([
    kpi_card("Vendedores", kpis_curr["vends"], kpis_curr["vends"], kpis_prev["vends"] if kpis_prev else None, fmt_num),
    kpi_card("Marcas activas", kpis_curr["marcas"], None, None, fmt_num),
    kpi_card("% Envío Full", kpis_curr["pct_full"], None, None, fmt_pct),
    kpi_card("% Envío Gratis", kpis_curr["pct_free"], None, None, fmt_pct),
])
st.markdown(f'<div class="kpi-grid">{row1}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="kpi-grid" style="margin-top:12px">{row2}</div>', unsafe_allow_html=True)
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

tab_analisis, tab_ranking, tab_tendencias = st.tabs(["📊 Análisis", "🏆 Ranking", "📈 Tendencias"])

with tab_analisis:
    col_chart, col_marcas = st.columns([3, 1], gap="small")
    with col_chart:
        colors = ["#f59e0b" if r in SPECIAL else "#7c6af7" for r in df_evo["periodo"]]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_evo["periodo"], y=df_evo["gmv_usd"], name="GMV (USD)", marker_color=colors, opacity=0.9, hovertemplate="<b>%{x}</b><br>GMV: USD %{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df_evo["periodo"], y=df_evo["unidades"], name="Unidades", yaxis="y2", line=dict(color="#fbbf24", width=2), mode="lines+markers", marker=dict(size=4, color="#fbbf24"), hovertemplate="<b>%{x}</b><br>Unidades: %{y:,.0f}<extra></extra>"))
        fig.update_layout(height=300, template="plotly_dark", paper_bgcolor="#161625", plot_bgcolor="#161625",
            title=dict(text="Evolución 13 Meses", font=dict(size=11, color="#6b7a99"), x=0),
            yaxis=dict(title="GMV USD", tickformat=",.0f", gridcolor="#252538", color="#6b7a99"),
            yaxis2=dict(title="Unidades", overlaying="y", side="right", tickformat=",.0f", color="#6b7a99", gridcolor="rgba(0,0,0,0)"),
            margin=dict(l=10, r=10, t=36, b=40), legend=dict(orientation="h", y=1.18, x=0, font=dict(size=10)), bargap=0.25)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_marcas:
        df_m = top_marcas(periodo, sub_f, cat_f, limit=10)
        if not df_m.empty:
            total_m = df_m["gmv_usd"].sum()
            rows = ""
            for i, row in df_m.iterrows():
                pct = row["gmv_usd"] / total_m * 100 if total_m else 0
                rows += f'<div class="top-row"><span class="top-n">{i+1}</span><span class="top-name">{esc(row["brand_name"])}</span><span class="top-bar-w"><div class="top-bar-bg"><div class="top-bar" style="width:{pct:.1f}%"></div></div></span><span class="top-pct">{pct:.1f}%</span><span class="top-gmv">{fmt_usd(row["gmv_usd"])}</span></div>'
            st.markdown(f'<div class="vs-card"><div class="vs-card-title">Top Marcas <span style="font-weight:400;color:var(--text-muted)">GMV</span></div>{rows}</div>', unsafe_allow_html=True)

    log = logistica_breakdown(periodo, sub_f, cat_f)
    col_d1, col_d2, col_d3 = st.columns(3, gap="small")
    DONUT_LAYOUT = dict(height=240, paper_bgcolor="#161625", plot_bgcolor="#161625", margin=dict(l=10, r=10, t=10, b=10), showlegend=False, font=dict(color="#e2e8f0"))

    def donut_fig(labels, values, colors):
        fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.58, marker_colors=colors, textinfo="none", hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>"))
        fig.update_layout(**DONUT_LAYOUT)
        return fig

    with col_d1:
        total_log = int(log["total"] or 1)
        st.plotly_chart(donut_fig(["Full", "Flex", "Sin Full"], [int(log["n_full"]), int(log["n_flex"]), int(log["n_sin"])], ["#7c6af7", "#4f8ef7", "#252538"]), use_container_width=True, config={"displayModeBar": False})
        leg = "".join(f'<div class="dleg-row"><span class="dleg-dot" style="background:{c}"></span><span class="dleg-name">{n}</span><span class="dleg-pct">{v/total_log*100:.1f}%</span></div>'
                      for n, v, c in [("Full", log["n_full"], "#7c6af7"), ("Flex", log["n_flex"], "#4f8ef7"), ("Sin Full", log["n_sin"], "#94a3b8")])
        st.markdown(f'<div class="donut-card"><div class="donut-title">Logística</div><div class="dleg">{leg}</div></div>', unsafe_allow_html=True)

    with col_d2:
        st.plotly_chart(donut_fig(["Con Envío Gratis", "Con Costo"], [int(log["n_free"]), int(log["n_paid"])], ["#4ade80", "#f87171"]), use_container_width=True, config={"displayModeBar": False})
        leg2 = "".join(f'<div class="dleg-row"><span class="dleg-dot" style="background:{c}"></span><span class="dleg-name">{n}</span><span class="dleg-pct">{v/total_log*100:.1f}%</span></div>'
                       for n, v, c in [("Envío Gratis", log["n_free"], "#4ade80"), ("Con Costo", log["n_paid"], "#f87171")])
        st.markdown(f'<div class="donut-card"><div class="donut-title">Envío Gratis</div><div class="dleg">{leg2}</div></div>', unsafe_allow_html=True)

    with col_d3:
        df_sub = q("SELECT subrubro, SUM(gmv) gmv_usd FROM marcas WHERE rubro=? AND periodo=? GROUP BY subrubro ORDER BY gmv_usd DESC", (RUBRO_DB, periodo))
        df_sub["subrubro"] = df_sub["subrubro"].apply(_ungarble)
        sub_colors = ["#7c6af7", "#4f8ef7", "#a78bfa", "#fbbf24", "#94a3b8"]
        if not df_sub.empty:
            tot_sub = df_sub["gmv_usd"].sum()
            st.plotly_chart(donut_fig(df_sub["subrubro"].tolist(), df_sub["gmv_usd"].tolist(), sub_colors[:len(df_sub)]), use_container_width=True, config={"displayModeBar": False})
            leg3 = "".join(f'<div class="dleg-row"><span class="dleg-dot" style="background:{sub_colors[i%len(sub_colors)]}"></span><span class="dleg-name">{esc(r["subrubro"])}</span><span class="dleg-pct">{r["gmv_usd"]/tot_sub*100:.1f}%</span></div>'
                           for i, r in df_sub.iterrows())
            st.markdown(f'<div class="donut-card"><div class="donut-title">Por Subrubro</div><div class="dleg">{leg3}</div></div>', unsafe_allow_html=True)

    cob_pct, gmv_m, _ = cobertura_pubs(periodo, sub_f, cat_f)
    gmv_pubs_str = "~" + str(round(cob_pct, 1)) + "% del GMV de mercado (" + fmt_usd(gmv_m) + " seg\u00fan top 100 marcas)"
    st.markdown(f'<div style="margin:4px 0 12px 0;padding:7px 14px;background:rgba(124,106,247,.06);border:1px solid rgba(124,106,247,.2);border-radius:8px;font-size:10px;color:var(--text-muted)">Envio/log. calculado sobre top 100 publicaciones por unidades · <strong style="color:var(--accent)">{cob_pct:.1f}% del GMV de mercado</strong> ({fmt_usd(gmv_m)} seg\u00fan top 100 marcas)</div>', unsafe_allow_html=True)

    col_conc, col_char = st.columns(2, gap="small")
    with col_conc:
        df_v15 = top_vends(periodo, sub_f, cat_f, limit=15)
        if not df_v15.empty:
            tv = df_v15["gmv_usd"].sum()
            t3 = df_v15.head(3)["gmv_usd"].sum(); t5 = df_v15.head(5)["gmv_usd"].sum(); t10 = df_v15.head(10)["gmv_usd"].sum()
            rows_v = ""
            for i, row in df_v15.head(8).iterrows():
                pct = row["gmv_usd"] / tv * 100 if tv else 0
                tipo = f'<span style="font-size:9px;background:rgba(124,106,247,.12);color:#7c6af7;border-radius:4px;padding:1px 5px">{esc(row.get("seller_type",""))}</span>' if row.get("seller_type") else ""
                rows_v += f'<div class="top-row"><span class="top-n">{i+1}</span><span class="top-name">{esc(row["seller_nickname"])} {tipo}</span><span class="top-bar-w"><div class="top-bar-bg"><div class="top-bar" style="width:{pct:.1f}%"></div></div></span><span class="top-pct">{pct:.1f}%</span><span class="top-gmv">{fmt_usd(row["gmv_usd"])}</span></div>'
            footer = f'<div class="conc-footer"><div class="conc-foot-item"><div class="conc-foot-val">{t3/tv*100:.1f}%</div><div class="conc-foot-lbl">Top 3</div></div><div class="conc-foot-item"><div class="conc-foot-val">{t5/tv*100:.1f}%</div><div class="conc-foot-lbl">Top 5</div></div><div class="conc-foot-item"><div class="conc-foot-val">{t10/tv*100:.1f}%</div><div class="conc-foot-lbl">Top 10</div></div></div>'
            st.markdown(f'<div class="vs-card"><div class="vs-card-title">Concentración Vendedores <span style="font-weight:400;color:var(--text-muted)">{kpis_curr["vends"]} activos</span></div>{rows_v}{footer}</div>', unsafe_allow_html=True)

    with col_char:
        yoy_txt = "—"
        if len(df_evo) >= 12:
            yp = f"{int(periodo[:4])-1}-{periodo[5:7]}"
            row_y = df_evo[df_evo["periodo"] == yp]
            if not row_y.empty:
                d = delta_pct(kpis_curr["gmv"], row_y["gmv_usd"].iloc[0])
                if d is not None:
                    yoy_txt = f'<span class="{"kpi-up" if d>0 else "kpi-dn"}">{d:+.1f}%</span>'
        mejor = df_evo.loc[df_evo["gmv_usd"].idxmax()] if not df_evo.empty else None
        cat_count = len(cats_df["categoria"].unique()) if not cats_df.empty else "—"
        st.markdown(f'''<div class="vs-card"><div class="vs-card-title">Características del Mercado</div>
<div class="char-grid">
  <div class="char-stat"><div class="char-val" style="font-size:16px">{fmt_usd(ticket)}</div><div class="char-lbl">Ticket Promedio</div></div>
  <div class="char-stat"><div class="char-val" style="font-size:16px">{yoy_txt}</div><div class="char-lbl">YoY vs {int(periodo[:4])-1}</div></div>
  <div class="char-stat"><div class="char-val" style="font-size:14px">{mejor["periodo"] if mejor is not None else "—"}</div><div class="char-lbl">Mejor mes</div><div class="char-sub">{fmt_usd(mejor["gmv_usd"]) if mejor is not None else ""}</div></div>
  <div class="char-stat"><div class="char-val" style="font-size:20px">{cat_count}</div><div class="char-lbl">Categorías activas</div><div class="char-sub">{fmt_pct(kpis_curr["pct_cat"])} catálogo</div></div>
</div></div>''', unsafe_allow_html=True)

with tab_ranking:
    rtab1, rtab2, rtab3 = st.tabs(["📦 Publicaciones", "🏷️ Marcas", "🏪 Vendedores"])
    with rtab1:
        df_pub = top_pubs(periodo, sub_f, cat_f, limit=50)
        if df_pub.empty:
            st.warning("Sin datos.")
        else:
            rows_pub = ""
            for i, row in df_pub.iterrows():
                rb_cls = "rb-g" if i==0 else "rb-s" if i==1 else "rb-b" if i==2 else ""
                thumb = f'<img class="thumb" src="{esc(row["picture"])}" onerror="this.style.display=\'none\'">' if row.get("picture") else '<span class="thumb-ph">📦</span>'
                pills = ""
                if row.get("full_delivery") == "SI": pills += '<span class="pill p-full">Full</span>'
                if row.get("free_shipping") == "SI": pills += '<span class="pill p-free">Free</span>'
                if row.get("flex") == "SI": pills += '<span class="pill p-flex">Flex</span>'
                if row.get("catalog_listing") == "SI": pills += '<span class="pill p-cat">Cat.</span>'
                title_link = f'<a href="{esc(row["url"])}" target="_blank" style="color:var(--text);text-decoration:none">{esc(str(row["title"])[:70])}{"…" if len(str(row["title"]))>70 else ""}</a>' if row.get("url") else esc(str(row["title"])[:70])
                rows_pub += f'<tr><td><span class="rb {rb_cls}">{i+1}</span></td><td>{thumb}</td><td style="max-width:320px"><span class="t-title">{title_link}</span><span class="t-sub">{esc(row.get("brand",""))} · {esc(row.get("seller_nickname",""))}</span></td><td style="font-size:10px;color:var(--text-muted)">{esc(row["categoria"])}</td><td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv_usd"])}</td><td class="num">{fmt_num(row["unidades"])}</td><td class="num">{fmt_usd(row["price"])}</td><td>{pills}</td></tr>'
            st.markdown(f'<div class="vs-card" style="padding:0;overflow:hidden"><table class="rank-tbl"><thead><tr><th>#</th><th>Img</th><th>Producto</th><th>Cat.</th><th class="num">GMV USD</th><th class="num">Uds.</th><th class="num">Precio</th><th>Log.</th></tr></thead><tbody>{rows_pub}</tbody></table><div style="padding:8px 14px;font-size:10px;color:var(--text-muted)">Top {len(df_pub)} por GMV · {periodo}</div></div>', unsafe_allow_html=True)

    with rtab2:
        df_mbig = top_marcas(periodo, sub_f, cat_f, limit=30)
        if not df_mbig.empty:
            total_mb = df_mbig["gmv_usd"].sum()
            rows_m = ""
            for i, row in df_mbig.iterrows():
                rb_cls = "rb-g" if i==0 else "rb-s" if i==1 else "rb-b" if i==2 else ""
                pct = row["gmv_usd"] / total_mb * 100 if total_mb else 0
                rows_m += f'<tr><td><span class="rb {rb_cls}">{i+1}</span></td><td style="font-weight:600;color:var(--text)">{esc(row["brand_name"])}</td><td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv_usd"])}</td><td class="num">{fmt_num(row["unidades"])}</td><td class="num" style="color:var(--accent);font-weight:600">{pct:.1f}%</td><td style="min-width:100px"><div class="top-bar-bg"><div class="top-bar" style="width:{pct:.1f}%"></div></div></td></tr>'
            col_tbl, col_side = st.columns([2, 1], gap="small")
            with col_tbl:
                st.markdown(f'<div class="vs-card" style="padding:0;overflow:hidden"><table class="rank-tbl"><thead><tr><th>#</th><th>Marca</th><th class="num">GMV USD</th><th class="num">Unidades</th><th class="num">% Mercado</th><th>Share</th></tr></thead><tbody>{rows_m}</tbody></table></div>', unsafe_allow_html=True)
            with col_side:
                t3m=df_mbig.head(3)["gmv_usd"].sum(); t5m=df_mbig.head(5)["gmv_usd"].sum(); t10m=df_mbig.head(10)["gmv_usd"].sum()
                lider=df_mbig.iloc[0]
                st.markdown(f'<div class="vs-card"><div class="vs-card-title">Concentración</div><div class="conc-row"><span class="conc-lbl">Top 3</span><span class="conc-val">{t3m/total_mb*100:.1f}%</span></div><div class="conc-row"><span class="conc-lbl">Top 5</span><span class="conc-val">{t5m/total_mb*100:.1f}%</span></div><div class="conc-row"><span class="conc-lbl">Top 10</span><span class="conc-val">{t10m/total_mb*100:.1f}%</span></div><div class="conc-row" style="margin-top:8px"><span class="conc-lbl">Líder</span><span style="font-size:12px;font-weight:600;color:var(--text)">{esc(lider["brand_name"])}</span></div><div class="conc-row"><span class="conc-lbl">GMV</span><span class="conc-val">{fmt_usd(lider["gmv_usd"])}</span></div></div>', unsafe_allow_html=True)

    with rtab3:
        df_vbig = top_vends(periodo, sub_f, cat_f, limit=30)
        if not df_vbig.empty:
            total_vb = df_vbig["gmv_usd"].sum()
            rows_v2 = ""
            for i, row in df_vbig.iterrows():
                rb_cls = "rb-g" if i==0 else "rb-s" if i==1 else "rb-b" if i==2 else ""
                pct = row["gmv_usd"] / total_vb * 100 if total_vb else 0
                tipo = f'<span style="font-size:9px;background:rgba(124,106,247,.12);color:#7c6af7;border-radius:4px;padding:1px 5px">{esc(row.get("seller_type",""))}</span>' if row.get("seller_type") else ""
                rows_v2 += f'<tr><td><span class="rb {rb_cls}">{i+1}</span></td><td style="font-weight:600;color:var(--text)">{esc(row["seller_nickname"])} {tipo}</td><td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv_usd"])}</td><td class="num">{fmt_num(row["unidades"])}</td><td class="num" style="color:var(--accent);font-weight:600">{pct:.1f}%</td><td style="min-width:100px"><div class="top-bar-bg"><div class="top-bar" style="width:{pct:.1f}%"></div></div></td></tr>'
            col_tbl2, col_side2 = st.columns([2, 1], gap="small")
            with col_tbl2:
                st.markdown(f'<div class="vs-card" style="padding:0;overflow:hidden"><table class="rank-tbl"><thead><tr><th>#</th><th>Vendedor</th><th class="num">GMV USD</th><th class="num">Unidades</th><th class="num">% Top30</th><th>Share</th></tr></thead><tbody>{rows_v2}</tbody></table></div>', unsafe_allow_html=True)
            with col_side2:
                t3v=df_vbig.head(3)["gmv_usd"].sum(); t5v=df_vbig.head(5)["gmv_usd"].sum(); t10v=df_vbig.head(10)["gmv_usd"].sum()
                lv=df_vbig.iloc[0]
                st.markdown(f'<div class="vs-card"><div class="vs-card-title">Concentración</div><div class="conc-row"><span class="conc-lbl">Top 3</span><span class="conc-val">{t3v/total_vb*100:.1f}%</span></div><div class="conc-row"><span class="conc-lbl">Top 5</span><span class="conc-val">{t5v/total_vb*100:.1f}%</span></div><div class="conc-row"><span class="conc-lbl">Top 10</span><span class="conc-val">{t10v/total_vb*100:.1f}%</span></div><div class="conc-row"><span class="conc-lbl">Líder</span><span style="font-size:12px;font-weight:600;color:var(--text)">{esc(lv["seller_nickname"])}</span></div><div class="conc-row"><span class="conc-lbl">GMV</span><span class="conc-val">{fmt_usd(lv["gmv_usd"])}</span></div></div>', unsafe_allow_html=True)

with tab_tendencias:
    col_t1, col_t2 = st.columns(2, gap="small")
    with col_t1:
        fig_tend = go.Figure()
        bar_c2 = ["#f59e0b" if r in SPECIAL else "#7c6af7" for r in df_evo["periodo"]]
        fig_tend.add_trace(go.Bar(x=df_evo["periodo"], y=df_evo["gmv_usd"], name="GMV USD", marker_color=bar_c2, opacity=0.85))
        fig_tend.add_trace(go.Scatter(x=df_evo["periodo"], y=df_evo["unidades"], name="Unidades", yaxis="y2", line=dict(color="#fbbf24", width=2), mode="lines+markers", marker=dict(size=4)))
        fig_tend.update_layout(height=300, template="plotly_dark", paper_bgcolor="#161625", plot_bgcolor="#161625",
            title=dict(text="GMV + Unidades — Evolución Mensual", font=dict(size=11, color="#6b7a99"), x=0),
            yaxis=dict(gridcolor="#252538", color="#6b7a99", tickformat=",.0f"),
            yaxis2=dict(overlaying="y", side="right", color="#6b7a99", tickformat=",.0f", gridcolor="rgba(0,0,0,0)"),
            legend=dict(orientation="h", y=1.18, font=dict(size=10)), margin=dict(l=10, r=10, t=36, b=40), bargap=0.25)
        st.plotly_chart(fig_tend, use_container_width=True, config={"displayModeBar": False})
    with col_t2:
        if not df_evo.empty:
            best = df_evo.loc[df_evo["gmv_usd"].idxmax()]; worst = df_evo.loc[df_evo["gmv_usd"].idxmin()]
            st.markdown(f'''<div class="vs-card"><div class="vs-card-title">Estadísticas {len(df_evo)} Meses</div>
<div class="char-grid">
  <div class="char-stat"><div class="char-val" style="font-size:15px">{fmt_usd(best["gmv_usd"])}</div><div class="char-lbl">Mejor mes</div><div class="char-sub">{best["periodo"]}</div></div>
  <div class="char-stat"><div class="char-val" style="font-size:15px">{fmt_usd(worst["gmv_usd"])}</div><div class="char-lbl">Peor mes</div><div class="char-sub">{worst["periodo"]}</div></div>
  <div class="char-stat"><div class="char-val" style="font-size:15px">{fmt_usd(df_evo["gmv_usd"].mean())}</div><div class="char-lbl">GMV Promedio</div></div>
  <div class="char-stat"><div class="char-val" style="font-size:15px">{fmt_num(int(df_evo["unidades"].mean()))}</div><div class="char-lbl">Uds. Promedio</div></div>
</div></div>''', unsafe_allow_html=True)

    col_t3, col_t4 = st.columns(2, gap="small")
    with col_t3:
        if len(df_evo) >= 2:
            df_evo2 = df_evo.copy().reset_index(drop=True)
            df_evo2["mom"] = df_evo2["gmv_usd"].pct_change() * 100
            df_evo2 = df_evo2.dropna(subset=["mom"])
            fig_mom = go.Figure(go.Bar(x=df_evo2["periodo"], y=df_evo2["mom"], marker_color=["#4ade80" if v >= 0 else "#f87171" for v in df_evo2["mom"]], opacity=0.85))
            fig_mom.add_hline(y=0, line_color="#252538", line_width=1)
            fig_mom.update_layout(height=240, template="plotly_dark", paper_bgcolor="#161625", plot_bgcolor="#161625",
                title=dict(text="Variación MoM (%)", font=dict(size=11, color="#6b7a99"), x=0),
                yaxis=dict(gridcolor="#252538", color="#6b7a99", ticksuffix="%"),
                margin=dict(l=10, r=10, t=36, b=40), bargap=0.25, showlegend=False)
            st.plotly_chart(fig_mom, use_container_width=True, config={"displayModeBar": False})
    with col_t4:
        df_tick = q(f"""SELECT m.periodo, SUM(m.gmv)/NULLIF(SUM(m.sold_quantity),0) ticket_usd
            FROM marcas m WHERE m.rubro=? {'AND m.subrubro=?' if sub_f else ''} {'AND m.categoria=?' if cat_f else ''}
            GROUP BY m.periodo ORDER BY m.periodo""",
            tuple([RUBRO_DB] + ([_garble(sub_f)] if sub_f else []) + ([_garble(cat_f)] if cat_f else [])))
        if not df_tick.empty:
            fig_tick = go.Figure(go.Scatter(x=df_tick["periodo"], y=df_tick["ticket_usd"],
                line=dict(color="#7c6af7", width=2), mode="lines+markers", marker=dict(size=5, color="#7c6af7"),
                fill="tozeroy", fillcolor="rgba(124,106,247,0.08)"))
            fig_tick.update_layout(height=240, template="plotly_dark", paper_bgcolor="#161625", plot_bgcolor="#161625",
                title=dict(text="Ticket Promedio USD", font=dict(size=11, color="#6b7a99"), x=0),
                yaxis=dict(gridcolor="#252538", color="#6b7a99", tickprefix="USD "),
                margin=dict(l=10, r=10, t=36, b=40), showlegend=False)
            st.plotly_chart(fig_tick, use_container_width=True, config={"displayModeBar": False})

st.markdown(f"""
<div style="margin:20px 20px 0;padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:8px;display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted)">
  <span>📊 VS Analytics — Pequeños Electrodomésticos · MLA</span>
  <span>64K publicaciones · {len(periodos)} períodos · {periodos[-1]} → {periodos[0]}</span>
  <span>v2.0 · Streamlit Cloud</span>
</div>""", unsafe_allow_html=True)
