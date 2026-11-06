"""Sondeo temporal: cómo muestran las tallas las grillas Salesforce."""
import re, urllib.request, gzip
UA = "Mozilla/5.0 (compatible; PriveOfertazosBot/1.0)"
def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(r, timeout=40) as x:
        b = x.read()
        return (gzip.decompress(b) if x.headers.get("Content-Encoding") == "gzip" else b).decode("utf-8", "replace")
import sys, json
for t in json.load(open("tiendas.json")):
    if t["nombre"] not in ("Tricot", "Hites", "abc"):
        continue
    url = f"https://{t['dominio']}/on/demandware.store/Sites-{t['sitio']}-Site/default/Search-UpdateGrid?cgid={t.get('categoria','root')}&start=0&sz=12" + (f"&srule={t.get('orden','discount-off')}" if t.get('orden','discount-off') else "")
    try:
        h = get(url)
    except Exception as e:
        print(t["nombre"], "ERROR", e); continue
    print("=====", t["nombre"], len(h))
    for pat in [r"(?is)<[^>]*(?:tile-variation-Talla|swatch|size|talla)[^>]*>", r"dwvar_\w+?=([^&\"]+)"]:
        vistos = []
        for m in re.finditer(pat, h):
            v = re.sub(r"\s+", " ", m.group(0))[:220]
            if v not in vistos: vistos.append(v)
        print(" patrón", pat[:30], len(vistos))
        for v in vistos[:14]: print("   ", v)
