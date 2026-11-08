#!/usr/bin/env python3
"""
Recolector diario de cupones y códigos de descuento (Chile).

Fuentes (todas públicas):
  - Picodi Chile: códigos de descuento de ~200 tiendas (incluye códigos de influencers que publica Picodi).
  - Banco de Chile: catálogo público de beneficios (descuentos con tarjeta y códigos).
  - Entel: descuentos del Club Entel.
  - Club Metrogas: descuentos del club.
Los cupones que la dueña agrega a mano (por ejemplo, los que ve en Instagram) viven en Vercel
y se suman en la página.

Escribe datos/cupones.json y lo cifra en datos/cupones.enc (igual que las ofertas).
Uso:  python recolector/cupones.py            (todo)
      python recolector/cupones.py --prueba   (solo muestra ejemplos, no escribe)
"""
import base64
import concurrent.futures
import datetime as dt
import gzip
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "datos", "cupones.json")
SALIDA_CIFRADA = os.path.join(RAIZ, "datos", "cupones.enc")
ESTADO = os.path.join(RAIZ, "datos", "cupones_estado.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
PRUEBA = "--prueba" in sys.argv

TELCOS = {"entel", "wom", "claro", "movistar", "vtr", "mundo", "gtd"}
BANCOS = {"bancochile", "bancoestado", "santander", "bci", "scotiabank", "itau", "banco-falabella", "banco-ripley",
          "tenpo", "mach", "mercado-pago", "mercadopago", "cmr", "cencosud-scotiabank", "lider-bci", "coopeuch"}
GAS = re.compile(r"lipigas|abastible|gasco|metrogas|gas licuado|cilindro", re.I)


def pedir(url, cabeceras=None, intentos=2):
    h = {"User-Agent": UA, "Accept-Language": "es-CL,es;q=0.9", "Accept-Encoding": "gzip",
         "Accept": "text/html,application/json,*/*"}
    h.update(cabeceras or {})
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
                b = r.read()
            if b[:2] == b"\x1f\x8b":
                b = gzip.decompress(b)
            return b.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404, 406, 410):
                raise
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    raise RuntimeError("sin respuesta: " + url)


