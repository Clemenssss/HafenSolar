#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import locale
import os
from datetime import datetime

try:
    locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'German_Germany.1252')
    except:
        locale.setlocale(locale.LC_ALL, '')


def fmt_zahl(zahl, stellen=0):
    if zahl is None:
        return 'k.A.'
    if stellen == 0:
        return locale.format_string("%d", int(round(zahl)), grouping=True)
    return locale.format_string(f"%.{stellen}f", zahl, grouping=True)


def ts():
    return datetime.now().strftime("[%H:%M:%S]")


def log(msg):
    print(f"{ts()} {msg}")


def col(gdf, *candidates):
    """Ersten passenden Spaltennamen zurückgeben (case-insensitiv)."""
    for c in candidates:
        for colname in gdf.columns:
            if colname.lower() == c.lower():
                return colname
    return None


def excel_dateiname(basis="hafen_solar_dachseiten.xlsx"):
    if not os.path.exists(basis):
        return basis
    name, ext = os.path.splitext(basis)
    i = 1
    while os.path.exists(f"{name} ({i}){ext}"):
        i += 1
    return f"{name} ({i}){ext}"
