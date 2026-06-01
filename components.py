"""
VS Analytics — Componentes HTML
================================
Builders puros que reciben datos y devuelven HTML strings.
Nada de lógica de negocio ni queries acá.

Para cambiar el look de un componente: lo tocás acá y el cambio aplica en toda la app.
"""

import html as _html
import pandas as pd
from config import SPECIAL, COLORS, fmt_usd, fmt_num, fmt_pct, delta_pct


def esc(s) -> str:
    return _html.escape(str(s or ""))


# ═══════════════════════════════════════════════════════════════════
# HEADER Y NAV
# ═══════════════════════════════════════════════════════════════════

def header_html(rubro_label: str, scope: str, periodo: str) -> str:
    special = SPECIAL.get(periodo, "")
    period_txt = f"{periodo}{' · ' + special if special else ''}"
    return f"""
<div class="vs-header">
  <div class="vs-icon">📊</div>
  <div>
    <div class="vs-brand-name">VS Analytics</div>
    <div class="vs-brand-sub">{esc(rubro_label)} · MLA</div>
  </div>
  <span class="vs-scope">{esc(scope)}</span>
  <span class="vs-period">📅 {esc(period_txt)}</span>
</div>"""


def breadcrumb_html(rubro_label: str, sub_sel: str, cat_sel: str) -> str:
    return f"""
<div class="vs-bc">
  <span>{esc(rubro_label)}</span>
  <span class="bc-sep">›</span>
  <span>{esc(sub_sel)}</span>
  <span class="bc-sep">›</span>
  <span class="bc-active">{esc(cat_sel)}</span>
</div>"""


# ═══════════════════════════════════════════════════════════════════
# INSIGHTS BAR
# ═══════════════════════════════════════════════════════════════════

def insights_html(insights: list[tuple[str, str]]) -> str:
    """insights: lista de (emoji, html_text)"""
    items = "".join(
        f'<div class="insight-item">'
        f'<span class="insight-icon">{ico}</span>'
        f'<span class="insight-text">{txt}</span>'
        f'</div>'
        for ico, txt in insights
    )
    return f'<div class="insights-panel">{items}</div>'


def build_insights(kpis_curr: dict, kpis_prev: dict | None,
                   df_marcas5: pd.DataFrame, df_vends5: pd.DataFrame,
                   df_evo: pd.DataFrame, periodo: str,
                   comp_label: str = "MoM") -> list[tuple[str, str]]:
    """Computa la lista de insights a partir de los datos."""
    insights = []

    # GMV vs período comparado
    if kpis_prev and kpis_prev["gmv"]:
        d = delta_pct(kpis_curr["gmv"], kpis_prev["gmv"])
        if d is not None:
            ico = "📈" if d > 0 else "📉"
            insights.append((ico, f'<strong>GMV {d:+.1f}% {comp_label}</strong> — '
                                   f'{fmt_usd(kpis_prev["gmv"])} → {fmt_usd(kpis_curr["gmv"])}'))

    # Top 3 marcas
    if not df_marcas5.empty:
        tot = df_marcas5["gmv_usd"].sum()
        top3_gmv = df_marcas5.head(3)["gmv_usd"].sum()
        top3_names = ", ".join(df_marcas5.head(3)["brand_name"].tolist())
        insights.append(("🏆", f'<strong>Top 3 marcas: {top3_gmv/tot*100:.1f}%</strong> del mercado '
                                f'— <em>{esc(top3_names)}</em>'))

    # Logística
    insights.append(("📦", f'<strong>{kpis_curr["pct_full"]:.1f}% con Envío Full</strong> '
                            f'· {kpis_curr["pct_free"]:.1f}% Envío Gratis'))

    # Líder vendedor
    if not df_vends5.empty:
        tot_v = df_vends5["gmv_usd"].sum()
        lider = df_vends5.iloc[0]
        if tot_v > 0:
            insights.append(("🏪", f'<strong>Líder: {esc(lider["seller_nickname"])}</strong> '
                                    f'— {lider["gmv_usd"]/tot_v*100:.1f}% del top 5'))

    # YoY
    if len(df_evo) >= 12:
        yoy_per = f"{int(periodo[:4])-1}-{periodo[5:7]}"
        row_yoy = df_evo[df_evo["periodo"] == yoy_per]
        if not row_yoy.empty:
            d = delta_pct(kpis_curr["gmv"], row_yoy["gmv_usd"].iloc[0])
            if d is not None:
                ico = "📈" if d > 0 else "📉"
                insights.append((ico, f'<strong>YoY {d:+.1f}%</strong> vs {yoy_per}'))

    return insights


