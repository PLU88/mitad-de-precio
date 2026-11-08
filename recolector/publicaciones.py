"""Arma cada mañana las imágenes y el texto para Instagram con las mejores ofertas del día.

Se ejecuta en cada vuelta del recolector, pero solo trabaja una vez al día (desde las 7:30 de Chile).
Deja en datos/publicaciones/<fecha>/ un carrusel (portada + 7 ofertas, 1080x1350), la historia de
invitación (1080x1920) y texto.txt; y en datos/publicaciones/indice.json la lista de los últimos 7 días.
Además, cada 3 horas, datos/publicaciones/vitrina/ con 30 historias de ofertas y sus links para subirlas a mano.
"""
import datetime as dt
import io
import json
import math
import os
import random
import re
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES = os.path.join(RAIZ, "recolector", "fuentes")
CARPETA = os.path.join(RAIZ, "datos", "publicaciones")
OFERTAS = os.path.join(RAIZ, "datos", "ofertas.json")
ESTADO = os.path.join(RAIZ, "datos", "estado.json")
CHILE = ZoneInfo("America/Santiago")
HORA_INICIO = (7, 30)
DIAS_GUARDADOS = 7
CANTIDAD = 7

MARINO, FUCSIA, CREMA, BLANCO, GRIS = "#1A1A2E", "#D61F69", "#F7F3EE", "#FFFFFF", "#6B6B7B"
TRAMOS = {50: ("#F2B705", "#2B2100"), 60: ("#F07B13", "#2A1200"), 70: ("#D7262E", "#FFFFFF"), 80: ("#9D1660", "#FFFFFF")}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
UA = "Mozilla/5.0 (compatible; PriveOfertazosBot/1.0; +https://priveofertazos.cl)"


# ------------------------------------------------------------------ utilidades
def fuente(nombre, tam, peso=None):
    f = ImageFont.truetype(os.path.join(FUENTES, nombre), tam)
    if peso is not None:
        try:
            f.set_variation_by_axes([peso])
        except Exception:
            pass
    return f


def montserrat(tam, peso=700): return fuente("Montserrat.ttf", tam, peso)
def figtree(tam, peso=500): return fuente("Figtree.ttf", tam, peso)
def playfair(tam): return fuente("PlayfairDisplay-Italic.ttf", tam, 400)
def barlow(tam): return fuente("BarlowCondensed-ExtraBold.ttf", tam)


def nombre_bonito(t):
    """'PARKA HOMBRE NEGRA' -> 'Parka hombre negra' (los nombres en mayúsculas se ven gritados)."""
    letras = [c for c in t if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) > 0.55:
        t = t.lower()
        t = t[:1].upper() + t[1:]
    return re.sub(r"\s+", " ", t).strip()


def clp(n):
    return "$" + f"{int(n):,}".replace(",", ".")


def tramo(d):
    return 80 if d >= 80 else 70 if d >= 70 else 60 if d >= 60 else 50


def fecha_larga(d):
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def partir(dibujo, texto, letra, ancho, lineas_max):
    """Corta el texto en líneas que caben en `ancho`; agrega … si sobra."""
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if dibujo.textlength(prueba, font=letra) <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = p
        if len(lineas) == lineas_max:
            break
    if actual and len(lineas) < lineas_max:
        lineas.append(actual)
    usadas = " ".join(lineas).split()
    if len(usadas) < len(palabras) and lineas:
        ult = lineas[-1]
        while ult and dibujo.textlength(ult + "…", font=letra) > ancho:
            ult = ult.rsplit(" ", 1)[0] if " " in ult else ult[:-1]
        lineas[-1] = ult + "…"
    return lineas


def foto_grande(url):
    """Pide a la tienda una versión grande de la foto."""
    try:
        x = urllib.parse.urlsplit(url)
        q = dict(urllib.parse.parse_qsl(x.query))
        if "cdn.shopify.com" in x.netloc or "/cdn/shop/" in x.path:
            q["width"] = "1100"
        elif "/dw/image/" in x.path:
            q.update(sw="1100", sh="1100")
        elif "vteximg" in x.netloc or "vtexassets" in x.netloc:
            url = re.sub(r"/ids/(\d+)(-\d+-\d+)?/", r"/ids/\1-1100-1100/", url)
            return url
        return urllib.parse.urlunsplit(x._replace(query=urllib.parse.urlencode(q)))
    except Exception:
        return url


