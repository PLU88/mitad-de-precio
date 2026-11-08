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
for kw in ["decodeOfferCode(e){","decodeOfferCode(","atob("]:
    for m in list(re.finditer(re.escape(kw),js))[:2]: print("PJS",kw,"::",js[max(0,m.start()-100):m.start()+500].replace("\n"," "))
for m in list(re.finditer(r'class ri\{|class ri ',js))[:1]: print("RI",js[m.start():m.start()+1500])
hdr={"Accept":"application/json","Referer":"https://www.picodi.com/cl/shein","Origin":"https://www.picodi.com","X-Requested-With":"XMLHttpRequest"}
for u in ["https://s.picodi.com/cl/api/offers/69984","https://s.picodi.com/cl/api/offers?ids=69984"]:
    s,t2=get(u,hdr); print("PAPI",u,s,t2[:1500])
s,t=get("https://aplicaciones.lipigas.cl/cupones/"); print("LIPI",s,len(t),txt(t)[:2500]); print("LIPIapi",sorted(set(re.findall(r'["\']((?:https?:)?/[^"\'\s]*(?:api|json|cupon)[^"\'\s]*)["\']',t)))[:20])
s,t=get("https://sitiospublicos.bancochile.cl/api/content/spaces/personas/types/beneficios/entries?per_page=100",{"Accept":"application/json"})
try:
    d=json.loads(t); print("BCH meta",d.get("meta")); e=d["entries"]; print("BCH n",len(e)); print("BCH fields",list(e[0]["fields"].keys()))
    for x in e[:6]: f=x["fields"]; print("BCH",x["meta"]["category"],"|",f.get("Titulo"),"|",f.get("Extracto"),"|",{k:v for k,v in f.items() if k in("Descuento","Dcto","Porcentaje","Codigo","Código","Bajada","Tope","Dias")})
    print("BCH cats", sorted(set(x["meta"]["category"] for x in e)))
except Exception as ex: print("BCH err",ex,t[:300])
s,t=get("https://www.clubmetrogas.cl/"); T=txt(t); i=T.find("Descuentos Destacados"); print("METRO",T[i:i+1500]); print("METRO links",sorted(set(re.findall(r'href="([^"]*(?:descuento|beneficio|canje)[^"]*)"',t,re.I)))[:20])
s,t=get("https://www.entel.cl/beneficios/descuentos/burger-king"); print("ENTEL h1",re.findall(r'<h1[^>]*>(.*?)</h1>',t,re.S)[:2]); print("ENTEL og",re.findall(r'<meta[^>]+(?:og:title|og:description|name="description")[^>]+>',t)[:4])
s,t=get("https://www.entel.cl/beneficios"); i=t.find('/beneficios/descuentos/burger-king'); print("ENTEL card",txt(t[i-1500:i+800]))