# ═══════════════════════════════════════════════════════════════════
# KPI CARDS
# ═══════════════════════════════════════════════════════════════════

def _delta_html(d: float | None, label: str = "") -> str:
    if d is None:
        return f'<span class="kpi-ne">— {label}</span>'
    cls = "kpi-up" if d > 0 else "kpi-dn"
    ico = "▲" if d > 0 else "▼"
    lbl = f" {label}" if label else ""
    return f'<span class="{cls}">{ico} {abs(d):.1f}%{lbl}</span>'


def kpi_card_html(label: str, value: str,
                  delta: float | None, comp_label: str = "") -> str:
    return f"""
<div class="kpi-card">
  <div class="kpi-lbl">{esc(label)}</div>
  <div class="kpi-val">{value}</div>
  {_delta_html(delta, comp_label)}
</div>"""


def kpi_grid_html(kpis_curr: dict, kpis_prev: dict | None,
                  comp_label: str = "MoM") -> str:
    """Construye las 2 filas de 4 KPI cards."""
    ticket = kpis_curr["gmv"] / max(kpis_curr["units"], 1)
    ticket_p = (kpis_prev["gmv"] / max(kpis_prev["units"], 1)
                if kpis_prev and kpis_prev["units"] else None)

    def d(curr, prev):
        return delta_pct(curr, prev) if prev else None

    prev = kpis_prev or {}
    cards_r1 = [
        kpi_card_html("GMV (USD)",       fmt_usd(kpis_curr["gmv"]),   d(kpis_curr["gmv"],   prev.get("gmv")),   comp_label),
        kpi_card_html("Unidades",        fmt_num(kpis_curr["units"]),  d(kpis_curr["units"], prev.get("units")), comp_label),
        kpi_card_html("Ticket Promedio", fmt_usd(ticket),              d(ticket, ticket_p),                      comp_label),
        kpi_card_html("Publicaciones",   fmt_num(kpis_curr["pubs"]),   d(kpis_curr["pubs"],  prev.get("pubs")),  comp_label),
    ]
    cards_r2 = [
        kpi_card_html("Vendedores",      fmt_num(kpis_curr["vends"]),  d(kpis_curr["vends"], prev.get("vends")), comp_label),
        kpi_card_html("Marcas activas",  fmt_num(kpis_curr["marcas"]), None, ""),
        kpi_card_html("% Envío Full",    fmt_pct(kpis_curr["pct_full"]), None, ""),
        kpi_card_html("% Envío Gratis",  fmt_pct(kpis_curr["pct_free"]), None, ""),
    ]
    r1 = "".join(cards_r1)
    r2 = "".join(cards_r2)
    return f'<div class="kpi-grid">{r1}</div><div class="kpi-grid" style="margin-top:8px">{r2}</div>'


# ═══════════════════════════════════════════════════════════════════
# TOP LISTS (Marcas, Vendedores)
# ═══════════════════════════════════════════════════════════════════

def top_list_html(df: pd.DataFrame, label_col: str, value_col: str,
                  title: str, sub_label: str = "GMV") -> str:
    if df.empty:
        return ""
    total = df[value_col].sum()
    rows = ""
    for i, row in df.iterrows():
        pct = row[value_col] / total * 100 if total else 0
        rows += f"""
<div class="top-row">
  <span class="top-n">{i+1}</span>
  <span class="top-name">{esc(row[label_col])}</span>
  <span class="top-bar-w"><div class="top-bar-bg"><div class="top-bar" style="width:{pct:.1f}%"></div></div></span>
  <span class="top-pct">{pct:.1f}%</span>
  <span class="top-gmv">{fmt_usd(row[value_col])}</span>
</div>"""
    return f"""
<div class="vs-card">
  <div class="vs-card-title">{esc(title)} <span style="font-weight:400;color:var(--text-muted)">{esc(sub_label)}</span></div>
  {rows}
</div>"""


