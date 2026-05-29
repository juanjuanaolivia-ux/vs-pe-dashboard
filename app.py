"""
VS Analytics — Pequeños Electrodomésticos Dashboard
====================================================
Single-file Streamlit app que reemplaza el stack anterior (FastAPI + HTML + JS).

Stack: Python + Streamlit + Plotly + SQLite
Deploy: Streamlit Cloud (gratis, sin tarjeta)
Data: vs_pe.db (DB de Mercado Libre Argentina acotada a categoría PE — 64K publicaciones)

Para correr localmente:
    pip install -r requirements.txt
    streamlit run app.py
"""

import gzip
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================================
# CONFIG
# ============================================================================

st.set_page_config(
    page_title="VS Analytics — PE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme override + estilos custom
st.markdown("""
<style>
    .stApp { background-color: #0d0d1a; }
    [data-testid="stSidebar"] { background-color: #161625; }
    h1, h2, h3 { color: #e2e8f0 !important; }
    .stMetric { background-color: #161625; padding: 1rem; border-radius: 8px; border: 1px solid #252538; }
    [data-testid="stMetricValue"] { color: #e2e8f0; font-weight: 700; }
    [data-testid="stMetricDelta"] { font-weight: 600; }
    .stDataFrame { background-color: #161625; }
    section[data-testid="stSidebar"] .stMarkdown h3 { color: #7c6af7 !important; }
</style>
""", unsafe_allow_html=True)

DB_GZ_PATH = Path(__file__).parent / "vs_pe.db.gz"
DB_PATH = Path(__file__).parent / "vs_pe.db"

# ============================================================================
# ENCODING FIX (CP437 garbled — bug histórico del loader original)
# ============================================================================

def _garble(s: str) -> str:
    """UTF-8 → CP437 garbled (para queries)"""
    try:
        return s.encode("utf-8").decode("cp437")
    except Exception:
        return s

def _ungarble(s) -> str:
    """CP437 garbled → UTF-8 (para mostrar)"""
    if not s:
        return s
    try:
        return s.encode("cp437").decode("utf-8")
    except Exception:
        return s

# ============================================================================
# DB SETUP (descomprime gz al boot si hace falta — solo primera vez)
# ============================================================================

@st.cache_resource(show_spinner=False)
def ensure_db():
    """Descomprime vs_pe.db.gz → vs_pe.db si no existe. Cached."""
    if DB_PATH.exists() and DB_PATH.stat().st_size > 100_000_000:
        return str(DB_PATH)
    if not DB_GZ_PATH.exists():
        st.error(f"❌ No se encontró {DB_GZ_PATH}. Subí vs_pe.db.gz al repo.")
        st.stop()
    with st.spinner("Descomprimiendo DB (primera vez, ~10s)..."):
        with gzip.open(DB_GZ_PATH, "rb") as fin, open(DB_PATH, "wb") as fout:
            shutil.copyfileobj(fin, fout)
    return str(DB_PATH)

@st.cache_resource(show_spinner=False)
def get_connection():
    db = ensure_db()
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, check_same_thread=False)
    conn.execute("PRAGMA cache_size = -32768")  # 32 MB cache
    conn.execute("PRAGMA mmap_size = 134217728")  # 128 MB mmap
    return conn

