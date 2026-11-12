"""Arma cada día 10 historias de Instagram (1080x1920) con cupones, una por cupón.

Se ejecuta después de cupones.py (workflow «Actualizar cupones»). Lee datos/cupones.json y deja:
  datos/publicaciones/cupones/<fecha>/cupon_01.jpg ... cupon_10.jpg
  datos/publicaciones/cupones/indice.json  {"dias": [{"fecha", "historias": [...]}], "recientes": {clave: fecha}}
La función /api/instagram (llamada con ?parte=cupones) las publica como historias.

Elige primero cupones con código (uno por comercio) y completa con beneficios de bancos y Entel.
No repite un mismo cupón en 14 días ni un mismo comercio en 4 días.
Uso: python recolector/cupones_ig.py [--forzar] [--prueba]   (--prueba: guarda en /tmp/cupones_ig)
"""
import datetime as dt
import json
import os
import random
import re
import shutil
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from publicaciones import (BLANCO, CHILE, CREMA, FUCSIA, MARINO, MESES, AMARILLO, barlow, centrar, figtree, logo,  # noqa: E402
                           ancho_logo, montserrat, partir, playfair, rectangulo)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUPONES = os.path.join(RAIZ, "datos", "cupones.json")
PRUEBA = "--prueba" in sys.argv
CARPETA = "/tmp/cupones_ig" if PRUEBA else os.path.join(RAIZ, "datos", "publicaciones", "cupones")
CANTIDAD = 10
DIAS_GUARDADOS = 7
ROJO = "#E8262E"
SUAVE = "#C9C9D6"
# comercios conocidos primero (se ven más en Instagram)
CONOCIDOS = re.compile(r"falabella|paris|ripley|easy|sodimac|lider|jumbo|adidas|nike|puma|asics|skechers|merrell|marmot|"
                       r"mamut|lenovo|hp|huawei|lg|samsung|xiaomi|abc|hites|la polar|fashion|cyzone|l'bel|esika|natura|"
                       r"doggis|juan maestro|carl|starbucks|dunkin|burger|papa john|mcdonald|kfc|domino|pedidosya|uber|"
                       r"cocha|despegar|barcel|cinemark|cine|hot topic|decathlon|petco|superzoo|farmex|cruz verde|"
                       r"salcobrand|ahumada|entel|movistar|wom|claro|mercado libre|aliexpress|shein|temu|airalo", re.I)


def clave(c):
    return (c["m"].lower() + "|" + (c["c"] or c["ti"]).lower())[:120]


def monto(c):
    """El descuento para mostrar en grande. '$80' de AliExpress son dólares: se deja fuera."""
    x = (c.get("x") or "").strip()
    if x.startswith("$"):
        n = int(re.sub(r"\D", "", x) or 0)
        return x if n >= 1000 else ""
    return x


def elegir(cupones, recientes, hoy):
    hace = lambda dias: (hoy - dt.timedelta(days=dias)).isoformat()
    usados = {k for k, f in recientes.items() if f >= hace(14)}
    comercios_recientes = {k.split("|")[0] for k, f in recientes.items() if f >= hace(4)}
    azar = random.Random(hoy.isoformat())

    def candidatos(filtro):
        lista = [c for c in cupones if filtro(c) and clave(c) not in usados and c["m"].lower() not in comercios_recientes
                 and len(c["m"]) <= 40 and (monto(c) or c["c"])]
        azar.shuffle(lista)
        # los conocidos y los que tienen monto primero
        lista.sort(key=lambda c: (not CONOCIDOS.search(c["m"]), not monto(c)))
        return lista

    elegidos, comercios = [], set()

    def tomar(lista, cuantos):
        for c in lista:
            if len(elegidos) >= CANTIDAD or cuantos <= 0:
                return
            if c["m"].lower() in comercios:
                continue
            comercios.add(c["m"].lower())
            elegidos.append(c)
            cuantos -= 1

    tomar(candidatos(lambda c: c["c"] and c["t"] == "Tiendas"), 6)
    tomar(candidatos(lambda c: c["c"] and c["t"] != "Tiendas"), 1)
    tomar(candidatos(lambda c: c["t"] == "Bancos" and not c["c"]), 2)
    tomar(candidatos(lambda c: c["t"] == "Telefonía"), 1)
    tomar(candidatos(lambda c: True), CANTIDAD)  # completar si faltó algo
    return elegidos


