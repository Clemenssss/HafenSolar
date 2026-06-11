#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import folium

from config import (FARBEN_DACHSEITEN, FARBE_PARKPLATZ, FARBE_PARKPLATZ_RAND,
                    HAMBURG_FLAECHE_KM2,
                    FARBE_MASTR_BETRIEB, FARBE_MASTR_STILL, FARBE_MASTR_RAND,
                    FARBE_HALDE, FARBE_HALDE_RAND,
                    FARBE_GEWERBE_FREI, FARBE_GEWERBE_RAND,
                    FARBE_BRACHE_OSM, FARBE_BRACHE_OSM_RAND)
from utils import fmt_zahl

import math


def _farbe_dachseite(feature):
    v = feature['properties'].get('eignung', '')
    try:
        v = int(str(v).split()[1])
    except:
        v = 0
    return {
        "color":       FARBEN_DACHSEITEN.get(v, '#cccccc'),
        "weight":      0.5,
        "fillOpacity": 0.8,
    }


def _tooltip_dachseiten():
    return folium.GeoJsonTooltip(
        fields=['area', 'aspect', 'aufstd', 'buildingid', 'eignung', 'eignung_t',
                'ertkwp_k', 'ertkwp_ka', 'ertkwha_k', 'ertkwha_ka',
                'percentms', 'percentmsa', 'power', 'pvarea', 'pvareat',
                'roofid', 'schatten', 'schattena', 'slope'],
        aliases=['Fläche Dachseite [m²]', 'Ausrichtung [°]', 'Aufständerung [0/1]',
                 'ID Gebäude', 'Eignung PV', 'Eignung Solarthermie',
                 'Ertrag [kWh/kWp/a] ohne Aufstd', 'Ertrag [kWh/kWp/a] mit Aufstd',
                 'Ertrag [kWh/a] ohne Aufstd', 'Ertrag [kWh/a] mit Aufstd',
                 'Einstrahlung ohne Aufstd [%]', 'Einstrahlung mit Aufstd [%]',
                 'Power [kWp]', 'Fläche PV [m²]', 'Fläche ST [m²]',
                 'ID Dachseite', 'Schatten ohne Aufstd [%/a]',
                 'Schatten mit Aufstd [%/a]', 'Neigung [°]'],
        localize=True,
        sticky=True,
    )


def _tooltip_parkplaetze():
    return folium.GeoJsonTooltip(
        fields=['name', 'operator', 'flaeche_m2', 'solar_flaeche_m2',
                'solar_kwp', 'solar_kwha', 'capacity', 'covered',
                'surface', 'parking', 'building:levels', 'roof:levels',
                'maxheight', 'access', 'fee'],
        aliases=['Name', 'Betreiber', 'Fläche [m²]', 'Solar-Nutzfläche [m²]',
                 'Leistung (ca.) [kWp]', 'Ertrag (ca.) [kWh/a]',
                 'Stellplätze', 'Überdacht', 'Belag',
                 'Typ', 'Stockwerke Gebäude', 'Stockwerke Dach',
                 'Max. Höhe', 'Zugang', 'Gebührenpflichtig'],
        localize=True,
        sticky=True,
    )


def _tooltip_halden():
    return folium.GeoJsonTooltip(
        fields=['nutzart', 'bez', 'flaeche_m2'],
        aliases=['Nutzungsart', 'Bezeichnung', 'Fläche [m²]'],
        localize=True,
        sticky=True,
    )


def _tooltip_gewerbe_frei():
    return folium.GeoJsonTooltip(
        fields=['nutzart', 'bez', 'flaeche_m2'],
        aliases=['Nutzungsart (umliegend)', 'Bezeichnung', 'Fläche unbebaut [m²]'],
        localize=True,
        sticky=True,
    )


def _tooltip_brache_osm():
    return folium.GeoJsonTooltip(
        fields=['name', 'landuse', 'flaeche_m2'],
        aliases=['Name', 'OSM landuse', 'Fläche [m²]'],
        localize=True,
        sticky=True,
    )


