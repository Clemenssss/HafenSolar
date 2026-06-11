#!/usr/bin/env python3
# -*- coding: utf-8 -*-

WFS_URL       = "https://geodienste.hamburg.de/wfs_solarpotenzialanalyse"
WFS_TYPENAME  = "de.hh.up:dachseiten"
CACHE_FILE    = "dachseiten_cache.gpkg"
HAFEN_ZIP     = "hafengebietsgrenzen_json.zip"
HAFEN_JSON    = "app_hafengebietsgrenzen_EPSG_25832.json"
OUTPUT_HTML   = "index.html"
OUTPUT_EXCEL  = "hafen_solar_dachseiten.xlsx"

HAMBURG_FLAECHE_KM2 = 755.2

# Solarschätzung Dachflächen
WP_PRO_M2    = 0.175   # kWp/m²
KWH_PRO_KWP  = 950     # kWh/kWp/a

# Solarschätzung Parkplätze
PARK_NUTZFAKTOR = 0.80  # 80% der Parkfläche nutzbar

FARBEN_DACHSEITEN = {
    1: '#d73027',
    2: '#f46d43',
    3: '#fdae61',
    6: '#fee090',
    0: '#e0e0e0',
    8: '#f0f0f0',
}

FARBE_PARKPLATZ      = "#4da6e8"
FARBE_PARKPLATZ_RAND = "#1a6faf"

# MaStR-Farben
FARBE_MASTR_BETRIEB = "#2ecc71"
FARBE_MASTR_STILL   = "#bdc3c7"
FARBE_MASTR_RAND    = "#1a7a3a"

# Brach-/Gewerbeflächen-Farben
FARBE_HALDE          = "#8d6e63"   # braun – Halden/Tagebau
FARBE_HALDE_RAND     = "#5d4037"
FARBE_GEWERBE_FREI   = "#9c27b0"   # lila – unbebaute Gewerbeflächen
FARBE_GEWERBE_RAND   = "#6a1b9a"
FARBE_BRACHE_OSM     = "#d32f2f"   # rot – OSM Brachflächen
FARBE_BRACHE_OSM_RAND= "#7f0000"