def encabezado(c):
    if c["t"] == "Bancos":
        return "BENEFICIO " + (c["f"] if c["f"] != "Picodi" else "BANCARIO").upper()
    if c["t"] == "Telefonía":
        return "BENEFICIO CLIENTES " + c["f"].upper()
    if c["t"] == "Gas":
        return "BENEFICIO " + c["f"].upper()
    return "CÓDIGO DE DESCUENTO"


def sin_codigo(c):
    if c["t"] == "Bancos":
        return "Paga con tarjeta " + (c["f"] if c["f"] != "Picodi" else "del banco")
    if c["t"] == "Telefonía":
        return "Código en la App " + c["f"]
    return "Sin código: se aplica solo"


def ajustar(d, texto, maximo, ancho, hacer):
    tam = maximo
    while tam > 30 and d.textlength(texto, font=hacer(tam)) > ancho:
        tam -= 4
    return hacer(tam)


def ticket(lienzo, d, y, c):
    """Ticket blanco con perforación: «CUPÓN: CÓDIGO» y la marca de agua @priveofertazos."""
    x0, x1, alto = 90, 990, 190
    rectangulo(d, (x0, y, x1, y + alto), 95, BLANCO)
    # talón amarillo con perforación
    rectangulo(d, (x0 + 26, y + 34, x0 + 186, y + alto - 34), 22, AMARILLO)
    d.text((x0 + 106, y + alto / 2), "%", font=barlow(110), fill=MARINO, anchor="mm")
    for yy in range(y + 18, y + alto - 18, 22):
        d.line((x0 + 212, yy, x0 + 212, yy + 11), fill=MARINO, width=4)
    if c["c"]:
        d.text((x0 + 240, y + 62), "CUPÓN:", font=montserrat(34, 900), fill="#2B3A8C", anchor="lm")
        codigo = c["c"].upper()
        letra = ajustar(d, codigo, 92, x1 - x0 - 290, montserrat_negra)
        d.text((x0 + 240, y + 128), codigo, font=letra, fill=MARINO, anchor="lm")
        # marca de agua (como en las cuentas de cupones): no tapa la lectura del código
        marca = Image.new("RGBA", (520, 70), (0, 0, 0, 0))
        ImageDraw.Draw(marca).text((260, 35), "@priveofertazos", font=playfair(46), fill=(214, 31, 105, 170), anchor="mm")
        marca = marca.rotate(-4, resample=Image.BICUBIC, expand=True)
        lienzo.paste(marca, (x1 - marca.width - 60, y + alto - 88), marca)
    else:
        d.text((x0 + 240, y + 70), "SIN CÓDIGO", font=montserrat(34, 900), fill="#2B3A8C", anchor="lm")
        letra = ajustar(d, sin_codigo(c), 52, x1 - x0 - 290, lambda t: figtree(t, 700))
        d.text((x0 + 240, y + 128), sin_codigo(c), font=letra, fill=MARINO, anchor="lm")


def montserrat_negra(tam):
    return montserrat(tam, 900)


def historia(c, n, total, total_cupones, fecha):
    img = Image.new("RGB", (1080, 1920), MARINO)
    d = ImageDraw.Draw(img)
    logo(d, (1080 - ancho_logo(1.0)) / 2, 110, 1.0, claro=True)
    d.text((1010, 215), f"{n}/{total}", font=montserrat(32, 700), fill=SUAVE, anchor="rm")
    # franja blanca de título
    d.rectangle((0, 260, 1080, 420), fill=CREMA)
    centrar(d, 280, "CUPONES DEL DÍA", barlow(84), MARINO)
    centrar(d, 372, f"{fecha.day} de {MESES[fecha.month - 1]}", figtree(34, 600), FUCSIA)
    # tipo de beneficio y comercio
    centrar(d, 480, encabezado(c), montserrat(34, 900), "#FF4F8B")
    comercio = c["m"].upper()
    letra = ajustar(d, comercio, 120, 820, barlow)
    w = d.textlength(comercio, font=letra)
    rectangulo(d, ((1080 - w) / 2 - 50, 545, (1080 + w) / 2 + 50, 705), 80, AMARILLO)
    d.text((540, 625), comercio, font=letra, fill=MARINO, anchor="mm")
    # ticket con el código
    ticket(img, d, 760, c)
    # burbuja con el descuento
    rectangulo(d, (120, 1010, 960, 1500), 60, BLANCO)
    m = monto(c)
    y = 1050
    if m:
        letra = ajustar(d, m, 230, 760, barlow)
        centrar(d, y, m, letra, ROJO)
        y += letra.size + 30
        lineas = partir(d, quitar_monto(c["ti"], m), figtree(42, 700), 740, 3)
    else:
        lineas = partir(d, c["ti"], figtree(52, 800), 740, 5)
    for linea in lineas:
        letra = figtree(42, 700) if m else figtree(52, 800)
        centrar(d, y, linea, letra, "#2B3A8C")
        y += letra.size + 14
    # condiciones / vigencia
    extra = c.get("v") or c.get("d") or ""
    y = 1540
    for linea in partir(d, extra, figtree(34, 500), 900, 2):
        centrar(d, y, linea, figtree(34, 500), SUAVE)
        y += 46
    # cierre
    rectangulo(d, (90, 1630, 990, 1740), 55, FUCSIA)
    centrar(d, 1653, f"+{total_cupones:,} cupones en priveofertazos.cl".replace(",", "."), figtree(42, 700), BLANCO)
    centrar(d, 1765, "Sección «Cupones» · link en la bio", figtree(32, 600), SUAVE)
    return img


