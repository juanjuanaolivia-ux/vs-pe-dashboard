"""
VS Analytics — App principal
==============================
Solo orchestration: sidebar -> datos -> componentes -> layout.
Nada de queries, CSS ni HTML generado aca.

Para agregar un rubro nuevo: editar config.py unicamente.
Para cambiar el diseno: editar style.css o components.py.
Para cambiar una query: editar data.py.
"""

from pathlib import Path
import streamlit as st

from config import RUBROS, SPECIAL, COLORS, FIN_COLORS, fmt_usd, fmt_num, delta_pct, yoy_periodo, prev_periodo
from data import (
    get_periodos, get_cats, kpis, evolucion, ticket_evolution,
    top_marcas, top_vends, top_pubs, top_catalogo, top_tiendas, top_modelos,
    logistica_breakdown, financiacion_breakdown, subrubro_breakdown,
    brand_share_evolution, generar_excel,
)
from components import (
    header_html, breadcrumb_html, insights_html, build_insights,
    kpi_grid_html, top_list_html, concentration_card_html, concentration_side_html,
    donut_legend_html, market_char_html, rank_table_html, footer_html,
    pub_rows_html, vend_rows_html, catalogo_rows_html,
    tiendas_rows_html, marcas_rows_html, modelos_rows_html,
)
from charts import evolution_chart, mom_chart, ticket_chart, donut_fig, brand_share_chart

