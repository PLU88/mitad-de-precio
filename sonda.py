import subprocess, re, urllib.request, gzip
subprocess.run(["python","cupones.py","--prueba"])
UA="Mozilla/5.0"
def get(u):
    r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Encoding":"gzip"}),timeout=30); b=r.read()
    return (gzip.decompress(b) if b[:2]==b"\x1f\x8b" else b).decode("utf-8","replace")
t=get("https://sitiospublicos.bancochile.cl/personas/beneficios")
print("BCH links", sorted(set(re.findall(r'href="(/personas/beneficios/[^"]+)"',t)))[:15])
print("BCH detalle", re.findall(r'[^"\']*detalle[^"\']*',t)[:5])
