"""
Solarpotenzial Hamburger Hafengebiet – WFS-Auswertung
======================================================
Datenquelle: Solarkataster Hamburg (LGV), Frühjahrsbefliegung 2022
Lizenz: Datenlizenz Deutschland Namensnennung 2.0

Abhängigkeiten:
    pip install geopandas requests owslib shapely pandas

Ausführung:
    python solar_hafen_hamburg.py
"""

import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from io import StringIO
import json

# ─────────────────────────────────────────────
# 1) KONFIGURATION
# ─────────────────────────────────────────────

# WFS-Endpoint Hamburger Solarkataster (LGV)
WFS_URL = "https://geodienste.hamburg.de/HH_WFS_Solarkataster"

# BBOX Hamburger Hafengebiet (EPSG:25832, UTM32N)
# Grob: von Norderelbe bis südlich, Landungsbrücken bis Köhlbrandbrücke
# Anpassen nach Bedarf (exakte Hafenentwicklungsgebiet-Grenzen s. unten)
HAFEN_BBOX_UTM = {
    "minx": 559000,
    "miny": 5929000,
    "maxx": 572000,
    "maxy": 5935000,
}

# Alternative: Hafengebiet als WGS84-Koordinaten (für Kontrollzwecke)
HAFEN_BBOX_WGS84 = {
    "west": 9.90,
    "south": 53.51,
    "east": 10.05,
    "north": 53.54,
}

# Layer-Name im WFS (aus GetCapabilities ermittelt)
LAYER_GEBAEUDE = "app:Gebaeude"
LAYER_DACHSEITE = "app:Dachseite"


# ─────────────────────────────────────────────
# 2) WFS CAPABILITIES PRÜFEN
# ─────────────────────────────────────────────

def get_capabilities():
    """Gibt verfügbare Layer-Namen aus."""
    r = requests.get(WFS_URL, params={
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetCapabilities",
    }, timeout=30)
    r.raise_for_status()
    # Layer-Namen aus XML extrahieren (vereinfacht)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(r.text)
    ns = {"wfs": "http://www.opengis.net/wfs/2.0"}
    layers = [ft.find("wfs:Name", ns).text
              for ft in root.findall(".//wfs:FeatureType", ns)
              if ft.find("wfs:Name", ns) is not None]
    print("Verfügbare Layer:", layers)
    return layers


# ─────────────────────────────────────────────
# 3) DATEN LADEN (WFS GetFeature mit BBOX)
# ─────────────────────────────────────────────

def load_solar_data(layer: str, bbox: dict, crs: str = "EPSG:25832") -> gpd.GeoDataFrame:
    """
    Lädt Solarkataster-Features via WFS für eine BBOX.
    bbox: dict mit minx, miny, maxx, maxy in der angegebenen CRS
    """
    bbox_str = f"{bbox['minx']},{bbox['miny']},{bbox['maxx']},{bbox['maxy']},{crs}"

    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": layer,
        "BBOX": bbox_str,
        "OUTPUTFORMAT": "application/json",
        "COUNT": "10000",  # ggf. erhöhen oder Paging nutzen
    }

    print(f"Lade Layer '{layer}' für BBOX {bbox} ...")
    r = requests.get(WFS_URL, params=params, timeout=120)
    r.raise_for_status()

    gdf = gpd.read_file(StringIO(r.text))
    gdf = gdf.set_crs(crs, allow_override=True)
    print(f"  → {len(gdf)} Features geladen")
    return gdf


# ─────────────────────────────────────────────
# 4) OPTIONAL: Clipping auf Hafenentwicklungsgebiet
# ─────────────────────────────────────────────

def load_hafenentwicklungsgebiet() -> gpd.GeoDataFrame:
    """
    Lädt das offizielle Hafenentwicklungsgebiet via WFS Verwaltungsgrenzen
    oder als GeoJSON aus dem Transparenzportal.
    Alternativ: lokale Shapefile/GeoJSON-Datei einlesen.
    """
    # Option A: WFS HPA (Hamburg Port Authority) – falls verfügbar
    # Option B: Manuell gezeichnetes GeoJSON einlesen
    # Hier: einfacher Umriss als Fallback (grobe Hafengrenzen)

    hafen_geom = box(
        HAFEN_BBOX_UTM["minx"],
        HAFEN_BBOX_UTM["miny"],
        HAFEN_BBOX_UTM["maxx"],
        HAFEN_BBOX_UTM["maxy"],
    )
    gdf = gpd.GeoDataFrame(geometry=[hafen_geom], crs="EPSG:25832")
    print("Hafenumriss (vereinfachte BBOX) geladen.")
    return gdf