# -- Config de pagina --
st.set_page_config(
    page_title="VS Analytics",
    page_icon="\U0001f4ca",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- CSS global (un solo archivo, cargado una vez) --
_css = (Path(__file__).parent / "style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("### \U0001f4ca VS Analytics")
    st.divider()

    # Rubro
    rubro_options = list(RUBROS.keys())
    if len(rubro_options) > 1:
        rubro_labels = {k: f"{v['icon']} {v['label']}" for k, v in RUBROS.items()}
        rubro_sel = st.selectbox(
            "\U0001f3f7\ufe0f Rubro",
            options=rubro_options,
            format_func=lambda k: rubro_labels[k],
        )
    else:
        rubro_sel = rubro_options[0]

    rubro_cfg = RUBROS[rubro_sel]

    # Periodo
    periodos = get_periodos(rubro_sel)
    if not periodos:
        st.error("Sin datos. Verifica el archivo .db.gz")
        st.stop()

    default_idx = 1 if len(periodos) > 1 else 0
    periodo = st.selectbox("\U0001f4c5 Periodo", periodos, index=default_idx)

    # Comparar vs.
    mom_per = prev_periodo(periodo)
    yoy_per = yoy_periodo(periodo)
    comp_map = {}
    if mom_per in periodos:
        comp_map["Mes anterior (MoM)"] = mom_per
    if yoy_per in periodos:
        comp_map["Anio anterior (YoY)"] = yoy_per

    if comp_map:
        comp_label_sel = st.selectbox("\U0001f4ca Comparar vs.", list(comp_map.keys()))
        comp_periodo = comp_map[comp_label_sel]
        comp_label = comp_label_sel.split("(")[1].rstrip(")")
    else:
        comp_periodo = None
        comp_label = ""

    st.divider()

    # Filtros
    st.markdown("### \U0001f3db Filtros")
    cats_df = get_cats(rubro_sel, periodo)
    subs = ["Todos"] + sorted(cats_df["subrubro"].dropna().unique().tolist())
    sub_sel = st.selectbox("\U0001f4c2 Subrubro", subs)
    sub_f = None if sub_sel == "Todos" else sub_sel

    if sub_f:
        cats = cats_df[cats_df["subrubro"] == sub_f]["categoria"].dropna().sort_values().tolist()
    else:
        cats = cats_df["categoria"].dropna().sort_values().tolist()

    cat_sel = st.selectbox(f"\U0001f4e6 Categoria ({len(cats)})", ["Todas"] + cats)
    cat_f = None if cat_sel == "Todas" else cat_sel

    st.divider()
    st.caption(f"Periodo: **{periodo}**")
    if comp_periodo:
        st.caption(f"Comparando vs: **{comp_periodo}**")
    if SPECIAL.get(periodo):
        st.caption(f"\u26a0\ufe0f **{SPECIAL[periodo]}**")
    st.caption(f"Periodos disponibles: **{len(periodos)}**")
    st.caption(f"{periodos[-1]} -> {periodos[0]}")

    if st.button("\U0001f504 Limpiar cache"):
        st.cache_data.clear()
        st.rerun()

# =============================================================================
# CARGA DE DATOS
# =============================================================================

kpis_curr = kpis(rubro_sel, periodo, sub_f, cat_f)
kpis_prev = kpis(rubro_sel, comp_periodo, sub_f, cat_f) if comp_periodo else None

df_evo = evolucion(rubro_sel, sub_f, cat_f)
df_m5  = top_marcas(rubro_sel, periodo, sub_f, cat_f, limit=5)
df_v5  = top_vends(rubro_sel, periodo, sub_f, cat_f, limit=5)
df_m10 = top_marcas(rubro_sel, periodo, sub_f, cat_f, limit=10)
df_v15 = top_vends(rubro_sel, periodo, sub_f, cat_f, limit=15)

scope = sub_sel if sub_sel != "Todos" else rubro_cfg["short"]
if cat_sel != "Todas":
    scope += f" > {cat_sel}"

# =============================================================================
# HEADER + INSIGHTS + KPIs
# =============================================================================

st.markdown(header_html(rubro_cfg["label"], scope, periodo), unsafe_allow_html=True)
st.markdown(breadcrumb_html(rubro_cfg["label"], sub_sel, cat_sel), unsafe_allow_html=True)

_insights = build_insights(kpis_curr, kpis_prev, df_m5, df_v5, df_evo, periodo, comp_label)
st.markdown(insights_html(_insights), unsafe_allow_html=True)

st.markdown(kpi_grid_html(kpis_curr, kpis_prev, comp_label), unsafe_allow_html=True)
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

# =============================================================================
# TABS PRINCIPALES
# =============================================================================

tab_analisis, tab_ranking, tab_tendencias = st.tabs([
    "\U0001f4ca Analisis", "\U0001f3c6 Ranking", "\U0001f4c8 Tendencias"
])

# =============================================================================
# TAB: ANALISIS
# =============================================================================

with tab_analisis:

    col_chart, col_marcas = st.columns([3, 1], gap="small")
    with col_chart:
        st.plotly_chart(evolution_chart(df_evo), use_container_width=True,
                        config={"displayModeBar": False})
    with col_marcas:
        st.markdown(top_list_html(df_m10, "brand_name", "gmv_usd", "Top Marcas", "GMV"),
                    unsafe_allow_html=True)

    log    = logistica_breakdown(rubro_sel, periodo, sub_f, cat_f)
    df_fin = financiacion_breakdown(rubro_sel, periodo, sub_f, cat_f)
    df_sub = subrubro_breakdown(rubro_sel, periodo)

    total_log  = int(log["total"] or 1)
    SUB_COLORS = [COLORS["accent"], COLORS["accent2"], COLORS["purple"],
                  COLORS["yellow"], COLORS["muted"]]

    col_d1, col_d2, col_d3, col_d4 = st.columns(4, gap="small")

    with col_d1:
        st.plotly_chart(donut_fig(
            ["Full", "Flex", "Sin Full"],
            [int(log["n_full"]), int(log["n_flex"]), int(log["n_sin"])],
            [COLORS["accent"], COLORS["accent2"], COLORS["border"]],
        ), use_container_width=True, config={"displayModeBar": False})
        st.markdown(donut_legend_html("Logistica", [
            ("Full",     log["n_full"], COLORS["accent"],  total_log),
            ("Flex",     log["n_flex"], COLORS["accent2"], total_log),
            ("Sin Full", log["n_sin"],  "#94a3b8",         total_log),
        ]), unsafe_allow_html=True)

    with col_d2:
        st.plotly_chart(donut_fig(
            ["Gratis", "Con Costo"],
            [int(log["n_free"]), int(log["n_paid"])],
            [COLORS["green"], COLORS["red"]],
        ), use_container_width=True, config={"displayModeBar": False})
        st.markdown(donut_legend_html("Envio Gratis", [
            ("Gratis",    log["n_free"], COLORS["green"], total_log),
            ("Con Costo", log["n_paid"], COLORS["red"],   total_log),
        ]), unsafe_allow_html=True)

    with col_d3:
        if not df_fin.empty:
            tot_fin  = df_fin["gmv_usd"].sum()
            fin_cols = [FIN_COLORS.get(r, "#6b7a99") for r in df_fin["financiacion"]]
            st.plotly_chart(donut_fig(
                df_fin["financiacion"].tolist(),
                df_fin["gmv_usd"].tolist(),
                fin_cols,
            ), use_container_width=True, config={"displayModeBar": False})
            st.markdown(donut_legend_html("Financiacion", [
                (row["financiacion"], row["gmv_usd"],
                 FIN_COLORS.get(row["financiacion"], "#6b7a99"), tot_fin)
                for _, row in df_fin.iterrows()
            ]), unsafe_allow_html=True)

    with col_d4:
        if not df_sub.empty:
            tot_sub = df_sub["gmv_usd"].sum()
            st.plotly_chart(donut_fig(
                df_sub["subrubro"].tolist(),
                df_sub["gmv_usd"].tolist(),
                SUB_COLORS[:len(df_sub)],
            ), use_container_width=True, config={"displayModeBar": False})
            st.markdown(donut_legend_html("Por Subrubro", [
                (row["subrubro"], row["gmv_usd"], SUB_COLORS[i % len(SUB_COLORS)], tot_sub)
                for i, row in df_sub.iterrows()
            ]), unsafe_allow_html=True)

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    col_conc, col_char = st.columns(2, gap="small")

    with col_conc:
        st.markdown(concentration_card_html(
            df_v15, "gmv_usd", "seller_nickname", "Concentracion Vendedores"
        ), unsafe_allow_html=True)

    with col_char:
        yoy_d   = None
        yoy_lbl = str(int(periodo[:4]) - 1)
        if len(df_evo) >= 12:
            yoy_p = f"{int(periodo[:4])-1}-{periodo[5:7]}"
            row_y = df_evo[df_evo["periodo"] == yoy_p]
            if not row_y.empty:
                yoy_d = delta_pct(kpis_curr["gmv"], row_y["gmv_usd"].iloc[0])

        best      = df_evo.loc[df_evo["gmv_usd"].idxmax()] if not df_evo.empty else None
        cat_count = len(cats_df["categoria"].unique()) if not cats_df.empty else 0

        st.markdown(market_char_html(
            ticket       = kpis_curr["gmv"] / max(kpis_curr["units"], 1),
            yoy_delta    = yoy_d,
            yoy_label    = yoy_lbl,
            best_periodo = best["periodo"] if best is not None else "---",
            best_gmv     = best["gmv_usd"] if best is not None else 0,
            cat_count    = cat_count,
            pct_cat      = kpis_curr["pct_cat"],
        ), unsafe_allow_html=True)

# =============================================================================
# TAB: RANKING
# =============================================================================

with tab_ranking:

    col_tb1, col_tb2 = st.columns([2, 1], gap="small")
    with col_tb2:
        excel_bytes = generar_excel(rubro_sel, periodo, sub_f, cat_f)
        fname = (f"VS_{rubro_cfg['short']}_{periodo}_{sub_sel}_{cat_sel}.xlsx"
                 .replace(" ", "_").replace("/", "-"))
        st.download_button(
            label="\u2b07 Descargar Excel - 6 hojas",
            data=excel_bytes, file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    rtab1, rtab2, rtab3, rtab4, rtab5, rtab6 = st.tabs([
        "\U0001f4e6 Publicaciones", "\U0001f4cb Catalogo", "\U0001f3ea Vendedores",
        "\U0001f3ec Tiendas", "\U0001f3f7\ufe0f Marcas", "\U0001f527 Modelos",
    ])

    TBL_FOOTER = lambda n, lbl: f'<div style="padding:8px 14px;font-size:10px;color:var(--text-muted)">Top {n} {lbl} - {periodo}</div>'

    with rtab1:
        df_pub = top_pubs(rubro_sel, periodo, sub_f, cat_f, limit=100)
        if df_pub.empty:
            st.warning("Sin datos para esta seleccion.")
        else:
            st.markdown(rank_table_html(
                pub_rows_html(df_pub),
                [{"label":"#"},{"label":""},{"label":"Producto / Vendedor"},
                 {"label":"GMV USD","cls":"num"},{"label":"% Mdo.","cls":"num"},
                 {"label":"Uds.","cls":"num"},{"label":"Precio","cls":"num"},{"label":"Log."}],
                TBL_FOOTER(len(df_pub), "publicaciones"),
            ), unsafe_allow_html=True)

    with rtab2:
        df_cat = top_catalogo(rubro_sel, periodo, sub_f, cat_f, limit=100)
        if df_cat.empty:
            st.warning("Sin datos de catalogo.")
        else:
            col_tbl, col_side = st.columns([3, 1], gap="small")
            with col_tbl:
                st.markdown(rank_table_html(
                    catalogo_rows_html(df_cat),
                    [{"label":"#"},{"label":"Producto / Marca - Modelo"},
                     {"label":"GMV USD","cls":"num"},{"label":"% Mdo.","cls":"num"},
                     {"label":"Uds.","cls":"num"},{"label":"Pubs.","cls":"num"},
                     {"label":"Vends.","cls":"num"},{"label":"P.Prom.","cls":"num"}],
                    TBL_FOOTER(len(df_cat), "productos de catalogo"),
                ), unsafe_allow_html=True)
            with col_side:
                st.markdown(concentration_side_html(df_cat, "gmv", "title", "Lider catalogo"),
                            unsafe_allow_html=True)

    with rtab3:
        df_vbig = top_vends(rubro_sel, periodo, sub_f, cat_f, limit=100)
        if df_vbig.empty:
            st.warning("Sin datos de vendedores.")
        else:
            col_tbl, col_side = st.columns([2, 1], gap="small")
            with col_tbl:
                st.markdown(rank_table_html(
                    vend_rows_html(df_vbig),
                    [{"label":"#"},{"label":"Vendedor"},
                     {"label":"GMV USD","cls":"num"},{"label":"% Mdo.","cls":"num"},
                     {"label":"Uds.","cls":"num"},{"label":"Share"}],
                    TBL_FOOTER(len(df_vbig), "vendedores"),
                ), unsafe_allow_html=True)
            with col_side:
                st.markdown(concentration_side_html(df_vbig, "gmv_usd", "seller_nickname"),
                            unsafe_allow_html=True)

    with rtab4:
        df_tiendas = top_tiendas(rubro_sel, periodo, sub_f, cat_f, limit=100)
        if df_tiendas.empty:
            st.warning("Sin datos de tiendas oficiales.")
        else:
            col_tbl, col_side = st.columns([2, 1], gap="small")
            with col_tbl:
                st.markdown(rank_table_html(
                    tiendas_rows_html(df_tiendas),
                    [{"label":"#"},{"label":"Tienda Oficial"},
                     {"label":"GMV USD","cls":"num"},{"label":"% Mdo.","cls":"num"},
                     {"label":"Uds.","cls":"num"},{"label":"Items","cls":"num"},{"label":"Share"}],
                    TBL_FOOTER(len(df_tiendas), "tiendas oficiales"),
                ), unsafe_allow_html=True)
            with col_side:
                st.markdown(concentration_side_html(df_tiendas, "gmv_usd", "store_name"),
                            unsafe_allow_html=True)

    with rtab5:
        df_mbig = top_marcas(rubro_sel, periodo, sub_f, cat_f, limit=100)
        if df_mbig.empty:
            st.warning("Sin datos de marcas.")
        else:
            col_tbl, col_side = st.columns([2, 1], gap="small")
            with col_tbl:
                st.markdown(rank_table_html(
                    marcas_rows_html(df_mbig),
                    [{"label":"#"},{"label":"Marca"},
                     {"label":"GMV USD","cls":"num"},{"label":"% Mdo.","cls":"num"},
                     {"label":"Uds.","cls":"num"},{"label":"Items","cls":"num"},{"label":"Share"}],
                    TBL_FOOTER(len(df_mbig), "marcas"),
                ), unsafe_allow_html=True)
            with col_side:
                st.markdown(concentration_side_html(df_mbig, "gmv_usd", "brand_name"),
                            unsafe_allow_html=True)

    with rtab6:
        df_mod = top_modelos(rubro_sel, periodo, sub_f, cat_f, limit=100)
        if df_mod.empty:
            st.warning("Sin datos de modelos.")
        else:
            col_tbl, col_side = st.columns([2, 1], gap="small")
            with col_tbl:
                st.markdown(rank_table_html(
                    modelos_rows_html(df_mod),
                    [{"label":"#"},{"label":"Modelo"},{"label":"Marca"},
                     {"label":"GMV USD","cls":"num"},{"label":"% Mdo.","cls":"num"},
                     {"label":"Uds.","cls":"num"},{"label":"P.Prom.","cls":"num"},{"label":"Share"}],
                    TBL_FOOTER(len(df_mod), "modelos"),
                ), unsafe_allow_html=True)
            with col_side:
                st.markdown(concentration_side_html(df_mod, "gmv_usd", "model_name"),
                            unsafe_allow_html=True)

# =============================================================================
# TAB: TENDENCIAS
# =============================================================================

with tab_tendencias:

    col_t1, col_t2 = st.columns(2, gap="small")
    with col_t1:
        st.plotly_chart(evolution_chart(df_evo, height=300),
                        use_container_width=True, config={"displayModeBar": False})
    with col_t2:
        if not df_evo.empty:
            best  = df_evo.loc[df_evo["gmv_usd"].idxmax()]
            worst = df_evo.loc[df_evo["gmv_usd"].idxmin()]
            st.markdown(f"""
<div class="vs-card">
  <div class="vs-card-title">Estadisticas - {len(df_evo)} meses</div>
  <div class="char-grid">
    <div class="char-stat"><div class="char-val" style="font-size:15px">{fmt_usd(best["gmv_usd"])}</div><div class="char-lbl">Mejor mes</div><div class="char-sub">{best["periodo"]}</div></div>
    <div class="char-stat"><div class="char-val" style="font-size:15px">{fmt_usd(worst["gmv_usd"])}</div><div class="char-lbl">Peor mes</div><div class="char-sub">{worst["periodo"]}</div></div>
    <div class="char-stat"><div class="char-val" style="font-size:15px">{fmt_usd(df_evo["gmv_usd"].mean())}</div><div class="char-lbl">GMV Promedio</div></div>
    <div class="char-stat"><div class="char-val" style="font-size:15px">{fmt_num(int(df_evo["unidades"].mean()))}</div><div class="char-lbl">Uds. Promedio</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    col_t3, col_t4 = st.columns(2, gap="small")
    with col_t3:
        st.plotly_chart(mom_chart(df_evo), use_container_width=True,
                        config={"displayModeBar": False})
    with col_t4:
        df_tick = ticket_evolution(rubro_sel, sub_f, cat_f)
        st.plotly_chart(ticket_chart(df_tick), use_container_width=True,
                        config={"displayModeBar": False})

    st.markdown("---")
    df_share = brand_share_evolution(rubro_sel, periodo, sub_f, cat_f, top_n=5)
    if not df_share.empty:
        st.plotly_chart(brand_share_chart(df_share, height=320),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            '<div style="font-size:10px;color:var(--text-muted);margin-top:-8px">' +
            'Top 5 marcas del periodo seleccionado - evolucion de share de GMV % sobre el mercado total.' +
            '</div>',
            unsafe_allow_html=True,
        )

# =============================================================================
# FOOTER
# =============================================================================

st.markdown(footer_html(
    rubro_label   = rubro_cfg["label"],
    n_periodos    = len(periodos),
    periodo_desde = periodos[-1],
    periodo_hasta = periodos[0],
), unsafe_allow_html=True)