def _radius_kwp(kwp, min_r=5, max_r=20):
    """Kreisradius logarithmisch skaliert nach kWp."""
    if kwp is None or kwp <= 0:
        return min_r
    return min(max_r, min_r + math.log1p(kwp) * 1.8)


def _mastr_popup_html(row) -> str:
    """HTML-Popup für eine MaStR-Anlage."""
    def val(key, einheit="", default="k.A."):
        v = row.get(key)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        if einheit:
            return f"{v} {einheit}"
        return str(v)

    kwp = row.get("leistung_kwp")
    kwp_str = f"{kwp:,.1f} kWp".replace(",", ".") if kwp else "k.A."

    ertrag_str = "k.A."
    if kwp:
        ertrag_kwh = kwp * 950
        ertrag_str = f"{ertrag_kwh:,.0f} kWh/a".replace(",", ".")

    status = row.get("status_text", "unbekannt")
    farbe  = FARBE_MASTR_BETRIEB if "Betrieb" in status else FARBE_MASTR_STILL

    adresse_teile = [
        row.get("strasse"), row.get("plz"), row.get("ort")
    ]
    adresse = " ".join(str(t) for t in adresse_teile if t and str(t) != "nan") or "k.A."

    return f"""
<div style="font-family:Arial,sans-serif;font-size:12px;min-width:220px;">
  <div style="background:{farbe};color:white;padding:5px 8px;border-radius:4px 4px 0 0;
              font-weight:bold;font-size:13px;">
    ⚡ {val('mastr_name', default='PV-Anlage')}
  </div>
  <table style="width:100%;border-collapse:collapse;margin-top:4px;">
    <tr><td style="color:#666;padding:2px 4px;">Status</td>
        <td style="padding:2px 4px;font-weight:bold;">{status}</td></tr>
    <tr style="background:#f9f9f9;">
        <td style="color:#666;padding:2px 4px;">Leistung</td>
        <td style="padding:2px 4px;font-weight:bold;">{kwp_str}</td></tr>
    <tr><td style="color:#666;padding:2px 4px;">Jahresertrag (ca.)</td>
        <td style="padding:2px 4px;">{ertrag_str}</td></tr>
    <tr><td style="color:#666;padding:2px 4px;">Inbetriebnahme</td>
        <td style="padding:2px 4px;">{val('inbetriebnahme')}</td></tr>
    <tr style="background:#f9f9f9;">
        <td style="color:#666;padding:2px 4px;">Lage</td>
        <td style="padding:2px 4px;">{val('lage')}</td></tr>
    <tr><td style="color:#666;padding:2px 4px;">Adresse</td>
        <td style="padding:2px 4px;">{adresse}</td></tr>
    <tr style="background:#f9f9f9;">
        <td style="color:#666;padding:2px 4px;">MaStR-Nr.</td>
        <td style="padding:2px 4px;font-size:11px;">{val('mastr_id')}</td></tr>
  </table>
</div>
"""


