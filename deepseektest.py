#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose: Räumliche Übereinstimmung Hafen vs. Solar-Gebäude
"""

import geopandas as gpd
import zipfile
import tempfile
import os
import glob

# ------------------------------------------------------------
# 1. Hafengebiet laden (wie gehabt)
# ------------------------------------------------------------
hafen_pfad = "zip://hafengebietsgrenzen_json.zip!app_hafengebietsgrenzen_EPSG_25832.json"
hafen = gpd.read_file(hafen_pfad)
hafen = hafen.set_crs(25832, allow_override=True)
print("=== HAFENGEBIET ===")
print(f"Anzahl Polygone: {len(hafen)}")
print(f"CRS: {hafen.crs}")
bbox = hafen.total_bounds
print(f"Bounding Box: {bbox}")  # (minx, miny, maxx, maxy)
print(f"Fläche (m²): {hafen.area.sum():.0f}")
print()

# ------------------------------------------------------------
# 2. Solar-Gebäude laden (mit korrigiertem CRS)
# ------------------------------------------------------------
solar_zip = None
for f in glob.glob("*solar*.zip"):
    solar_zip = f
    break

if not solar_zip:
    print("Keine Solar-ZIP gefunden!")
    exit()

print(f"Solar-ZIP: {solar_zip}")

with tempfile.TemporaryDirectory() as tmpdir:
    with zipfile.ZipFile(solar_zip, 'r') as zf:
        zf.extractall(tmpdir)
    # Gebäude-Datei mit 25832 suchen
    geb_path = None
    for f in os.listdir(tmpdir):
        if 'gebaeude' in f.lower() and '25832' in f:
            geb_path = os.path.join(tmpdir, f)
            break
    if not geb_path:
        print("Keine Gebäude-Datei mit 25832 gefunden!")
        exit()

    gebaeude = gpd.read_file(geb_path)
    # CRS erzwingen (weil die Datei oft falsches CRS angibt)
    gebaeude = gebaeude.set_crs(25832, allow_override=True)

    print("\n=== SOLAR-GEBÄUDE ===")
    print(f"Anzahl Gebäude: {len(gebaeude):,}")
    print(f"CRS (erzwungen): {gebaeude.crs}")
    bbox_g = gebaeude.total_bounds
    print(f"Bounding Box: {bbox_g}")

    # Prüfen, ob die BBoxen sich überlappen
    overlap = not (bbox[2] < bbox_g[0] or bbox[0] > bbox_g[2] or bbox[3] < bbox_g[1] or bbox[1] > bbox_g[3])
    print(f"Bounding Boxen überlappen: {overlap}")

    # Geometrietypen prüfen
    print(f"Geometrietypen: {gebaeude.geometry.geom_type.unique()}")
    print(f"Anzahl gültige Geometrien: {gebaeude.geometry.is_valid.sum()}")
    print(f"Anzahl leere Geometrien: {gebaeude.geometry.is_empty.sum()}")

    # Erste 3 Gebäude-Polygone anzeigen (repräsentativer Punkt)
    print("\nBeispiel-Koordinaten (repräsentativer Punkt der ersten 3 Gebäude):")
    for i in range(min(3, len(gebaeude))):
        point = gebaeude.geometry.iloc[i].representative_point()
        print(f"  {i}: {point.x:.1f} / {point.y:.1f}")

    # --------------------------------------------------------
    # 3. Räumlicher Test: Liegen die ersten 100 Gebäude innerhalb des Hafens?
    # --------------------------------------------------------
    print("\n=== RÄUMLICHER TEST (erste 100 Gebäude) ===")
    test_gdf = gebaeude.head(100)
    # Räumlicher Join (innerhalb)
    within = gpd.sjoin(test_gdf, hafen, predicate='within')
    print(f"Anzahl Gebäude vollständig innerhalb Hafen: {len(within)}")

    # Räumlicher Join (intersects) – Überschneidung
    intersects = gpd.sjoin(test_gdf, hafen, predicate='intersects')
    print(f"Anzahl Gebäude, die Hafen schneiden: {len(intersects)}")

    # Falls keine, prüfen wir die Entfernung zum Hafen
    if len(intersects) == 0:
        # Berechne Mindestabstand der ersten 100 Gebäude zum Hafen
        distances = test_gdf.geometry.distance(hafen.unary_union)
        print(f"Minimale Distanz zum Hafen (erste 100 Gebäude): {distances.min():.1f} Meter")
        print(f"Maximale Distanz: {distances.max():.1f} Meter")
        print(f"Durchschnittliche Distanz: {distances.mean():.1f} Meter")

    # --------------------------------------------------------
    # 4. Einfache Karte zur visuellen Prüfung (speichern und öffnen)
    # --------------------------------------------------------
    import folium

    # Zentrum auf Hafengebiet
    center = [hafen.geometry.centroid.y.mean(), hafen.geometry.centroid.x.mean()]
    m = folium.Map(location=center, zoom_start=13)
    folium.GeoJson(hafen.to_crs(4326), name="Hafen",
                   style_function=lambda x: {"color": "blue", "fillOpacity": 0.2}).add_to(m)
    # Erste 200 Gebäude in WGS84
    geb_wgs = test_gdf.to_crs(4326)
    folium.GeoJson(geb_wgs, name="Gebäude (Sample)", style_function=lambda x: {"color": "red", "weight": 1}).add_to(m)
    m.save("diagnose_karte.html")
    print("\nKarte gespeichert: diagnose_karte.html")
    import webbrowser

    webbrowser.open("diagnose_karte.html")