# ═══════════════════════════════════════════════════════════════════
# CONCENTRACIÓN
# ═══════════════════════════════════════════════════════════════════

def concentration_card_html(df: pd.DataFrame, value_col: str,
                             label_col: str, title: str,
                             max_rows: int = 8) -> str:
    if df.empty:
        return ""
    total = df[value_col].sum()
    t3  = df.head(3)[value_col].sum()
    t5  = df.head(5)[value_col].sum()
    t10 = df.head(10)[value_col].sum()
    lider = df.iloc[0]

    rows = ""
    for i, row in df.head(max_rows).iterrows():
        pct = row[value_col] / total * 100 if total else 0
        tipo = ""
        if "seller_type" in row and row.get("seller_type"):
            tipo = f'<span style="font-size:9px;background:rgba(124,106,247,.12);color:#7c6af7;border-radius:4px;padding:1px 5px">{esc(row["seller_type"])}</span>'
        rows += f"""
<div class="top-row">
  <span class="top-n">{i+1}</span>
  <span class="top-name">{esc(row[label_col])} {tipo}</span>
  <span class="top-bar-w"><div class="top-bar-bg"><div class="top-bar" style="width:{pct:.1f}%"></div></div></span>
  <span class="top-pct">{pct:.1f}%</span>
  <span class="top-gmv">{fmt_usd(row[value_col])}</span>
</div>"""

    footer = f"""
<div class="conc-footer">
  <div class="conc-foot-item"><div class="conc-foot-val">{t3/total*100:.1f}%</div><div class="conc-foot-lbl">Top 3</div></div>
  <div class="conc-foot-item"><div class="conc-foot-val">{t5/total*100:.1f}%</div><div class="conc-foot-lbl">Top 5</div></div>
  <div class="conc-foot-item"><div class="conc-foot-val">{t10/total*100:.1f}%</div><div class="conc-foot-lbl">Top 10</div></div>
</div>"""

    return f"""
<div class="vs-card">
  <div class="vs-card-title">{esc(title)}</div>
  {rows}
  {footer}
</div>"""


# ═══════════════════════════════════════════════════════════════════
# DONUT LEGEND
# ═══════════════════════════════════════════════════════════════════

def donut_legend_html(title: str, items: list[tuple[str, float, str, float]]) -> str:
    """items: (nombre, valor, color, total)"""
    rows = ""
    for name, val, color, total in items:
        pct = val / total * 100 if total else 0
        rows += f"""
<div class="dleg-row">
  <span class="dleg-dot" style="background:{color}"></span>
  <span class="dleg-name">{esc(name)}</span>
  <span class="dleg-pct">{pct:.1f}%</span>
</div>"""
    return f'<div class="donut-card"><div class="donut-title">{esc(title)}</div><div class="dleg">{rows}</div></div>'


# ═══════════════════════════════════════════════════════════════════
# CARACTERÍSTICAS DEL MERCADO
# ═══════════════════════════════════════════════════════════════════

def market_char_html(ticket: float, yoy_delta: float | None, yoy_label: str,
                     best_periodo: str, best_gmv: float,
                     cat_count: int, pct_cat: float) -> str:
    if yoy_delta is None:
        yoy_txt = "—"
    else:
        cls = "kpi-up" if yoy_delta > 0 else "kpi-dn"
        yoy_txt = f'<span class="{cls}">{yoy_delta:+.1f}%</span>'

    return f"""
<div class="vs-card">
  <div class="vs-card-title">Características del Mercado</div>
  <div class="char-grid">
    <div class="char-stat">
      <div class="char-val" style="font-size:16px">{fmt_usd(ticket)}</div>
      <div class="char-lbl">Ticket Promedio</div>
    </div>
    <div class="char-stat">
      <div class="char-val" style="font-size:16px">{yoy_txt}</div>
      <div class="char-lbl">YoY vs {esc(yoy_label)}</div>
    </div>
    <div class="char-stat">
      <div class="char-val" style="font-size:14px">{esc(best_periodo)}</div>
      <div class="char-lbl">Mejor mes</div>
      <div class="char-sub">{fmt_usd(best_gmv)}</div>
    </div>
    <div class="char-stat">
      <div class="char-val" style="font-size:20px">{cat_count}</div>
      <div class="char-lbl">Categorías activas</div>
      <div class="char-sub">{fmt_pct(pct_cat)} en catálogo</div>
    </div>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════════
# RANK TABLES (Rankings tab)
# ═══════════════════════════════════════════════════════════════════

def rank_table_html(rows_html: str, headers: list[dict], footer: str = "") -> str:
    th = "".join(
        f'<th class="{h.get("cls","")}">{h["label"]}</th>'
        for h in headers
    )
    return f"""
