#!/usr/bin/env python3
"""
Recolector de ofertas del retail chileno (descuentos de 50% o más).

Cómo funciona, en simple:
  1. Lee la lista de tiendas en tiendas.json.
  2. Lee el catálogo público de cada tienda con el "lector" que corresponde a su
     plataforma:
       - shopify: tiendas Shopify publican /products.json con precio y precio anterior.
       - sfcc:    tiendas Salesforce (como Hites) muestran su grilla ordenada por
                  descuento, y cada producto trae sus datos en la página.
       - vtex:    tiendas VTEX publican un catálogo ordenable por descuento.
  3. Se queda con los productos con stock y descuento >= 50%.
  4. Guarda el historial de precios para detectar descuentos "inflados".
  5. Escribe docs/ofertas.json, que es lo que muestra la página web.

Solo usa Python estándar: no hay que instalar nada.
Uso:  python recolector/recolectar.py
"""
import datetime as dt
import gzip
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_TIENDAS = os.path.join(RAIZ, "tiendas.json")
ARCHIVO_SALIDA = os.path.join(RAIZ, "docs", "ofertas.json")
ARCHIVO_HISTORIAL = os.path.join(RAIZ, "datos", "historial.json")
ARCHIVO_ESTADO = os.path.join(RAIZ, "docs", "estado.json")

DESCUENTO_MINIMO = 50          # % mínimo para guardar una oferta
MAX_PAGINAS = 40               # tope de páginas por tienda
PAUSA_SEGUNDOS = 1.0           # pausa entre consultas, para no sobrecargar a la tienda
DIAS_HISTORIAL = 60
USER_AGENT = ("Mozilla/5.0 (compatible; MitadDePrecioBot/1.0; "
              "+https://plu88.github.io/mitad-de-precio/)")


# ---------------------------------------------------------------- utilidades
def leer_json(ruta, por_defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return por_defecto


def escribir_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def pedir(url, intentos=3, acepta="application/json"):
    """Descarga una URL y devuelve el texto (descomprime gzip si hace falta)."""
    ultimo_error = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": USER_AGENT, "Accept": acepta, "Accept-Language": "es-CL,es;q=0.9",
                "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=40) as r:
                crudo = r.read()
            if crudo[:2] == b"\x1f\x8b":
                crudo = gzip.decompress(crudo)
            return crudo.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            ultimo_error = e
            if e.code in (400, 401, 403, 404):
                raise  # no tiene sentido reintentar
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            ultimo_error = e
        time.sleep(3 * (i + 1))
    raise ultimo_error


def pedir_json(url, intentos=3):
    """Como pedir(), pero interpreta JSON. Devuelve None si la respuesta no es JSON."""
    texto = pedir(url, intentos)
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return None


def a_numero(valor):
    """Convierte '21.990', '21990.0' o 21990 en número; devuelve 0 si no se puede."""
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = re.sub(r"[^0-9,.]", "", str(valor or ""))
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "")
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return 0.0


def calcular_descuento(precio, normal):
    if not precio or not normal or normal <= precio:
        return 0
    return round((1 - precio / normal) * 100)


