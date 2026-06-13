"""
Debug: ave:Nutzung WFS-Anfrage mit mehreren Varianten testen
"""
import requests
import geopandas as gpd
from io import BytesIO

WFS_URL = "https://geodienste.hamburg.de/WFS_HH_ALKIS_vereinfacht"

VARIANTS = [
    # (label, params)
    ("v2.0.0 + GeoJSON + BBOX urn", {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": "ave:Nutzung",
        "BBOX": "563000,5933000,564000,5934000,urn:ogc:def:crs:EPSG::25832",
        "COUNT": "5", "OUTPUTFORMAT": "application/json",
    }),
    ("v1.1.0 + GML + BBOX plain", {
        "SERVICE": "WFS", "VERSION": "1.1.0", "REQUEST": "GetFeature",
        "TYPENAME": "ave:Nutzung",
        "BBOX": "563000,5933000,564000,5934000,EPSG:25832",
        "MAXFEATURES": "5",
    }),
    ("v2.0.0 + GML + COUNT only (no bbox)", {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": "ave:Nutzung",
        "COUNT": "2",
    }),
    ("v2.0.0 + json (gml3 outputformat)", {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": "ave:Nutzung",
        "BBOX": "563000,5933000,564000,5934000",
        "COUNT": "5",
    }),
]


def main():
    for label, params in VARIANTS:
        print(f"\n{'='*60}")
        print(f"Variante: {label}")
        print(f"Params: {params}")
        try:
            r = requests.get(WFS_URL, params=params, timeout=60)
            print(f"HTTP {r.status_code}, Content-Type: {r.headers.get('content-type')}")
            if r.status_code != 200:
                print("Antwort-Body (erste 1500 Zeichen):")
                print(r.text[:1500])
                continue

            ct = r.headers.get("content-type", "")
            if "json" in ct:
                gdf = gpd.read_file(BytesIO(r.content))
            else:
                gdf = gpd.read_file(BytesIO(r.content))  # geopandas kann auch GML

            print(f"-> {len(gdf)} Features, Spalten: {list(gdf.columns)}")
            if len(gdf) > 0:
                print(gdf.iloc[0].drop("geometry", errors="ignore").to_dict())
            return  # erste erfolgreiche Variante reicht

        except Exception as e:
            print(f"FEHLER: {e}")


if __name__ == "__main__":
    main()