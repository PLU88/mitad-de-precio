import urllib.request, re, gzip, json, sys
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"es-CL","Accept-Encoding":"gzip","Accept":"text/html,application/json,*/*"}),timeout=30)
        b=r.read()
        if b[:2]==b"\x1f\x8b": b=gzip.decompress(b)
        return r.status, b.decode("utf-8","replace")
    except Exception as e:
        return str(e), ""
print("=== picodi shein")
s,t=get("https://www.picodi.com/cl/shein"); print(s,len(t))
i=t.find("CÓDIGO"); print(t[i-3000:i+3000] if i>0 else t[:3000])
for pat in [r'data-code="[^"]*"', r'"code"\s*:\s*"[^"]*"', r'data-[a-z-]*code[a-z-]*="[^"]*"', r'/cl/[a-z0-9-]+/\?offer=\d+', r'data-offer[a-z-]*="[^"]*"', r'coupon[^"\s]{0,40}']:
    print(pat, re.findall(pat,t)[:8])
print("=== tiendas")
s,t=get("https://www.picodi.com/cl/tiendas"); print(s,len(t))
links=sorted(set(re.findall(r'href="(?:https://www\.picodi\.com)?/cl/([a-z0-9\-]+)"',t)))
print(len(links)); print(" ".join(links))
for marca in ["entel","movistar","lipigas","metrogas","abastible","gasco","wom","claro","bancoestado","santander","bci","banco-falabella","cmr"]:
    s,t=get("https://www.picodi.com/cl/"+marca); print("==",marca,s,len(t), re.findall(r'<title>([^<]*)',t)[:1])
