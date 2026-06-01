"""
VS Analytics — Capa de datos
==============================
Todas las queries SQLite viven acá. Ninguna query en app.py o components.py.

Para agregar una query nueva: agregala acá con @st.cache_data y llamala desde app.py.
Para cambiar filtros o columnas: tocás solo este archivo.
"""

import gzip, shutil, sqlite3, io
from pathlib import Path
import pandas as pd
import streamlit as st

from config import RUBROS, garble, ungarble


# ═══════════════════════════════════════════════════════════════════
# CONEXIÓN Y HELPERS
# ═══════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def _get_conn(db_path: str):
    """Una conexión read-only por archivo DB, cacheada globalmente."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    conn.execute("PRAGMA cache_size = -32768")
    conn.execute("PRAGMA mmap_size = 134217728")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


@st.cache_resource(show_spinner=False)
def ensure_db(rubro_key: str) -> str:
    """Descomprime el .db.gz si el .db no existe o está incompleto. Retorna path."""
    cfg = RUBROS[rubro_key]
    db_path: Path = cfg["db_path"]
    db_gz:   Path = cfg["db_gz"]

    if db_path.exists() and db_path.stat().st_size > 10_000_000:
        return str(db_path)

    if not db_gz.exists():
        st.error(f"❌ No se encontró {db_gz.name}. Verificá que el archivo esté en la carpeta.")
        st.stop()

    with st.spinner(f"Preparando base de datos para {cfg['label']}…"):
        with gzip.open(db_gz, "rb") as fin, open(db_path, "wb") as fout:
            shutil.copyfileobj(fin, fout)

    return str(db_path)


def get_conn(rubro_key: str):
    return _get_conn(ensure_db(rubro_key))


@st.cache_data(ttl=3600, show_spinner=False)
def _q(sql: str, params: tuple, rubro_key: str) -> pd.DataFrame:
    """Query genérica cacheada. Clave de caché = sql + params + rubro_key."""
    return pd.read_sql_query(sql, get_conn(rubro_key), params=params)


def _where(rubro_key: str, periodo: str | None = None,
           subrubro: str | None = None, categoria: str | None = None,
           table_prefix: str = "") -> tuple[str, list]:
    """Construye cláusula WHERE y lista de parámetros."""
    p = table_prefix + "." if table_prefix else ""
    rub = RUBROS[rubro_key]["rubro_db"]
    clauses = [f"{p}rubro=?"]
    params  = [rub]
    if periodo:
        clauses.append(f"{p}periodo=?")
        params.append(periodo)
    if subrubro:
        clauses.append(f"{p}subrubro=?")
        params.append(garble(subrubro))
    if categoria:
        clauses.append(f"{p}categoria=?")
        params.append(garble(categoria))
    return " AND ".join(clauses), params


# ═══════════════════════════════════════════════════════════════════
# QUERIES PÚBLICAS
# ═══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def get_periodos(rubro_key: str) -> list[str]:
    return _q("SELECT DISTINCT periodo FROM publicaciones ORDER BY periodo DESC",
              (), rubro_key)["periodo"].tolist()


@st.cache_data(ttl=3600, show_spinner=False)
def get_cats(rubro_key: str, periodo: str) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo)
    df = _q(f"SELECT DISTINCT subrubro, categoria FROM publicaciones WHERE {w} ORDER BY subrubro, categoria",
            tuple(p), rubro_key)
    df["subrubro"]  = df["subrubro"].apply(ungarble)
    df["categoria"] = df["categoria"].apply(ungarble)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def kpis(rubro_key: str, periodo: str,
         subrubro: str | None = None, categoria: str | None = None) -> dict:
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    dm = _q(f"""SELECT SUM(gmv)                gmv_usd,
                       SUM(sold_quantity)       unidades,
                       COUNT(DISTINCT brand_name) marcas
               FROM marcas WHERE {w}""", tuple(p), rubro_key)
    dp = _q(f"""SELECT COUNT(DISTINCT item_id)  pubs,
                       COUNT(DISTINCT seller_id) vends,
                       AVG(CASE WHEN fulfillment='SI'    THEN 1.0 ELSE 0 END)*100 pct_full,
                       AVG(CASE WHEN free_shipping='SI'  THEN 1.0 ELSE 0 END)*100 pct_free,
                       AVG(CASE WHEN flex='SI'           THEN 1.0 ELSE 0 END)*100 pct_flex,
                       AVG(CASE WHEN catalog_listing='SI'THEN 1.0 ELSE 0 END)*100 pct_cat
               FROM publicaciones WHERE {w}""", tuple(p), rubro_key)
    return {
        "gmv":      float(dm["gmv_usd"].iloc[0]   or 0),
        "units":    int(  dm["unidades"].iloc[0]   or 0),
        "marcas":   int(  dm["marcas"].iloc[0]     or 0),
        "pubs":     int(  dp["pubs"].iloc[0]       or 0),
        "vends":    int(  dp["vends"].iloc[0]      or 0),
        "pct_full": float(dp["pct_full"].iloc[0]   or 0),
        "pct_free": float(dp["pct_free"].iloc[0]   or 0),
        "pct_flex": float(dp["pct_flex"].iloc[0]   or 0),
        "pct_cat":  float(dp["pct_cat"].iloc[0]    or 0),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def evolucion(rubro_key: str,
              subrubro: str | None = None, categoria: str | None = None) -> pd.DataFrame:
    w, p = _where(rubro_key, None, subrubro, categoria)
    return _q(f"""SELECT periodo, SUM(gmv) gmv_usd, SUM(sold_quantity) unidades
               FROM marcas WHERE {w} GROUP BY periodo ORDER BY periodo""",
              tuple(p), rubro_key)


@st.cache_data(ttl=3600, show_spinner=False)
def ticket_evolution(rubro_key: str,
                     subrubro: str | None = None, categoria: str | None = None) -> pd.DataFrame:
    w, p = _where(rubro_key, None, subrubro, categoria)
    return _q(f"""SELECT periodo,
                       SUM(gmv) / NULLIF(SUM(sold_quantity), 0) ticket_usd
               FROM marcas WHERE {w} GROUP BY periodo ORDER BY periodo""",
              tuple(p), rubro_key)


@st.cache_data(ttl=3600, show_spinner=False)
def top_marcas(rubro_key: str, periodo: str,
               subrubro: str | None = None, categoria: str | None = None,
               limit: int = 10) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    df = _q(f"""SELECT brand_name, SUM(gmv) gmv_usd, SUM(sold_quantity) unidades,
                       SUM(items_count) items
               FROM marcas WHERE {w}
               GROUP BY brand_name ORDER BY gmv_usd DESC LIMIT ?""",
            tuple(p + [limit]), rubro_key)
    df["brand_name"] = df["brand_name"].apply(ungarble)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def top_vends(rubro_key: str, periodo: str,
              subrubro: str | None = None, categoria: str | None = None,
              limit: int = 100) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    return _q(f"""SELECT seller_nickname, seller_type,
                       SUM(gmv) gmv_usd, SUM(sold_quantity) unidades
               FROM vendedores WHERE {w}
               GROUP BY seller_nickname ORDER BY gmv_usd DESC LIMIT ?""",
              tuple(p + [limit]), rubro_key)


@st.cache_data(ttl=3600, show_spinner=False)
def top_pubs(rubro_key: str, periodo: str,
             subrubro: str | None = None, categoria: str | None = None,
             limit: int = 100) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    df = _q(f"""SELECT title, brand, seller_nickname, categoria,
                       COALESCE(gmv, price * sold_quantity, 0) gmv_usd,
                       sold_quantity unidades, price,
                       fulfillment full_delivery, free_shipping, flex,
                       catalog_listing, url, picture
               FROM publicaciones WHERE {w}
               ORDER BY gmv_usd DESC LIMIT ?""",
            tuple(p + [limit]), rubro_key)
    df["categoria"] = df["categoria"].apply(ungarble)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def top_catalogo(rubro_key: str, periodo: str,
                 subrubro: str | None = None, categoria: str | None = None,
                 limit: int = 100) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    df = _q(f"""SELECT title, brand, model, gmv, sold_quantity unidades,
                       pub_con_ventas, vend_con_ventas, vend_profesionales, precio_promedio
               FROM catalogo WHERE {w} ORDER BY gmv DESC LIMIT ?""",
            tuple(p + [limit]), rubro_key)
    df["brand"] = df["brand"].apply(ungarble)
    df["title"] = df["title"].apply(ungarble)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def top_tiendas(rubro_key: str, periodo: str,
                subrubro: str | None = None, categoria: str | None = None,
                limit: int = 100) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    df = _q(f"""SELECT store_name,
                       SUM(gmv) gmv_usd, SUM(sold_quantity) unidades,
                       SUM(items_count) items, MAX(vend_profesionales) tipo
               FROM tiendas_oficiales WHERE {w}
               GROUP BY store_name ORDER BY gmv_usd DESC LIMIT ?""",
            tuple(p + [limit]), rubro_key)
    df["store_name"] = df["store_name"].apply(ungarble)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def top_modelos(rubro_key: str, periodo: str,
                subrubro: str | None = None, categoria: str | None = None,
                limit: int = 100) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    df = _q(f"""SELECT model_name, brand_name,
                       SUM(gmv) gmv_usd, SUM(sold_quantity) unidades,
                       SUM(items_count) items, MAX(precio_promedio) precio_promedio
               FROM modelos WHERE {w}
               GROUP BY model_name, brand_name ORDER BY gmv_usd DESC LIMIT ?""",
            tuple(p + [limit]), rubro_key)
    df["model_name"] = df["model_name"].apply(ungarble)
    df["brand_name"] = df["brand_name"].apply(ungarble)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def logistica_breakdown(rubro_key: str, periodo: str,
                        subrubro: str | None = None, categoria: str | None = None):
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    return _q(f"""SELECT
        SUM(CASE WHEN fulfillment='SI'                          THEN 1 ELSE 0 END) n_full,
        SUM(CASE WHEN flex='SI' AND fulfillment!='SI'           THEN 1 ELSE 0 END) n_flex,
        SUM(CASE WHEN fulfillment!='SI' AND flex!='SI'          THEN 1 ELSE 0 END) n_sin,
        SUM(CASE WHEN free_shipping='SI'                        THEN 1 ELSE 0 END) n_free,
        SUM(CASE WHEN free_shipping!='SI'                       THEN 1 ELSE 0 END) n_paid,
        COUNT(*) total
        FROM publicaciones WHERE {w}""", tuple(p), rubro_key).iloc[0]


@st.cache_data(ttl=3600, show_spinner=False)
def financiacion_breakdown(rubro_key: str, periodo: str,
                           subrubro: str | None = None, categoria: str | None = None) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo, subrubro, categoria)
    df = _q(f"""SELECT financiacion, SUM(gmv) gmv_usd, COUNT(*) items
               FROM publicaciones
               WHERE {w} AND financiacion IS NOT NULL AND financiacion != ''
               GROUP BY financiacion ORDER BY gmv_usd DESC""", tuple(p), rubro_key)
    df["financiacion"] = df["financiacion"].apply(ungarble)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def subrubro_breakdown(rubro_key: str, periodo: str) -> pd.DataFrame:
    w, p = _where(rubro_key, periodo)
    df = _q(f"""SELECT subrubro, SUM(gmv) gmv_usd
               FROM marcas WHERE {w}
               GROUP BY subrubro ORDER BY gmv_usd DESC""", tuple(p), rubro_key)
    df["subrubro"] = df["subrubro"].apply(ungarble)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def brand_share_evolution(rubro_key: str, periodo: str,
                          subrubro: str | None = None, categoria: str | None = None,
                          top_n: int = 5) -> pd.DataFrame:
    """
    Top N marcas del período seleccionado → su share de GMV en todos los períodos.
    Ideal para ver quién ganó y quién perdió terreno en el tiempo.
    """
    # 1. Obtener top N marcas del período actual (garbled, como están en DB)
    w_curr, p_curr = _where(rubro_key, periodo, subrubro, categoria)
    df_top = _q(f"""SELECT brand_name FROM marcas WHERE {w_curr}
                   GROUP BY brand_name ORDER BY SUM(gmv) DESC LIMIT ?""",
                tuple(p_curr + [top_n]), rubro_key)
    if df_top.empty:
        return pd.DataFrame()

    top_garbled = df_top["brand_name"].tolist()  # ya están garbled en DB

    # 2. Su GMV por período (toda la historia)
    w_all, p_all = _where(rubro_key, None, subrubro, categoria)
    placeholders = ",".join(["?" for _ in top_garbled])
    df_brands = _q(f"""SELECT periodo, brand_name, SUM(gmv) gmv_usd
                      FROM marcas WHERE {w_all} AND brand_name IN ({placeholders})
                      GROUP BY periodo, brand_name ORDER BY periodo""",
                   tuple(p_all + top_garbled), rubro_key)

    # 3. GMV total del mercado por período
    df_total = _q(f"""SELECT periodo, SUM(gmv) total_gmv
                     FROM marcas WHERE {w_all}
                     GROUP BY periodo ORDER BY periodo""",
                  tuple(p_all), rubro_key)

    if df_brands.empty or df_total.empty:
        return pd.DataFrame()

    df = df_brands.merge(df_total, on="periodo", how="left")
    df["share_pct"] = df["gmv_usd"] / df["total_gmv"].replace(0, None) * 100
    df["brand_name"] = df["brand_name"].apply(ungarble)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def generar_excel(rubro_key: str, periodo: str,
                  subrubro: str | None, categoria: str | None) -> bytes:
    """Excel de 6 hojas: Publicaciones, Catálogo, Vendedores, Tiendas, Marcas, Modelos."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df1 = top_pubs(rubro_key, periodo, subrubro, categoria, limit=100)
        df1.drop(columns=["picture", "url"], errors="ignore").to_excel(
            writer, sheet_name="Publicaciones", index=False)
        top_catalogo(rubro_key, periodo, subrubro, categoria).to_excel(
            writer, sheet_name="Catalogo", index=False)
        top_vends(rubro_key, periodo, subrubro, categoria).to_excel(
            writer, sheet_name="Vendedores", index=False)
        top_tiendas(rubro_key, periodo, subrubro, categoria).to_excel(
            writer, sheet_name="Tiendas Oficiales", index=False)
        top_marcas(rubro_key, periodo, subrubro, categoria, limit=100).to_excel(
            writer, sheet_name="Marcas", index=False)
        top_modelos(rubro_key, periodo, subrubro, categoria).to_excel(
            writer, sheet_name="Modelos", index=False)
    return output.getvalue()