def _legende(ds_stats, pp_stats, mastr_stats, mastr_hamburg, hafen_km2,
              halden_stats=None, gewerbe_stats=None, brache_stats=None):
    f = fmt_zahl

    park_block = ""
    if pp_stats:
        park_block = f'''
    <hr style="margin:8px 0;">
    <b>🅿️ Parkplätze (OSM)</b><br>
    <span style="background:{FARBE_PARKPLATZ};padding:1px 10px;margin-right:6px;">&nbsp;</span>Parkplatzfläche<br>
    🅿️ Anzahl: <b>{f(pp_stats["n"])}</b><br>
    📐 Fläche gesamt: <b>{f(pp_stats["flaeche_ges"])} m²</b><br>
    ⚡ Solar-Potenzial (ca.): <b>{f(pp_stats["mwp_ges"], 1)} MWp</b><br>
    🔋 Ertrag (ca.): <b>{f(pp_stats["gwh_ges"], 1)} GWh/Jahr</b><br>
    <span style="font-size:11px;color:grey;">Annahme: 80% Nutzfläche, 175 Wp/m², 950 kWh/kWp/a</span><br>'''

    mastr_block = ""
    if mastr_stats:
        if mastr_hamburg:
            n_zeile   = f'📍 Anlagen: <b>{f(mastr_stats["n"])}</b> (Hamburg: {f(mastr_hamburg["n"])})<br>'
            kwp_zeile = (f'⚡ Installierte Leistung: <b>{f(mastr_stats["kwp_gesamt"], 1)} kWp</b> '
                         f'(Hamburg: {f(mastr_hamburg["kwp_gesamt"], 1)} kWp)<br>')
            gwh_zeile = (f'🔋 Ertrag (ca.): <b>{f(mastr_stats["gwh_gesamt"], 1)} GWh/Jahr</b> '
                         f'(Hamburg: {f(mastr_hamburg["gwh_gesamt"], 1)} GWh/Jahr)<br>')
        else:
            n_zeile   = f'📍 Anlagen: <b>{f(mastr_stats["n"])}</b><br>'
            kwp_zeile = f'⚡ Installierte Leistung: <b>{f(mastr_stats["kwp_gesamt"], 1)} kWp</b><br>'
            gwh_zeile = f'🔋 Ertrag (ca.): <b>{f(mastr_stats["gwh_gesamt"], 1)} GWh/Jahr</b><br>'

        mastr_block = f'''
    <hr style="margin:8px 0;">
    <b>⚡ Installierte PV-Anlagen (MaStR)</b><br>
    <span style="background:{FARBE_MASTR_BETRIEB};display:inline-block;
          width:12px;height:12px;border-radius:50%;margin-right:6px;
          vertical-align:middle;border:1px solid #1a7a3a;">&nbsp;</span>In Betrieb<br>
    <span style="background:{FARBE_MASTR_STILL};display:inline-block;
          width:12px;height:12px;border-radius:50%;margin-right:6px;
          vertical-align:middle;border:1px solid #888;">&nbsp;</span>Stillgelegt / Sonstige<br>
    {n_zeile}
    {kwp_zeile}
    {gwh_zeile}
    <span style="font-size:11px;color:grey;">Kreisgröße ∝ Leistung (log). Annahme: 950 kWh/kWp/a. Quelle: BNetzA MaStR</span>'''

    brachen_block = ""
    if halden_stats or gewerbe_stats or brache_stats:
        zeilen = []
        if halden_stats:
            zeilen.append(
                f'<span style="background:{FARBE_HALDE};padding:1px 10px;margin-right:6px;">&nbsp;</span>'
                f'Halden/Tagebau (ALKIS): <b>{f(halden_stats["n"])}</b> – '
                f'{f(halden_stats["flaeche_m2"])} m²<br>'
            )
        if gewerbe_stats:
            zeilen.append(
                f'<span style="background:{FARBE_GEWERBE_FREI};padding:1px 10px;margin-right:6px;">&nbsp;</span>'
                f'Unbebaute Gewerbeflächen (ALKIS, ≥ 500 m²): <b>{f(gewerbe_stats["n"])}</b> – '
                f'{f(gewerbe_stats["flaeche_m2"])} m² '
                f'({f(gewerbe_stats["flaeche_m2"]/10000, 1)} ha)<br>'
            )
        if brache_stats:
            zeilen.append(
                f'<span style="background:{FARBE_BRACHE_OSM};padding:1px 10px;margin-right:6px;">&nbsp;</span>'
                f'Brachflächen (OSM): <b>{f(brache_stats["n"])}</b> – '
                f'{f(brache_stats["flaeche_m2"])} m²<br>'
            )
        brachen_block = f'''
    <hr style="margin:8px 0;">
    <b>🏗️ Brach- und ungenutzte Flächen</b><br>
    {"".join(zeilen)}
    <span style="font-size:11px;color:grey;">ALKIS Tatsächliche Nutzung (LGV) + OpenStreetMap. "Unbebaute Gewerbeflächen" = Industrie/Gewerbe-Parzellen minus Gebäude-Footprint, kann auch Lager-/Stellflächen enthalten.</span>'''

    return f'''
<div style="position:fixed;bottom:30px;left:30px;background:white;padding:12px 16px;
            border-radius:8px;box-shadow:2px 2px 6px grey;font-size:13px;z-index:1000;
            font-family:Arial,sans-serif;min-width:280px;max-width:320px;
            word-wrap:break-word;max-height:80vh;overflow-y:auto;">
    <b style="font-size:14px;">☀️ Solarpotenzial Hamburger Hafen</b><br><br>
    🏠 Dachseiten: <b>{f(ds_stats["n_hafen"])}</b> (Hamburg: {f(ds_stats["n_gesamt"])})<br>
    📐 PV-Fläche: <b>{f(ds_stats["pv_hafen"])} m²</b> (Hamburg: {f(ds_stats["pv_gesamt"])} m²)<br>
    ⚡ Leistung (ca.): <b>{f(ds_stats["mwp_hafen"], 1)} MWp</b> (Hamburg: {f(ds_stats["mwp_gesamt"], 1)} MWp)<br>
    🔋 Ertrag (ca.): <b>{f(ds_stats["gwh_hafen"], 1)} GWh/Jahr</b> (Hamburg: {f(ds_stats["gwh_gesamt"], 1)} GWh/Jahr)<br>
    📏 Hafengebiet: <b>{f(hafen_km2, 1)} km²</b> (Hamburg: {f(HAMBURG_FLAECHE_KM2, 1)} km²)<br>
    <hr style="margin:8px 0;">
    <b>Eignung Photovoltaik</b><br>
    <span style="background:{FARBEN_DACHSEITEN[1]};padding:1px 10px;margin-right:6px;">&nbsp;</span>Eignung 1 – sehr hohe Einstrahlung<br>
    <span style="background:{FARBEN_DACHSEITEN[2]};padding:1px 10px;margin-right:6px;">&nbsp;</span>Eignung 2 – hohe Einstrahlung<br>
    <span style="background:{FARBEN_DACHSEITEN[3]};padding:1px 10px;margin-right:6px;">&nbsp;</span>Eignung 3 – mittlere Einstrahlung<br>
    <span style="background:{FARBEN_DACHSEITEN[6]};padding:1px 10px;margin-right:6px;">&nbsp;</span>Eignung 6 – geringe Einstrahlung<br>
    <span style="background:{FARBEN_DACHSEITEN[0]};padding:1px 10px;margin-right:6px;border:1px solid #ccc;">&nbsp;</span>Eignung 0 – Datenqualität unzureichend<br>
    <span style="background:{FARBEN_DACHSEITEN[8]};padding:1px 10px;margin-right:6px;border:1px solid #ccc;">&nbsp;</span>Eignung 8 – kein Gebäude erkannt<br>
    {park_block}
    {mastr_block}
    {brachen_block}
    <hr style="margin:8px 0;">
    <span style="font-size:11px;color:grey;">Quellen: WFS Solarpotenzialflächen Hamburg (LGV), OpenStreetMap, MaStR (BNetzA), ALKIS (LGV)</span>
</div>
'''


