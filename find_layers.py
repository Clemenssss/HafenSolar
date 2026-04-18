"""
Findet WFS-URL und featureType für Masterportal-Layer-IDs.
Führe aus:  python find_layers.py
"""
import requests, json, sys

SERVICES_JSON_URL = "https://geoportal-hamburg.de/lgv-config/services-internet.json"
#SERVICES_JSON_URL = "https://geoportal-hamburg.de/lgv-config/services-fhhnet.json"
# Die Layer-IDs aus deiner Geoportal-URL:
TARGET_IDS = {"19969", "12883", "34570", "16101", "16102", "30916", "30915"}

print(f"Lade {SERVICES_JSON_URL} ...")
r = requests.get(SERVICES_JSON_URL, timeout=60,
                 headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()
print(f"HTTP {r.status_code}, {len(r.content)//1024} KB")

data = json.loads(r.content.decode("utf-8-sig"))
# services-internet.json ist eine Liste von Layer-Objekten
if isinstance(data, dict):
    # Manchmal ist es ein Dict mit einem "layers"-Key
    layers = data.get("layers", data.get("services", list(data.values())[0]))
else:
    layers = data

print(f"\n{len(layers)} Layer total\n")
print("="*70)

found = {}
for layer in layers:
    lid = str(layer.get("id", ""))
    if lid in TARGET_IDS:
        found[lid] = layer
        name = layer.get("name", "?")
        typ  = layer.get("typ", "?")
        url  = layer.get("url", "?")
        ft   = layer.get("featureType", layer.get("layers", "?"))
        ns   = layer.get("featureNS", "")
        ver  = layer.get("version", "")
        print(f"ID: {lid}")
        print(f"  Name:        {name}")
        print(f"  Typ:         {typ}")
        print(f"  URL:         {url}")
        print(f"  featureType: {ft}")
        if ns:  print(f"  featureNS:   {ns}")
        if ver: print(f"  Version:     {ver}")
        print()
wfs_layers = []

for layer in layers:
    if layer.get("typ") == "WFS":
        wfs_layers.append({
            "id": layer.get("id"),
            "name": layer.get("name"),
            "url": layer.get("url"),
            "featureType": layer.get("featureType")
        })

print(f"{len(wfs_layers)} WFS-Layer gefunden:\n")
for l in wfs_layers[:20]:
    print(l)
missing = TARGET_IDS - set(found.keys())
if missing:
    print(f"Nicht gefunden: {missing}")
    print("(Möglicherweise in services-fhhnet.json oder anderer Datei)")
