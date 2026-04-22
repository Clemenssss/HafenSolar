#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solarpotenzialanalyse Hamburger Hafen – WFS-Version
Daten direkt vom WFS Solarpotenzialflächen Hamburg
"""

import geopandas as gpd
import folium
import webbrowser
import requests
import locale
from datetime import datetime
import os
# -------------------------------
# Deutsches Zahlenformat
# -------------------------------
try:
    locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'German_Germany.1252')
    except:
        locale.setlocale(locale.LC_ALL, '')

def fmt_zahl(zahl, stellen=0):
    if zahl is None:
        return 'k.A.'
    if stellen == 0:
        return locale.format_string("%d", int(round(zahl)), grouping=True)
    return locale.format_string(f"%.{stellen}f", zahl, grouping=True)

def ts():
    return datetime.now().strftime("[%H:%M:%S]")

def log(msg):
    print(f"{ts()} {msg}")

# -------------------------------
# Hauptprogramm
# -------------------------------
log("Starte Solarpotenzialanalyse Hafen")

# 1. Hafengebiet laden
log("Lade Hafengebiet...")
hafen = gpd.read_file("zip://hafengebietsgrenzen_json.zip!app_hafengebietsgrenzen_EPSG_25832.json")
hafen = hafen.set_crs(25832, allow_override=True)
log(f"Hafengebiet geladen: {len(hafen)} Polygon(e)")

# BBOX des Hafengebiets für WFS-Filter
bounds = hafen.total_bounds  # (minx, miny, maxx, maxy) in EPSG:25832
bbox_str = f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]},urn:ogc:def:crs:EPSG::25832"
log(f"BBOX: {bounds}")

# 2. WFS-Abfrage: Dachseiten im Hafengebiet
WFS_URL = "https://geodienste.hamburg.de/wfs_solarpotenzialanalyse"

def wfs_get(typename, bbox):
    params = {
        "SERVICE": "WFS",
        "VERSION": "1.1.0",
        "REQUEST": "GetFeature",
        "typename": typename,
        "BBOX": bbox,
    }
    log(f"Rufe WFS ab: {typename} ...")
    r = requests.get(WFS_URL, params=params, timeout=120)
    r.raise_for_status()
    import io
    return gpd.read_file(io.BytesIO(r.content))
def excel_dateiname(basis="hafen_solar_dachseiten.xlsx"):
    if not os.path.exists(basis):
        return basis
    name, ext = os.path.splitext(basis)
    i = 1
    while os.path.exists(f"{name} ({i}){ext}"):
        i += 1
    return f"{name} ({i}){ext}"
try:
    CACHE_FILE = "dachseiten_cache.gpkg"

    if os.path.exists(CACHE_FILE):
        log(f"Lade aus Cache: {CACHE_FILE}")
        dachseiten = gpd.read_file(CACHE_FILE)
    else:
        dachseiten = wfs_get("de.hh.up:dachseiten", bbox_str)
        log(f"Dachseiten geladen: {fmt_zahl(len(dachseiten))}")
        log("Speichere Cache...")
        dachseiten.to_file(CACHE_FILE, driver="GPKG")
        log("Cache gespeichert.")
except Exception as e:
    log(f"Fehler beim WFS-Abruf: {e}")
    exit(1)

if len(dachseiten) == 0:
    log("Keine Dachseiten im Hafengebiet gefunden.")
    exit(0)

# CRS sicherstellen
if dachseiten.crs is None:
    dachseiten = dachseiten.set_crs(25832)
elif dachseiten.crs.to_epsg() != 25832:
    dachseiten = dachseiten.to_crs(25832)
# Geometrien bereinigen
log("Bereinige Geometrien...")
dachseiten.geometry = dachseiten.geometry.buffer(0)
hafen.geometry = hafen.geometry.buffer(0)
# Gesamtwerte vor Clip
# hier schon definieren
def col(gdf, *candidates):
    """Ersten gefundenen Spaltennamen zurückgeben."""
    for c in candidates:
        for col in gdf.columns:
            if col.lower() == c.lower():
                return col
    return None
col_pv   = col(dachseiten, 'pvarea')
col_ert  = col(dachseiten, 'ertkwha_k')
col_eig  = col(dachseiten, 'eignung')

pv_summe_ges     = dachseiten[col_pv].sum()  if col_pv  else None
ertrag_summe_ges = dachseiten[col_ert].sum() if col_ert else None
leistung_mwp_ges = (pv_summe_ges * 0.175 / 1000)    if pv_summe_ges else None
ertrag_gwh_ges   = (ertrag_summe_ges / 1_000_000)    if ertrag_summe_ges else None
# 3. Räumlicher Clip auf Hafengebiet
log("Clippe auf Hafengebiet...")
dachseiten_hafen = gpd.clip(dachseiten, hafen)
log(f"Dachseiten nach Clip: {fmt_zahl(len(dachseiten_hafen))}")

# 4. Spalten ausgeben (zur Orientierung)
log(f"Verfügbare Spalten: {list(dachseiten_hafen.columns)}")

# 5. Statistiken (Spaltennamen ggf. anpassen nach erstem Lauf)
# Typische Spalten laut Metadaten: Flaeche_PV, Ertrag_ohneAufstd, Eignung_PV


FARBEN_DACHSEITEN = {
    1: '#d73027',  # rot       – sehr hohe Einstrahlung
    2: '#f46d43',  # orange-rot
    3: '#fdae61',  # orange
    6: '#fee090',  # gelb
    0: '#e0e0e0',  # grau      – Datenqualität unzureichend
    8: '#f0f0f0',  # hellgrau  – kein Gebäude
}
pv_summe     = dachseiten_hafen[col_pv].sum()  if col_pv  else None
ertrag_summe = dachseiten_hafen[col_ert].sum() if col_ert else None
leistung_mwp = (pv_summe * 0.175 / 1000)       if pv_summe else None
ertrag_gwh   = (ertrag_summe / 1_000_000)       if ertrag_summe else None

log(f"PV-Fläche gesamt:  {fmt_zahl(pv_summe)} m²")
log(f"Ertrag gesamt:     {fmt_zahl(ertrag_summe)} kWh/a")
log(f"Leistung (ca.):    {fmt_zahl(leistung_mwp, 1)} MWp")
log(f"Ertrag (ca.):      {fmt_zahl(ertrag_gwh, 1)} GWh/a")

# 6. Karte
log("Erstelle Karte...")
centroid = hafen.geometry.centroid.to_crs(4326)
center = [centroid.y.mean(), centroid.x.mean()]

hafen_wgs      = hafen.to_crs(4326)
dachseiten_wgs = dachseiten_hafen.to_crs(4326)

m = folium.Map(location=center, zoom_start=14, tiles='CartoDB positron')

folium.GeoJson(
    hafen_wgs,
    name="Hafengrenze",
    style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.05}
).add_to(m)

# Einfärbung nach Eignung (1=grün … 8=rot) falls Spalte vorhanden
def farbe_dachseite(feature):
    v = feature['properties'].get('eignung', '')
    try:
        # "Eignung 1 (geeignet, sehr hohe Einstrahlung)" → 1
        v = int(str(v).split()[1])
    except:
        v = 0
    return {
        "color": FARBEN_DACHSEITEN.get(v, '#cccccc'),
        "weight": 0.5,
        "fillOpacity": 0.8
    }

folium.GeoJson(
    dachseiten_wgs,
    name=f"Dachseiten ({fmt_zahl(len(dachseiten_wgs))})",
    style_function=farbe_dachseite,
    tooltip=folium.GeoJsonTooltip(
        fields=['area','aspect','aufstd','buildingid','eignung','eignung_t',
                'ertkwp_k','ertkwp_ka','ertkwha_k','ertkwha_ka',
                'percentms','percentmsa','power','pvarea','pvareat',
                'roofid','schatten','schattena','slope'],
        aliases=['Fläche Dachseite [m²]','Ausrichtung [°]','Aufständerung [0/1]',
                 'ID Gebäude','Eignung PV','Eignung Solarthermie',
                 'Ertrag [kWh/kWp/a] ohne Aufstd','Ertrag [kWh/kWp/a] mit Aufstd',
                 'Ertrag [kWh/a] ohne Aufstd','Ertrag [kWh/a] mit Aufstd',
                 'Einstrahlung ohne Aufstd [%]','Einstrahlung mit Aufstd [%]',
                 'Power [kWp]','Fläche PV [m²]','Fläche ST [m²]',
                 'ID Dachseite','Schatten ohne Aufstd [%/a]','Schatten mit Aufstd [%/a]',
                 'Neigung [°]'],
        localize=True,
        sticky=True
    )
).add_to(m)
# für die legende
hafen_flaeche_km2 = hafen.geometry.area.sum() / 1_000_000
hamburg_flaeche_km2 = 755.2
legend_html = f'''
<div style="position:fixed;bottom:30px;left:30px;background:white;padding:12px 16px;
            border-radius:8px;box-shadow:2px 2px 6px grey;font-size:13px;z-index:1000;
            font-family:Arial,sans-serif;min-width:280px;">
    <b style="font-size:14px;">☀️ Solarpotenzial Hamburger Hafen</b><br><br>
    🏠 Dachseiten: <b>{fmt_zahl(len(dachseiten_hafen))}</b> (Hamburg: {fmt_zahl(len(dachseiten))})<br>
    📐 PV-Fläche: <b>{fmt_zahl(pv_summe)} m²</b> (Hamburg: {fmt_zahl(pv_summe_ges)} m²)<br>
    ⚡ Leistung (ca.): <b>{fmt_zahl(leistung_mwp, 1)} MWp</b> (Hamburg: {fmt_zahl(leistung_mwp_ges, 1)} MWp)<br>
    🔋 Ertrag (ca.): <b>{fmt_zahl(ertrag_gwh, 1)} GWh/Jahr</b> (Hamburg: {fmt_zahl(ertrag_gwh_ges, 1)} GWh/Jahr)<br>
    📏 Hafengebiet: <b>{fmt_zahl(hafen_flaeche_km2, 1)} km²</b> (Hamburg: {fmt_zahl(hamburg_flaeche_km2, 1)} km²)<br>
    <hr style="margin:8px 0;">
    <b>Eignung Photovoltaik</b><br>
    <span style="background:{FARBEN_DACHSEITEN[1]};padding:1px 10px;margin-right:6px;">&nbsp;</span>Eignung 1 – sehr hohe Einstrahlung<br>
    <span style="background:{FARBEN_DACHSEITEN[2]};padding:1px 10px;margin-right:6px;">&nbsp;</span>Eignung 2 – hohe Einstrahlung<br>
    <span style="background:{FARBEN_DACHSEITEN[3]};padding:1px 10px;margin-right:6px;">&nbsp;</span>Eignung 3 – mittlere Einstrahlung<br>
    <span style="background:{FARBEN_DACHSEITEN[6]};padding:1px 10px;margin-right:6px;">&nbsp;</span>Eignung 6 – geringe Einstrahlung<br>
    <span style="background:{FARBEN_DACHSEITEN[0]};padding:1px 10px;margin-right:6px;border:1px solid #ccc;">&nbsp;</span>Eignung 0 – Datenqualität unzureichend<br>
    <span style="background:{FARBEN_DACHSEITEN[8]};padding:1px 10px;margin-right:6px;border:1px solid #ccc;">&nbsp;</span>Eignung 8 – kein Gebäude erkannt<br>
    <hr style="margin:8px 0;">
    <span style="font-size:11px;color:grey;">Quelle: WFS Solarpotenzialflächen Hamburg, LGV</span>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl().add_to(m)
log("Exportiere nach Excel...")
excel_file = excel_dateiname()
dachseiten_hafen.drop(columns='geometry').to_excel(excel_file, index=False)
log(f"Excel gespeichert: {excel_file}")
out_file = "index.html"
m.save(out_file)
webbrowser.open(out_file)
log(f"Karte gespeichert: {out_file}")