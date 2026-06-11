#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brach- und ungenutzte Flächen im Hafengebiet.

Drei unabhängige Layer:
  1. Halden / Tagebau (ALKIS)          -> "enge" Brachen-Kandidaten
  2. Unbebaute Gewerbeflächen (ALKIS)  -> Industrie/Gewerbe minus Gebäude
  3. Brachflächen (OSM)                -> landuse=brownfield/vacant
"""
import geopandas as gpd
import pandas as pd
import requests
from io import BytesIO

from utils import log

ALKIS_WFS_URL = "https://geodienste.hamburg.de/WFS_HH_ALKIS_vereinfacht"
PAGE_SIZE = 5000

# Kategorien für "enge" Brachen
NUTZART_BRACHE_ENG = ["Halde", "Tagebau Grube Steinbruch"]

# Kategorien die für "unbebaute Gewerbefläche" infrage kommen
NUTZART_GEWERBE = ["Industrie Und Gewerbeflaeche", "Flaeche Besonderer Funktionaler Praegung"]

# Mindestgröße für unbebaute Gewerbeflächen-Polygone [m²]
MIN_FLAECHE_GEWERBE_M2 = 500


def _wfs_get_feature_single(typename: str, bbox: tuple, crs_epsg: int = 25832) -> gpd.GeoDataFrame:
    """Einzelne WFS-GetFeature-Anfrage für eine BBOX (max. PAGE_SIZE Features)."""
    bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:{crs_epsg}"
    params = {
        "SERVICE":     "WFS",
        "VERSION":     "1.1.0",
        "REQUEST":     "GetFeature",
        "TYPENAME":    typename,
        "BBOX":        bbox_str,
        "MAXFEATURES": str(PAGE_SIZE),
    }
    r = requests.get(ALKIS_WFS_URL, params=params, timeout=180)
    r.raise_for_status()
    return gpd.read_file(BytesIO(r.content))


def _wfs_get_feature_recursive(typename: str, bbox: tuple, crs_epsg: int = 25832,
                                depth: int = 0, max_depth: int = 6) -> list:
    """
    Lädt Features für eine BBOX. Falls das Ergebnis genau PAGE_SIZE
    Features enthält (= vermutlich abgeschnitten), wird die BBOX in
    vier Quadranten aufgeteilt und rekursiv weiter abgefragt.
    Gibt eine Liste von GeoDataFrames zurück.
    """
    gdf = _wfs_get_feature_single(typename, bbox, crs_epsg)
    n = len(gdf)

    if n < PAGE_SIZE or depth >= max_depth:
        if n >= PAGE_SIZE:
            log(f"  WARNUNG: max_depth erreicht bei BBOX {bbox} ({n} Features, "
                f"evtl. unvollständig)")
        if n > 0:
            log(f"  {typename}: BBOX {[round(b) for b in bbox]} -> {n} Features")
        return [gdf] if n > 0 else []

    log(f"  {typename}: BBOX {[round(b) for b in bbox]} -> {n} Features (Limit), "
        f"teile in 4 Quadranten...")

    minx, miny, maxx, maxy = bbox
    midx = (minx + maxx) / 2
    midy = (miny + maxy) / 2

    quadranten = [
        (minx, miny, midx, midy),
        (midx, miny, maxx, midy),
        (minx, midy, midx, maxy),
        (midx, midy, maxx, maxy),
    ]

    parts = []
    for q in quadranten:
        parts.extend(_wfs_get_feature_recursive(typename, q, crs_epsg, depth + 1, max_depth))
    return parts


def _wfs_get_feature_paginated(typename: str, bbox: tuple, crs_epsg: int = 25832) -> gpd.GeoDataFrame:
    """
    Lädt alle Features eines ALKIS-WFS-Layers für eine BBOX.
    Nutzt rekursives BBOX-Splitting, da STARTINDEX vom Server ignoriert wird.
    Dubletten (Features die in mehreren Quadranten auftauchen) werden
    über 'gml_id' bzw. 'oid' entfernt.
    """
    parts = _wfs_get_feature_recursive(typename, bbox, crs_epsg)

    if not parts:
        return gpd.GeoDataFrame(geometry=[], crs=crs_epsg)

    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True))
    gdf = gdf.set_crs(crs_epsg, allow_override=True)

    # Dubletten entfernen (Features an Quadranten-Grenzen)
    id_col = "gml_id" if "gml_id" in gdf.columns else ("oid" if "oid" in gdf.columns else None)
    if id_col:
        n_vor = len(gdf)
        gdf = gdf.drop_duplicates(subset=id_col).reset_index(drop=True)
        if n_vor != len(gdf):
            log(f"  {typename}: {n_vor - len(gdf)} Dubletten entfernt "
                f"(Quadranten-Grenzen)")

    gdf.geometry = gdf.geometry.buffer(0)
    return gdf


def lade_alkis_nutzung(hafen: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Lädt alle ALKIS-Nutzungsflächen (ave:Nutzung) im BBOX des Hafengebiets."""
    log("Lade ALKIS Nutzung (ave:Nutzung)...")
    bounds = hafen.total_bounds
    gdf = _wfs_get_feature_paginated("ave:Nutzung", bounds)
    log(f"ALKIS Nutzung gesamt (BBOX): {len(gdf)} Features")
    return gdf