def _mastr_stats(mastr_anlagen):
    if mastr_anlagen is None or mastr_anlagen.empty:
        return None
    kwp = mastr_anlagen["leistung_kwp"].sum() if "leistung_kwp" in mastr_anlagen.columns else 0
    return {
        "n":           len(mastr_anlagen),
        "kwp_gesamt":  kwp,
        "gwh_gesamt":  kwp / 1_000_000 * 950,
    }


def erstelle_karte(hafen, dachseiten_hafen, ds_stats, pp_stats,
                   mastr_anlagen=None, mastr_hamburg=None,
                   halden=None, gewerbe_frei=None, brache_osm=None):
    centroid = hafen.geometry.centroid.to_crs(4326)
    center   = [centroid.y.mean(), centroid.x.mean()]

    m = folium.Map(location=center, zoom_start=14, tiles='CartoDB positron')

    # Hafengrenze
    folium.GeoJson(
        hafen.to_crs(4326),
        name="Hafengrenze",
        style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.05}
    ).add_to(m)

    # Dachseiten
    folium.GeoJson(
        dachseiten_hafen.to_crs(4326),
        name=f"Dachseiten ({fmt_zahl(len(dachseiten_hafen))})",
        style_function=_farbe_dachseite,
        tooltip=_tooltip_dachseiten(),
    ).add_to(m)

    # Parkplätze
    if pp_stats:
        pp_wgs = pp_stats["parkplaetze"].to_crs(4326)
        folium.GeoJson(
            pp_wgs,
            name=f"Parkplätze OSM ({pp_stats['n']})",
            style_function=lambda x: {
                "color":       FARBE_PARKPLATZ_RAND,
                "fillColor":   FARBE_PARKPLATZ,
                "weight":      1,
                "fillOpacity": 0.6,
            },
            tooltip=_tooltip_parkplaetze(),
        ).add_to(m)

    # MaStR-Anlagen
    ms = _mastr_stats(mastr_anlagen)
    if mastr_anlagen is not None and not mastr_anlagen.empty:
        layer_name = f"Installierte PV-Anlagen MaStR ({ms['n']})"
        fg = folium.FeatureGroup(name=layer_name)
        anlagen_wgs = mastr_anlagen.to_crs(4326)

        for _, row in anlagen_wgs.iterrows():
            status = row.get("status_text", "")
            in_betrieb = "Betrieb" in str(status)
            farbe = FARBE_MASTR_BETRIEB if in_betrieb else FARBE_MASTR_STILL
            rand  = "#1a7a3a" if in_betrieb else "#888888"

            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=_radius_kwp(row.get("leistung_kwp")),
                color=rand,
                weight=1,
                fill=True,
                fill_color=farbe,
                fill_opacity=0.85,
                popup=folium.Popup(
                    _mastr_popup_html(row),
                    max_width=280,
                ),
            ).add_to(fg)

        fg.add_to(m)

    # Layer: Halden / Tagebau (ALKIS) – "enge" Brachen
    halden_stats = None
    if halden is not None and not halden.empty:
        halden_stats = {
            "n":          len(halden),
            "flaeche_m2": halden["flaeche_m2"].sum(),
        }
        folium.GeoJson(
            halden.to_crs(4326),
            name=f"Halden/Tagebau ALKIS ({halden_stats['n']})",
            style_function=lambda x: {
                "color":       FARBE_HALDE_RAND,
                "fillColor":   FARBE_HALDE,
                "weight":      1,
                "fillOpacity": 0.6,
            },
            tooltip=_tooltip_halden(),
        ).add_to(m)

    # Layer: Unbebaute Gewerbeflächen (ALKIS minus Gebäude)
    gewerbe_stats = None
    if gewerbe_frei is not None and not gewerbe_frei.empty:
        gewerbe_stats = {
            "n":          len(gewerbe_frei),
            "flaeche_m2": gewerbe_frei["flaeche_m2"].sum(),
        }
        folium.GeoJson(
            gewerbe_frei.to_crs(4326),
            name=f"Unbebaute Gewerbeflächen ALKIS ({gewerbe_stats['n']})",
            style_function=lambda x: {
                "color":       FARBE_GEWERBE_RAND,
                "fillColor":   FARBE_GEWERBE_FREI,
                "weight":      1,
                "fillOpacity": 0.45,
            },
            tooltip=_tooltip_gewerbe_frei(),
        ).add_to(m)

    # Layer: Brachflächen (OSM)
    brache_stats = None
    if brache_osm is not None and not brache_osm.empty:
        brache_stats = {
            "n":          len(brache_osm),
            "flaeche_m2": brache_osm["flaeche_m2"].sum(),
        }
        folium.GeoJson(
            brache_osm.to_crs(4326),
            name=f"Brachflächen OSM ({brache_stats['n']})",
            style_function=lambda x: {
                "color":       FARBE_BRACHE_OSM_RAND,
                "fillColor":   FARBE_BRACHE_OSM,
                "weight":      1,
                "fillOpacity": 0.5,
            },
            tooltip=_tooltip_brache_osm(),
        ).add_to(m)

    hafen_km2 = hafen.geometry.area.sum() / 1_000_000
    m.get_root().html.add_child(
        folium.Element(_legende(ds_stats, pp_stats, ms, mastr_hamburg, hafen_km2,
                                halden_stats, gewerbe_stats, brache_stats))
    )
    folium.LayerControl().add_to(m)
    return m