# Categorías comunes para todas las tiendas (cada tienda nombra las suyas distinto)
CATEGORIAS = [
    ("Calzado", r"zapat|zapatill|bot[ai]n|\bbotas?\b|sandal|calzado|chala|pantufl|mocas|sneaker|\bshoes?\b|clog|zueco"),
    ("Deportes", r"deport|running|trekking|outdoor|bicicl|fitness|yoga|camping|\bgym\b|futbol|fútbol"),
    ("Tecnología", r"notebook|celular|smartphone|tablet|\btv\b|televis|monitor|audífon|audifon|parlante|consola|tecnolog|computador|smartwatch|cámara"),
    ("Electrohogar", r"refriger|lavadora|secadora|microond|horno|freidora|aspirador|cafetera|hervidor|licuadora|electrohogar|cocina a gas|estufa"),
    ("Muebles y hogar", r"sof[aá]|silla|mesa|cama|colch[oó]n|plum[oó]n|s[aá]bana|almohad|mueble|cortina|alfombra|hogar|decoraci|vajilla|toalla|bater[ií]a de cocina|l[aá]mpara"),
    ("Belleza y salud", r"perfum|crema|shampoo|maquill|belleza|cosm[eé]t|farmacia|vitamin|dermo|protector solar|colonia"),
    ("Infantil", r"infantil|beb[eé]|niñ[oa]s?|kids|juguet|junior|escolar"),
    ("Accesorios", r"mochila|bolso|cartera|billetera|gorr[oa]|jockey|lentes|reloj|cintur[oó]n|calcet|bufanda|guantes|accesorio|maleta|equipaje"),
    ("Vestuario", r"polera|poler[oó]n|pantal[oó]n|jean|chaqueta|parka|vestido|camisa|blusa|falda|short|calza|buzo|sweater|chaleco|abrigo|ropa|vestuario|polar|cortaviento|traje de baño|bikini|pijama|\btop\b|jacket|hoodie|t-shirt|tee\b"),
]


def categoria_comun(*textos):
    t = " ".join(x for x in textos if x).lower()
    for nombre, patron in CATEGORIAS:
        if re.search(patron, t):
            return nombre
    return "Otros"


def nueva_oferta(tienda, pid, nombre, marca, cat_tienda, precio, normal, imagen, url):
    return {
        "id": f"{tienda['id']}-{pid}",
        "tienda": tienda["nombre"],
        "nombre": (nombre or "").strip(),
        "marca": (marca or "").strip(),
        "categoria": categoria_comun(cat_tienda, nombre),
        "precio": int(round(precio)),
        "precio_normal": int(round(normal)),
        "descuento": calcular_descuento(precio, normal),
        "imagen": imagen or "",
        "url": url,
    }


# ---------------------------------------------------------------- Shopify
def recolectar_shopify(tienda):
    """Recorre /products.json (250 productos por página)."""
    base = "https://" + tienda["dominio"]
    ofertas = []
    for pagina in range(1, MAX_PAGINAS + 1):
        datos = pedir_json(f"{base}/products.json?limit=250&page={pagina}")
        if not isinstance(datos, dict) or "products" not in datos:
            if pagina == 1:
                raise ValueError("no respondió como tienda Shopify")
            break
        productos = datos["products"]
        if not productos:
            break
        for p in productos:
            mejor = None
            for v in p.get("variants") or []:
                if v.get("available") is False:
                    continue
                try:
                    precio = float(v.get("price") or 0)
                    normal = float(v.get("compare_at_price") or 0)
                except ValueError:
                    continue
                d = calcular_descuento(precio, normal)
                if d >= DESCUENTO_MINIMO and (mejor is None or d > mejor[0]):
                    mejor = (d, precio, normal)
            if mejor:
                imagenes = p.get("images") or []
                ofertas.append(nueva_oferta(
                    tienda, p.get("id"), p.get("title"), p.get("vendor"), p.get("product_type"),
                    mejor[1], mejor[2], imagenes[0].get("src") if imagenes else "",
                    f"{base}/products/{p.get('handle')}"))
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


# ---------------------------------------------------------------- Salesforce (SFCC)
TILE = re.compile(r'data-gtmselectitem="([^"]+)"')
HREF = re.compile(r'<a[^>]+href="(https?://[^"]+?\.html)[^"]*"')
IMG = re.compile(r'<img[^>]+(?:src|data-src)="(https?://[^"]+?\.(?:jpg|jpeg|png|webp)[^"]*)"')


