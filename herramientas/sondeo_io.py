"""Sondeo temporal: grillas HTML de Magento (iO, Ash) y PrestaShop (El Volcán)."""
import re, json, gzip, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
def get(url, acepta="text/html", extra=None):
    h = {"User-Agent": UA, "Accept": acepta, "Accept-Encoding": "gzip", "Accept-Language": "es-CL,es;q=0.9"}; h.update(extra or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40) as x:
        b = x.read(); b = gzip.decompress(b) if x.headers.get("Content-Encoding") == "gzip" else b
        return x.geturl(), b.decode("utf-8", "replace")
q = '{storeConfig{store_code store_name} products(search:"",pageSize:2){total_count items{name}}}'
for dom in ["www.iochile.cl", "www.ashchile.cl"]:
    for store in [None, "io", "io_storeview", "default", "ash", "ash_storeview", "cl"]:
        try:
            _, t = get(f"https://{dom}/graphql?query=" + urllib.parse.quote(q), "application/json", {"Store": store} if store else None)
            print(f"[{dom} gql store={store}]", t[:300])
        except Exception as e:
            print(f"[{dom} gql store={store}] ERROR", e)
    try:
        _, home = get(f"https://{dom}/")
        enlaces = sorted(set(re.findall(r'href="(https://' + re.escape(dom) + r'/[^"#?]*(?:sale|outlet|oferta|descuento|rebaja|liquidaci|cyber|promo|black)[^"#?]*)"', home, re.I)))
        print(f"[{dom}] enlaces de ofertas:", enlaces[:20])
        cats = sorted(set(re.findall(r'href="(https://' + re.escape(dom) + r'/[a-z0-9-]+\.html)"', home)))
        print(f"[{dom}] categorías .html:", len(cats), cats[:40])
        for u in (enlaces[:2] or []) + [f"https://{dom}/catalogsearch/result/?q=%25"]:
            try:
                final, h = get(u + ("&" if "?" in u else "?") + "product_list_limit=36")
                print(f"  [{u}] -> {final} items={len(re.findall(r'product-item-info', h))} old={len(re.findall(r'data-price-type=.oldPrice', h))} final={len(re.findall(r'data-price-type=.finalPrice', h))} total={re.findall(r'toolbar-number\">(\d+)', h)[:3]}")
                m = re.search(r'(?s)data-price-type="oldPrice".{0,200}', h)
                if m: print("    ", re.sub(r"\s+", " ", h[max(0, m.start()-900):m.end()])[:1300])
            except Exception as e:
                print(f"  [{u}] ERROR", e)
    except Exception as e:
        print(f"[{dom}] ERROR", e)
for u in ["https://www.elvolcan.cl/index.php?controller=prices-drop", "https://www.elvolcan.cl/productos-rebajados", "https://www.elvolcan.cl/prices-drop"]:
    try:
        final, h = get(u)
        print(f"[volcan {u}] -> {final} bytes={len(h)} miniaturas={len(re.findall(r'js-product-miniature', h))} regular={h.count('regular-price')} paginas={re.findall(r'[?&]page=(\d+)', h)[-3:]}")
        m = re.search(r'(?s)<article[^>]*js-product-miniature.{0,2500}', h)
        if m: print("   ", re.sub(r"\s+", " ", m.group(0))[:2500]); break
    except Exception as e:
        print(f"[volcan {u}] ERROR", e)
