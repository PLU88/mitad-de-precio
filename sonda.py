import urllib.request, re, gzip, json, html as H
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(u, extra=None):
    try:
        h={"User-Agent":UA,"Accept-Language":"es-CL","Accept-Encoding":"gzip","Accept":"text/html,application/json,*/*"}
        if extra: h.update(extra)
        r=urllib.request.urlopen(urllib.request.Request(u,headers=h),timeout=30)
        b=r.read()
        if b[:2]==b"\x1f\x8b": b=gzip.decompress(b)
        return r.status, b.decode("utf-8","replace")
    except Exception as e:
        return str(e), ""
def txt(t): return re.sub(r'\s+',' ',H.unescape(re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>',' ',t,flags=re.S)))
s,t=get("https://www.picodi.com/cl/shein")
for kw in ["S_PICODI_PATH","envs","market="]:
    for m in list(re.finditer(re.escape(kw),t))[:3]: print("PENV",kw,t[max(0,m.start()-100):m.start()+300].replace("\n"," "))
s,js=get("https://cdn.picodi.com/assets/v20/js/shop-single.b5b01c0d.js")
for kw in ["decodeOfferCode","api/offers/","grecaptcha.execute","captcha"]:
    for m in list(re.finditer(re.escape(kw),js))[:3]: print("PJS",kw,"::",js[max(0,m.start()-300):m.start()+400].replace("\n"," "))
for u in ["https://www.picodi.com/cl/api/offers/69984","https://s.picodi.com/cl/api/offers/69984","https://www.picodi.com/api/offers/69984"]:
    s,t2=get(u,{"Accept":"application/json","X-Requested-With":"XMLHttpRequest"}); print("PAPI",u,s,t2[:800])
s,t=get("https://sitiospublicos.bancochile.cl/api/content/spaces/personas/types/beneficios/entries?per_page=3",{"Accept":"application/json"})
print("BCHAPI",s,len(t),t[:3000])
for u in ["https://lipigas.cl/hogar/promociones/cupones/","https://lipigas.cl/cupones/","https://www.clubmetrogas.cl/","https://ww2.movistar.cl/movistar-club/","https://ww2.movistar.cl/club/","https://www.movistar.cl/club"]:
    s,t=get(u); T=txt(t); print("PAGE",u,s,len(t),T[:1200])
s,t=get("https://lipigas.cl/hogar/promociones/"); print("LIPI links",sorted(set(re.findall(r'href="([^"]*(?:cupon|promoc|descuent)[^"]*)"',t,re.I)))[:30])
s,t=get("https://www.bci.cl/beneficios/beneficios-bci/restaurantes"); print("BCI js",sorted(set(re.findall(r'(?:src|href)="([^"]*\.js[^"]*)"',t)))[:15]); print("BCI urls",sorted(set(re.findall(r'["\'](https?://[^"\']*(?:api|json)[^"\']*)["\']',t)))[:20]); print(txt(t)[1500:3500])