def leer_grilla_sfcc(tienda, texto):
    """Extrae productos de una grilla Salesforce que trae los datos en data-gtmselectitem."""
    productos = []
    posiciones = [m for m in TILE.finditer(texto)]
    for i, m in enumerate(posiciones):
        fin = posiciones[i + 1].start() if i + 1 < len(posiciones) else m.end() + 8000
        trozo = texto[m.end():fin]
        try:
            dato = json.loads(html.unescape(m.group(1)))
        except json.JSONDecodeError:
            continue
        item = dato.get("item") or dato
        precio = a_numero(item.get("price") or dato.get("value"))
        rebaja = a_numero(item.get("discount"))
        if not precio:
            continue
        enlace = HREF.search(trozo)
        imagen = IMG.search(trozo)
        productos.append(nueva_oferta(
            tienda, item.get("item_id"), item.get("item_name"), item.get("item_brand"),
            item.get("item_category"), precio, precio + rebaja,
            html.unescape(imagen.group(1)) if imagen else "",
            html.unescape(enlace.group(1)) if enlace else f"https://{tienda['dominio']}/"))
    return productos


def recolectar_sfcc(tienda):
    """Pide la grilla ordenada por mayor descuento, de 48 en 48, hasta bajar del 50%."""
    base = f"https://{tienda['dominio']}/on/demandware.store/Sites-{tienda['sitio']}-Site/default/Search-UpdateGrid"
    regla = tienda.get("orden", "discount-off")
    ofertas, vistos = [], set()
    for pagina in range(MAX_PAGINAS):
        url = f"{base}?cgid={tienda.get('categoria', 'root')}&srule={regla}&start={pagina * 48}&sz=48"
        productos = leer_grilla_sfcc(tienda, pedir(url, acepta="text/html"))
        if not productos:
            if pagina == 0:
                raise ValueError("la grilla de productos llegó vacía")
            break
        sobre_umbral = 0
        for o in productos:
            if o["id"] in vistos:
                continue
            vistos.add(o["id"])
            if o["descuento"] >= DESCUENTO_MINIMO:
                ofertas.append(o)
                sobre_umbral += 1
        if sobre_umbral == 0:
            break  # viene ordenado por descuento: lo que sigue es menor
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


# ---------------------------------------------------------------- VTEX
def recolectar_vtex(tienda):
    ofertas = []
    for pagina in range(MAX_PAGINAS):
        desde = pagina * 50
        params = {"O": "OrderByBestDiscountDESC", "_from": desde, "_to": desde + 49}
        url = f"https://{tienda['dominio']}/api/catalog_system/pub/products/search?" + urllib.parse.urlencode(params)
        datos = pedir_json(url)
        if not isinstance(datos, list):
            if pagina == 0:
                raise ValueError("no respondió como tienda VTEX")
            break
        if not datos:
            break
        sobre_umbral = 0
        for p in datos:
            mejor = None
            for item in p.get("items") or []:
                imgs = item.get("images") or []
                for s in item.get("sellers") or []:
                    co = s.get("commertialOffer") or {}
                    if co.get("AvailableQuantity", 0) <= 0:
                        continue
                    d = calcular_descuento(co.get("Price"), co.get("ListPrice"))
                    if mejor is None or d > mejor[0]:
                        mejor = (d, co["Price"], co["ListPrice"], imgs[0].get("imageUrl") if imgs else "")
            if mejor and mejor[0] >= DESCUENTO_MINIMO:
                cats = p.get("categories") or [""]
                ofertas.append(nueva_oferta(
                    tienda, p.get("productId"), p.get("productName"), p.get("brand"), cats[0],
                    mejor[1], mejor[2], mejor[3],
                    p.get("link") or f"https://{tienda['dominio']}/{p.get('linkText', '')}/p"))
                sobre_umbral += 1
        if sobre_umbral == 0:
            break
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


RECOLECTORES = {"shopify": recolectar_shopify, "sfcc": recolectar_sfcc, "vtex": recolectar_vtex}


def explicar_error(e):
    """Traduce el error a algo entendible en docs/estado.json."""
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 403):
            return f"La tienda bloqueó la consulta (error {e.code})."
        if e.code == 404:
            return "La tienda no publica ese catálogo (error 404)."
        if e.code == 429:
            return "La tienda pidió esperar (demasiadas consultas). Se reintentará en la próxima vuelta."
        return f"La tienda respondió con error {e.code}."
    if isinstance(e, ValueError):
        return f"Respuesta inesperada: {e}."
    if isinstance(e, KeyError):
        return "Tipo de tienda no soportado todavía."
    return f"No se pudo conectar: {str(e)[:150]}"


