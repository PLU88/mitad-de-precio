"""Sondeo temporal: estructura de El Volcán (PrestaShop), Le Creuset y Casaideas."""
import re, gzip, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
def get(url, acepta="text/html"):
    h = {"User-Agent": UA, "Accept": acepta, "Accept-Encoding": "gzip", "Accept-Language": "es-CL,es;q=0.9"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40) as x:
        b = x.read(); b = gzip.decompress(b) if x.headers.get("Content-Encoding") == "gzip" else b
        return x.geturl(), b.decode("utf-8", "replace")
try:
    _, h = get("https://www.elvolcan.cl/productos-rebajados")
    i = h.find("regular-price")
    print("[volcan] trozo:", re.sub(r"\s+", " ", h[max(0, i - 2500):i + 600]))
    print("[volcan] paginación:", sorted(set(re.findall(r'href="([^"]*productos-rebajados\?page=\d+)"', h)))[-3:])
except Exception as e:
    print("[volcan] ERROR", e)
for dom in ["www.lecreuset.cl", "www.casaideas.cl"]:
    try:
        final, h = get(f"https://{dom}/")
        pistas = [p for p in ["vtex", "shopify", "magento", "woocommerce", "demandware", "salesforce", "prestashop", "jumpseller", "bsale", "__NEXT_DATA__", "nuxt", "wix", "vtexassets", "mage/", "graphql", "algolia", "searchspring", "klevu", "doofinder", "constructor.io"] if p.lower() in h.lower()]
        print(f"[{dom}] {final} bytes={len(h)} pistas={pistas}")
        print("   urls:", sorted(set(re.findall(r'https?://[a-z0-9.-]+\.(?:com|cl|io|net)/?', h)))[:40])
    except Exception as e:
        print(f"[{dom}] ERROR", e)
for u in ["https://www.lecreuset.cl/api/catalog_system/pub/products/search?_from=0&_to=1", "https://www.lecreuset.cl/products.json?limit=1",
          "https://www.lecreuset.cl/graphql?query=%7BstoreConfig%7Bstore_code%7D%7D"]:
    try:
        f, t = get(u, "application/json"); print("[lecreuset]", u, "->", t[:300])
    except Exception as e:
        print("[lecreuset]", u, "ERROR", e)
