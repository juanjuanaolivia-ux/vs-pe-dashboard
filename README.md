# VS Analytics — Pequeños Electrodomésticos

Dashboard local-style estilo VirtualSeller Analytics, acotado a la categoría Pequeños Electrodomésticos de Mercado Libre Argentina.

**Stack:** Python + Streamlit + Plotly + SQLite
**Deploy:** Streamlit Cloud (gratis, sin tarjeta)

---

## 🚀 Deploy en Streamlit Cloud (5 min)

1. https://share.streamlit.io → Sign in with GitHub
2. New app → seleccionar este repo
3. Main file: `app.py`
4. Branch: `main`
5. Deploy
6. Listo, URL pública asignada automáticamente

---

## 🏠 Correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abre http://localhost:8501

---

## 📊 Estructura

| Archivo | Detalle |
|---|---|
| `app.py` | Single-file Streamlit app (~500 líneas) |
| `vs_pe.db.gz` | DB SQLite acotada a PE (~21 MB comprimida → 119 MB descomprimida en runtime) |
| `requirements.txt` | streamlit + pandas + plotly |

**DB cubre:**
- 64,144 publicaciones de Pequeños Electrodomésticos
- 51 categorías (41 Para Cocina + 10 Para Hogar)
- 17 períodos mensuales (2025-01 a 2026-05)
- Tablas: publicaciones, vendedores, marcas, modelos, tiendas_oficiales, catalogo

---

## 🎯 Filosofía

Versión simplificada y estable de un proyecto previo (FastAPI + HTML + JS) que tenía issues crónicos de estabilidad. Acá: 1 archivo Python, 1 DB acotada, hosting cloud gratuito con auto-restart.

**Cuando se valide PE:** replicar mismo template para otros rubros (Climatización, Cocción, etc) agregando filtros adicionales.