# ---------------------------------------------------------------- historial
def actualizar_historial(historial, ofertas, hoy):
    """Guarda (fecha, precio, precio_normal) por producto y recorta lo antiguo."""
    limite = (dt.date.fromisoformat(hoy) - dt.timedelta(days=DIAS_HISTORIAL)).isoformat()
    for o in ofertas:
        registros = historial.setdefault(o["id"], [])
        if registros and registros[-1][0] == hoy:
            registros[-1] = [hoy, o["precio"], o["precio_normal"]]
        else:
            registros.append([hoy, o["precio"], o["precio_normal"]])
    for clave in list(historial):
        historial[clave] = [r for r in historial[clave] if r[0] >= limite]
        if not historial[clave]:
            del historial[clave]
    return historial


def evaluar_con_historial(oferta, registros, hoy):
    """
    minimo_30d: el precio de hoy es el más bajo visto en 30 días.
    dudoso: llevamos 7+ días observando el producto y nunca se cobró algo
            cercano al "precio normal" que la tienda usa para calcular el %.
    """
    hace30 = (dt.date.fromisoformat(hoy) - dt.timedelta(days=30)).isoformat()
    previos = [r for r in registros if r[0] < hoy]
    recientes = [r for r in previos if r[0] >= hace30]
    oferta["minimo_30d"] = bool(recientes) and oferta["precio"] <= min(r[1] for r in recientes)
    oferta["dias_observado"] = len({r[0] for r in registros})
    if previos:
        primer_dia = dt.date.fromisoformat(previos[0][0])
        dias = (dt.date.fromisoformat(hoy) - primer_dia).days
        max_cobrado = max(r[1] for r in registros)
        oferta["dudoso"] = dias >= 7 and max_cobrado < 0.8 * oferta["precio_normal"]
    else:
        oferta["dudoso"] = False
    return oferta


# ---------------------------------------------------------------- principal
def main():
    tiendas = [t for t in leer_json(ARCHIVO_TIENDAS, []) if t.get("activa", True)]
    if not tiendas:
        print("No hay tiendas activas en tiendas.json")
        return 1

    hoy = dt.date.today().isoformat()
    todas, estado = [], []
    for tienda in tiendas:
        inicio = time.time()
        try:
            recolector = RECOLECTORES[tienda.get("tipo", "vtex")]
            ofertas = recolector(tienda)
            todas.extend(ofertas)
            estado.append({"tienda": tienda["nombre"], "ok": True, "ofertas": len(ofertas)})
            print(f"✔ {tienda['nombre']}: {len(ofertas)} ofertas ({time.time() - inicio:.0f}s)")
        except Exception as e:  # una tienda caída no debe botar todo
            motivo = explicar_error(e)
            estado.append({"tienda": tienda["nombre"], "ok": False, "error": motivo})
            print(f"✘ {tienda['nombre']}: {motivo}")

    # quitar duplicados (mismo id) quedándose con el mayor descuento
    unicas = {}
    for o in todas:
        if o["id"] not in unicas or o["descuento"] > unicas[o["id"]]["descuento"]:
            unicas[o["id"]] = o
    ofertas = list(unicas.values())

    ahora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    escribir_json(ARCHIVO_ESTADO, {"actualizado": ahora, "tiendas": estado})
    if not ofertas:
        print("No llegó ninguna oferta: se mantienen las del día anterior.")
        return 0

    historial = leer_json(ARCHIVO_HISTORIAL, {})
    for o in ofertas:
        evaluar_con_historial(o, historial.get(o["id"], []), hoy)
    actualizar_historial(historial, ofertas, hoy)

    ofertas.sort(key=lambda o: (-o["descuento"], o["precio"]))
    escribir_json(ARCHIVO_SALIDA, {"actualizado": ahora, "total": len(ofertas), "ofertas": ofertas})
    escribir_json(ARCHIVO_HISTORIAL, historial)
    print(f"Listo: {len(ofertas)} ofertas de {DESCUENTO_MINIMO}% o más.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
