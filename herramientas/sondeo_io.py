"""Sondeo temporal: Casaideas (Magento headless), Le Creuset (Salesforce) y Zuhaus."""
import re, gzip, json, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
def get(url, acepta="text/html", extra=None):
    h = {"User-Agent": UA, "Accept": acepta, "Accept-Encoding": "gzip", "Accept-Language": "es-CL,es;q=0.9"}; h.update(extra or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40) as x:
        b = x.read(); b = gzip.decompress(b) if x.headers.get("Content-Encoding") == "gzip" else b
        return x.geturl(), b.decode("utf-8", "replace")
q = '{products(search:"",pageSize:2,filter:{price:{from:"1"}}){total_count items{name sku url_key price_range{minimum_price{regular_price{value} final_price{value}}}}}}'
for base in ["https://headless.casaideas.cl/graphql", "https://mcintegration.casaideas.cl/graphql", "https://www.casaideas.cl/graphql", "https://www.casaideas.cl/api/graphql"]:
    try:
        f, t = get(base + "?query=" + urllib.parse.quote(q), "application/json"); print("[casaideas]", base, "->", t[:400])
    except Exception as e:
        print("[casaideas]", base, "ERROR", e)
try:
    f, h = get("https://www.casaideas.cl/")
    nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    if nd:
        d = json.loads(nd.group(1)); print("[casaideas] runtime", json.dumps(d.get("runtimeConfig") or {}, ensure_ascii=False)[:600], "| page", d.get("page"))
    print("[casaideas] endpoints", sorted(set(re.findall(r'https?://[a-z0-9.-]*casaideas[a-z0-9.-]*/[a-zA-Z0-9_/.-]*', h)))[:30])
except Exception as e:
    print("[casaideas] ERROR", e)
try:
    f, h = get("https://www.lecreuset.cl/")
    print("[lecreuset] sites:", sorted(set(re.findall(r'Sites-[A-Za-z0-9_-]+-Site', h)))[:10], "| demandware:", "demandware" in h, "| commercecloud:", "commercecloud" in h.lower(), "| mobify/pwa:", "mobify" in h.lower() or "pwa-kit" in h.lower())
    print("   ", sorted(set(re.findall(r'href="(/[a-z0-9-]+/?)"', h)))[:40])
except Exception as e:
    print("[lecreuset] ERROR", e)
for u in ["https://zuhaus.cl/products.json?limit=5", "https://zuhaus.cl/wp-json/wc/store/v1/products?per_page=2", "https://zuhaus.cl/"]:
    try:
        f, t = get(u, "application/json" if "json" in u else "text/html"); print("[zuhaus]", u, "->", t[:300].replace("\n", " "))
    except Exception as e:
        print("[zuhaus]", u, "ERROR", e)
