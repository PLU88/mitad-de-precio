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
s,js=get("https://cdn.picodi.com/assets/v20/js/shop-single.b5b01c0d.js")
for kw in ["/api/","fetch(","axios",",code:","getCode","offerId","/offer"]:
    for m in list(re.finditer(re.escape(kw),js))[:4]:
        print("PJS",kw,"::",js[max(0,m.start()-150):m.start()+200].replace("\n"," "))
s,t=get("https://www.picodi.com/cl/shein")
for m in list(re.finditer(r'data-[a-z\-]+="[^"]{0,80}"',t))[:0]: pass
i=t.find('id="c_shein_69984"'); print("LI", t[i-600:i+100])
s,t=get("https://sitiospublicos.bancochile.cl/personas/beneficios")
print("BCH scripts json", [m[:80] for m in re.findall(r'<script[^>]*type="application/(?:json|ld\+json)"[^>]*>(.{0,200})',t,re.S)][:5])
print("BCH apis", sorted(set(re.findall(r'["\'](/[^"\'\s]*(?:api|json)[^"\'\s]*)["\']',t)))[:30])
T=txt(t); i=T.find('%'); print("BCH text", T[:200], "...", T[i-500:i+1500])
print("BCH codigos", re.findall(r'[Cc]ódigo[^.]{0,80}',T)[:20])
s,t=get("https://www.bci.cl/beneficios/beneficios-bci")
print("BCI spaces", sorted(set(re.findall(r'/api/content/spaces/[^"\'\s<>]+',t)))[:20])
T=txt(t); print("BCI text", T[:1500])
for u in ["https://www.bci.cl/api/content/spaces/beneficios/types/beneficio/entries?per_page=5","https://www.bci.cl/api/content/spaces/beneficios-bci/types/beneficios/entries?per_page=5"]:
    s,t2=get(u); print("BCIAPI",u,s,t2[:600])
s,t=get("https://www.entel.cl/beneficios")
L=sorted(set(re.findall(r'https://www\.entel\.cl/beneficios/[a-z\-]+/[a-z0-9\-]+',t))); print("ENTEL",len(L),L[:60])
print("ENTEL spaces", sorted(set(re.findall(r'/api/content/spaces/[^"\'\s<>]+',t)))[:20])
if L:
    s,t3=get(L[0]); T=txt(t3); i=T.find('%'); print("ENTEL1",L[0],T[max(0,i-400):i+800])
s,t=get("https://lipigas.cl/hogar/promociones/"); T=txt(t); print("LIPI",s,T[:3000])
s,t=get("https://www.metrogas.cl/"); print("METRO links", sorted(set(re.findall(r'href="([^"]*(?:benef|promo|descu|club)[^"]*)"',t,re.I)))[:20]); print(txt(t)[:800])
s,t=get("https://ww2.movistar.cl/"); print("MOV links", sorted(set(re.findall(r'href="([^"]*(?:club|benef|descu)[^"]*)"',t,re.I)))[:20])
