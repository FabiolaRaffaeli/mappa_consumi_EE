# -*- coding: utf-8 -*-
#"""
#Created on Fri Dec  5 15:39:12 2025

#@author: RaffaeliFabiola(AU)
#"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Mappa Energia Italia",
    layout="wide",
)

# --------------------------------------------------------
# 1. Sidebar: Input file
# --------------------------------------------------------
st.sidebar.header("Impostazioni Dati")

# --- Upload manuale CSV ---
uploaded_csv = st.sidebar.file_uploader(
    "Carica file CSV",
    type=["csv"],
)

# --- GeoJSON con nome file ---
file_geojson = st.sidebar.text_input(
    "File GeoJSON regioni",
    value="italy_regions.geojson",
)

# --------------------------------------------------------
# 2. Caricamento CSV
# --------------------------------------------------------
@st.cache_data
def carica_dati(file):
    df = pd.read_csv(file, sep=';', decimal=',')

    # Controllo colonne obbligatorie
    colonne_richieste = ["regione", "potenza_imp", "tariffa", "residenza", "energia_tot"]
    mancanti = [c for c in colonne_richieste if c not in df.columns]
    if mancanti:
        raise ValueError(f"Colonne mancanti nel CSV: {mancanti}")

    # Pulizia stringhe
    for col in ["regione", "potenza_imp", "tariffa", "residenza"]:
        df[col] = df[col].astype(str).str.strip()

    # Uniformazione nomi regione
    df["regione"] = df["regione"].str.title()

    # Energia → numerico
    df["energia_tot"] = pd.to_numeric(df["energia_tot"], errors="coerce").fillna(0)

    # Rimuove righe senza regione
    df = df.dropna(subset=["regione"])

    return df


# Se non c’è file, fermiamo l’app
if uploaded_csv is None:
    st.warning("Carica un file CSV per continuare.")
    st.stop()

# Carica CSV
try:
    with st.spinner("Caricamento CSV..."):
        df = carica_dati(uploaded_csv)
except Exception as e:
    st.error(str(e))
    st.stop()

# --------------------------------------------------------
# 3. Caricamento GeoJSON (da file locale)
# --------------------------------------------------------
@st.cache_data
def carica_geojson(file_geojson: str):
    path = Path(file_geojson)
    if not path.exists():
        raise FileNotFoundError(f"File GeoJSON '{file_geojson}' non trovato.")

    with open(path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    return geojson


try:
    with st.spinner("Caricamento GeoJSON..."):
        geojson = carica_geojson(file_geojson)
except Exception as e:
    st.error(str(e))
    st.stop()

# --------------------------------------------------------
# 4. Filtri dinamici
# --------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Filtri")

# Potenza
potenza_options = sorted(df["potenza_imp"].unique())
potenza_imp_filter = st.sidebar.selectbox("Potenza Imp.", potenza_options)

# Tariffa
tariffa_options = sorted(df[df["potenza_imp"] == potenza_imp_filter]["tariffa"].unique())
if not tariffa_options:
    st.warning("Nessuna tariffa trovata per la potenza selezionata.")
    st.stop()

tariffa_filter = st.sidebar.selectbox("Tariffa", tariffa_options)

# Residenza
residenza_options = sorted(
    df[(df["potenza_imp"] == potenza_imp_filter) &
       (df["tariffa"] == tariffa_filter)]["residenza"].unique()
)

if not residenza_options:
    st.warning("Nessuna residenza trovata per i filtri attuali.")
    st.stop()

residenza_filter = st.sidebar.selectbox("Residenza", residenza_options)

# --------------------------------------------------------
# 5. Funzione filtro
# --------------------------------------------------------
@st.cache_data
def filtra_dati(df, potenza, tariffa, residenza):
    df_filtered = df[
        (df["potenza_imp"] == potenza) &
        (df["tariffa"] == tariffa) &
        (df["residenza"] == residenza)
    ]

    df_region = (
        df_filtered.groupby("regione")["energia_tot"]
        .sum()
        .reset_index()
    )

    totale = df_filtered["energia_tot"].sum()

    return df_region, totale


df_region, totale_energia = filtra_dati(df, potenza_imp_filter, tariffa_filter, residenza_filter)

# --------------------------------------------------------
# 6. Output numerico
# --------------------------------------------------------
st.header("Consumi energetici filtrati")

col1, col2 = st.columns(2)
col1.metric("Energia totale (kWh)", f"{totale_energia:,.2f}")
col2.write(" ")

# --------------------------------------------------------
# 7. Mappa Plotly
# --------------------------------------------------------
st.subheader("Mappa dei consumi per regione")

fig = px.choropleth_mapbox(
    df_region,
    geojson=geojson,
    locations="regione",
    featureidkey="properties.reg_name",
    color="energia_tot",
    color_continuous_scale="Reds",
    mapbox_style="carto-positron",
    center={"lat": 42.5, "lon": 12.5},
    zoom=4.5,
    hover_data={"regione": True, "energia_tot": ":,.2f"},
)

fig.update_layout(
    margin=dict(r=0, t=0, l=0, b=0),
    coloraxis_colorbar=dict(title="Energia (kWh)"),
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------
# Fine
# --------------------------------------------------------



