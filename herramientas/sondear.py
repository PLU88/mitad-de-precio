"""Sondea muchas tiendas con varios métodos y escribe muestras/sondeo.json con lo que respondió cada una."""
import concurrent.futures as cf, gzip, json, os, re, ssl, sys, urllib.request, urllib.error

UA = "Mozilla/5.0 (compatible; MitadDePrecioBot/1.0; +https://mitad-de-precio.vercel.app/)"
NAV = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
LAXO = ssl.create_default_context(); LAXO.check_hostname = False; LAXO.verify_mode = ssl.CERT_NONE


def get(url, ua=UA, acepta="application/json"):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={
            "User-Agent": ua, "Accept": acepta, "Accept-Encoding": "gzip", "Accept-Language": "es-CL,es;q=0.9"}),
            timeout=15, context=LAXO)
        b = r.read(4_000_000); b = gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b
        return r.status, r.geturl(), b.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        return "ERR", url, str(e)[:60]


def cuenta50(pares):
    return sum(1 for p, n in pares if n and p and n > p and 1 - p / n >= 0.5)


def sondear(d):
    r = {"dominio": d}
    c, f, b = get(f"https://{d}/products.json?limit=250")
    if c == 200 and b.lstrip().startswith('{"products"'):
        ps = json.loads(b)["products"]; pares = []
        for p in ps:
            for v in p.get("variants", [])[:1]:
                try: pares.append((float(v.get("price") or 0), float(v.get("compare_at_price") or 0)))
                except ValueError: pass
        return {**r, "tipo": "shopify", "productos": len(ps), "con50": cuenta50(pares), "final": f}
    c, f, b = get(f"https://{d}/api/catalog_system/pub/products/search?_from=0&_to=49&O=OrderByBestDiscountDESC")
    if c in (200, 206) and b.lstrip().startswith("["):
        ps = json.loads(b); pares = []
        for p in ps:
            try:
                co = p["items"][0]["sellers"][0]["commertialOffer"]; pares.append((co["Price"], co["ListPrice"]))
            except (KeyError, IndexError): pass
        return {**r, "tipo": "vtex", "productos": len(ps), "con50": cuenta50(pares), "final": f}
    c, f, b = get(f"https://{d}/api/io/_v/api/intelligent-search/product_search/?query=&count=50&page=1&sort=discount:desc&hideUnavailableItems=true")
    if c == 200 and b.lstrip().startswith("{") and '"products"' in b:
        ps = json.loads(b).get("products", []); pares = []
        for p in ps:
            try:
                co = p["items"][0]["sellers"][0]["commertialOffer"]; pares.append((co["Price"], co["ListPrice"]))
            except (KeyError, IndexError): pass
        return {**r, "tipo": "vtex_is", "productos": len(ps), "con50": cuenta50(pares), "final": f}
    c, f, b = get(f"https://{d}/wp-json/wc/store/v1/products?on_sale=true&per_page=100")
    if c == 200 and b.lstrip().startswith("["):
        ps = json.loads(b); pares = []
        for p in ps:
            pr = p.get("prices") or {}
            try: pares.append((float(pr.get("sale_price") or pr.get("price") or 0), float(pr.get("regular_price") or 0)))
            except ValueError: pass
        return {**r, "tipo": "woo", "productos": len(ps), "con50": cuenta50(pares), "final": f}
    c, f, h = get(f"https://{d}/", ua=NAV, acepta="text/html")
    low = h.lower()
    pistas = [p for p in ("shopify", "vtex", "woocommerce", "magento", "demandware", "jumpseller", "bsale",
                          "__next_data__", "cloudflare", "akamai", "prestashop") if p in low]
    sitios = sorted(set(re.findall(r"Sites-([A-Za-z0-9_]+)-Site", h)))[:2]
    return {**r, "tipo": "no", "estado": c, "final": f[:80], "pistas": pistas, "sfcc": sitios}


if __name__ == "__main__":
    dominios = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]
    with cf.ThreadPoolExecutor(16) as ex:
        res = list(ex.map(sondear, dominios))
    os.makedirs("muestras", exist_ok=True)
    json.dump(res, open("muestras/sondeo.json", "w"), ensure_ascii=False, indent=1)
    for x in res:
        print(json.dumps(x, ensure_ascii=False))