@st.cache_data(ttl=3600, show_spinner=False)
def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Query helper con cache TTL 1h."""
    conn = get_connection()
    return pd.read_sql_query(sql, conn, params=params)

# ============================================================================
# DATA HELPERS
# ============================================================================

RUBRO = "Pequeños Electrodomésticos"
RUBRO_DB = _garble(RUBRO)

@st.cache_data(ttl=3600, show_spinner=False)
def get_periodos() -> list:
    df = run_query("SELECT DISTINCT periodo FROM publicaciones ORDER BY periodo DESC")
    return df["periodo"].tolist()

@st.cache_data(ttl=3600, show_spinner=False)
def get_subrubros_y_categorias(periodo: str) -> pd.DataFrame:
    """Devuelve subrubro/categoria disponibles para el período."""
    df = run_query("""
        SELECT DISTINCT subrubro, categoria
        FROM publicaciones
        WHERE periodo = ? AND rubro = ?
        ORDER BY subrubro, categoria
    """, (periodo, RUBRO_DB))
    df["subrubro"] = df["subrubro"].apply(_ungarble)
    df["categoria"] = df["categoria"].apply(_ungarble)
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def kpis_rubro(periodo: str, subrubro: Optional[str] = None) -> dict:
    """KPIs principales del rubro/subrubro en período (en tabla marcas que tiene gmv USD)."""
    where = "rubro = ? AND periodo = ?"
    params = [RUBRO_DB, periodo]
    if subrubro:
        where += " AND subrubro = ?"
        params.append(_garble(subrubro))

    df = run_query(f"""
        SELECT
            SUM(gmv) AS gmv_usd,
            SUM(sold_quantity) AS unidades,
            COUNT(DISTINCT brand_name) AS marcas,
            COUNT(DISTINCT categoria) AS categorias
        FROM marcas
        WHERE {where}
    """, tuple(params))

    df_pub = run_query(f"""
        SELECT
            COUNT(DISTINCT item_id) AS publicaciones,
            COUNT(DISTINCT seller_id) AS vendedores,
            AVG(CAST(full_delivery AS REAL)) * 100 AS pct_full,
            AVG(CAST(free_shipping AS REAL)) * 100 AS pct_envio_gratis,
            AVG(CASE WHEN catalog_listing IS NOT NULL AND catalog_listing != '' THEN 1.0 ELSE 0 END) * 100 AS pct_catalogo
        FROM publicaciones
        WHERE {where}
    """, tuple(params))

    return {
        "gmv_usd": float(df["gmv_usd"].iloc[0] or 0),
        "unidades": int(df["unidades"].iloc[0] or 0),
        "marcas": int(df["marcas"].iloc[0] or 0),
        "categorias": int(df["categorias"].iloc[0] or 0),
        "publicaciones": int(df_pub["publicaciones"].iloc[0] or 0),
        "vendedores": int(df_pub["vendedores"].iloc[0] or 0),
        "pct_full": float(df_pub["pct_full"].iloc[0] or 0),
        "pct_envio_gratis": float(df_pub["pct_envio_gratis"].iloc[0] or 0),
        "pct_catalogo": float(df_pub["pct_catalogo"].iloc[0] or 0),
    }

@st.cache_data(ttl=3600, show_spinner=False)
def evolucion_mensual(subrubro: Optional[str] = None, categoria: Optional[str] = None) -> pd.DataFrame:
    """Serie temporal GMV + unidades por mes."""
    where = "rubro = ?"
    params = [RUBRO_DB]
    if subrubro:
        where += " AND subrubro = ?"
        params.append(_garble(subrubro))
    if categoria:
        where += " AND categoria = ?"
        params.append(_garble(categoria))

    df = run_query(f"""
        SELECT
            periodo,
            SUM(gmv) AS gmv_usd,
            SUM(sold_quantity) AS unidades
        FROM marcas
        WHERE {where}
        GROUP BY periodo
        ORDER BY periodo
    """, tuple(params))
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def top_marcas(periodo: str, subrubro: Optional[str] = None, categoria: Optional[str] = None, limit: int = 15) -> pd.DataFrame:
    where = "rubro = ? AND periodo = ?"
    params = [RUBRO_DB, periodo]
    if subrubro:
        where += " AND subrubro = ?"
        params.append(_garble(subrubro))
    if categoria:
        where += " AND categoria = ?"
        params.append(_garble(categoria))

    df = run_query(f"""
        SELECT
            brand_name,
            SUM(gmv) AS gmv_usd,
            SUM(sold_quantity) AS unidades,
            COUNT(DISTINCT categoria) AS categorias
        FROM marcas
        WHERE {where}
        GROUP BY brand_name
        ORDER BY gmv_usd DESC
        LIMIT ?
    """, tuple(params + [limit]))
    df["brand_name"] = df["brand_name"].apply(_ungarble)
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def top_publicaciones(periodo: str, subrubro: Optional[str] = None, categoria: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
    where = "p.rubro = ? AND p.periodo = ?"
    params = [RUBRO_DB, periodo]
    if subrubro:
        where += " AND p.subrubro = ?"
        params.append(_garble(subrubro))
    if categoria:
        where += " AND p.categoria = ?"
        params.append(_garble(categoria))

    df = run_query(f"""
        SELECT
            p.title,
            p.brand,
            p.seller_nickname,
            p.categoria,
            COALESCE(p.gmv, p.price * p.sold_quantity, 0) AS gmv_usd,
            p.sold_quantity AS unidades,
            p.price,
            p.full_delivery,
            p.free_shipping,
            p.url,
            p.picture
        FROM publicaciones p
        WHERE {where}
        ORDER BY gmv_usd DESC
        LIMIT ?
    """, tuple(params + [limit]))
    df["categoria"] = df["categoria"].apply(_ungarble)
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def top_vendedores(periodo: str, subrubro: Optional[str] = None, categoria: Optional[str] = None, limit: int = 15) -> pd.DataFrame:
    where = "rubro = ? AND periodo = ?"
    params = [RUBRO_DB, periodo]
    if subrubro:
        where += " AND subrubro = ?"
        params.append(_garble(subrubro))
    if categoria:
        where += " AND categoria = ?"
        params.append(_garble(categoria))

    df = run_query(f"""
        SELECT
            seller_nickname,
            seller_type,
            SUM(gmv) AS gmv_usd,
            SUM(sold_quantity) AS unidades
        FROM vendedores
        WHERE {where}
        GROUP BY seller_nickname
        ORDER BY gmv_usd DESC
        LIMIT ?
    """, tuple(params + [limit]))
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def breakdown_subrubro(periodo: str) -> pd.DataFrame:
    """Distribución por subrubro."""
    df = run_query("""
        SELECT
            subrubro,
            SUM(gmv) AS gmv_usd,
            SUM(sold_quantity) AS unidades,
            COUNT(DISTINCT categoria) AS categorias
        FROM marcas
        WHERE rubro = ? AND periodo = ?
        GROUP BY subrubro
        ORDER BY gmv_usd DESC
    """, (RUBRO_DB, periodo))
    df["subrubro"] = df["subrubro"].apply(_ungarble)
    return df

# ============================================================================
# UI HELPERS
# ============================================================================

def fmt_usd(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    if v >= 1_000_000:
        return f"USD {v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"USD {v/1_000:.1f}K"
    return f"USD {v:.0f}"

def fmt_num(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.0f}".replace(",", ".")

def fmt_pct(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:.1f}%"

def delta_pct(curr, prev) -> Optional[float]:
    if not prev or prev == 0:
        return None
    return round((curr - prev) / prev * 100, 1)

def prev_periodo(periodo: str) -> str:
    if not periodo or len(periodo) < 7:
        return ""
    y, m = int(periodo[:4]), int(periodo[5:7])
    m -= 1
    if m == 0:
        m, y = 12, y - 1
    return f"{y}-{m:02d}"

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### 🎛 Filtros")
    periodos = get_periodos()
    if not periodos:
        st.error("No hay datos en la DB")
        st.stop()

    # Default al penúltimo período (el último puede estar incompleto)
    default_idx = 1 if len(periodos) > 1 else 0
    periodo = st.selectbox("📅 Período", periodos, index=default_idx)

    cats_df = get_subrubros_y_categorias(periodo)
    subrubros = ["Todos"] + sorted(cats_df["subrubro"].dropna().unique().tolist())
    subrubro_sel = st.selectbox("🏷️ Subrubro", subrubros)
    subrubro_filter = None if subrubro_sel == "Todos" else subrubro_sel

    if subrubro_filter:
        cats_filtered = cats_df[cats_df["subrubro"] == subrubro_filter]["categoria"].dropna().sort_values().tolist()
    else:
        cats_filtered = cats_df["categoria"].dropna().sort_values().tolist()

    cats_options = ["Todas"] + cats_filtered
    categoria_sel = st.selectbox(f"📦 Categoría ({len(cats_filtered)})", cats_options)
    categoria_filter = None if categoria_sel == "Todas" else categoria_sel

    st.divider()
    st.markdown("### ℹ️ Info")
    st.caption(f"Rubro: **{RUBRO}**")
    st.caption(f"Período activo: **{periodo}**")
    st.caption(f"Filtros: **{subrubro_sel}** / **{categoria_sel}**")
    st.caption(f"Períodos disponibles: {len(periodos)} ({periodos[-1]} → {periodos[0]})")

    if st.button("🔄 Limpiar caché y recargar"):
        st.cache_data.clear()
        st.rerun()

# ============================================================================
# MAIN
# ============================================================================

st.title("📊 VS Analytics — Pequeños Electrodomésticos")
st.caption(f"Mercado Libre Argentina · Análisis competitivo · {periodo}")

scope = subrubro_sel if subrubro_sel != "Todos" else "Todo PE"
if categoria_sel != "Todas":
    scope += f" › {categoria_sel}"
st.markdown(f"**Scope actual:** {scope}")

st.divider()

# ============================================================================
# KPIs PRINCIPALES (con MoM)
# ============================================================================

kpis_curr = kpis_rubro(periodo, subrubro_filter)
periodo_prev = prev_periodo(periodo)
kpis_prev = kpis_rubro(periodo_prev, subrubro_filter) if periodo_prev in periodos else None

st.markdown("### 💰 KPIs principales")

col1, col2, col3, col4 = st.columns(4)
with col1:
    delta = delta_pct(kpis_curr["gmv_usd"], kpis_prev["gmv_usd"]) if kpis_prev else None
    st.metric("GMV (USD)", fmt_usd(kpis_curr["gmv_usd"]), f"{delta:+.1f}% MoM" if delta is not None else None)
with col2:
    delta = delta_pct(kpis_curr["unidades"], kpis_prev["unidades"]) if kpis_prev else None
    st.metric("Unidades", fmt_num(kpis_curr["unidades"]), f"{delta:+.1f}% MoM" if delta is not None else None)
with col3:
    ticket = kpis_curr["gmv_usd"] / max(kpis_curr["unidades"], 1)
    ticket_prev = (kpis_prev["gmv_usd"] / max(kpis_prev["unidades"], 1)) if kpis_prev and kpis_prev["unidades"] else None
    delta = delta_pct(ticket, ticket_prev) if ticket_prev else None
    st.metric("Ticket promedio", fmt_usd(ticket), f"{delta:+.1f}% MoM" if delta is not None else None)
with col4:
    delta = delta_pct(kpis_curr["publicaciones"], kpis_prev["publicaciones"]) if kpis_prev else None
    st.metric("Publicaciones", fmt_num(kpis_curr["publicaciones"]), f"{delta:+.1f}% MoM" if delta is not None else None)

col5, col6, col7, col8 = st.columns(4)
with col5:
    delta = delta_pct(kpis_curr["vendedores"], kpis_prev["vendedores"]) if kpis_prev else None
    st.metric("Vendedores", fmt_num(kpis_curr["vendedores"]), f"{delta:+.1f}% MoM" if delta is not None else None)
with col6:
    st.metric("Marcas", fmt_num(kpis_curr["marcas"]))
with col7:
    st.metric("% Envío Full", fmt_pct(kpis_curr["pct_full"]))
with col8:
    st.metric("% Envío Gratis", fmt_pct(kpis_curr["pct_envio_gratis"]))

st.divider()

# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["📈 Evolución", "🏆 Rankings", "🏷️ Subrubros", "🔍 Insights"])

# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### Evolución temporal (todos los períodos)")
    df_evo = evolucion_mensual(subrubro_filter, categoria_filter)
    if df_evo.empty:
        st.warning("Sin datos para esta combinación.")
    else:
        col_a, col_b = st.columns([3, 1])
        with col_a:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_evo["periodo"], y=df_evo["gmv_usd"],
                                 name="GMV (USD)", marker_color="#7c6af7",
                                 hovertemplate="%{x}<br>GMV: USD %{y:,.0f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=df_evo["periodo"], y=df_evo["unidades"],
                                     name="Unidades", yaxis="y2", line=dict(color="#fbbf24", width=2),
                                     mode="lines+markers",
                                     hovertemplate="%{x}<br>Unidades: %{y:,.0f}<extra></extra>"))
            fig.update_layout(
                height=400, template="plotly_dark",
                paper_bgcolor="#161625", plot_bgcolor="#161625",
                yaxis=dict(title="GMV (USD)", tickformat=",.0f"),
                yaxis2=dict(title="Unidades", overlaying="y", side="right", tickformat=",.0f"),
                margin=dict(l=40, r=40, t=20, b=40),
                legend=dict(orientation="h", y=1.15),
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.markdown("**Estadísticos**")
            if len(df_evo) > 0:
                st.caption(f"Mejor mes: **{df_evo.loc[df_evo['gmv_usd'].idxmax(), 'periodo']}**")
                st.caption(f"GMV máximo: **{fmt_usd(df_evo['gmv_usd'].max())}**")
                st.caption(f"GMV promedio: **{fmt_usd(df_evo['gmv_usd'].mean())}**")
                st.caption(f"Períodos con data: **{len(df_evo)}**")
                if len(df_evo) >= 12:
                    yoy_curr = df_evo[df_evo["periodo"] == periodo]["gmv_usd"].sum()
                    periodo_yoy = f"{int(periodo[:4])-1}-{periodo[5:7]}"
                    yoy_prev = df_evo[df_evo["periodo"] == periodo_yoy]["gmv_usd"].sum()
                    if yoy_prev > 0:
                        st.caption(f"YoY: **{delta_pct(yoy_curr, yoy_prev):+.1f}%**")

# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    rank_tab1, rank_tab2, rank_tab3 = st.tabs(["📦 Top Publicaciones", "🏷️ Top Marcas", "🏪 Top Vendedores"])

    with rank_tab1:
        df_pub = top_publicaciones(periodo, subrubro_filter, categoria_filter, limit=50)
        if df_pub.empty:
            st.warning("Sin datos.")
        else:
            df_pub["GMV (USD)"] = df_pub["gmv_usd"].apply(fmt_usd)
            df_pub["Unidades"] = df_pub["unidades"].apply(fmt_num)
            df_pub["Precio"] = df_pub["price"].apply(fmt_usd)
            df_pub["Full"] = df_pub["full_delivery"].apply(lambda x: "✅" if x else "—")
            df_pub["Free Ship"] = df_pub["free_shipping"].apply(lambda x: "✅" if x else "—")
            display = df_pub[["picture", "title", "brand", "categoria", "seller_nickname", "GMV (USD)", "Unidades", "Precio", "Full", "Free Ship", "url"]].rename(columns={
                "picture": "Imagen", "title": "Producto", "brand": "Marca",
                "categoria": "Categoría", "seller_nickname": "Vendedor", "url": "Link"
            })
            st.dataframe(
                display, use_container_width=True, hide_index=True,
                column_config={
                    "Imagen": st.column_config.ImageColumn("📷", width="small"),
                    "Link": st.column_config.LinkColumn("Ver", width="small", display_text="🔗"),
                },
                height=600,
            )
            st.caption(f"Mostrando top {len(df_pub)} publicaciones por GMV")

    with rank_tab2:
        df_brands = top_marcas(periodo, subrubro_filter, categoria_filter, limit=15)
        if df_brands.empty:
            st.warning("Sin datos.")
        else:
            col_a, col_b = st.columns([2, 1])
            with col_a:
                fig = px.bar(
                    df_brands.head(10), x="gmv_usd", y="brand_name", orientation="h",
                    text="gmv_usd", color="gmv_usd", color_continuous_scale=["#252538", "#7c6af7"],
                )
                fig.update_traces(texttemplate="USD %{x:,.0f}", textposition="outside")
                fig.update_layout(
                    height=450, template="plotly_dark", paper_bgcolor="#161625", plot_bgcolor="#161625",
                    yaxis=dict(autorange="reversed", title=""),
                    xaxis=dict(title="GMV (USD)", tickformat=",.0f"),
                    margin=dict(l=40, r=80, t=20, b=40),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                total_gmv = df_brands["gmv_usd"].sum()
                top3_gmv = df_brands.head(3)["gmv_usd"].sum()
                top5_gmv = df_brands.head(5)["gmv_usd"].sum()
                st.metric("Concentración Top 3", fmt_pct(top3_gmv / total_gmv * 100 if total_gmv else 0))
                st.metric("Concentración Top 5", fmt_pct(top5_gmv / total_gmv * 100 if total_gmv else 0))
                st.metric("Total marcas (top 15)", len(df_brands))
                st.caption(f"**Líder:** {df_brands.iloc[0]['brand_name']}")
                st.caption(f"GMV: {fmt_usd(df_brands.iloc[0]['gmv_usd'])}")

            display = df_brands.copy()
            display["GMV (USD)"] = display["gmv_usd"].apply(fmt_usd)
            display["Unidades"] = display["unidades"].apply(fmt_num)
            display["% Mercado"] = (display["gmv_usd"] / total_gmv * 100).apply(lambda x: f"{x:.1f}%" if total_gmv else "—")
            st.dataframe(
                display[["brand_name", "GMV (USD)", "Unidades", "% Mercado", "categorias"]].rename(columns={
                    "brand_name": "Marca", "categorias": "Categorías"
                }),
                use_container_width=True, hide_index=True, height=400,
            )

    with rank_tab3:
        df_sellers = top_vendedores(periodo, subrubro_filter, categoria_filter, limit=15)
        if df_sellers.empty:
            st.warning("Sin datos.")
        else:
            col_a, col_b = st.columns([2, 1])
            with col_a:
                fig = px.bar(
                    df_sellers.head(10), x="gmv_usd", y="seller_nickname", orientation="h",
                    color="seller_type", text="gmv_usd",
                )
                fig.update_traces(texttemplate="USD %{x:,.0f}", textposition="outside")
                fig.update_layout(
                    height=450, template="plotly_dark", paper_bgcolor="#161625", plot_bgcolor="#161625",
                    yaxis=dict(autorange="reversed", title=""),
                    xaxis=dict(title="GMV (USD)", tickformat=",.0f"),
                    margin=dict(l=40, r=80, t=20, b=40),
                )
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                total_gmv = df_sellers["gmv_usd"].sum()
                top3 = df_sellers.head(3)["gmv_usd"].sum()
                st.metric("Concentración Top 3 sellers", fmt_pct(top3 / total_gmv * 100 if total_gmv else 0))
                st.metric("Top seller share", fmt_pct(df_sellers.iloc[0]['gmv_usd'] / total_gmv * 100 if total_gmv else 0))
                st.caption(f"**Líder:** {df_sellers.iloc[0]['seller_nickname']}")
                st.caption(f"Tipo: {df_sellers.iloc[0]['seller_type']}")

            display = df_sellers.copy()
            display["GMV (USD)"] = display["gmv_usd"].apply(fmt_usd)
            display["Unidades"] = display["unidades"].apply(fmt_num)
            display["% Mercado"] = (display["gmv_usd"] / total_gmv * 100).apply(lambda x: f"{x:.1f}%" if total_gmv else "—")
            st.dataframe(
                display[["seller_nickname", "seller_type", "GMV (USD)", "Unidades", "% Mercado"]].rename(columns={
                    "seller_nickname": "Vendedor", "seller_type": "Tipo"
                }),
                use_container_width=True, hide_index=True, height=400,
            )

# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### Distribución por subrubro")
    df_sub = breakdown_subrubro(periodo)
    if df_sub.empty:
        st.warning("Sin datos.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            fig = px.pie(
                df_sub, values="gmv_usd", names="subrubro", hole=0.55,
                color_discrete_sequence=["#7c6af7", "#4f8ef7", "#a78bfa", "#fbbf24"],
            )
            fig.update_traces(textposition="outside", textinfo="label+percent",
                              hovertemplate="%{label}<br>GMV: USD %{value:,.0f}<br>%{percent}<extra></extra>")
            fig.update_layout(
                height=400, template="plotly_dark", paper_bgcolor="#161625", plot_bgcolor="#161625",
                showlegend=False, margin=dict(l=20, r=20, t=40, b=20),
                title="Distribución de GMV por subrubro",
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            display = df_sub.copy()
            display["GMV (USD)"] = display["gmv_usd"].apply(fmt_usd)
            display["Unidades"] = display["unidades"].apply(fmt_num)
            display["% del total"] = (display["gmv_usd"] / display["gmv_usd"].sum() * 100).apply(lambda x: f"{x:.1f}%")
            st.dataframe(
                display[["subrubro", "GMV (USD)", "Unidades", "categorias", "% del total"]].rename(columns={
                    "subrubro": "Subrubro", "categorias": "Categorías"
                }),
                use_container_width=True, hide_index=True, height=300,
            )

        # Top categorías por subrubro
        st.markdown("### Top categorías por GMV")
        df_cats = run_query("""
            SELECT subrubro, categoria, SUM(gmv) AS gmv_usd, SUM(sold_quantity) AS unidades
            FROM marcas
            WHERE rubro = ? AND periodo = ?
            GROUP BY subrubro, categoria
            ORDER BY gmv_usd DESC
            LIMIT 30
        """, (RUBRO_DB, periodo))
        df_cats["subrubro"] = df_cats["subrubro"].apply(_ungarble)
        df_cats["categoria"] = df_cats["categoria"].apply(_ungarble)

        fig = px.treemap(
            df_cats, path=["subrubro", "categoria"], values="gmv_usd",
            color="gmv_usd", color_continuous_scale=["#252538", "#7c6af7"],
        )
        fig.update_layout(
            height=500, template="plotly_dark", paper_bgcolor="#161625",
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 🔍 Insights automáticos")

    insights = []

    # 1. Variación MoM
    if kpis_prev and kpis_prev["gmv_usd"]:
        d = delta_pct(kpis_curr["gmv_usd"], kpis_prev["gmv_usd"])
        emoji = "📈" if d and d > 0 else "📉"
        insights.append(f"{emoji} **GMV {d:+.1f}% MoM** ({fmt_usd(kpis_prev['gmv_usd'])} → {fmt_usd(kpis_curr['gmv_usd'])})")

    # 2. Top marcas concentración
    df_b = top_marcas(periodo, subrubro_filter, categoria_filter, limit=5)
    if not df_b.empty:
        tot = df_b["gmv_usd"].sum()
        top3 = df_b.head(3)["gmv_usd"].sum()
        top3_names = ", ".join(df_b.head(3)["brand_name"].tolist())
        insights.append(f"🏆 **Top 3 marcas concentran {top3/tot*100:.1f}%** del mercado: _{top3_names}_")

    # 3. Penetración Full
    insights.append(f"📦 **{kpis_curr['pct_full']:.1f}% del mercado** opera con Envío Full")

    # 4. Penetración Catálogo
    if kpis_curr["pct_catalogo"] > 0:
        insights.append(f"📚 **{kpis_curr['pct_catalogo']:.1f}% de las publicaciones** están en catálogo")

    # 5. Top vendedor
    df_v = top_vendedores(periodo, subrubro_filter, categoria_filter, limit=5)
    if not df_v.empty:
        tot_v = df_v["gmv_usd"].sum()
        lider = df_v.iloc[0]
        share = lider['gmv_usd'] / tot_v * 100
        insights.append(f"🏪 **Líder vendedor:** _{lider['seller_nickname']}_ ({share:.1f}% share top 5)")

    # 6. Mejor mes histórico
    df_evo_full = evolucion_mensual(subrubro_filter, categoria_filter)
    if not df_evo_full.empty:
        mejor_mes = df_evo_full.loc[df_evo_full["gmv_usd"].idxmax()]
        insights.append(f"⭐ **Mejor mes histórico:** _{mejor_mes['periodo']}_ ({fmt_usd(mejor_mes['gmv_usd'])})")

    # 7. YoY si hay
    if not df_evo_full.empty and len(df_evo_full) >= 12:
        periodo_yoy = f"{int(periodo[:4])-1}-{periodo[5:7]}"
        yoy_data = df_evo_full[df_evo_full["periodo"] == periodo_yoy]
        if not yoy_data.empty:
            yoy_prev = yoy_data["gmv_usd"].iloc[0]
            d = delta_pct(kpis_curr["gmv_usd"], yoy_prev)
            if d is not None:
                emoji = "📈" if d > 0 else "📉"
                insights.append(f"{emoji} **YoY {d:+.1f}%** vs {periodo_yoy} ({fmt_usd(yoy_prev)} → {fmt_usd(kpis_curr['gmv_usd'])})")

    for ins in insights:
        st.markdown(f"- {ins}")

    st.divider()
    st.markdown("### 💡 Para profundizar")
    st.markdown("""
    - **Tab Evolución:** identificar estacionalidad y momentum
    - **Tab Rankings:** comparar tu posición vs competencia (marcas, vendedores)
    - **Tab Subrubros:** entender mix de portfolio del rubro
    - Filtrá por **categoría específica** en sidebar para análisis más fino
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
with col_f1:
    st.caption("📊 VS Analytics — Pequeños Electrodomésticos")
with col_f2:
    st.caption(f"Data: 64K publicaciones · {len(periodos)} períodos · {periodos[-1]} → {periodos[0]}")
with col_f3:
    st.caption("v1.0 · Streamlit")