def texto(t, largo=None):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t or "", flags=re.S)
    t = re.sub(r"<br\s*/?>|</p>|</li>", ". ", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\*\*", "", t)
    t = re.sub(r"\s+", " ", t).strip(" .")
    t = re.sub(r"(\. ){2,}", ". ", t)
    if largo and len(t) > largo:
        t = t[:largo].rsplit(" ", 1)[0] + "…"
    return t


def descuento_en(t):
    m = re.search(r"(\d{1,2})\s?%", t or "")
    if m:
        return m.group(1) + "%"
    m = re.search(r"\$\s?(\d{1,3}(?:\.\d{3})+|\d{3,6})", t or "")
    return ("$" + m.group(1)) if m else ""


def cupon(tipo, fuente, comercio, titulo, detalle="", codigo="", vigencia="", url="", descuento=""):
    return {"t": tipo, "f": fuente, "m": comercio.strip(), "ti": texto(titulo, 140), "d": texto(detalle, 220),
            "c": (codigo or "").strip(), "v": texto(vigencia, 90), "u": url or "",
            "x": descuento or descuento_en(titulo) or descuento_en(detalle)}


# ---------------------------------------------------------------- Picodi
def picodi_codigo(oid):
    j = json.loads(pedir(f"https://s.picodi.com/cl/api/offers/{oid}", {
        "Accept": "application/json", "Referer": "https://www.picodi.com/cl/", "Origin": "https://www.picodi.com",
        "X-Requested-With": "XMLHttpRequest"}))
    if j.get("o_pc") or not j.get("o_c"):
        return None, j
    crudo = base64.b64decode(j["o_c"]).decode("utf-8", "replace")
    return crudo[6:-6], j


def picodi_tienda(slug):
    t = pedir("https://www.picodi.com/cl/" + slug)
    nombre = re.search(r'<h1 class="hero-shop__header">(?:Cupón|Código|Cupones?)?\s*(.*?)\s+(?:y oferta|y promoción|-|\|)', t)
    nombre = html.unescape(nombre.group(1)) if nombre else slug.replace("-", " ").title()
    salida = []
    # solo la lista principal de la tienda (no las tiendas "similares")
    i = t.find("shop-main-offers")
    bloque = t[i:t.find("</section>", i)] if i > 0 else ""
    for li in re.finditer(r'<li class="of of--row type-(code|promo)"(.*?)</li>', bloque, re.S):
        tipo_of, cuerpo = li.group(1), li.group(2)
        oid = re.search(r'data-offer-id="(\d+)"', cuerpo)
        titulo = re.search(r'class="of__title">(.*?)</h3>', cuerpo, re.S)
        if not oid or not titulo:
            continue
        desc = re.search(r'class="of__description">(.*?)</p>', cuerpo, re.S)
        fin = re.search(r'class="of__offer-end-date">(.*?)</div>', cuerpo, re.S)
        valor = re.search(r'class="discount__value">(.*?)</span>', cuerpo, re.S)
        if tipo_of != "code":
            continue  # las promociones sin código de Picodi solo llevan a la tienda
        try:
            codigo, _ = picodi_codigo(oid.group(1))
        except Exception:
            codigo = None
        if not codigo or len(codigo) > 40:
            continue
        vig = texto(fin.group(1)) if fin else ""
        vig = "" if "curso" in vig.lower() else vig.replace("Expira:", "Vence:").strip()
        tipo = "Telefonía" if slug in TELCOS else "Bancos" if slug in BANCOS else "Tiendas"
        salida.append(cupon(tipo, "Picodi", nombre, re.sub(r"^\s*(cup[oó]n|c[oó]digo)( de)?( descuento| promocional)?\s+" + re.escape(nombre) + r"\s*:?\s*", "", texto(titulo.group(1)), flags=re.I) or texto(titulo.group(1)),
                            texto(desc.group(1)) if desc else "", codigo, vig, "", texto(valor.group(1)) if valor else ""))
        time.sleep(0.4)
    return salida


def picodi():
    t = pedir("https://www.picodi.com/cl/tiendas")
    slugs = sorted(set(re.findall(r'href="(?:https://www\.picodi\.com)?/cl/([a-z0-9\-]+)"', t)))
    slugs = [s for s in slugs if s not in {"tiendas", "categoria", "contacto", "blog", "cashback", "top-50", "terminos", "privacidad"}]
    if PRUEBA:
        slugs = ["shein", "entel", "adidas", "cruz-verde", "nike", "ripley"] + slugs[:6]
    salida = []
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        for r in ex.map(lambda s: _seguro(picodi_tienda, s), slugs):
            salida += r
    return salida


def _seguro(f, *a):
    try:
        return f(*a)
    except Exception as e:
        print("  aviso:", a, e)
        return []


# ---------------------------------------------------------------- Banco de Chile
def bancochile():
    base = "https://sitiospublicos.bancochile.cl/api/content/spaces/personas/types/beneficios/entries?per_page=100&page="
    salida, pagina, total = [], 1, 1
    while pagina <= total and pagina <= 15:
        d = json.loads(pedir(base + str(pagina), {"Accept": "application/json"}))
        total = d.get("meta", {}).get("total_pages", 1)
        for e in d.get("entries", []):
            f, meta = e.get("fields", {}), e.get("meta", {})
            if meta.get("unpublish_at") and meta["unpublish_at"] < dt.datetime.utcnow().isoformat():
                continue
            titulo = f.get("Titulo") or meta.get("name") or ""
            desc = texto(f.get("Descripcion") or "")
            cond = texto(f.get("Condiciones Comerciales") or "")
            tipo_b = texto(str(f.get("Tipo Beneficio") or ""))
            todo = " ".join([desc, cond, tipo_b, f.get("Extracto") or ""])
            cod = re.search(r"c[oó]digo(?: de descuento| promocional)?:?\s*[«\"“]?([A-Z0-9][A-Z0-9\-]{3,24})\b", todo)
            cat = meta.get("category", "")
            tipo = "Gas" if GAS.search(titulo + " " + todo) else "Bancos"
            slug = meta.get("slug", "")
            url = f.get("Url Beneficio Externa") or (
                f"https://sitiospublicos.bancochile.cl/personas/beneficios/detalle/{slug}" if slug else "")
            rubro = cat.split("/")[-1].replace("-", " ").capitalize() if cat else ""
            det = (f.get("Extracto") or "").strip()
            det = (det[0].upper() + det[1:] + ". " if det else "") + (desc or cond)
            x = descuento_en(tipo_b) or descuento_en(desc) or descuento_en(cond)
            ti = (x + " de descuento" if x and not x.startswith("$") else x + " de descuento" if x else "Beneficio") + \
                 " con tarjetas Banco de Chile" + (f" ({rubro.lower()})" if rubro else "")
            salida.append(cupon(tipo, "Banco de Chile", titulo, ti, det, cod.group(1) if cod else "",
                                f.get("Vigencia") or "", url if isinstance(url, str) else "", x))
        pagina += 1
        time.sleep(0.5)
    return salida


# ---------------------------------------------------------------- Entel
def entel():
    t = pedir("https://www.entel.cl/beneficios")
    salida, vistos = [], set()
    for m in re.finditer(r"'(\{[^']*\"title\"[^']*\"description\"[^']*\})'", t):
        try:
            o = json.loads(html.unescape(m.group(1)))
        except Exception:
            continue
        nombre, desc = o.get("title") or o.get("label") or "", o.get("description") or ""
        if not nombre or not desc or nombre in vistos or not re.search(r"\d", desc):
            continue
        vistos.add(nombre)
        slug = re.sub(r"[^a-z0-9]+", "-", nombre.lower()).strip("-")
        url = f"https://www.entel.cl/beneficios/descuentos/{slug}" if f"/descuentos/{slug}" in t else "https://www.entel.cl/beneficios"
        salida.append(cupon("Telefonía", "Entel", nombre, texto(desc), "Exclusivo clientes Entel: el código se obtiene en la App Entel (Beneficios).",
                            "", "", url))
    return salida


# ---------------------------------------------------------------- Club Metrogas
def metrogas():
    salida = []
    try:
        lista = json.loads(pedir("https://www.clubmetrogas.cl/wp-json/wp/v2/beneficios?per_page=100", {"Accept": "application/json"}))
    except Exception:
        lista = []
    for b in lista if isinstance(lista, list) else []:
        nombre = texto(b.get("title", {}).get("rendered", ""))
        cuerpo = texto(b.get("content", {}).get("rendered", "") or b.get("excerpt", {}).get("rendered", ""), 220)
        if nombre:
            salida.append(cupon("Gas", "Club Metrogas", nombre, (descuento_en(cuerpo) + " de descuento para clientes Metrogas") if descuento_en(cuerpo) else "Beneficio para clientes Metrogas",
                                cuerpo, "", "", b.get("link", "https://www.clubmetrogas.cl/")))
    if not salida:  # plan B: leer la página de descuentos
        t = pedir("https://www.clubmetrogas.cl/canjes-descuentos/?tipo=beneficios")
        for m in re.finditer(r'href="(https://www\.clubmetrogas\.cl/beneficios/[a-z0-9\-]+/)"', t):
            u = m.group(1)
            if any(x["u"] == u for x in salida):
                continue
            trozo = texto(t[max(0, m.start() - 900):m.start() + 300])
            nombre = u.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()
            x = descuento_en(trozo)
            salida.append(cupon("Gas", "Club Metrogas", nombre, (x + " de descuento para clientes Metrogas") if x else "Beneficio para clientes Metrogas",
                                "", "", "", u, x))
    return salida


# ---------------------------------------------------------------- todo junto
def main():
    fuentes = {"Picodi": picodi, "Banco de Chile": bancochile, "Entel": entel, "Club Metrogas": metrogas}
    cupones, estado = [], {}
    for nombre, f in fuentes.items():
        inicio = time.time()
        try:
            r = f()
            estado[nombre] = {"ok": True, "cupones": len(r)}
        except Exception as e:
            r = []
            estado[nombre] = {"ok": False, "error": str(e)[:200]}
        print(f"{nombre}: {len(r)} cupones en {time.time() - inicio:.0f} s")
        cupones += r
        if PRUEBA:
            for c in r[:6]:
                print("   ", json.dumps(c, ensure_ascii=False))
    # sin repetidos (mismo comercio y mismo código o título)
    vistos, unicos = set(), []
    for c in cupones:
        k = (c["m"].lower(), c["c"] or c["ti"].lower())
        if k not in vistos:
            vistos.add(k)
            unicos.append(c)
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    print(f"Total: {len(unicos)} cupones ({sum(1 for c in unicos if c['c'])} con código)")
    if PRUEBA:
        return 0
    if len(unicos) < 30:
        print("Muy pocos cupones: se mantiene la versión anterior.")
        return 0
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump({"actualizado": ahora, "cupones": unicos}, fh, ensure_ascii=False, separators=(",", ":"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cifrar import cifrar, CLAVE
    with open(SALIDA, "rb") as fh, open(CLAVE, "rb") as fk:
        sobre = cifrar(fh.read(), fk.read())
    with open(SALIDA_CIFRADA, "w", encoding="utf-8") as fh:
        json.dump(sobre, fh)
    with open(ESTADO, "w", encoding="utf-8") as fh:
        json.dump({"actualizado": ahora, "total": len(unicos), "fuentes": estado}, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
