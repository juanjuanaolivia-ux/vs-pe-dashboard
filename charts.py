"""
VS Analytics — Figuras Plotly
================================
Todas las figuras del dashboard viven acá.
Reciben DataFrames y devuelven go.Figure.
Nada de st.plotly_chart acá — eso lo hace app.py.
"""

import plotly.graph_objects as go
import pandas as pd
from config import SPECIAL, COLORS, BRAND_PALETTE, FIN_COLORS, PLOTLY_BASE, GRID_COLOR, GRID_COLOR0

# Shorthand
_B = PLOTLY_BASE


# ═══════════════════════════════════════════════════════════════════
# EVOLUCIÓN (GMV + Unidades)
# ═══════════════════════════════════════════════════════════════════

def evolution_chart(df: pd.DataFrame, height: int = 300) -> go.Figure:
    """Barras GMV + línea Unidades, con períodos especiales en amarillo."""
    if df.empty:
        return go.Figure()

    bar_colors = [COLORS["yellow"] if p in SPECIAL else COLORS["accent"]
                  for p in df["periodo"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["periodo"], y=df["gmv_usd"],
        name="GMV (USD)",
        marker_color=bar_colors,
        opacity=0.9,
        hovertemplate="<b>%{x}</b><br>GMV: USD %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["periodo"], y=df["unidades"],
        name="Unidades",
        yaxis="y2",
        line=dict(color=COLORS["yellow"], width=2),
        mode="lines+markers",
        marker=dict(size=4, color=COLORS["yellow"]),
        hovertemplate="<b>%{x}</b><br>Uds: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        **_B,
        height=height,
        title=dict(text="Evolución Mensual", font=dict(size=11, color=COLORS["muted"]), x=0),
        yaxis=dict(title="GMV USD", tickformat=",.0f", gridcolor=GRID_COLOR, color=COLORS["muted"]),
        yaxis2=dict(title="Unidades", overlaying="y", side="right",
                    tickformat=",.0f", color=COLORS["muted"], gridcolor=GRID_COLOR0),
        legend=dict(orientation="h", y=1.18, x=0, font=dict(size=10)),
        bargap=0.25,
    )
    return fig


# ═══════════════════════════════════════════════════════════════════
# VARIACIÓN MoM
# ═══════════════════════════════════════════════════════════════════

def mom_chart(df: pd.DataFrame, height: int = 240) -> go.Figure:
    """Barras verde/rojo de variación MoM %."""
    if df.empty or len(df) < 2:
        return go.Figure()

    df2 = df.copy().reset_index(drop=True)
    df2["mom"] = df2["gmv_usd"].pct_change() * 100
    df2 = df2.dropna(subset=["mom"])
    if df2.empty:
        return go.Figure()

    colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in df2["mom"]]

    fig = go.Figure(go.Bar(
        x=df2["periodo"], y=df2["mom"],
        marker_color=colors,
        opacity=0.85,
        hovertemplate="<b>%{x}</b><br>MoM: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=GRID_COLOR, line_width=1)
    fig.update_layout(
        **_B,
        height=height,
        title=dict(text="Variación MoM (%)", font=dict(size=11, color=COLORS["muted"]), x=0),
        yaxis=dict(gridcolor=GRID_COLOR, color=COLORS["muted"], ticksuffix="%"),
        bargap=0.25,
        showlegend=False,
    )
    return fig


# ═══════════════════════════════════════════════════════════════════
# TICKET PROMEDIO
# ═══════════════════════════════════════════════════════════════════

def ticket_chart(df: pd.DataFrame, height: int = 240) -> go.Figure:
    """Área con evolución del ticket promedio."""
    if df.empty:
        return go.Figure()

    fig = go.Figure(go.Scatter(
        x=df["periodo"], y=df["ticket_usd"],
        line=dict(color=COLORS["accent"], width=2),
        mode="lines+markers",
        marker=dict(size=5, color=COLORS["accent"]),
        fill="tozeroy",
        fillcolor="rgba(124,106,247,0.08)",
        hovertemplate="<b>%{x}</b><br>Ticket: USD %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        **_B,
        height=height,
        title=dict(text="Ticket Promedio (USD)", font=dict(size=11, color=COLORS["muted"]), x=0),
        yaxis=dict(gridcolor=GRID_COLOR, color=COLORS["muted"], tickprefix="USD "),
        showlegend=False,
    )
    return fig


# ═══════════════════════════════════════════════════════════════════
# DONUT
# ═══════════════════════════════════════════════════════════════════

def donut_fig(labels: list, values: list, colors: list,
              height: int = 200) -> go.Figure:
    """Donut chart genérico."""
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.58,
        marker_colors=colors,
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        height=height,
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        font=dict(color=COLORS["text"] if "text" in COLORS else "#e2e8f0"),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════
# BRAND SHARE EVOLUTION (nuevo)
# ═══════════════════════════════════════════════════════════════════

def brand_share_chart(df: pd.DataFrame, height: int = 300) -> go.Figure:
    """
    Evolución del share de GMV % para las top N marcas del período seleccionado.
    Muestra quién ganó y quién perdió terreno en el tiempo.
    """
    if df.empty:
        return go.Figure()

    brands = df["brand_name"].unique()
    fig = go.Figure()

    for i, brand in enumerate(brands):
        df_b = df[df["brand_name"] == brand].sort_values("periodo")
        color = BRAND_PALETTE[i % len(BRAND_PALETTE)]
        fig.add_trace(go.Scatter(
            x=df_b["periodo"],
            y=df_b["share_pct"],
            name=brand,
            line=dict(color=color, width=2),
            mode="lines+markers",
            marker=dict(size=5, color=color),
            hovertemplate=f"<b>{brand}</b><br>%{{x}}<br>Share: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        **_B,
        height=height,
        title=dict(text="Evolución de Share — Top Marcas (%)", font=dict(size=11, color=COLORS["muted"]), x=0),
        yaxis=dict(gridcolor=GRID_COLOR, color=COLORS["muted"], ticksuffix="%"),
        legend=dict(orientation="h", y=1.18, x=0, font=dict(size=10)),
        bargap=0.25,
    )
    return fig
