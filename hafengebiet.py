#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solarpotenzialanalyse Hamburger Hafen
Modularisierte Version mit deutscher Zahlenformatierung
"""

import os
import glob
import zipfile
import tempfile
import webbrowser
import geopandas as gpd
import folium
from shapely.geometry import Polygon

# ============================================================
# 1. HILFSFUNKTIONEN
# ============================================================
def zahl_format(zahl, stellen=0):
    """
    Formatiert Zahlen im deutschen Stil:
    Tausender-Punkt, Dezimal-Komma.
    Beispiel: 1234567.89 -> "1.234.567,89"
    """
    if stellen == 0:
        return f"{int(round(zahl)):,}".replace(",", ".")
    else:
        format_str = f"{{:,.{stellen}f}}"
        return format_str.format(zahl).replace(",", "X").replace(".", ",").replace("X", ".")

def finde_solar_zip(verzeichnis="."):
    """Sucht automatisch nach der Solarpotenzial-ZIP-Datei."""
    # Bekannte mögliche Namen
    kandidaten = [
        "solarpotenzialanalyse_json.zip",
        "Solarpotenzialflächen_Hamburg_GeoJSON.zip",
        "*solar*.zip"
    ]
    for pattern in kandidaten:
        treffer = glob.glob(os.path.join(verzeichnis, pattern))
        if treffer:
            return treffer[0]
    return None

# ============================================================
# 2. LADEN DER DATEN
# ============================================================
def lade_hafengebiet(pfad_zip="hafengebietsgrenzen_json.zip",
                     datei_in_zip="app_hafengebietsgrenzen_EPSG_25832.json"):
    """
    Lädt das Hafengebiet aus der ZIP-Datei.
    Gibt GeoDataFrame im CRS EPSG:25832 zurück.
    """
    voller_pfad = f"zip://{pfad_zip}!{datei_in_zip}"
    hafen = gpd.read_file(voller_pfad)
    hafen = hafen.set_crs(25832, allow_override=True)
    print(f"✅ Hafengebiet geladen: {len(hafen)} Polygon(e)")
    return hafen

def lade_solar_daten(zip_pfad):
    """
    Entpackt die Solar-ZIP temporär und lädt:
    - Gebäude (EPSG:25832 und EPSG:4326)
    - Dachseiten (falls vorhanden)
    Gibt ein Dictionary mit den DataFrames zurück.
    """
    ergebnis = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_pfad, 'r') as zf:
            zf.extractall(tmpdir)
            dateiliste = zf.namelist()
            print(f"📦 {zip_pfad} enthält {len(dateiliste)} Dateien")

        # Alle JSON-Dateien sammeln
        alle_json = []
        for root, dirs, files in os.walk(tmpdir):
            for f in files:
                if f.endswith('.json'):
                    alle_json.append(os.path.join(root, f))

        # Gebäude mit 25832
        gdf_geb = None
        gdf_geb_wgs = None
        gdf_dach = None
        gdf_dach_wgs = None

        for pfad in alle_json:
            name = os.path.basename(pfad)
            if 'gebaeude' in name.lower():
                if '25832' in pfad:
                    gdf_geb = gpd.read_file(pfad)
                    print(f"   Gebäude (25832): {len(gdf_geb):,} Objekte")
                elif '4326' in pfad:
                    gdf_geb_wgs = gpd.read_file(pfad)
                    print(f"   Gebäude (4326): {len(gdf_geb_wgs):,} Objekte")
            elif 'dachseiten' in name.lower():
                if '25832' in pfad:
                    gdf_dach = gpd.read_file(pfad)
                    print(f"   Dachseiten (25832): {len(gdf_dach):,} Objekte")
                elif '4326' in pfad:
                    gdf_dach_wgs = gpd.read_file(pfad)
                    print(f"   Dachseiten (4326): {len(gdf_dach_wgs):,} Objekte")

        # Falls WGS84-Version fehlt, konvertieren
        if gdf_geb is not None and gdf_geb_wgs is None:
            gdf_geb_wgs = gdf_geb.to_crs(4326)
            print("   → Gebäude nach WGS84 konvertiert")
        if gdf_dach is not None and gdf_dach_wgs is None:
            gdf_dach_wgs = gdf_dach.to_crs(4326)
            print("   → Dachseiten nach WGS84 konvertiert")

        ergebnis['gebaeude'] = gdf_geb
        ergebnis['gebaeude_wgs'] = gdf_geb_wgs
        ergebnis['dachseiten'] = gdf_dach
        ergebnis['dachseiten_wgs'] = gdf_dach_wgs

    return ergebnis

# ============================================================
# 3. ANALYSE (VERSCHNEIDUNG)
# ============================================================
def verschneide_mit_hafen(gdf, hafen_gdf, name="Objekte"):
    """Schneidet einen GeoDataFrame mit dem Hafengebiet."""
    if gdf is None or len(gdf) == 0:
        print(f"⚠️  {name}: Keine Daten zum Verschneiden")
        return None
    if gdf.crs != hafen_gdf.crs:
        gdf = gdf.to_crs(hafen_gdf.crs)
    ergebnis = gpd.overlay(gdf, hafen_gdf, how='intersection')
    print(f"✂️  {name} im Hafen: {len(ergebnis):,}")
    return ergebnis

def berechne_statistiken(geb_im_hafen, dach_im_hafen):
    """Erstellt eine übersichtliche Statistik mit deutschen Zahlen."""
    print("\n" + "="*70)
    print("📊  STATISTIK – SOLARPOTENZIAL IM HAMBURGER HAFEN")
    print("="*70)

    if geb_im_hafen is not None and len(geb_im_hafen) > 0:
        anz_geb = len(geb_im_hafen)
        if 'shape_area' in geb_im_hafen.columns:
            flaeche_geb = geb_im_hafen['shape_area'].sum()
            print(f"🏢 Gebäude mit Potenzial : {zahl_format(anz_geb)} Stück")
            print(f"📐 Grundfläche gesamt    : {zahl_format(flaeche_geb)} m²  ({zahl_format(flaeche_geb/10000, 2)} ha)")
        else:
            print(f"🏢 Gebäude mit Potenzial : {zahl_format(anz_geb)} Stück")
    else:
        print("🏢 Keine Gebäude mit Solarpotenzial im Hafengebiet gefunden.")

    if dach_im_hafen is not None and len(dach_im_hafen) > 0:
        anz_dach = len(dach_im_hafen)
        if 'shape_area' in dach_im_hafen.columns:
            flaeche_dach = dach_im_hafen['shape_area'].sum()
            print(f"\n🏠 Dachseiten (detailliert): {zahl_format(anz_dach)} Stück")
            print(f"📐 Dachfläche gesamt       : {zahl_format(flaeche_dach)} m²  ({zahl_format(flaeche_dach/10000, 2)} ha)")
        else:
            print(f"\n🏠 Dachseiten (detailliert): {zahl_format(anz_dach)} Stück")
    else:
        print("\n🏠 Keine Dachseiten-Daten im Hafengebiet.")

    print("="*70)

# ============================================================
# 4. KARTE ERSTELLEN
# ============================================================
def erstelle_karte(hafen_wgs, geb_im_hafen_wgs, dach_im_hafen_wgs, zentrum=None):
    """
    Erstellt eine interaktive Folium-Karte mit Layern.
    """
    if zentrum is None:
        # Zentrum aus Hafengeometrie berechnen
        centroid = hafen_wgs.geometry.centroid
        zentrum = [centroid.y.mean(), centroid.x.mean()]

    m = folium.Map(location=zentrum, zoom_start=13, tiles='CartoDB positron')

    # 1. Hafengrenze (blau, transparent)
    folium.GeoJson(
        hafen_wgs,
        name="Hafengebiet",
        style_function=lambda x: {"fillColor": "blue", "color": "black", "weight": 2, "fillOpacity": 0.1}
    ).add_to(m)

    # 2. Gebäude im Hafen (orange)
    if geb_im_hafen_wgs is not None and len(geb_im_hafen_wgs) > 0:
        # Tooltip nur, wenn 'shape_area' vorhanden
        if 'shape_area' in geb_im_hafen_wgs.columns:
            tooltip = folium.GeoJsonTooltip(
                fields=['shape_area'],
                aliases=['Fläche m²:'],
                localize=True,
                style="background-color: white; font-size: 12px;"
            )
        else:
            tooltip = None

        folium.GeoJson(
            geb_im_hafen_wgs,
            name=f"Solar-Gebäude im Hafen ({len(geb_im_hafen_wgs):,})",
            style_function=lambda x: {"fillColor": "orange", "color": "red", "weight": 1, "fillOpacity": 0.6},
            tooltip=tooltip
        ).add_to(m)

    # 3. Dachseiten im Hafen (grün)
    if dach_im_hafen_wgs is not None and len(dach_im_hafen_wgs) > 0:
        # Verfügbare Felder für Tooltip bestimmen
        felder = []
        alias = []
        for spalte in ['shape_area', 'neigung', 'ausrichtung']:
            if spalte in dach_im_hafen_wgs.columns:
                felder.append(spalte)
                if spalte == 'shape_area':
                    alias.append('Fläche m²:')
                elif spalte == 'neigung':
                    alias.append('Neigung:')
                elif spalte == 'ausrichtung':
                    alias.append('Ausrichtung:')

        tooltip = folium.GeoJsonTooltip(
            fields=felder,
            aliases=alias,
            localize=True,
            style="background-color: white; font-size: 12px;"
        ) if felder else None

        folium.GeoJson(
            dach_im_hafen_wgs,
            name=f"Dachseiten im Hafen ({len(dach_im_hafen_wgs):,})",
            style_function=lambda x: {"fillColor": "green", "color": "darkgreen", "weight": 0.5, "fillOpacity": 0.5},
            tooltip=tooltip
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

# ============================================================
# 5. HAUPTABLAUF
# ============================================================
def main():
    print("\n" + "█"*70)
    print("  SOLARPOTENZIALANALYSE HAMBURGER HAFEN")
    print("█"*70 + "\n")

    # 1. Hafengebiet laden
    try:
        hafen = lade_hafengebiet()
        hafen_wgs = hafen.to_crs(4326)
    except Exception as e:
        print(f"❌ Fehler beim Laden des Hafengebiets: {e}")
        return

    # 2. Solar-ZIP finden
    zip_pfad = finde_solar_zip()
    if not zip_pfad:
        print("❌ Keine Solarpotenzial-ZIP gefunden. Bitte Datei in den Ordner legen.")
        print(f"   Gesucht in: {os.getcwd()}")
        return
    print(f"✅ Solar-ZIP gefunden: {zip_pfad}")

    # 3. Solardaten laden
    try:
        solar = lade_solar_daten(zip_pfad)
    except Exception as e:
        print(f"❌ Fehler beim Laden der Solardaten: {e}")
        return

    if solar.get('gebaeude') is None:
        print("❌ Keine Gebäudedaten in der ZIP gefunden.")
        return

    # 4. Verschneidung mit Hafengebiet
    geb_im_hafen = verschneide_mit_hafen(solar['gebaeude'], hafen, "Gebäude")
    dach_im_hafen = None
    if solar.get('dachseiten') is not None:
        dach_im_hafen = verschneide_mit_hafen(solar['dachseiten'], hafen, "Dachseiten")

    # 5. Statistik ausgeben (mit deutschen Zahlen)
    berechne_statistiken(geb_im_hafen, dach_im_hafen)

    # 6. Karte vorbereiten (WGS84)
    geb_wgs = solar.get('gebaeude_wgs')
    dach_wgs = solar.get('dachseiten_wgs')

    # Für die Karte nur die geschnittenen Bereiche verwenden (Performance)
    geb_im_hafen_wgs = geb_im_hafen.to_crs(4326) if geb_im_hafen is not None else None
    dach_im_hafen_wgs = dach_im_hafen.to_crs(4326) if dach_im_hafen is not None else None

    # 7. Karte erstellen und speichern
    zentrum = [hafen_wgs.geometry.centroid.y.mean(), hafen_wgs.geometry.centroid.x.mean()]
    karte = erstelle_karte(hafen_wgs, geb_im_hafen_wgs, dach_im_hafen_wgs, zentrum)

    ausgabe_datei = "hafen_solar_analyse.html"
    karte.save(ausgabe_datei)
    webbrowser.open(ausgabe_datei)
    print(f"\n🌍 Karte gespeichert: {ausgabe_datei}")
    print("✅ Analyse abgeschlossen.\n")

if __name__ == "__main__":
    main()