def quitar_monto(titulo, m):
    """'20% de descuento con tarjetas…' -> 'de descuento con tarjetas…' (el monto ya va en grande)."""
    t = re.sub(r"^\s*-?\s*" + re.escape(m) + r"\s*(OFF\b)?\s*", "", titulo, flags=re.I)
    t = re.sub(r"\s*con codigo (promocional|descuento) \S+\s*$", "", t, flags=re.I)
    return (t[:1].upper() + t[1:]) if t else titulo


def main():
    forzar = "--forzar" in sys.argv
    if not os.path.exists(CUPONES):
        print("Cupones IG: no hay datos/cupones.json")
        return 0
    cupones = json.load(open(CUPONES, encoding="utf-8"))["cupones"]
    hoy = dt.datetime.now(CHILE).date()
    os.makedirs(CARPETA, exist_ok=True)
    ruta_indice = os.path.join(CARPETA, "indice.json")
    indice = json.load(open(ruta_indice, encoding="utf-8")) if os.path.exists(ruta_indice) else {"dias": [], "recientes": {}}
    if any(x["fecha"] == hoy.isoformat() for x in indice["dias"]) and not forzar:
        print("Cupones IG: las de hoy ya están.")
        return 0
    elegidos = elegir(cupones, indice.get("recientes", {}), hoy)
    if len(elegidos) < 3:
        print("Cupones IG: muy pocos cupones para publicar.")
        return 0
    carpeta_dia = os.path.join(CARPETA, hoy.isoformat())
    shutil.rmtree(carpeta_dia, ignore_errors=True)
    os.makedirs(carpeta_dia)
    nombres = []
    for i, c in enumerate(elegidos, 1):
        nombre = f"cupon_{i:02d}.jpg"
        historia(c, i, len(elegidos), len(cupones), hoy).save(os.path.join(carpeta_dia, nombre), quality=90, optimize=True)
        nombres.append(nombre)
        indice.setdefault("recientes", {})[clave(c)] = hoy.isoformat()
    indice["dias"] = [x for x in indice["dias"] if x["fecha"] != hoy.isoformat()]
    indice["dias"].append({"fecha": hoy.isoformat(), "historias": nombres,
                           "cupones": [{"m": c["m"], "c": c["c"], "ti": c["ti"]} for c in elegidos]})
    # guardar solo los últimos días
    fechas = sorted({x["fecha"] for x in indice["dias"]}, reverse=True)[:DIAS_GUARDADOS]
    indice["dias"] = [x for x in indice["dias"] if x["fecha"] in fechas]
    limite = (hoy - dt.timedelta(days=21)).isoformat()
    indice["recientes"] = {k: f for k, f in indice["recientes"].items() if f >= limite}
    for nombre in os.listdir(CARPETA):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", nombre) and nombre not in fechas:
            shutil.rmtree(os.path.join(CARPETA, nombre), ignore_errors=True)
    json.dump(indice, open(ruta_indice, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Cupones IG: {len(nombres)} historias para {hoy}: " + ", ".join(c["m"] for c in elegidos))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # nunca frenar la actualización de cupones
        print("Cupones IG: no se pudieron hacer:", e)
        sys.exit(0)
