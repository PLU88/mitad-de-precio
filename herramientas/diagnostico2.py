"""Segunda ronda: Shopify (/products.json), Magento (GraphQL), Salcobrand y muestras HTML de Salesforce."""
import json, os, re, urllib.request, urllib.error, urllib.parse

NAV = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
os.makedirs("muestras", exist_ok=True)


def get(url, extra=None):
    h = {"User-Agent": NAV, "Accept": "application/json, text/html;q=0.9", "Accept-Language": "es-CL,es;q=0.9"}
    if extra:
        h.update(extra)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25) as r:
            return r.status, r.geturl(), r.read(3_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, e.read(400).decode("utf-8", "replace")
    except Exception as e:
        return "ERR", url, str(e)[:150]


print("=== SHOPIFY /products.json ===")
for d in ["fashionspark.com", "www.hushpuppies.cl", "www.skechers.cl", "www.casaideas.com", "www.rockford.cl",
          "www.bata.cl", "www.lippioutdoor.com", "www.colloky.cl", "www.saxoline.cl", "www.columbia.cl",
          "www.mango.com", "www.cat.cl", "www.merrell.cl", "www.newbalance.cl", "www.converse.cl", "www.vans.cl",
          "www.maui.cl", "www.ellus.cl", "www.paula.cl", "www.lounge.cl", "www.topitop.cl", "www.reebok.cl",
          "www.jdsports.cl", "www.blockstore.cl", "www.underarmour.cl", "www.crocs.cl", "www.samsonite.cl"]:
    c, final, b = get(f"https://{d}/products.json?limit=3")
    resumen = b[:90].replace("\n", " ")
    if c == 200 and b.lstrip().startswith("{"):
        try:
            ps = json.loads(b).get("products", [])
            v = ps[0]["variants"][0] if ps and ps[0].get("variants") else {}
            resumen = f"SHOPIFY OK productos={len(ps)} precio={v.get('price')} antes={v.get('compare_at_price')}"
        except Exception as e:
            resumen = "json raro " + str(e)[:60]
    print(f"{d:24} {c} {final[:60]} | {resumen}")

print("\n=== MAGENTO GraphQL ===")
q = '{products(search:"",pageSize:2,sort:{price:ASC}){total_count items{name url_key price_range{minimum_price{regular_price{value} final_price{value} discount{percent_off}}}}}}'
for d in ["cl.puma.com", "www.thenorthface.cl", "www.casaideas.cl", "www.casaideas.com"]:
    c, final, b = get(f"https://{d}/graphql?query=" + urllib.parse.quote(q), {"Store": "default"})
    print(f"{d:24} {c} | {b[:260].replace(chr(10), ' ')}")

print("\n=== SALCOBRAND ===")
c, final, b = get("https://salcobrand.cl/api/v1/catalog_system/pub/products/search.json?_from=0&_to=1&O=OrderByBestDiscountDESC")
print(c, final[:80], "|", b[:300].replace("\n", " "))

print("\n=== SALESFORCE (muestras HTML) ===")
for d, ruta in [("www.hites.com", "/search?q=zapatillas"), ("www.abc.cl", "/search?q=zapatillas"),
                ("www.tricot.cl", "/search?q=polera"), ("www.farmaciasahumada.cl", "/search?q=shampoo")]:
    c, final, b = get(f"https://{d}{ruta}")
    nombre = d.replace("www.", "").split(".")[0]
    with open(f"muestras/{nombre}.html", "w", encoding="utf-8") as f:
        f.write(b)
    pist = {p: len(re.findall(p, b)) for p in ["data-pid", "product-tile", "application/ld\\+json", "data-gtm",
                                                 "data-product", "strike-through", "sales", "list", "srule"]}
    print(f"{d:24} {c} {final[:60]} bytes={len(b)} {pist}")
