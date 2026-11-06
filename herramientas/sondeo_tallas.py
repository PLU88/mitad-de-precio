"""Sondeo temporal: cómo informa las tallas cada tienda que hoy no las muestra."""
import json, re, sys, urllib.request, gzip, html, urllib.parse
UA = "Mozilla/5.0 (compatible; PriveOfertazosBot/1.0)"
def get(url, acepta="application/json"):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": acepta, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(r, timeout=40) as x:
        b = x.read()
        if x.headers.get("Content-Encoding") == "gzip": b = gzip.decompress(b)
        return b.decode("utf-8", "replace")
for d in ["www.crocs.cl", "www.blockstore.cl", "www.volkanica.cl", "www.lineatre.cl", "www.raindoor.cl", "www.nicopoly.cl", "www.nostalgic.cl", "www.guante.cl", "www.stevemadden.cl"]:
    try:
        ps = json.loads(get(f"https://{d}/products.json?limit=4"))["products"]
        for p in ps[:3]:
            print(d, "|", p["title"][:40], "| options:", [(o["name"], o.get("values", [])[:6]) for o in p.get("options", [])],
                  "| v1:", {k: p["variants"][0].get(k) for k in ("option1", "option2", "option3", "title")})
    except Exception as e:
        print(d, "ERROR", e)
try:
    q = '{products(search:"",pageSize:3,currentPage:1){items{name __typename ... on ConfigurableProduct{configurable_options{attribute_code label values{label}} variants{product{stock_status} attributes{code label}}}}}}'
    print("rapsodia", get("https://www.rapsodia.cl/graphql?query=" + urllib.parse.quote(q))[:1500])
except Exception as e:
    print("rapsodia ERROR", e)
try:
    ps = json.loads(get("https://www.levi.cl/api/catalog_system/pub/products/search?O=OrderByBestDiscountDESC&_from=0&_to=2"))
    for p in ps[:2]:
        print("levis", p["productName"][:40], [(it.get("name"), it.get("variations"), {k: it.get(k) for k in it.get("variations") or []}) for it in p["items"][:3]])
except Exception as e:
    print("levis ERROR", e)
for nombre, url in [("tricot", "https://www.tricot.cl/on/demandware.store/Sites-Tricot-Site/default/Search-UpdateGrid?cgid=root&start=0&sz=6&srule=discount-off"),
                    ("hites", "https://www.hites.com/on/demandware.store/Sites-HITES-Site/default/Search-UpdateGrid?cgid=root&start=0&sz=6&srule=discount-off"),
                    ("abc", "https://www.abc.cl/on/demandware.store/Sites-abc-Site/default/Search-UpdateGrid?cgid=root&start=0&sz=6&srule=discount-off")]:
    try:
        t = get(url, "text/html")
        print(nombre, len(t), "| menciones:", sorted(set(re.findall(r'(?i)[\w-]*(?:size|talla)[\w-]*', t)))[:30])
        m = re.search(r'(?is).{0,300}(?:size|talla).{0,400}', t)
        print("   ", re.sub(r"\s+", " ", m.group(0))[:700] if m else "-")
    except Exception as e:
        print(nombre, "ERROR", e)
try:
    t = get("https://www.falabella.com/falabella-cl/search?Ntt=polera&f.range.derived.variant.discount=50%25+dcto+y+m%C3%A1s", "text/html")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
    r = json.loads(m.group(1))["props"]["pageProps"]["results"][0]
    print("falabella keys", list(r.keys()))
    print("   ", json.dumps({k: v for k, v in r.items() if re.search("size|talla|variant|filter|attribute", k, re.I)}, ensure_ascii=False)[:1500])
except Exception as e:
    print("falabella ERROR", e)
