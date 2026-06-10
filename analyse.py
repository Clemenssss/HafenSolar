#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import geopandas as gpd

from config import (HAMBURG_FLAECHE_KM2, KWH_PRO_KWP, PARK_NUTZFAKTOR, WP_PRO_M2)
from utils import col, log


def _solar(pv_flaeche_m2):
    """Leistung [MWp] und Ertrag [GWh/a] aus PV-Fläche [m²]."""
    if pv_flaeche_m2 is None:
        return None, None
    leistung_mwp = pv_flaeche_m2 * WP_PRO_M2 / 1000
    ertrag_gwh   = leistung_mwp * KWH_PRO_KWP / 1000
    return leistung_mwp, ertrag_gwh


def berechne_dachseiten_stats(dachseiten_gesamt, dachseiten_hafen):
    c_pv  = col(dachseiten_gesamt, 'pvarea')
    c_ert = col(dachseiten_gesamt, 'ertkwha_k')
    c_eig = col(dachseiten_gesamt, 'eignung')

    def summe(gdf, c):
        return gdf[c].sum() if c else None

    pv_ges  = summe(dachseiten_gesamt, c_pv)
    ert_ges = summe(dachseiten_gesamt, c_ert)
    pv_haf  = summe(dachseiten_hafen,  c_pv)
    ert_haf = summe(dachseiten_hafen,  c_ert)

    mwp_ges, gwh_ges = _solar(pv_ges)
    mwp_haf, gwh_haf = _solar(pv_haf)

    log(f"PV-Fläche Hafen:   {pv_haf:,.0f} m²")
    log(f"Ertrag Hafen:      {ert_haf:,.0f} kWh/a")
    log(f"Leistung Hafen:    {mwp_haf:.1f} MWp")
    log(f"Ertrag Hafen:      {gwh_haf:.1f} GWh/a")

    return {
        "col_pv":  c_pv,
        "col_ert": c_ert,
        "col_eig": c_eig,
        # Hafen
        "n_hafen":      len(dachseiten_hafen),
        "pv_hafen":     pv_haf,
        "ertrag_hafen": ert_haf,
        "mwp_hafen":    mwp_haf,
        "gwh_hafen":    gwh_haf,
        # Hamburg gesamt
        "n_gesamt":      len(dachseiten_gesamt),
        "pv_gesamt":     pv_ges,
        "ertrag_gesamt": ert_ges,
        "mwp_gesamt":    mwp_ges,
        "gwh_gesamt":    gwh_ges,
    }


def berechne_parkplatz_stats(parkplaetze):
    if parkplaetze is None or len(parkplaetze) == 0:
        return None

    parkplaetze = parkplaetze.copy()
    parkplaetze['flaeche_m2']       = parkplaetze.geometry.area
    parkplaetze['solar_flaeche_m2'] = (parkplaetze['flaeche_m2'] * PARK_NUTZFAKTOR).round(0)
    parkplaetze['solar_kwp']        = (parkplaetze['solar_flaeche_m2'] * WP_PRO_M2).round(1)
    parkplaetze['solar_kwha']       = (parkplaetze['solar_kwp'] * KWH_PRO_KWP).round(0)

    flaeche_ges = parkplaetze['flaeche_m2'].sum()
    mwp_ges, gwh_ges = _solar(parkplaetze['solar_flaeche_m2'].sum())

    log(f"Parkplatzfläche:   {flaeche_ges:,.0f} m²")
    log(f"Solar-Leistung:    {mwp_ges:.1f} MWp")
    log(f"Solar-Ertrag:      {gwh_ges:.1f} GWh/a")

    return {
        "parkplaetze":  parkplaetze,
        "n":            len(parkplaetze),
        "flaeche_ges":  flaeche_ges,
        "mwp_ges":      mwp_ges,
        "gwh_ges":      gwh_ges,
    }


def berechne_hafen_flaeche(hafen):
    return hafen.geometry.area.sum() / 1_000_000
