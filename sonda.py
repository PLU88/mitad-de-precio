import urllib.request, re, gzip, json
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
s,t=get("https://www.picodi.com/cl/shein")
scripts=re.findall(r'<script[^>]+src="([^"]+)"',t); print("SCRIPTS",scripts)
print("AJAXSTR", sorted(set(re.findall(r'["\'](/[a-z]{2}/[a-zA-Z_\-/]*(?:ajax|api|offer|code|coupon)[a-zA-Z_\-/]*)["\']',t)))[:30])
i=t.find('btn__code'); print("BTN", t[i-200:i+200])
for src in scripts:
    if 'picodi' in src or src.startswith('/'):
        u=src if src.startswith('http') else 'https://www.picodi.com'+src
        s2,js=get(u); print("JS",u,s2,len(js))
        for m in sorted(set(re.findall(r'["\'`]([^"\'`\s]{0,60}(?:ajax|/api/|getCode|get-code|offer/|code)[^"\'`\s]{0,60})["\'`]',js)))[:60]: print("  ",m)
for u in ["https://sitiospublicos.bancochile.cl/personas/beneficios","https://banco.santander.cl/beneficios","https://www.bci.cl/beneficios","https://www.entel.cl/beneficios","https://ww2.movistar.cl/club-movistar/","https://www.lipigas.cl/","https://www.metrogas.cl/","https://www.bancoestado.cl/","https://www.cmr.cl/beneficios","https://www.tenpo.cl/beneficios"]:
    s,t=get(u); ttl=re.findall(r'<title>([^<]*)',t)[:1]
    api=sorted(set(re.findall(r'https?://[a-zA-Z0-9.\-]+/[^"\'\s<>]*(?:api|json|beneficio|promoc|descuento)[^"\'\s<>]{0,80}',t)))[:25]
    print("==",u,s,len(t),ttl); [print("   ",a) for a in api]
