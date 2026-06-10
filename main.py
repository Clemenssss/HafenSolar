#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solarpotenzialanalyse Hamburger Hafen
"""
import webbrowser
import pandas as pd
import geopandas as gpd

from analyse import berechne_dachseiten_stats, berechne_parkplatz_stats
from config import OUTPUT_EXCEL, OUTPUT_HTML
from daten import lade_dachseiten, lade_hafengebiet, lade_parkplaetze
from karte import erstelle_karte
from mastr import lade_mastr_anlagen
from utils import excel_dateiname, log

log("Starte Solarpotenzialanalyse Hafen")

# 1. Geodaten laden
hafen       = lade_hafengebiet()
dachseiten  = lade_dachseiten(hafen)
parkplaetze = lade_parkplaetze(hafen)

# 2. Clip Dachseiten auf Hafengebiet
log("Clippe Dachseiten auf Hafengebiet...")
dachseiten_hafen = gpd.clip(dachseiten, hafen)
log(f"Dachseiten im Hafen: {len(dachseiten_hafen)}")

# 3. MaStR-Anlagen laden
mastr_anlagen, mastr_hamburg = lade_mastr_anlagen(hafen)

# 4. Statistiken
ds_stats = berechne_dachseiten_stats(dachseiten, dachseiten_hafen)
pp_stats = berechne_parkplatz_stats(parkplaetze)

# 5. Karte
log("Erstelle Karte...")
karte = erstelle_karte(hafen, dachseiten_hafen, ds_stats, pp_stats,
                       mastr_anlagen=mastr_anlagen, mastr_hamburg=mastr_hamburg)
karte.save(OUTPUT_HTML)
webbrowser.open(OUTPUT_HTML)
log(f"Karte gespeichert: {OUTPUT_HTML}")

# 6. Excel-Export
log("Exportiere nach Excel...")
excel_file = excel_dateiname(OUTPUT_EXCEL)
with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    dachseiten_hafen.drop(columns='geometry').to_excel(
        writer, sheet_name='Dachseiten', index=False)
    if pp_stats:
        pp_stats["parkplaetze"].drop(columns='geometry').to_excel(
            writer, sheet_name='Parkplaetze', index=False)
    if mastr_anlagen is not None and not mastr_anlagen.empty:
        mastr_anlagen.drop(columns='geometry').to_excel(
            writer, sheet_name='MaStR_Anlagen', index=False)
log(f"Excel gespeichert: {excel_file}")