def enlace_limpio(url):
    """Enlace al producto sin parámetros de seguimiento (más corto para el texto)."""
    x = urllib.parse.urlsplit(url or "")
    return urllib.parse.urlunsplit((x.scheme or "https", x.netloc, x.path, "", "")).rstrip("/") if x.netloc else ""


def enlace_corto(dibujo, url, letra, ancho):
    """Enlace sin "https://www." y recortado con "…" para que quepa en la imagen."""
    t = re.sub(r"^https?://(www\.)?", "", enlace_limpio(url))
    if dibujo.textlength(t, font=letra) <= ancho:
        return t
    while t and dibujo.textlength(t + "…", font=letra) > ancho:
        t = t[:-1]
    return t + "…"


def bajar_imagen(url):
    req = urllib.request.Request(foto_grande(url), headers={"User-Agent": UA, "Accept": "image/avif,image/webp,image/*,*/*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        datos = r.read(8_000_000)
    img = Image.open(io.BytesIO(datos))
    img = ImageOps.exif_transpose(img).convert("RGBA")
    if min(img.size) < 250:
        raise ValueError("foto muy chica")
    fondo = Image.new("RGB", img.size, BLANCO)
    fondo.paste(img, mask=img.split()[3])
    return fondo


def rectangulo(dibujo, caja, radio, relleno):
    dibujo.rounded_rectangle(caja, radius=radio, fill=relleno)


def centrar(dibujo, y, texto, letra, color, ancho=1080):
    w = dibujo.textlength(texto, font=letra)
    dibujo.text(((ancho - w) / 2, y), texto, font=letra, fill=color)


def logo(dibujo, x, y, escala=1.0, claro=False):
    """Monograma PO + 'Privé OFERTAZOS'. Devuelve el ancho usado."""
    color = BLANCO if claro else MARINO
    acento = "#FF4F8B" if claro else FUCSIA
    d = int(86 * escala)
    dibujo.ellipse((x, y, x + d, y + d), outline=color, width=max(2, int(3 * escala)))
    dibujo.text((x + d * 0.62, y + d * 0.70), "O", font=montserrat(int(42 * escala), 900), fill=acento, anchor="ms")
    dibujo.text((x + d * 0.42, y + d * 0.74), "P", font=playfair(int(60 * escala)), fill=color, anchor="ms")
    tx = x + d + int(16 * escala)
    dibujo.text((tx, y + d * 0.46), "Privé", font=playfair(int(44 * escala)), fill=color, anchor="ls")
    dibujo.text((tx + 2, y + d * 0.86), "OFERTAZOS", font=montserrat(int(22 * escala), 900), fill=acento, anchor="ls")
    return d + int(16 * escala) + dibujo.textlength("OFERTAZOS", font=montserrat(int(22 * escala), 900))


def ancho_logo(escala):
    return logo(ImageDraw.Draw(Image.new("RGB", (10, 10))), 0, 0, escala)


def insignia(dibujo, x, y, descuento, tam=1.0):
    fondo, tinta = TRAMOS[tramo(descuento)]
    texto = f"-{descuento}%"
    letra = barlow(int(96 * tam))
    w = dibujo.textlength(texto, font=letra)
    rectangulo(dibujo, (x, y, x + w + 44 * tam, y + 118 * tam), int(18 * tam), fondo)
    dibujo.text((x + 22 * tam, y + 59 * tam), texto, font=letra, fill=tinta, anchor="lm")


# ------------------------------------------------------------------ sello de campaña (Black Friday)
BLACK_FRIDAY_HASTA = dt.date(2026, 11, 30)   # después de esta fecha el sello deja de aparecer solo
AMARILLO = "#FFD23F"


def hay_black_friday():
    return dt.datetime.now(CHILE).date() <= BLACK_FRIDAY_HASTA


def sello_black_friday(lienzo, cx, cy, escala=1.0, giro=-6):
    """Pega el sello «¡Suscríbete! BLACK FRIDAY 27 al 30 de noviembre» centrado en (cx, cy)."""
    if not hay_black_friday():
        return
    e = escala
    w, h = int(470 * e), int(250 * e)
    s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((0, int(34 * e), w - 1, h - 1), radius=int(30 * e), fill=MARINO, outline=FUCSIA, width=max(3, int(7 * e)))
    # cinta «¡SUSCRÍBETE!»
    letra = montserrat(int(30 * e), 900)
    tw = d.textlength("¡SUSCRÍBETE!", font=letra)
    x0 = (w - tw) / 2 - 22 * e
    d.rounded_rectangle((x0, 0, x0 + tw + 44 * e, 64 * e), radius=int(12 * e), fill=AMARILLO)
    d.text((w / 2, 33 * e), "¡SUSCRÍBETE!", font=letra, fill=MARINO, anchor="mm")
    # BLACK FRIDAY
    tam = int(104 * e)
    while True:  # achica la letra hasta que quepa con margen
        grande = barlow(tam)
        wb, wf = d.textlength("BLACK ", font=grande), d.textlength("FRIDAY", font=grande)
        if wb + wf <= w - 56 * e or tam < 20:
            break
        tam -= 2
    xb = (w - wb - wf) / 2
    d.text((xb, 128 * e), "BLACK ", font=grande, fill=BLANCO, anchor="lm")
    d.text((xb + wb, 128 * e), "FRIDAY", font=grande, fill=AMARILLO, anchor="lm")
    # fechas
    chica = montserrat(int(25 * e), 900)
    ft = "27 AL 30 DE NOVIEMBRE"
    fw = d.textlength(ft, font=chica)
    d.rounded_rectangle(((w - fw) / 2 - 20 * e, 180 * e, (w + fw) / 2 + 20 * e, 226 * e), radius=int(23 * e), fill=BLANCO)
    d.text((w / 2, 203 * e), ft, font=chica, fill=MARINO, anchor="mm")
    s = s.rotate(giro, resample=Image.BICUBIC, expand=True)
    lienzo.paste(s, (int(cx - s.width / 2), int(cy - s.height / 2)), s)


def pegar_foto(lienzo, foto, caja, radio=28):
    x0, y0, x1, y1 = caja
    w, h = x1 - x0, y1 - y0
    f = ImageOps.contain(foto, (w - 40, h - 40), Image.LANCZOS)
    marco = Image.new("RGB", (w, h), BLANCO)
    marco.paste(f, ((w - f.width) // 2, (h - f.height) // 2))
    mascara = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, w, h), radius=radio, fill=255)
    lienzo.paste(marco, (x0, y0), mascara)


# ------------------------------------------------------------------ láminas
def lamina_portada(fecha, elegidas, total_ofertas, total_tiendas, linea1="LOS OFERTAZOS", linea2="DE HOY", pie=None):
    img2 = Image.new("RGB", (1080, 1350), MARINO)
    d = ImageDraw.Draw(img2)
    logo(d, (1080 - ancho_logo(1.25)) / 2, 90, 1.25, claro=True)
    centrar(d, 310, linea1, barlow(150), BLANCO)
    centrar(d, 450, linea2, barlow(150), "#FF4F8B")
    centrar(d, 620, fecha_larga(fecha).capitalize(), figtree(44, 600), "#C9C9D6")
    maximo = max(o["descuento"] for o in elegidas)
    centrar(d, 700, f"{len(elegidas)} ofertas de hasta -{maximo}%", figtree(44, 700), BLANCO)
    # tres fotos en abanico
    x = 105
    for o in elegidas[:3]:
        caja = (x, 800, x + 270, 1070)
        pegar_foto(img2, o["_foto"], caja, 24)
        insignia(d, x + 12, 812, o["descuento"], 0.42)
        x += 300
    rectangulo(d, (90, 1130, 990, 1250), 60, FUCSIA)
    centrar(d, 1158, pie or f"+{total_ofertas:,} ofertas en {total_tiendas} tiendas".replace(",", "."), figtree(40, 700), BLANCO)
    centrar(d, 1278, "Desliza para verlas  →", figtree(34, 600), "#C9C9D6")
    sello_black_friday(img2, 905, 250, 0.62, giro=8)
    return img2


def lamina_oferta(o, n, total, fecha):
    img = Image.new("RGB", (1080, 1350), MARINO)
    d = ImageDraw.Draw(img)
    logo(d, 60, 44, 0.8, claro=True)
    d.text((1020, 88), f"{n}/{total}", font=montserrat(30, 700), fill="#C9C9D6", anchor="rm")
    pegar_foto(img, o["_foto"], (60, 150, 1020, 870))
    insignia(d, 84, 174, o["descuento"], 1.0)
    d.text((60, 905), o["tienda"].upper(), font=montserrat(30, 700), fill="#FF4F8B")
    y = 950
    for linea in partir(d, o["nombre"], figtree(46, 600), 960, 2):
        d.text((60, y), linea, font=figtree(46, 600), fill=BLANCO)
        y += 58
    y = max(y + 14, 1085)
    d.text((60, y), clp(o["precio"]), font=barlow(130), fill=BLANCO)
    antes = "Antes " + clp(o["precio_normal"])
    letra = figtree(40, 500)
    xa = 60 + d.textlength(clp(o["precio"]), font=barlow(130)) + 36
    d.text((xa, y + 34), antes, font=letra, fill="#C9C9D6")
    wa = d.textlength(antes, font=letra)
    xs = xa + d.textlength("Antes ", font=letra)
    d.line((xs, y + 60, xa + wa, y + 60), fill="#C9C9D6", width=3)
    d.text((xa, y + 86), "Ahorras " + clp(o["precio_normal"] - o["precio"]), font=figtree(36, 700), fill="#FF4F8B")
    d.text((540, 1300), f"Precio del {fecha.day} de {MESES[fecha.month - 1]}, puede cambiar · priveofertazos.cl",
           font=figtree(26, 500), fill="#C9C9D6", anchor="mm")
    sello_black_friday(img, 860, 800, 0.62)
    return img


def historia_estrella(o, fecha, n=1, total=1):
    img = Image.new("RGB", (1080, 1920), MARINO)
    d = ImageDraw.Draw(img)
    logo(d, (1080 - ancho_logo(1.1)) / 2, 150, 1.1, claro=True)
    if total > 1:
        d.text((1010, 110), f"{n}/{total}", font=montserrat(34, 700), fill="#C9C9D6", anchor="rm")
    centrar(d, 330, "OFERTAZO DEL DÍA" if n == 1 else "OFERTAZO", barlow(120), "#FF4F8B")
    pegar_foto(img, o["_foto"], (90, 480, 990, 1250), 36)
    insignia(d, 120, 510, o["descuento"], 1.1)
    centrar(d, 1285, o["tienda"].upper(), montserrat(36, 700), "#FF4F8B")
    y = 1340
    for linea in partir(d, o["nombre"], figtree(50, 600), 900, 2):
        centrar(d, y, linea, figtree(50, 600), BLANCO)
        y += 62
    y += 60  # espacio libre para poner el sticker de enlace
    centrar(d, y + 8, clp(o["precio"]), barlow(150), BLANCO)
    centrar(d, y + 168, "Antes " + clp(o["precio_normal"]), figtree(42, 500), "#C9C9D6")
    rectangulo(d, (140, 1760, 940, 1860), 50, FUCSIA)
    centrar(d, 1785, "Más ofertas en priveofertazos.cl", figtree(40, 700), BLANCO)
    sello_black_friday(img, 840, 1180, 0.66)
    return img


def historia_promo(elegidas, total_ofertas, total_tiendas):
    img = Image.new("RGB", (1080, 1920), CREMA)
    d = ImageDraw.Draw(img)
    logo(d, (1080 - ancho_logo(1.4)) / 2, 160, 1.4)
    centrar(d, 330, "LO MEJOR, A MITAD DE PRECIO", montserrat(40, 700), GRIS)
    centrar(d, 450, f"+{total_ofertas:,}".replace(",", "."), barlow(220), FUCSIA)
    centrar(d, 680, "OFERTAS DESDE 50%", barlow(110), MARINO)
    centrar(d, 810, f"en {total_tiendas} tiendas de Chile", figtree(40, 600), MARINO)
    x = 75
    for o in elegidas[:3]:
        pegar_foto(img, o["_foto"], (x, 920, x + 290, 1210), 26)
        insignia(d, x + 12, 932, o["descuento"], 0.45)
        x += 320
    lineas = ["Moda, calzado, hogar, tecnología y más", "Ofertazos nuevos todos los días"]
    y = 1290
    for i, t in enumerate(lineas):
        centrar(d, y, t, figtree(42, 700 if i == 0 else 500), MARINO)
        y += 62
    rectangulo(d, (110, 1560, 970, 1680), 60, FUCSIA)
    centrar(d, 1590, "Pide tu acceso en priveofertazos.cl", figtree(42, 700), BLANCO)
    centrar(d, 1730, "o escríbenos por mensaje directo", figtree(38, 600), GRIS)
    sello_black_friday(img, 540, 1478, 0.55, giro=-3)
    return img


# ------------------------------------------------------------------ selección y texto
def elegir(ofertas, ya_publicadas, cantidad=CANTIDAD, por_tienda=1, por_categoria=2):
    candidatas = [o for o in ofertas if o.get("imagen") and not o.get("dudoso") and 55 <= o["descuento"] <= 85
                  and o["precio"] >= 3000 and 10000 <= o["precio_normal"] <= 1500000 and o["id"] not in ya_publicadas
                  and o.get("categoria") not in ("Otros",) and o.get("subcategoria") != "Salud y bienestar"]
    def puntaje(o):
        return o["descuento"] + (8 if o.get("minimo_30d") else 0) + 4 * math.log10(max(o["precio_normal"] - o["precio"], 1)) + random.random() * 6
    candidatas.sort(key=puntaje, reverse=True)
    elegidas, tiendas, categorias = [], {}, {}
    for o in candidatas:
        if tiendas.get(o["tienda"], 0) >= por_tienda or categorias.get(o["categoria"], 0) >= por_categoria:
            continue
        try:
            o["_foto"] = bajar_imagen(o["imagen"])
        except Exception as e:
            print(f"  sin foto para {o['nombre'][:40]}: {e}")
            continue
        o = dict(o, nombre=nombre_bonito(o["nombre"]), _foto=o["_foto"])
        elegidas.append(o)
        tiendas[o["tienda"]] = tiendas.get(o["tienda"], 0) + 1
        categorias[o["categoria"]] = categorias.get(o["categoria"], 0) + 1
        if len(elegidas) == cantidad:
            break
    return elegidas


def texto_publicacion(fecha, elegidas, total_ofertas, largo_nombre=None):
    lineas = [f"🔥 Los ofertazos de hoy, {fecha_larga(fecha)}", ""]
    for i, o in enumerate(elegidas, 1):
        nombre = o["nombre"] if not largo_nombre or len(o["nombre"]) <= largo_nombre else o["nombre"][:largo_nombre].rstrip() + "…"
        lineas.append(f"{i}. {nombre} en {o['tienda']}: {clp(o['precio'])} (antes {clp(o['precio_normal'])}, -{o['descuento']}%)")
        if enlace_limpio(o.get("url")):
            lineas.append("👉 " + enlace_limpio(o["url"]))
    lineas += ["", f"Estas y más de {total_ofertas:,} ofertas desde 50% de descuento en priveofertazos.cl".replace(",", "."),
               "Es solo para miembros: pide tu acceso en el link de la bio o escríbenos por DM 💌", "",
               "Precios revisados esta mañana; la tienda puede cambiarlos en cualquier momento.", "",
               "#ofertas #descuentos #ofertaschile #chile #liquidacion #outlet #ahorro #moda #hogar #priveofertazos"]
    texto = "\n".join(lineas)
    if len(texto) > 2200 and (largo_nombre or 999) > 30:  # Instagram acepta hasta 2.200 caracteres
        return texto_publicacion(fecha, elegidas, total_ofertas, (largo_nombre or 80) - 10)
    return texto


def guardar(img, ruta):
    img.save(ruta, "JPEG", quality=88, optimize=True, progressive=True)


# ------------------------------------------------------------------ vitrina: 30 historias para subir a mano
VITRINA = os.path.join(CARPETA, "vitrina")
VITRINA_CANTIDAD = 30
VITRINA_HORAS = 3


def vitrina(ofertas, forzar=False):
    """Cada 3 horas deja 30 historias de ofertas (fondo oscuro, sin link escrito) con su link aparte."""
    ahora = dt.datetime.now(CHILE)
    ruta = os.path.join(VITRINA, "indice.json")
    previo = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {}
    if not forzar and previo.get("creado"):
        if ahora - dt.datetime.fromisoformat(previo["creado"]) < dt.timedelta(hours=VITRINA_HORAS):
            return
    # no repetir lo mostrado en las últimas 24 horas
    recientes = {i: t for i, t in (previo.get("recientes") or {}).items() if ahora - dt.datetime.fromisoformat(t) < dt.timedelta(hours=24)}
    elegidas = elegir(ofertas, set(recientes), VITRINA_CANTIDAD, por_tienda=3, por_categoria=8)
    if len(elegidas) < 5:
        print("Vitrina: no hay suficientes ofertas con foto.")
        return
    os.makedirs(VITRINA, exist_ok=True)
    for a in os.listdir(VITRINA):
        if a.endswith(".jpg"):
            os.remove(os.path.join(VITRINA, a))
    sello = ahora.strftime("%Y%m%d%H%M")  # nombre nuevo en cada vuelta, para que no quede la imagen vieja en caché
    lista = []
    for n, o in enumerate(elegidas, 1):
        archivo = f"oferta_{sello}_{n:02d}.jpg"
        guardar(historia_estrella(o, ahora.date()), os.path.join(VITRINA, archivo))
        lista.append({"archivo": archivo, **{k: o[k] for k in ("id", "nombre", "tienda", "precio", "precio_normal", "descuento", "url")}})
        recientes[o["id"]] = ahora.isoformat(timespec="minutes")
    json.dump({"creado": ahora.isoformat(timespec="minutes"), "ofertas": lista, "recientes": recientes},
              open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Vitrina: {len(lista)} historias nuevas.")


# ------------------------------------------------------------------ Mercado Libre: 20 ofertas del día
ML_CARPETA = os.path.join(CARPETA, "mercadolibre")
ML_CANTIDAD = 20      # historias del día en el panel, con su link de afiliada
ML_CARRUSEL = 9       # de esas, las primeras van al carrusel automático (máximo 10 imágenes con la portada)
ML_DIAS_SIN_REPETIR = 2


def elegir_ml(ofertas, excluir, cantidad):
    candidatas = [o for o in ofertas if o.get("tienda") == "Mercado Libre" and o.get("imagen") and not o.get("dudoso")
                  and o["descuento"] >= 50 and o["precio"] >= 2000]
    def puntaje(o):
        return o["descuento"] + 4 * math.log10(max(o["precio_normal"] - o["precio"], 1)) + random.random() * 6
    candidatas.sort(key=puntaje, reverse=True)
    # primero las que no salieron en los últimos días; si no alcanzan, se repiten
    candidatas = [o for o in candidatas if o["id"] not in excluir] + [o for o in candidatas if o["id"] in excluir]
    elegidas, categorias, vistos = [], {}, set()
    # primera pasada: máximo 6 por categoría; segunda: sin tope, para completar las 20
    for pasada, o in [(1, o) for o in candidatas] + [(2, o) for o in candidatas]:
        if len(elegidas) == cantidad:
            break
        if o["id"] in vistos or (pasada == 1 and categorias.get(o.get("categoria"), 0) >= 6):
            continue
        vistos.add(o["id"])
        try:
            foto = bajar_imagen(o["imagen"])
        except Exception as e:
            print(f"  sin foto para {o['nombre'][:40]}: {e}")
            continue
        elegidas.append(dict(o, nombre=nombre_bonito(o["nombre"]), _foto=foto))
        categorias[o.get("categoria")] = categorias.get(o.get("categoria"), 0) + 1
        if len(elegidas) == cantidad:
            break
    return elegidas


def mercadolibre_del_dia(ofertas, forzar=False):
    """Una vez al día: 20 historias de Mercado Libre (con link de afiliada aparte) para el panel.
    Devuelve las ofertas del día (las nuevas traen su foto en "_foto")."""
    ahora = dt.datetime.now(CHILE)
    hoy = ahora.date().isoformat()
    ruta = os.path.join(ML_CARPETA, "indice.json")
    previo = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {}
    if not forzar and previo.get("fecha") == hoy:
        return previo.get("ofertas") or []
    limite = (ahora.date() - dt.timedelta(days=ML_DIAS_SIN_REPETIR)).isoformat()
    recientes = {i: f for i, f in (previo.get("recientes") or {}).items() if f > limite and f != hoy}
    elegidas = elegir_ml(ofertas, set(recientes), ML_CANTIDAD)
    if len(elegidas) < 5:
        print("Mercado Libre: no hay suficientes ofertas con foto.")
        return previo.get("ofertas") or []
    os.makedirs(ML_CARPETA, exist_ok=True)
    for a in os.listdir(ML_CARPETA):
        if a.endswith(".jpg"):
            os.remove(os.path.join(ML_CARPETA, a))
    sello = ahora.strftime("%Y%m%d%H%M")
    lista = []
    for n, o in enumerate(elegidas, 1):
        archivo = f"ml_{sello}_{n:02d}.jpg"
        guardar(historia_estrella(o, ahora.date(), n, len(elegidas)), os.path.join(ML_CARPETA, archivo))
        lista.append({"archivo": archivo, "imagen": o["imagen"], **{k: o[k] for k in ("id", "nombre", "tienda", "precio", "precio_normal", "descuento", "url")}})
        recientes[o["id"]] = hoy
    json.dump({"fecha": hoy, "creado": ahora.isoformat(timespec="minutes"), "ofertas": lista, "recientes": recientes},
              open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Mercado Libre: {len(lista)} historias del día.")
    for o, x in zip(elegidas, lista):
        x["_foto"] = o["_foto"]
    return lista


def texto_ml(fecha, elegidas, largo_nombre=None):
    lineas = [f"🛒 Mercado Libre: {len(elegidas)} ofertazos de hoy, {fecha_larga(fecha)}", ""]
    for i, o in enumerate(elegidas, 1):
        nombre = o["nombre"] if not largo_nombre or len(o["nombre"]) <= largo_nombre else o["nombre"][:largo_nombre].rstrip() + "…"
        lineas.append(f"{i}. {nombre}: {clp(o['precio'])} (antes {clp(o['precio_normal'])}, -{o['descuento']}%)")
        if o.get("url"):
            lineas.append("👉 " + o["url"].replace("https://", ""))
    lineas += ["", "Más ofertas de Mercado Libre y de +90 tiendas, desde 50% de descuento, en priveofertazos.cl",
               "Los links también están en nuestras historias 💌", "",
               "Precios revisados hoy; Mercado Libre puede cambiarlos en cualquier momento.", "",
               "#mercadolibre #ofertas #descuentos #ofertaschile #chile #ahorro #blackfriday #priveofertazos"]
    texto = "\n".join(lineas)
    if len(texto) > 2200 and (largo_nombre or 999) > 30:
        return texto_ml(fecha, elegidas, (largo_nombre or 80) - 10)
    return texto


def main(forzar=False):
    ahora = dt.datetime.now(CHILE)
    fecha = ahora.date()
    indice_ruta = os.path.join(CARPETA, "indice.json")
    indice = json.load(open(indice_ruta, encoding="utf-8")) if os.path.exists(indice_ruta) else {"dias": [], "publicadas": {}}
    datos = json.load(open(OFERTAS, encoding="utf-8"))
    ofertas = datos["ofertas"]
    try:
        vitrina(ofertas, forzar)
    except Exception as e:  # la vitrina nunca debe frenar lo demás
        print("Vitrina: no se pudo hacer:", e)
    try:
        ml = mercadolibre_del_dia(ofertas, forzar)
    except Exception as e:
        print("Mercado Libre: no se pudo hacer:", e)
        ml = []
    if not forzar:
        if (ahora.hour, ahora.minute) < HORA_INICIO:
            print("Publicaciones: todavía es temprano.")
            return 0
        if any(x["fecha"] == fecha.isoformat() for x in indice["dias"]):
            print("Publicaciones: las de hoy ya están hechas.")
            return 0
    tiendas = sum(1 for t in json.load(open(ESTADO, encoding="utf-8"))["tiendas"] if t.get("ok")) if os.path.exists(ESTADO) else 0
    ya = {i for f, ids in indice.get("publicadas", {}).items() for i in ids}
    elegidas = elegir(ofertas, ya)
    if len(elegidas) < 3:
        print("Publicaciones: no hay suficientes ofertas con foto.")
        return 0
    carpeta = os.path.join(CARPETA, fecha.isoformat())
    os.makedirs(carpeta, exist_ok=True)
    archivos = []
    guardar(lamina_portada(fecha, elegidas, len(ofertas), tiendas), os.path.join(carpeta, "carrusel_0.jpg"))
    archivos.append("carrusel_0.jpg")
    for n, o in enumerate(elegidas, 1):
        nombre = f"carrusel_{n}.jpg"
        guardar(lamina_oferta(o, n, len(elegidas), fecha), os.path.join(carpeta, nombre))
        archivos.append(nombre)
    # se publica sola solo la historia que invita a pedir acceso; las de ofertas (con link) están en la vitrina
    guardar(historia_promo(elegidas, len(ofertas), tiendas), os.path.join(carpeta, "historia_promo.jpg"))
    historias = ["historia_promo.jpg"]
    texto = texto_publicacion(fecha, elegidas, len(ofertas))
    open(os.path.join(carpeta, "texto.txt"), "w", encoding="utf-8").write(texto)
    # segundo carrusel: ofertas de Mercado Libre del día (con link de afiliada en el texto)
    carrusel_ml, txt_ml = [], ""
    try:
        para_ml = []
        for o in ml[:ML_CARRUSEL]:
            if "_foto" not in o:
                try:
                    o = dict(o, _foto=bajar_imagen(o["imagen"]))
                except Exception:
                    continue
            para_ml.append(o)
        if len(para_ml) >= 3:
            total_ml = sum(1 for o in ofertas if o.get("tienda") == "Mercado Libre")
            guardar(lamina_portada(fecha, para_ml, len(ofertas), tiendas, "MERCADO LIBRE", "OFERTAS DE HOY",
                                   f"{total_ml} ofertas de Mercado Libre desde 50%"), os.path.join(carpeta, "ml_0.jpg"))
            carrusel_ml.append("ml_0.jpg")
            for n, o in enumerate(para_ml, 1):
                guardar(lamina_oferta(o, n, len(para_ml), fecha), os.path.join(carpeta, f"ml_{n}.jpg"))
                carrusel_ml.append(f"ml_{n}.jpg")
            txt_ml = texto_ml(fecha, para_ml)
    except Exception as e:
        print("Mercado Libre: no se pudo armar el carrusel:", e)
        carrusel_ml, txt_ml = [], ""

    indice["dias"] = [x for x in indice["dias"] if x["fecha"] != fecha.isoformat()]
    indice["dias"].insert(0, {
        "fecha": fecha.isoformat(), "creado": ahora.isoformat(timespec="minutes"),
        "carrusel": archivos, "historias": historias, "texto": texto,
        **({"carrusel_ml": carrusel_ml, "texto_ml": txt_ml} if carrusel_ml else {}),
        "ofertas": [{k: o[k] for k in ("id", "nombre", "tienda", "precio", "precio_normal", "descuento", "url")} for o in elegidas],
    })
    # si se rehacen las de hoy, se suman a las ya elegidas (para no repetirlas en 21 días)
    previas = indice["publicadas"].get(fecha.isoformat(), [])
    indice["publicadas"][fecha.isoformat()] = previas + [o["id"] for o in elegidas if o["id"] not in previas]
    # guardar solo los últimos días
    fechas = sorted({x["fecha"] for x in indice["dias"]}, reverse=True)[:DIAS_GUARDADOS]
    indice["dias"] = [x for x in indice["dias"] if x["fecha"] in fechas]
    indice["publicadas"] = {f: v for f, v in indice["publicadas"].items() if f >= (fecha - dt.timedelta(days=21)).isoformat()}
    for nombre in os.listdir(CARPETA):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", nombre) and nombre not in fechas:
            for a in os.listdir(os.path.join(CARPETA, nombre)):
                os.remove(os.path.join(CARPETA, nombre, a))
            os.rmdir(os.path.join(CARPETA, nombre))
    json.dump(indice, open(indice_ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Publicaciones: listas las de {fecha} ({len(elegidas)} ofertas).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(forzar="--forzar" in sys.argv))
    except Exception as e:  # un problema con las imágenes nunca debe frenar la actualización de ofertas
        print("Publicaciones: no se pudieron hacer:", e)
        sys.exit(0)
