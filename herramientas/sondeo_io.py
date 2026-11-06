"""Sondeo temporal de iochile.cl (Magento): consultas GraphQL con filtros y lectura de la grilla HTML."""
import re, json, gzip, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
def get(url, acepta="application/json"):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": acepta, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(r, timeout=40) as x:
        b = x.read(); b = gzip.decompress(b) if x.headers.get("Content-Encoding") == "gzip" else b
        return b.decode("utf-8", "replace")
campos = "total_count items{name sku url_key url_suffix __typename stock_status small_image{url} categories{name} price_range{minimum_price{regular_price{value} final_price{value}}}}"
for nombre, filtro in [("precio", 'filter:{price:{from:"1"}}'), ("sku", 'filter:{sku:{match:"0"}}'), ("cat2", 'filter:{category_id:{eq:"2"}}'),
                       ("nombre", 'filter:{name:{match:"a"}}'), ("search a", 'search:"a"'), ("search polera", 'search:"polera"')]:
    q = "{products(%s,pageSize:3,currentPage:1){%s}}" % (filtro, campos)
    try:
        print(f"[{nombre}]", get("https://www.iochile.cl/graphql?query=" + urllib.parse.quote(q))[:700])
    except Exception as e:
        print(f"[{nombre}] ERROR", e)
try:
    print("[categorias]", get("https://www.iochile.cl/graphql?query=" + urllib.parse.quote("{categories{items{uid id name url_path product_count children{id name url_path product_count}}}}"))[:1500])
except Exception as e:
    print("[categorias] ERROR", e)
try:
    h = get("https://www.iochile.cl/bottoms.html?product_list_limit=36", "text/html")
    print("[grilla] bytes", len(h), "| items", len(re.findall(r'class="[^"]*product-item-info', h)),
          "| old-price", h.count("old-price"), "| data-price-amount", len(re.findall(r'data-price-amount="', h)))
    m = re.search(r'(?s)<li class="item product product-item.{0,3000}', h)
    print(re.sub(r"\s+", " ", m.group(0))[:2500] if m else "sin items")
except Exception as e:
    print("[grilla] ERROR", e)
