#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import os

import geopandas as gpd
import osmnx as ox
import requests

from config import (CACHE_FILE, HAFEN_JSON, HAFEN_ZIP, WFS_TYPENAME, WFS_URL)
from utils import log


def lade_hafengebiet():
    log("Lade Hafengebiet...")
    hafen = gpd.read_file(f"zip://{HAFEN_ZIP}!{HAFEN_JSON}")
    hafen = hafen.set_crs(25832, allow_override=True)
    hafen.geometry = hafen.geometry.buffer(0)
    log(f"Hafengebiet geladen: {len(hafen)} Polygon(e)")
    return hafen


def _wfs_request(bbox_str):
    params = {
        "SERVICE":  "WFS",
        "VERSION":  "1.1.0",
        "REQUEST":  "GetFeature",
        "typename": WFS_TYPENAME,
        "BBOX":     bbox_str,
    }
    log(f"Rufe WFS ab: {WFS_TYPENAME} ...")
    r = requests.get(WFS_URL, params=params, timeout=120)
    r.raise_for_status()
    return gpd.read_file(io.BytesIO(r.content))


def lade_dachseiten(hafen):
    bounds   = hafen.total_bounds
    bbox_str = (f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]},"
                "urn:ogc:def:crs:EPSG::25832")

    if os.path.exists(CACHE_FILE):
        log(f"Lade Dachseiten aus Cache: {CACHE_FILE}")
        dachseiten = gpd.read_file(CACHE_FILE)
    else:
        dachseiten = _wfs_request(bbox_str)
        log(f"Dachseiten geladen: {len(dachseiten)}")
        log("Speichere Cache...")
        dachseiten = dachseiten.set_crs(25832, allow_override=True)
        dachseiten.to_file(CACHE_FILE, driver="GPKG")
        log("Cache gespeichert.")

    # CRS sicherstellen
    if dachseiten.crs is None:
        dachseiten = dachseiten.set_crs(25832)
    elif dachseiten.crs.to_epsg() != 25832:
        dachseiten = dachseiten.to_crs(25832)

    dachseiten.geometry = dachseiten.geometry.buffer(0)
    return dachseiten


def lade_parkplaetze(hafen):
    log("Lade Parkplätze aus OSM...")
    try:
        pp = ox.features_from_polygon(
            hafen.to_crs(4326).union_all(),
            tags={"amenity": "parking"}
        )
        pp = pp[pp.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
        pp = pp.to_crs(25832)
        log(f"Parkplätze gefunden: {len(pp)}")
        return pp
    except Exception as e:
        log(f"OSM-Fehler: {e}")
        return None