<div class="vs-card" style="padding:0;overflow:hidden">
  <div class="tbl-wrap">
    <table class="rank-tbl">
      <thead><tr>{th}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
  {footer}
</div>"""


def _rb(i: int) -> str:
    cls = "rb-g" if i == 0 else "rb-s" if i == 1 else "rb-b" if i == 2 else ""
    return f'<span class="rb {cls}">{i+1}</span>'


def pub_rows_html(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    total = df["gmv_usd"].sum()
    rows = ""
    for i, row in df.iterrows():
        thumb = (f'<img class="thumb" src="{esc(row["picture"])}" onerror="this.style.display=\'none\'">'
                 if row.get("picture") else '<span class="thumb-ph">📦</span>')
        pills = ""
        if row.get("full_delivery") == "SI": pills += '<span class="pill p-full">Full</span>'
        if row.get("free_shipping")  == "SI": pills += '<span class="pill p-free">Free</span>'
        if row.get("flex")           == "SI": pills += '<span class="pill p-flex">Flex</span>'
        if row.get("catalog_listing")== "SI": pills += '<span class="pill p-cat">Cat.</span>'
        title_txt = str(row["title"] or "")
        title_disp = esc(title_txt[:70]) + ("…" if len(title_txt) > 70 else "")
        title_html = (f'<a href="{esc(row["url"])}" target="_blank" '
                      f'style="color:var(--text);text-decoration:none">{title_disp}</a>'
                      if row.get("url") else title_disp)
        ms = f'{row["gmv_usd"]/total*100:.1f}%' if total else "—"
        rows += f"""<tr>
<td>{_rb(i)}</td>
<td>{thumb}</td>
<td style="max-width:300px"><span class="t-title">{title_html}</span><span class="t-sub">{esc(row.get("brand",""))} · {esc(row.get("seller_nickname",""))}</span></td>
<td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv_usd"])}</td>
<td class="num">{ms}</td>
<td class="num">{fmt_num(row["unidades"])}</td>
<td class="num">{fmt_usd(row["price"])}</td>
<td>{pills}</td>
</tr>"""
    return rows


def vend_rows_html(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    total = df["gmv_usd"].sum()
    rows = ""
    for i, row in df.iterrows():
        pct = row["gmv_usd"] / total * 100 if total else 0
        tipo = (f'<span style="font-size:9px;background:rgba(124,106,247,.12);'
                f'color:#7c6af7;border-radius:4px;padding:1px 5px">{esc(row.get("seller_type",""))}</span>'
                if row.get("seller_type") else "")
        rows += f"""<tr>
<td>{_rb(i)}</td>
<td style="font-weight:600">{esc(row["seller_nickname"])} {tipo}</td>
<td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv_usd"])}</td>
<td class="num" style="color:var(--accent);font-weight:600">{pct:.1f}%</td>
<td class="num">{fmt_num(row["unidades"])}</td>
<td style="min-width:90px"><div class="top-bar-bg"><div class="top-bar" style="width:{min(pct,100):.1f}%"></div></div></td>
</tr>"""
    return rows


def catalogo_rows_html(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    total = df["gmv"].sum()
    rows = ""
    for i, row in df.iterrows():
        ms = f'{row["gmv"]/total*100:.1f}%' if total else "—"
        rows += f"""<tr>
<td>{_rb(i)}</td>
<td style="max-width:280px"><span class="t-title">{esc(str(row["title"])[:65])}</span><span class="t-sub">{esc(row.get("brand",""))} {esc(row.get("model",""))}</span></td>
<td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv"])}</td>
<td class="num">{ms}</td>
<td class="num">{fmt_num(row["unidades"])}</td>
<td class="num">{fmt_num(row.get("pub_con_ventas"))}</td>
<td class="num">{fmt_num(row.get("vend_con_ventas"))}</td>
<td class="num">{fmt_usd(row.get("precio_promedio"))}</td>
</tr>"""
    return rows


def tiendas_rows_html(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    total = df["gmv_usd"].sum()
    rows = ""
    for i, row in df.iterrows():
        pct = row["gmv_usd"] / total * 100 if total else 0
        rows += f"""<tr>