def lade_alkis_gebaeude(hafen: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Lädt alle ALKIS-Gebäude (ave:GebaeudeBauwerk) im BBOX des Hafengebiets."""
    log("Lade ALKIS Gebäude (ave:GebaeudeBauwerk)...")
    bounds = hafen.total_bounds
    gdf = _wfs_get_feature_paginated("ave:GebaeudeBauwerk", bounds)
    log(f"ALKIS Gebäude gesamt (BBOX): {len(gdf)} Features")
    return gdf


def extrahiere_halden_tagebau(nutzung_hafen: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Layer 1: Halden / Tagebau – 'enge' Brachen-Kandidaten."""
    gdf = nutzung_hafen[nutzung_hafen["nutzart"].isin(NUTZART_BRACHE_ENG)].copy()
    gdf["flaeche_m2"] = gdf.geometry.area.round(0)
    if "bez" in gdf.columns:
        gdf["bez"] = gdf["bez"].astype(object).where(gdf["bez"].notna(), "k.A.")
        gdf["bez"] = gdf["bez"].astype(str)
    gdf["nutzart"] = gdf["nutzart"].astype(str)
    log(f"Halden/Tagebau im Hafen: {len(gdf)} Flächen, "
        f"{gdf['flaeche_m2'].sum():,.0f} m²")
    return gdf


def berechne_unbebaute_gewerbeflaechen(nutzung_hafen: gpd.GeoDataFrame,
                                        gebaeude_hafen: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Layer 2: Industrie/Gewerbeflächen minus Gebäude-Footprint,
    gefiltert nach Mindestgröße.
    """
    gewerbe = nutzung_hafen[nutzung_hafen["nutzart"].isin(NUTZART_GEWERBE)].copy()
    log(f"Gewerbe/Industrie-Flächen vor Differenz: {len(gewerbe)}")

    if gewerbe.empty:
        return gewerbe

    if gebaeude_hafen is None or gebaeude_hafen.empty:
        log("Keine Gebäudedaten – unbebaute Fläche = Gesamtfläche")
        diff = gewerbe.copy()
    else:
        log("Berechne Differenz Gewerbe minus Gebäude (kann etwas dauern)...")
        gebaeude_union = gebaeude_hafen.geometry.union_all()
        diff = gpd.overlay(
            gewerbe[["nutzart", "bez", "geometry"]],
            gpd.GeoDataFrame(geometry=[gebaeude_union], crs=gewerbe.crs),
            how="difference",
        )

    # In Einzelpolygone auflösen (explode) und nach Größe filtern
    diff = diff.explode(index_parts=False).reset_index(drop=True)
    diff["flaeche_m2"] = diff.geometry.area
    diff = diff[diff["flaeche_m2"] >= MIN_FLAECHE_GEWERBE_M2].copy()
    diff = diff.sort_values("flaeche_m2", ascending=False).reset_index(drop=True)

    # NaN in 'bez' verursacht leere Folium-Tooltips -> als String mit Platzhalter
    if "bez" in diff.columns:
        diff["bez"] = diff["bez"].astype(object).where(diff["bez"].notna(), "k.A.")
        diff["bez"] = diff["bez"].astype(str)
    diff["nutzart"] = diff["nutzart"].astype(str)
    diff["flaeche_m2"] = diff["flaeche_m2"].round(0)

    log(f"Unbebaute Gewerbeflächen (>= {MIN_FLAECHE_GEWERBE_M2} m²): "
        f"{len(diff)} Flächen, {diff['flaeche_m2'].sum():,.0f} m² gesamt")
    return diff


def lade_brachflaechen_osm(hafen: gpd.GeoDataFrame) -> gpd.GeoDataFrame | None:
    """Layer 3: OSM landuse=brownfield / vacant."""
    import osmnx as ox

    log("Lade Brachflächen aus OSM (landuse=brownfield/vacant)...")
    try:
        bf = ox.features_from_polygon(
            hafen.to_crs(4326).union_all(),
            tags={"landuse": ["brownfield", "vacant"]},
        )
        bf = bf[bf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        if bf.empty:
            log("Keine OSM-Brachflächen gefunden.")
            return None
        bf = bf.to_crs(25832)
        bf["flaeche_m2"] = bf.geometry.area
        log(f"OSM-Brachflächen gefunden: {len(bf)}, "
            f"{bf['flaeche_m2'].sum():,.0f} m²")
        return bf
    except Exception as e:
        log(f"OSM-Fehler (Brachflächen): {e}")
        return None