"""Sondeo temporal de iochile.cl: busca de dónde saca la página sus productos y precios."""
import re, json, gzip, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
def get(url, acepta="text/html", datos=None, extra=None):
    h = {"User-Agent": UA, "Accept": acepta, "Accept-Encoding": "gzip"}
    h.update(extra or {})
    r = urllib.request.Request(url, data=datos, headers=h)
    with urllib.request.urlopen(r, timeout=40) as x:
        b = x.read()
        b = gzip.decompress(b) if x.headers.get("Content-Encoding") == "gzip" else b
        return x.status, x.geturl(), b.decode("utf-8", "replace")
def prueba(nombre, url, **kw):
    try:
        s, final, t = get(url, **kw)
        print(f"[{nombre}] {s} {final} {len(t)}b :: {re.sub(chr(10), ' ', t[:400])}")
        return t
    except Exception as e:
        print(f"[{nombre}] ERROR {e}")
        return ""
home = prueba("home", "https://www.iochile.cl/")
hosts = sorted(set(re.findall(r'https?://[a-z0-9.-]+\.[a-z]{2,}(?:/[a-z0-9_./-]*)?', home)))
print("hosts/urls:", [h for h in hosts if "iochile" in h or "graphql" in h or "api" in h][:60])
nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', home, re.S)
if nd:
    d = json.loads(nd.group(1)); print("NEXT keys:", list(d.keys()), "| buildId", d.get("buildId"), "| runtimeConfig", json.dumps(d.get("runtimeConfig"))[:500])
    print("pageProps keys:", list((d.get("props") or {}).get("pageProps", {}).keys())[:40])
scripts = re.findall(r'<script[^>]+src="([^"]+\.js)"', home)
print("scripts:", scripts[:30])
vistos = set()
for src in scripts[:25]:
    u = urllib.parse.urljoin("https://www.iochile.cl/", src)
    try:
        _, _, js = get(u, "*/*")
    except Exception:
        continue
    for m in re.findall(r'["\'](https?://[a-z0-9.-]+(?:/[a-zA-Z0-9_./-]*)?(?:graphql|/rest/|/api/)[a-zA-Z0-9_./-]*)["\']', js):
        if m not in vistos:
            vistos.add(m); print("  endpoint en", src[-40:], "->", m)
    for m in re.findall(r'(?:graphql|GRAPHQL|magento|MAGENTO)[A-Z_]*["\']?\s*[:=]\s*["\']([^"\']{6,120})["\']', js):
        if m not in vistos:
            vistos.add(m); print("  config ->", m)
q = '{products(search:"",pageSize:2,currentPage:1){total_count items{name sku url_key price_range{minimum_price{regular_price{value} final_price{value}}}}}}'
for base in ["https://www.iochile.cl/graphql", "https://iochile.cl/graphql", "https://www.iochile.cl/api/graphql", "https://admin.iochile.cl/graphql", "https://api.iochile.cl/graphql", "https://backend.iochile.cl/graphql", "https://magento.iochile.cl/graphql", "https://tienda.iochile.cl/graphql"]:
    prueba("gql " + base, base + "?query=" + urllib.parse.quote(q), acepta="application/json")
prueba("gql POST", "https://www.iochile.cl/graphql", acepta="application/json", datos=json.dumps({"query": q}).encode(), extra={"Content-Type": "application/json", "Store": "default"})
prueba("rest", "https://www.iochile.cl/rest/V1/products?searchCriteria[pageSize]=2", acepta="application/json")
prueba("sitemap", "https://www.iochile.cl/sitemap.xml")
prueba("ofertas", "https://www.iochile.cl/ofertas")
prueba("sale", "https://www.iochile.cl/sale")
