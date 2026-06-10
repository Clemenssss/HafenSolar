#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MaStR-Daten: installierte PV-Anlagen im Hafengebiet
Quelle: Marktstammdatenregister (Bundesnetzagentur) via open-mastr
"""
import geopandas as gpd
import pandas as pd
from open_mastr import Mastr

from utils import log

# Statuskürzel → Klartext
BETRIEBS_STATUS = {
    "InBetrieb":           "In Betrieb",
    "VoruebergehendStill": "Vorübergehend stillgelegt",
    "DauerhaftStillgelegt":"Dauerhaft stillgelegt",
    "InPlanung":           "In Planung",
    "Genehmigt":           "Genehmigt",
}


def lade_mastr_anlagen(hafen: gpd.GeoDataFrame) -> gpd.GeoDataFrame | None:
    """
    Lädt PV-Anlagen aus dem MaStR für Hamburg und clippt auf das Hafengebiet.

    Beim ersten Aufruf lädt open-mastr eine lokale SQLite-DB (~/.open_mastr/).
    Folgeaufrufe nutzen den lokalen Cache.

    Returns:
        GeoDataFrame (EPSG:25832) mit installierten Anlagen im Hafengebiet
        oder None bei Fehler.
    """
    log("Lade MaStR-Daten (PV, Hamburg)...")

    # --- Download / DB-Initialisierung ---
    try:
        db = Mastr()
        # db.download(data="solar", bulk=False, limit=None)  # nur einmalig nötig
    except Exception as e:
        log(f"MaStR-Download fehlgeschlagen: {e}")
        return None, None

    # --- Daten aus DB lesen ---
    try:
        log("Lese PV-Einheiten aus lokaler DB (Tabelle: solar_extended)...")
        df = pd.read_sql(
            sql="SELECT * FROM solar_extended WHERE Bundesland = 'Hamburg'",
            con=db.engine,
        )
    except Exception as e:
        log(f"MaStR-Abfrage fehlgeschlagen: {e}")
        # Fallback: vorhandene Tabellen ausgeben
        try:
            tables = pd.read_sql(
                "SELECT name FROM sqlite_master WHERE type=\'table\'",
                con=db.engine,
            )
            log(f"Vorhandene Tabellen: {tables['name'].tolist()}")
        except Exception:
            pass
        return None, None

    if df is None or df.empty:
        log("Keine MaStR-Daten für Hamburg gefunden.")
        return None, None

    log(f"MaStR Hamburg gesamt: {len(df)} Anlagen")
    log(f"Spalten: {list(df.columns)}")

    # --- Hamburg-Gesamtstatistik (vor Koordinaten-Filter / Clip) ---
    leistung_col = _find_col(df, ["Nettonennleistung", "InstallierteLeistung",
                                   "nettonennleistung"])
    kwp_hamburg_gesamt = 0.0
    if leistung_col:
        kwp_hamburg_gesamt = pd.to_numeric(df[leistung_col], errors="coerce").sum()

    hamburg_stats = {
        "n":          len(df),
        "kwp_gesamt": kwp_hamburg_gesamt,
        "gwh_gesamt": kwp_hamburg_gesamt / 1_000_000 * 950,
    }
    log(f"Hamburg gesamt: {hamburg_stats['n']} Anlagen, "
        f"{hamburg_stats['kwp_gesamt']:.1f} kWp, "
        f"{hamburg_stats['gwh_gesamt']:.1f} GWh/a")

    # --- Koordinaten-Spalten ermitteln ---
    lat_col = _find_col(df, ["Breitengrad", "lat", "latitude"])
    lon_col = _find_col(df, ["Laengengrad", "lon", "longitude"])
    log(f"Koordinatenspalten: lat='{lat_col}', lon='{lon_col}'")

    if not lat_col or not lon_col:
        log("FEHLER: Koordinatenspalten nicht gefunden – Abbruch.")
        return None, hamburg_stats

    # Wie viele haben überhaupt Koordinaten?
    n_vor = len(df)
    df = df.dropna(subset=[lat_col, lon_col]).copy()
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])
    log(f"Mit gültigen Koordinaten: {len(df)} / {n_vor}")

    if df.empty:
        log("FEHLER: Keine Einträge mit Koordinaten.")
        return None, hamburg_stats

    # Stichprobe der Koordinaten zur Plausibilitätsprüfung
    log(f"Koordinaten-Stichprobe (erste 3):\n{df[[lat_col, lon_col]].head(3).to_string()}")

    # --- GeoDataFrame bauen ---
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs=4326,
    ).to_crs(25832)

    log(f"GDF CRS: {gdf.crs}")
    log(f"GDF Bounds (UTM32): {gdf.total_bounds}")
    log(f"Hafen Bounds (UTM32): {hafen.total_bounds}")

    # --- Clip auf Hafengebiet ---
    hafen_union = hafen.union_all()
    gdf_hafen = gdf[gdf.geometry.within(hafen_union)].copy()
    log(f"MaStR-Anlagen im Hafengebiet: {len(gdf_hafen)}")

    if gdf_hafen.empty:
        log("Keine Anlagen im Hafengebiet – prüfe ob Bounds überlappen (s.o.).")
        return None, hamburg_stats

    gdf_hafen = _normalisiere_spalten(gdf_hafen)
    return gdf_hafen, hamburg_stats


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def _normalisiere_spalten(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Benennt relevante Spalten in einheitliche Namen um."""
    rename = {}
    mapping = {
        "mastr_name":          ["EinheitName", "NameEinheit", "name"],
        "mastr_id":            ["EinheitMastrNummer", "MastrNummer"],
        "leistung_kwp":        ["Nettonennleistung", "InstallierteLeistung",
                                "nettonennleistung"],
        "status":              ["EinheitBetriebsstatus", "Betriebsstatus",
                                "betriebsstatus"],
        "inbetriebnahme":      ["Inbetriebnahmedatum", "DatumInbetriebnahme",
                                "inbetriebnahmedatum"],
        "plz":                 ["Postleitzahl", "postleitzahl"],
        "ort":                 ["Ort", "ort"],
        "strasse":             ["Strasse", "strasse"],
        "lage":                ["Lage", "lage"],           # Freifläche / Gebäude
        "module_hersteller":   ["ModulHersteller", "Modulhersteller"],
    }
    lower = {c.lower(): c for c in gdf.columns}
    for ziel, quellen in mapping.items():
        for q in quellen:
            if q in gdf.columns:
                rename[q] = ziel
                break
            elif q.lower() in lower:
                rename[lower[q.lower()]] = ziel
                break

    gdf = gdf.rename(columns=rename)

    # Status-Klartext
    if "status" in gdf.columns:
        gdf["status_text"] = gdf["status"].map(BETRIEBS_STATUS).fillna(gdf["status"])
    else:
        gdf["status_text"] = "unbekannt"

    # Leistung numerisch
    if "leistung_kwp" in gdf.columns:
        gdf["leistung_kwp"] = pd.to_numeric(gdf["leistung_kwp"], errors="coerce")
    else:
        gdf["leistung_kwp"] = None

    return gdf