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
from flaechen import (lade_alkis_nutzung, lade_alkis_gebaeude,
                      extrahiere_halden_tagebau,
                      berechne_unbebaute_gewerbeflaechen,
                      lade_brachflaechen_osm)
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

# 3b. Brach- und ungenutzte Flächen
nutzung_hafen   = gpd.clip(lade_alkis_nutzung(hafen), hafen)
gebaeude_hafen  = gpd.clip(lade_alkis_gebaeude(hafen), hafen)
halden          = extrahiere_halden_tagebau(nutzung_hafen)
gewerbe_frei    = berechne_unbebaute_gewerbeflaechen(nutzung_hafen, gebaeude_hafen)
brache_osm      = lade_brachflaechen_osm(hafen)

# 4. Statistiken
ds_stats = berechne_dachseiten_stats(dachseiten, dachseiten_hafen)
pp_stats = berechne_parkplatz_stats(parkplaetze)

# 5. Karte
log("Erstelle Karte...")
karte = erstelle_karte(hafen, dachseiten_hafen, ds_stats, pp_stats,
                       mastr_anlagen=mastr_anlagen, mastr_hamburg=mastr_hamburg,
                       halden=halden, gewerbe_frei=gewerbe_frei, brache_osm=brache_osm)
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
    if halden is not None and not halden.empty:
        halden.drop(columns='geometry').to_excel(
            writer, sheet_name='Halden_Tagebau', index=False)
    if gewerbe_frei is not None and not gewerbe_frei.empty:
        gewerbe_frei.drop(columns='geometry').to_excel(
            writer, sheet_name='Unbebaute_Gewerbeflaechen', index=False)
    if brache_osm is not None and not brache_osm.empty:
        brache_osm.drop(columns='geometry').to_excel(
            writer, sheet_name='Brachflaechen_OSM', index=False)
log(f"Excel gespeichert: {excel_file}")