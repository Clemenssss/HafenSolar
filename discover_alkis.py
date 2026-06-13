"""
Discover-Script: ALKIS Tatsächliche Nutzung WFS Hamburg
=========================================================
Findet den korrekten Layer-Namen für die ALKIS-Nutzungsarten.

Ausführen:
    python discover_alkis.py
"""
import requests
import xml.etree.ElementTree as ET

WFS_CANDIDATES = [
    "https://geodienste.hamburg.de/WFS_HH_ALKIS_vereinfacht",
    "https://geodienste.hamburg.de/HH_WFS_ALKIS_Tatsaechliche_Nutzung",
    "https://geodienste.hamburg.de/HH_WFS_ALKIS_Nutzung",
]


def discover():
    print("=== WFS-Endpunkt Suche: ALKIS Tatsächliche Nutzung ===\n")
    for url in WFS_CANDIDATES:
        try:
            r = requests.get(url, params={
                "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetCapabilities"
            }, timeout=20)
            if r.status_code != 200:
                print(f"  ✗  HTTP {r.status_code}  →  {url}")
                continue

            root = ET.fromstring(r.content)
            layers = []
            for ns_uri in [
                "http://www.opengis.net/wfs/2.0",
                "http://www.opengis.net/wfs",
            ]:
                tag_ft   = f"{{{ns_uri}}}FeatureType"
                tag_name = f"{{{ns_uri}}}Name"
                for ft in root.iter(tag_ft):
                    n = ft.find(tag_name)
                    if n is not None and n.text:
                        layers.append(n.text)

            if layers:
                print(f"  ✓  {url}")
                # Nur Layer mit "nutzung" im Namen hervorheben
                for l in layers:
                    marker = "  ← Nutzung!" if "nutz" in l.lower() else ""
                    print(f"       {l}{marker}")
            else:
                print(f"  ?  {url}  (200 OK, keine Layer gefunden)")
            print()
        except Exception as e:
            print(f"  ✗  {url}  →  {e}\n")


if __name__ == "__main__":
    discover()