<td>{_rb(i)}</td>
<td style="font-weight:600;color:var(--text)">{esc(row["store_name"])}</td>
<td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv_usd"])}</td>
<td class="num" style="color:var(--accent);font-weight:600">{pct:.1f}%</td>
<td class="num">{fmt_num(row["unidades"])}</td>
<td class="num">{fmt_num(row.get("items"))}</td>
<td style="min-width:90px"><div class="top-bar-bg"><div class="top-bar" style="width:{min(pct,100):.1f}%"></div></div></td>
</tr>"""
    return rows


def marcas_rows_html(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    total = df["gmv_usd"].sum()
    rows = ""
    for i, row in df.iterrows():
        pct = row["gmv_usd"] / total * 100 if total else 0
        rows += f"""<tr>
<td>{_rb(i)}</td>
<td style="font-weight:600;color:var(--text)">{esc(row["brand_name"])}</td>
<td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv_usd"])}</td>
<td class="num" style="color:var(--accent);font-weight:600">{pct:.1f}%</td>
<td class="num">{fmt_num(row["unidades"])}</td>
<td class="num">{fmt_num(row.get("items"))}</td>
<td style="min-width:90px"><div class="top-bar-bg"><div class="top-bar" style="width:{min(pct,100):.1f}%"></div></div></td>
</tr>"""
    return rows


def modelos_rows_html(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    total = df["gmv_usd"].sum()
    rows = ""
    for i, row in df.iterrows():
        pct = row["gmv_usd"] / total * 100 if total else 0
        rows += f"""<tr>
<td>{_rb(i)}</td>
<td style="font-weight:600;color:var(--text)">{esc(row["model_name"])}</td>
<td style="color:var(--text-muted);font-size:10px">{esc(row["brand_name"])}</td>
<td class="num" style="font-weight:600;color:var(--text)">{fmt_usd(row["gmv_usd"])}</td>
<td class="num" style="color:var(--accent);font-weight:600">{pct:.1f}%</td>
<td class="num">{fmt_num(row["unidades"])}</td>
<td class="num">{fmt_usd(row.get("precio_promedio"))}</td>
<td style="min-width:90px"><div class="top-bar-bg"><div class="top-bar" style="width:{min(pct,100):.1f}%"></div></div></td>
</tr>"""
    return rows


def concentration_side_html(df: pd.DataFrame, value_col: str,
                             label_col: str, lider_label: str = "Líder") -> str:
    """Card lateral de concentración para usar junto a una tabla."""
    if df.empty:
        return ""
    total = df[value_col].sum()
    t3  = df.head(3)[value_col].sum()
    t5  = df.head(5)[value_col].sum()
    t10 = df.head(10)[value_col].sum()
    lider = df.iloc[0]
    return f"""
<div class="vs-card">
  <div class="vs-card-title">Concentración</div>
  <div class="conc-row"><span class="conc-lbl">Top 3</span><span class="conc-val">{t3/total*100:.1f}%</span></div>
  <div class="conc-row"><span class="conc-lbl">Top 5</span><span class="conc-val">{t5/total*100:.1f}%</span></div>
  <div class="conc-row"><span class="conc-lbl">Top 10</span><span class="conc-val">{t10/total*100:.1f}%</span></div>
  <div class="conc-row" style="margin-top:8px">
    <span class="conc-lbl">{lider_label}</span>
    <span style="font-size:11px;font-weight:600;color:var(--text)">{esc(str(lider[label_col])[:28])}</span>
  </div>
  <div class="conc-row">
    <span class="conc-lbl">GMV</span>
    <span class="conc-val">{fmt_usd(lider[value_col])}</span>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════

def footer_html(rubro_label: str, n_periodos: int,
                periodo_desde: str, periodo_hasta: str) -> str:
    return f"""
<div class="vs-footer">
  <span>📊 VS Analytics — {esc(rubro_label)} · MLA</span>
  <span>{n_periodos} períodos · {esc(periodo_desde)} → {esc(periodo_hasta)}</span>
  <span>v4.0</span>
</div>"""
