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
    1: '#d73027',   # rot       – sehr hohe Einstrahlung
    2: '#f46d43',   # orange-rot
    3: '#fdae61',   # orange
    6: '#fee090',   # gelb
    0: '#e0e0e0',   # grau      – Datenqualität unzureichend
    8: '#f0f0f0',   # hellgrau  – kein Gebäude erkannt
}

FARBE_PARKPLATZ      = "#4da6e8"
FARBE_PARKPLATZ_RAND = "#1a6faf"
# Diese drei Zeilen in config.py ergänzen (z.B. nach FARBE_PARKPLATZ_RAND):

FARBE_MASTR_BETRIEB = "#2ecc71"  # grün  – In Betrieb
FARBE_MASTR_STILL = "#bdc3c7"  # grau  – stillgelegt / sonstige
FARBE_MASTR_RAND = "#1a7a3a"  # dunkelgrün – Kreisrand