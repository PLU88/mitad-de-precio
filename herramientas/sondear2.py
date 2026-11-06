import gzip, json, os, re, ssl, urllib.request, urllib.error, urllib.parse
UA = "Mozilla/5.0 (compatible; MitadDePrecioBot/1.0; +https://mitad-de-precio.vercel.app/)"
NAV = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
LAXO = ssl.create_default_context(); LAXO.check_hostname = False; LAXO.verify_mode = ssl.CERT_NONE
os.makedirs("muestras", exist_ok=True)
def get(url, ua=NAV, extra=None):
    h = {"User-Agent": ua, "Accept": "*/*", "Accept-Encoding": "gzip", "Accept-Language": "es-CL,es;q=0.9"}
    if extra: h.update(extra)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25, context=LAXO)
        b = r.read(6_000_000); b = gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b
        return r.status, r.geturl(), b.decode("utf-8", "replace")
    except urllib.error.HTTPError as e: return e.code, url, e.read(300).decode("utf-8", "replace")
    except Exception as e: return "ERR", url, str(e)[:80]
def guardar(n, b): open(f"muestras/{n}.txt", "w").write(b)
pr = {}
# Falabella / Sodimac: páginas con __NEXT_DATA__
for n, u in {"fala_search": "https://www.falabella.com/falabella-cl/search?Ntt=zapatillas",
             "fala_coll": "https://www.falabella.com/falabella-cl/collection/ofertas",
             "fala_cat": "https://www.falabella.com/falabella-cl/category/cat720161/Zapatillas",
             "soda_search": "https://www.sodimac.cl/sodimac-cl/search?Ntt=taladro",
             "fala_api": "https://www.falabella.com/s/browse/v1/listing/cl?page=1&Ntt=zapatillas&sortBy=derived.price.search%2Casc"}.items():
    c, f, b = get(u); guardar(n, b)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', b, re.S)
    print(n, c, f[:80], "len", len(b), "next_data", bool(m), "results" in b, b[:120].replace("\n"," "))
# Salesforce genérico
for n, d, s in [("tricot","www.tricot.cl","TRICOT_CL"),("maicao","www.maicao.cl","MaicaoChile"),("cic","www.cic.cl","CIC_CL"),
                ("superzoo","www.superzoo.cl","SuperZoo"),("nb","www.newbalance.cl","NBEU")]:
    for loc in ("default","es_CL"):
        u = f"https://{d}/on/demandware.store/Sites-{s}-Site/{loc}/Search-UpdateGrid?cgid=root&start=0&sz=24"
        c, f, b = get(u); guardar(f"sfcc_{n}_{loc}", b)
        sr = sorted(set(re.findall(r"srule=([a-zA-Z0-9_-]+)", b)))[:10]
        print("sfcc", n, loc, c, "len", len(b), "pid", b.count("data-pid"), "gtmsel", b.count("gtmselectitem"),
              "content=", len(re.findall(r'class="value"[^>]*content="', b)), "srules", sr)
# Magento GraphQL
q = '{products(search:"",pageSize:3,currentPage:1){total_count items{name url_key price_range{minimum_price{regular_price{value} final_price{value} discount{percent_off}}}}}}'
for d in ["www.casaideas.cl","www.guess.cl","www.dbs.cl","www.novasalud.cl","www.schilling.cl","www.rosen.cl","www.cannonhome.cl",
          "www.thomas.cl","www.sparta.cl","www.andesgear.cl","www.antartica.cl","www.kipling.cl","liola.cl","www.rapsodia.cl"]:
    c, f, b = get(f"https://{d}/graphql?query=" + urllib.parse.quote(q), extra={"Store": "default", "Content-Type": "application/json"})
    print("magento", d, c, b[:200].replace("\n"," "))
