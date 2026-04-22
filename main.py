#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solarpotenzialanalyse Hamburger Hafen
"""
import webbrowser

import geopandas as gpd

from analyse import berechne_dachseiten_stats, berechne_parkplatz_stats
from config import OUTPUT_EXCEL, OUTPUT_HTML
from daten import lade_dachseiten, lade_hafengebiet, lade_parkplaetze
from karte import erstelle_karte
from utils import excel_dateiname, log

log("Starte Solarpotenzialanalyse Hafen")

# 1. Geodaten laden
hafen      = lade_hafengebiet()
dachseiten = lade_dachseiten(hafen)
parkplaetze = lade_parkplaetze(hafen)

# 2. Clip Dachseiten auf Hafengebiet
log("Clippe Dachseiten auf Hafengebiet...")
dachseiten_hafen = gpd.clip(dachseiten, hafen)
log(f"Dachseiten im Hafen: {len(dachseiten_hafen)}")

# 3. Statistiken
ds_stats = berechne_dachseiten_stats(dachseiten, dachseiten_hafen)
pp_stats = berechne_parkplatz_stats(parkplaetze)

# 4. Karte
log("Erstelle Karte...")
karte = erstelle_karte(hafen, dachseiten_hafen, ds_stats, pp_stats)
karte.save(OUTPUT_HTML)
webbrowser.open(OUTPUT_HTML)
log(f"Karte gespeichert: {OUTPUT_HTML}")

# 5. Excel-Export
log("Exportiere nach Excel...")
excel_file = excel_dateiname(OUTPUT_EXCEL)
dachseiten_hafen.drop(columns='geometry').to_excel(excel_file, index=False)
log(f"Excel gespeichert: {excel_file}")
