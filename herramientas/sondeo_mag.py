"""Sondeo temporal: tiendas Magento (API y grilla HTML)."""
import re, gzip, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
def get(url, acepta="text/html"):
    h = {"User-Agent": UA, "Accept": acepta, "Accept-Encoding": "gzip", "Accept-Language": "es-CL,es;q=0.9"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40) as x:
        b = x.read(); b = gzip.decompress(b) if x.headers.get("Content-Encoding") == "gzip" else b
        return x.geturl(), b.decode("utf-8", "replace")
q = '{products(search:"",pageSize:100,filter:{price:{from:"1"}}){total_count items{name price_range{minimum_price{regular_price{value} final_price{value}}}}}}'
for dom in ["stern.cl", "cannonhome.cl", "www.surprice.cl", "cl.todomoda.com", "www.kliper.cl"]:
    try:
        _, t = get(f"https://{dom}/graphql?query=" + urllib.parse.quote(q), "application/json")
        tot = re.search(r'"total_count":(\d+)', t); n50 = 0
        for r, f in re.findall(r'"regular_price":\{"value":([0-9.]+)\},"final_price":\{"value":([0-9.]+)\}', t):
            if float(r) > 0 and float(f) <= float(r) * 0.5: n50 += 1
        print(f"[{dom} gql] total={tot.group(1) if tot else None} con50(en 100)={n50} :: {t[:160]}")
    except Exception as e:
        print(f"[{dom} gql] ERROR {e}")
    try:
        _, h = get(f"https://{dom}/")
        ofertas = sorted(set(re.findall(r'href="((?:https?://[^"/]*)?/[^"#]*(?:oferta|sale|outlet|descuento|liquida|cyber|promo|rebaja)[^"#]*)"', h, re.I)))[:10]
        print(f"[{dom}] items={h.count('product-item-info')} oldPrice={h.count('oldPrice')} ofertas={ofertas}")
        for u in ofertas[:2]:
            u = urllib.parse.urljoin(f"https://{dom}/", u)
            try:
                _, g = get(u)
                print(f"   {u} items={g.count('product-item-info')} oldPrice={g.count('data-price-type=\"oldPrice\"')} vtex={'vtex' in g.lower()} total={re.findall(r'toolbar-number\">(\d+)', g)[:3]}")
            except Exception as e:
                print(f"   {u} ERROR {e}")
    except Exception as e:
        print(f"[{dom}] ERROR {e}")
