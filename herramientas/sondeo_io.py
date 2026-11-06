"""Sondeo temporal: Construmart (Magento) y Magenta Glass (Jumpseller)."""
import re, gzip, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
def get(url, acepta="text/html"):
    h = {"User-Agent": UA, "Accept": acepta, "Accept-Encoding": "gzip", "Accept-Language": "es-CL,es;q=0.9"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40) as x:
        b = x.read(); b = gzip.decompress(b) if x.headers.get("Content-Encoding") == "gzip" else b
        return x.geturl(), b.decode("utf-8", "replace")
q = '{products(search:"",pageSize:2,filter:{price:{from:"1"}}){total_count items{name}}}'
try:
    print("[construmart gql]", get("https://www.construmart.cl/graphql?query=" + urllib.parse.quote(q), "application/json")[1][:300])
except Exception as e:
    print("[construmart gql] ERROR", e)
for dom in ["www.construmart.cl", "magentaglass.cl"]:
    try:
        f, h = get(f"https://{dom}/")
        print(f"[{dom}] ofertas:", sorted(set(re.findall(r'href="([^"#]*(?:oferta|sale|outlet|descuento|liquida|cyber|promo)[^"#]*)"', h, re.I)))[:15])
        print(f"[{dom}] categorias:", sorted(set(re.findall(r'href="(https?://' + re.escape(dom) + r'/[a-z0-9-]+(?:\.html)?/?)"', h)))[:30])
        print(f"[{dom}] grid: product-item-info={h.count('product-item-info')} oldPrice={h.count('oldPrice')} product-block={h.count('product-block')} price-compare={h.count('compare')}")
    except Exception as e:
        print(f"[{dom}] ERROR", e)
