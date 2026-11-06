"""Prueba varias formas de leer el catálogo de cada tienda y muestra qué responde."""
import json, sys, urllib.request, urllib.error, ssl

NAV = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
BOT = "OfertasChileBot/1.0"

DOMINIOS = sys.argv[1:]
METODOS = [
    ("legacy-bot", BOT, "https://{d}/api/catalog_system/pub/products/search?_from=0&_to=1&O=OrderByBestDiscountDESC"),
    ("legacy-nav", NAV, "https://{d}/api/catalog_system/pub/products/search?_from=0&_to=1&O=OrderByBestDiscountDESC"),
    ("isearch-nav", NAV, "https://{d}/api/io/_v/api/intelligent-search/product_search/?query=&count=2&page=1&sort=discount:desc&hideUnavailableItems=true"),
    ("home-nav", NAV, "https://{d}/"),
]
ctx = ssl.create_default_context()
for d in DOMINIOS:
    for nombre, ua, plantilla in METODOS:
        url = plantilla.format(d=d)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json, text/html;q=0.9",
                                                       "Accept-Language": "es-CL,es;q=0.9"})
            with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                cuerpo = r.read(400000).decode("utf-8", "replace")
                codigo, final = r.status, r.geturl()
        except urllib.error.HTTPError as e:
            cuerpo, codigo, final = e.read(300).decode("utf-8", "replace"), e.code, url
        except Exception as e:
            cuerpo, codigo, final = str(e)[:120], "ERR", url
        resumen = cuerpo[:140].replace("\n", " ")
        extra = ""
        if nombre.startswith("home"):
            low = cuerpo.lower()
            pistas = [p for p in ("vtex", "vteximg", "vtexassets", "shopify", "magento", "salesforce", "demandware",
                                  "next.js", "__next_data__", "falabella", "algolia", "constructor.io") if p in low]
            extra = " pistas=" + ",".join(pistas)
            resumen = ""
        print(f"{d:28} {nombre:12} {codigo} {final[:70]}{extra} | {resumen}")
    print()