def clip_to_hafen(gdf: gpd.GeoDataFrame, hafen: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Verschneidet Solarkataster-Daten mit Hafengebiet."""
    gdf_clipped = gpd.clip(gdf, hafen)
    print(f"Nach Clip: {len(gdf_clipped)} Gebäude im Hafengebiet")
    return gdf_clipped


# ─────────────────────────────────────────────
# 5) QUANTIFIZIERUNG
# ─────────────────────────────────────────────

def quantify(gdf: gpd.GeoDataFrame) -> dict:
    """
    Berechnet Kennzahlen für das Hafengebiet.
    Erwartet Spalten: Fläche_PV, Leistung, Anzahl_Module, Eignung_PV
    """
    # Spaltennamen normalisieren (Sonderzeichen)
    cols = {c: c.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
            for c in gdf.columns}
    # Pflichtfelder prüfen
    required = ["Fläche_PV", "Leistung", "Anzahl_Module", "Eignung_PV"]
    missing = [c for c in required if c not in gdf.columns]
    if missing:
        print(f"Fehlende Spalten: {missing}")
        print("Vorhandene Spalten:", list(gdf.columns))
        return {}

    # Numerisch konvertieren
    for col in ["Fläche_PV", "Leistung", "Anzahl_Module"]:
        gdf[col] = pd.to_numeric(gdf[col], errors="coerce")

    results = {
        "Anzahl_Gebäude": len(gdf),
        "Gesamtfläche_PV_m2": gdf["Fläche_PV"].sum(),
        "Gesamtfläche_PV_ha": gdf["Fläche_PV"].sum() / 10_000,
        "Gesamtleistung_kWp": gdf["Leistung"].sum(),
        "Gesamtleistung_MWp": gdf["Leistung"].sum() / 1_000,
        "Anzahl_Module_gesamt": gdf["Anzahl_Module"].sum(),
        # Jahresertrag (Schätzung): Hamburg ~950 Volllaststunden/a
        "Jahresertrag_MWh_est": gdf["Leistung"].sum() / 1_000 * 950,
    }

    # Nach Eignungsklasse aufschlüsseln
    by_class = (
        gdf.groupby("Eignung_PV")
        .agg(
            Gebäude=("Eignung_PV", "count"),
            Fläche_PV_m2=("Fläche_PV", "sum"),
            Leistung_kWp=("Leistung", "sum"),
        )
        .reset_index()
    )
    results["Nach_Eignung"] = by_class.to_dict(orient="records")

    return results


# ─────────────────────────────────────────────
# 6) AUSGABE
# ─────────────────────────────────────────────

def print_results(r: dict):
    print("\n" + "=" * 55)
    print("  SOLARPOTENZIAL – HAMBURGER HAFENGEBIET")
    print("=" * 55)
    print(f"  Gebäude analysiert:      {r['Anzahl_Gebäude']:>10,}")
    print(f"  Geeignete Dachfläche:    {r['Gesamtfläche_PV_ha']:>10.1f} ha")
    print(f"                           ({r['Gesamtfläche_PV_m2']:>12,.0f} m²)")
    print(f"  Installierbare Leistung: {r['Gesamtleistung_MWp']:>10.1f} MWp")
    print(f"  Module (geschätzt):      {r['Anzahl_Module_gesamt']:>10,.0f}")
    print(f"  Jahresertrag (ca.):      {r['Jahresertrag_MWh_est']:>10,.0f} MWh/a")
    print()
    print("  Aufschlüsselung nach PV-Eignungsklasse:")
    print(f"  {'Klasse':<20} {'Gebäude':>8} {'Fläche m²':>12} {'Leistung kWp':>14}")
    print(f"  {'-' * 20} {'-' * 8} {'-' * 12} {'-' * 14}")
    for row in r.get("Nach_Eignung", []):
        print(f"  {str(row.get('Eignung_PV', '')):<20} "
              f"{row.get('Gebäude', 0):>8,} "
              f"{row.get('Fläche_PV_m2', 0):>12,.0f} "
              f"{row.get('Leistung_kWp', 0):>14,.0f}")
    print("=" * 55)
    print("  Datenquelle: LGV Hamburg, Solarkataster 2022")
    print("  Lizenz: Datenlizenz Deutschland Namensnennung 2.0")
    print("=" * 55)


def export_csv(gdf: gpd.GeoDataFrame, path: str = "solar_hafen.csv"):
    """Exportiert Rohdaten ohne Geometrie als CSV."""
    cols = [c for c in gdf.columns if c != "geometry"]
    gdf[cols].to_csv(path, index=False, encoding="utf-8-sig")
    print(f"CSV gespeichert: {path}")


# ─────────────────────────────────────────────
# 7) MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Capabilities prüfen (optional, auskommentierbar)
    # layers = get_capabilities()

    # Gebäude-Layer laden
    gdf = load_solar_data(LAYER_GEBAEUDE, HAFEN_BBOX_UTM)

    # Auf Hafengebiet zuschneiden (optional genauer via GeoJSON)
    hafen = load_hafenentwicklungsgebiet()
    gdf_hafen = clip_to_hafen(gdf, hafen)

    # Quantifizieren
    results = quantify(gdf_hafen)

    if results:
        print_results(results)
        export_csv(gdf_hafen, "solar_hafen.csv")

    # GeoJSON exportieren (für QGIS etc.)
    gdf_hafen.to_file("solar_hafen.geojson", driver="GeoJSON")
    print("GeoJSON gespeichert: solar_hafen.geojson")
