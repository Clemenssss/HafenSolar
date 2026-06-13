"""
Eindeutige nutzart-Werte im Hafengebiet (grobe BBOX)
"""
import requests
import geopandas as gpd
from io import BytesIO

WFS_URL = "https://geodienste.hamburg.de/WFS_HH_ALKIS_vereinfacht"

# Grobe BBOX Hamburger Hafen (EPSG:25832)
BBOX = "555000,5928000,575000,5936000,EPSG:25832"


def main():
    params = {
        "SERVICE": "WFS", "VERSION": "1.1.0", "REQUEST": "GetFeature",
        "TYPENAME": "ave:Nutzung",
        "BBOX": BBOX,
        "MAXFEATURES": "20000",
    }
    print("Lade Nutzung-Features für Hafen-BBOX (kann etwas dauern)...")
    r = requests.get(WFS_URL, params=params, timeout=180)
    r.raise_for_status()
    print(f"HTTP {r.status_code}, Content-Type: {r.headers.get('content-type')}")

    gdf = gpd.read_file(BytesIO(r.content))
    print(f"\n{len(gdf)} Features geladen")
    print(f"Spalten: {list(gdf.columns)}")

    print("\n--- Eindeutige 'nutzart' Werte mit Anzahl ---")
    print(gdf['nutzart'].value_counts().to_string())

    if 'bez' in gdf.columns:
        print("\n--- 'bez' (Bezeichnung/Detail) - nicht-null Beispiele ---")
        bez_vals = gdf['bez'].dropna()
        print(f"{len(bez_vals)} von {len(gdf)} haben einen 'bez'-Wert")
        print(bez_vals.value_counts().head(20).to_string())

    # Fläche pro nutzart (in EPSG:25832 -> m²)
    gdf = gdf.set_crs(25832, allow_override=True)
    gdf['flaeche_m2'] = gdf.geometry.area
    print("\n--- Gesamtfläche je nutzart [m²] ---")
    flaeche = gdf.groupby('nutzart')['flaeche_m2'].sum().sort_values(ascending=False)
    print(flaeche.to_string())


if __name__ == "__main__":
    main()