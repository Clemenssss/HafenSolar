"""
Inspektion: ave:Nutzung Attributstruktur
==========================================
Holt 3 Beispiel-Features um Spaltennamen und Wertebereiche
der Nutzungsart zu sehen.

Ausführen:
    python inspect_nutzung.py
"""
import requests
import geopandas as gpd
from io import BytesIO

WFS_URL = "https://geodienste.hamburg.de/WFS_HH_ALKIS_vereinfacht"

# Kleine BBOX im Hafengebiet zum Testen (Hansahafen-Bereich)
BBOX = "563000,5933000,564000,5934000,urn:ogc:def:crs:EPSG::25832"


def main():
    params = {
        "SERVICE":  "WFS",
        "VERSION":  "2.0.0",
        "REQUEST":  "GetFeature",
        "TYPENAMES": "ave:Nutzung",
        "BBOX":     BBOX,
        "COUNT":    "20",
        "OUTPUTFORMAT": "application/json",
    }
    r = requests.get(WFS_URL, params=params, timeout=60)
    r.raise_for_status()
    print(f"HTTP {r.status_code}, Content-Type: {r.headers.get('content-type')}")

    try:
        gdf = gpd.read_file(BytesIO(r.content))
    except Exception as e:
        print(f"GeoJSON-Parse fehlgeschlagen: {e}")
        print("Antwort (erste 1000 Zeichen):")
        print(r.text[:1000])
        return

    print(f"\n{len(gdf)} Features geladen")
    print(f"Spalten: {list(gdf.columns)}")

    # Nutzungsart-Spalte raten
    for col in gdf.columns:
        if "nutz" in col.lower() or "art" in col.lower() or "klasse" in col.lower():
            print(f"\nSpalte '{col}' - eindeutige Werte:")
            print(gdf[col].dropna().unique()[:30])

    print("\nErste 3 Zeilen (ohne Geometrie):")
    cols = [c for c in gdf.columns if c != "geometry"]
    print(gdf[cols].head(3).to_string())


if __name__ == "__main__":
    main()