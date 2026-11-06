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
  5. Escribe datos/ofertas.json; luego cifrar.py lo convierte en datos/ofertas.enc,
     que solo la página de miembros puede leer.

Solo usa Python estándar: no hay que instalar nada.
Uso:  python recolector/recolectar.py
"""
import datetime as dt
import gzip
import html
import json
import os
import concurrent.futures
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clasificar import (clasificar, genero, tallas as ordenar_tallas, ES_OPCION_TALLA,  # noqa: E402
                        TALLA_EN_NOMBRE, CON_TALLAS)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_TIENDAS = os.path.join(RAIZ, "tiendas.json")
ARCHIVO_SALIDA = os.path.join(RAIZ, "datos", "ofertas.json")   # no se sube: se cifra
ARCHIVO_HISTORIAL = os.path.join(RAIZ, "datos", "historial.json")
ARCHIVO_ESTADO = os.path.join(RAIZ, "datos", "estado.json")

DESCUENTO_MINIMO = 50          # % mínimo para guardar una oferta
MAX_PAGINAS = 40               # tope de páginas por tienda
PAUSA_SEGUNDOS = 1.0           # pausa entre consultas, para no sobrecargar a la tienda
DIAS_HISTORIAL = 60
# Algunas tiendas tienen su certificado de seguridad incompleto: los navegadores lo completan solos,
# Python no. Para esas tiendas ("ssl_flexible": true en tiendas.json) se omite esa verificación.
# Solo se leen precios públicos, así que no se expone ningún dato.
SSL_FLEXIBLE = ssl.create_default_context()
SSL_FLEXIBLE.check_hostname = False
SSL_FLEXIBLE.verify_mode = ssl.CERT_NONE
_local = threading.local()   # cada tienda se revisa en su propio hilo
TIENDAS_A_LA_VEZ = 8

USER_AGENT = ("Mozilla/5.0 (compatible; PriveOfertazosBot/1.0; "
              "+https://plu88.github.io/mitad-de-precio/)")


# ---------------------------------------------------------------- utilidades
def leer_json(ruta, por_defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return por_defecto


def escribir_json(ruta, datos, compacto=False):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compacto:
            json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
        else:
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
            with urllib.request.urlopen(req, timeout=40, context=getattr(_local, "ssl", None)) as r:
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


def nueva_oferta(tienda, pid, nombre, marca, cat_tienda, precio, normal, imagen, url, tallas=None, pistas=""):
    """Arma una oferta. `cat_tienda` y `pistas` (etiquetas, rutas de categoría) ayudan a clasificarla."""
    nombre = (nombre or "").strip()
    categoria, subcategoria = clasificar(nombre, cat_tienda, pistas, url)
    oferta = {
        "id": f"{tienda['id']}-{pid}",
        "tienda": tienda["nombre"],
        "nombre": nombre,
        "marca": (marca or "").strip(),
        "categoria": categoria,
        "subcategoria": subcategoria,
        "precio": int(round(precio)),
        "precio_normal": int(round(normal)),
        "descuento": calcular_descuento(precio, normal),
        "imagen": imagen or "",
        "url": url,
    }
    generos = genero(nombre, cat_tienda, pistas, url) or ([tienda["genero"]] if tienda.get("genero") and categoria in CON_TALLAS else [])
    if generos:
        oferta["genero"] = generos
    if not tallas:
        m = TALLA_EN_NOMBRE.search(nombre)  # "Zapato nude Talla 38"
        tallas = [m.group(1)] if m else []
    lista = ordenar_tallas(tallas) if categoria in CON_TALLAS else []
    if lista:
        oferta["tallas"] = lista
    return oferta


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
            mejor, tallas_oferta = None, []
            posiciones = [o.get("position") for o in p.get("options") or [] if ES_OPCION_TALLA.search(o.get("name") or "")]
            for v in p.get("variants") or []:
                if v.get("available") is False:
                    continue
                try:
                    precio = float(v.get("price") or 0)
                    normal = float(v.get("compare_at_price") or 0)
                except ValueError:
                    continue
                d = calcular_descuento(precio, normal)
                if d >= DESCUENTO_MINIMO:
                    tallas_oferta += [v.get(f"option{pos}") for pos in posiciones]
                if d >= DESCUENTO_MINIMO and (mejor is None or d > mejor[0]):
                    mejor = (d, precio, normal)
            if mejor:
                imagenes = p.get("images") or []
                etiquetas = p.get("tags") or []
                etiquetas = " ".join(etiquetas) if isinstance(etiquetas, list) else str(etiquetas)
                ofertas.append(nueva_oferta(
                    tienda, p.get("id"), p.get("title"), p.get("vendor"), p.get("product_type"),
                    mejor[1], mejor[2], imagenes[0].get("src") if imagenes else "",
                    f"{base}/products/{p.get('handle')}", tallas_oferta, etiquetas))
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


# ---------------------------------------------------------------- Salesforce (SFCC)
TILE = re.compile(r'data-gtmselectitem="([^"]+)"')
HREF = re.compile(r'<a[^>]+href="((?:https?://[^"/]+)?/[^"?]+?\.html)[^"]*"')
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
        if precio <= 1000 and precio + rebaja >= 9990:
            continue  # "$1.000" en productos caros: casi siempre es un error de precio
        enlace = HREF.search(trozo)
        imagen = IMG.search(trozo)
        if not enlace:
            continue  # sin enlace a la ficha no sirve mostrarlo
        tallas_oferta = []
        for bloque in re.findall(r'<select[^>]*tile-variation-Talla[^>]*>(.*?)</select>', trozo, re.S):
            tallas_oferta += [v for d, v in re.findall(r'<option([^>]*)data-attr-value="([^"]+)"', bloque) if "disabled" not in d]
        productos.append(nueva_oferta(
            tienda, item.get("item_id"), item.get("item_name"), item.get("item_brand"),
            item.get("item_category"), precio, precio + rebaja,
            html.unescape(imagen.group(1)) if imagen else "",
            urllib.parse.urljoin(f"https://{tienda['dominio']}/", html.unescape(enlace.group(1))), tallas_oferta))
    return productos


TILE_ABC = re.compile(r'class="product-tile__wrapper" data-pid="([^"]+)"')


def precio_bloque(trozo, clase):
    m = re.search(clase + r'[^>]*>.*?data-value="([0-9.]+)"', trozo, re.S)
    return float(m.group(1)) if m else 0.0


def leer_grilla_abc(tienda, texto):
    """Grilla Salesforce de abc/La Polar: usa el precio internet (no el exclusivo con tarjeta)."""
    productos = []
    posiciones = list(TILE_ABC.finditer(texto))
    for i, m in enumerate(posiciones):
        fin = posiciones[i + 1].start() if i + 1 < len(posiciones) else len(texto)
        trozo = texto[m.start():fin]
        normal = precio_bloque(trozo, r'js-normal-price')
        precio = precio_bloque(trozo, r'js-internet-price') or normal
        enlace = re.search(r'href="(/[^"?]+\.html)"[^>]*itemprop="url"', trozo) or re.search(r'href="(/[^"?]+\.html)"', trozo)
        nombre = re.search(r'data-product-name="([^"]+)"', trozo)
        imagen = re.search(r'class="tile-image[^"]*"[^>]*src="(https?://[^"]+)"', trozo)
        gtm = re.search(r'data-gtm="([^"]+)"', trozo)
        marca = categoria = ""
        if gtm:
            try:
                imp = json.loads(html.unescape(gtm.group(1)))["ecommerce"]["impressions"]
                marca, categoria = imp.get("brand", ""), imp.get("category", "")
            except (ValueError, KeyError, TypeError):
                pass
        if not (precio and normal and enlace and nombre):
            continue
        productos.append(nueva_oferta(
            tienda, m.group(1), html.unescape(nombre.group(1)), marca.title(), html.unescape(categoria),
            precio, normal, html.unescape(imagen.group(1)) if imagen else "",
            urllib.parse.urljoin(f"https://{tienda['dominio']}/", enlace.group(1))))
    return productos


def recolectar_sfcc(tienda):
    """Pide la grilla ordenada por mayor descuento, de 48 en 48, hasta bajar del 50%."""
    base = f"https://{tienda['dominio']}/on/demandware.store/Sites-{tienda['sitio']}-Site/default/Search-UpdateGrid"
    regla = tienda.get("orden", "discount-off")
    ofertas, vistos = [], set()
    for pagina in range(tienda.get("max_paginas", MAX_PAGINAS)):
        url = f"{base}?cgid={tienda.get('categoria', 'root')}&start={pagina * 48}&sz=48" + (f"&srule={regla}" if regla else "")
        lector = {"abc": leer_grilla_abc, "generica": leer_grilla_sfcc_generica}.get(tienda.get("formato"), leer_grilla_sfcc)
        productos = lector(tienda, pedir(url, acepta="text/html"))
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
        if sobre_umbral == 0 and pagina + 1 >= tienda.get("paginas_minimas", 1):
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
            mejor, tallas_oferta = None, []
            for item in p.get("items") or []:
                imgs = item.get("images") or []
                for s in item.get("sellers") or []:
                    co = s.get("commertialOffer") or {}
                    if co.get("AvailableQuantity", 0) <= 0:
                        continue
                    d = calcular_descuento(co.get("Price"), co.get("ListPrice"))
                    if d >= DESCUENTO_MINIMO:
                        for campo in item.get("variations") or []:
                            if ES_OPCION_TALLA.search(campo):
                                tallas_oferta += item.get(campo) or []
                    if mejor is None or d > mejor[0]:
                        mejor = (d, co["Price"], co["ListPrice"], imgs[0].get("imageUrl") if imgs else "")
            if mejor and mejor[0] >= DESCUENTO_MINIMO:
                cats = p.get("categories") or [""]
                pistas = " ".join(cats) + " " + " ".join(
                    " ".join(map(str, v)) for k, v in p.items() if re.search(r"g[eé]nero|sexo|gender", k, re.I) and isinstance(v, list))
                ofertas.append(nueva_oferta(
                    tienda, p.get("productId"), p.get("productName"), p.get("brand"), cats[0],
                    mejor[1], mejor[2], mejor[3],
                    p.get("link") or f"https://{tienda['dominio']}/{p.get('linkText', '')}/p", tallas_oferta, pistas))
                sobre_umbral += 1
        if sobre_umbral == 0:
            break
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


# ---------------------------------------------------------------- Salesforce genérico (precios en content="...")
TILE_PID = re.compile(r'data-pid="([^"]+)"')


def leer_grilla_sfcc_generica(tienda, texto):
    """Grillas Salesforce que muestran el precio normal (list/strike) y el de venta (sales) como content="…"."""
    productos, cortes, ultimo = [], [], None
    for m in TILE_PID.finditer(texto):
        if m.group(1) != ultimo:
            cortes.append((m.start(), m.group(1)))
            ultimo = m.group(1)
    for i, (ini, pid) in enumerate(cortes):
        fin = cortes[i + 1][0] if i + 1 < len(cortes) else len(texto)
        trozo = texto[ini:fin]
        venta = normal = 0.0
        for m in re.finditer(r'content="([0-9]+(?:\.[0-9]+)?)"', trozo):
            antes = trozo[max(0, m.start() - 300):m.start()]
            pos_venta = antes.rfind("sales")
            pos_normal = max(antes.rfind("list"), antes.rfind("strike"), antes.rfind("price-normal"))
            valor = float(m.group(1))
            if pos_venta > pos_normal and not venta:
                venta = valor
            elif pos_normal > pos_venta and not normal:
                normal = valor
        enlace = re.search(r'href="((?:https?://[^"/]+)?/[^"?]+?\.html)', trozo)
        nombre = (re.search(r'class="pdp-link"[^>]*>\s*<a[^>]*>\s*([^<\s][^<]{3,199})<', trozo)
                  or re.search(r'<img[^>]+title="([^"]{4,200})"', trozo)
                  or re.search(r'<img[^>]+alt="([^"]{4,200})"', trozo))
        imagen = re.search(r'<img[^>]+(?:data-src|src)="(https?://[^"]+?\.(?:jpg|jpeg|png|webp)[^"]*)"', trozo)
        if not (venta and normal and enlace and nombre):
            continue
        productos.append(nueva_oferta(
            tienda, pid, html.unescape(nombre.group(1)).strip(), "", "", venta, normal,
            html.unescape(imagen.group(1)) if imagen else "",
            urllib.parse.urljoin(f"https://{tienda['dominio']}/", html.unescape(enlace.group(1)))))
    return productos


# ---------------------------------------------------------------- Magento (GraphQL público)
CONSULTA_MAGENTO = ('{products(search:"",pageSize:100,currentPage:%d){total_count items{name sku url_key url_suffix '
                    'stock_status small_image{url} categories{name} price_range{minimum_price{regular_price{value} '
                    'final_price{value}}}}}}')


CONSULTA_MAGENTO_TALLAS = CONSULTA_MAGENTO.replace(
    "price_range{", "... on ConfigurableProduct{variants{product{stock_status} attributes{code label}}} price_range{")


def recolectar_magento(tienda):
    ofertas = []
    sufijo = tienda.get("sufijo_url", ".html")
    consulta = CONSULTA_MAGENTO_TALLAS
    for pagina in range(1, tienda.get("max_paginas", 60) + 1):
        api = tienda.get("graphql", tienda["dominio"])  # algunas tiendas tienen la API en otro subdominio
        url = f"https://{api}/graphql?query=" + urllib.parse.quote(consulta % pagina)
        datos = pedir_json(url)
        if pagina == 1 and consulta is CONSULTA_MAGENTO_TALLAS and not ((datos or {}).get("data") or {}).get("products"):
            consulta = CONSULTA_MAGENTO  # esta tienda no acepta la consulta de variantes: se usa la simple
            datos = pedir_json(f"https://{api}/graphql?query=" + urllib.parse.quote(consulta % pagina))
        try:
            items = datos["data"]["products"]["items"]
        except (TypeError, KeyError):
            if pagina == 1:
                raise ValueError("no respondió como tienda Magento")
            break
        if not items:
            break
        for it in items:
            if it.get("stock_status") == "OUT_OF_STOCK":
                continue
            precios = (it.get("price_range") or {}).get("minimum_price") or {}
            precio = a_numero((precios.get("final_price") or {}).get("value"))
            normal = a_numero((precios.get("regular_price") or {}).get("value"))
            if calcular_descuento(precio, normal) < DESCUENTO_MINIMO or not it.get("url_key"):
                continue
            cats = [c.get("name", "") for c in it.get("categories") or []]
            tallas_oferta = [a.get("label") for v in it.get("variants") or []
                             if (v.get("product") or {}).get("stock_status") != "OUT_OF_STOCK"
                             for a in v.get("attributes") or [] if ES_OPCION_TALLA.search(a.get("code") or "")]
            ofertas.append(nueva_oferta(
                tienda, it.get("sku"), it.get("name"), "", " ".join(cats[:3]), precio, normal,
                (it.get("small_image") or {}).get("url", ""),
                f"https://{tienda['dominio']}/{it['url_key']}{sufijo if tienda.get('sufijo_url') else (it.get('url_suffix') or sufijo)}",
                tallas_oferta, " ".join(cats)))
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


# ---------------------------------------------------------------- WooCommerce (Store API pública)
def recolectar_woo(tienda):
    ofertas = []
    for pagina in range(1, MAX_PAGINAS + 1):
        datos = pedir_json(f"https://{tienda['dominio']}/wp-json/wc/store/v1/products?on_sale=true&per_page=100&page={pagina}")
        if not isinstance(datos, list):
            if pagina == 1:
                raise ValueError("no respondió como tienda WooCommerce")
            break
        if not datos:
            break
        for p in datos:
            pr = p.get("prices") or {}
            div = 10 ** int(pr.get("currency_minor_unit") or 0)
            precio = a_numero(pr.get("sale_price") or pr.get("price")) / div
            normal = a_numero(pr.get("regular_price")) / div
            if not p.get("is_in_stock", True) or calcular_descuento(precio, normal) < DESCUENTO_MINIMO:
                continue
            imgs = p.get("images") or []
            cats = [c.get("name", "") for c in p.get("categories") or []]
            tallas_oferta = [t.get("name") for a in p.get("attributes") or [] if ES_OPCION_TALLA.search(a.get("name") or "")
                             for t in a.get("terms") or []]
            ofertas.append(nueva_oferta(
                tienda, p.get("id"), html.unescape(p.get("name") or ""), "", " ".join(cats[:2]), precio, normal,
                imgs[0].get("src", "") if imgs else "", p.get("permalink") or "", tallas_oferta, " ".join(cats)))
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


# ---------------------------------------------------------------- Falabella / Sodimac (datos de la página)
TERMINOS_FALABELLA = [
    "zapatillas", "zapatos", "botines", "sandalias", "polera", "poleron", "chaqueta", "parka", "pantalon", "jeans",
    "vestido", "blusa", "camisa", "short", "pijama", "ropa interior", "traje de baño", "mochila", "cartera", "billetera",
    "reloj", "lentes de sol", "perfume", "maquillaje", "crema", "sabanas", "plumon", "toalla", "cortina", "alfombra",
    "sofa", "colchon", "cama", "mesa", "silla", "lampara", "olla", "sarten", "vajilla", "freidora", "aspiradora",
    "cafetera", "televisor", "notebook", "celular", "audifonos", "parlante", "smartwatch", "juguete", "bicicleta",
    "carpa", "maleta", "herramientas", "taladro", "organizador", "decoracion",
]
FILTRO_50 = "f.range.derived.variant.discount=50%25+dcto+y+m%C3%A1s"
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def precios_falabella(lista):
    """Precio normal = el tachado; precio actual = el menor no tachado, sin contar el exclusivo con tarjeta (CMR)."""
    normal, actuales = 0.0, []
    for p in lista or []:
        valor = a_numero((p.get("price") or [""])[0])
        if not valor:
            continue
        if p.get("crossed") or p.get("type") == "normalPrice":
            normal = max(normal, valor)
        elif p.get("type") != "cmrPrice":
            actuales.append(valor)
    return (min(actuales) if actuales else 0.0), normal


def url_final(url):
    """Sigue las redirecciones y devuelve la dirección donde termina (Sodimac lleva la búsqueda a una categoría)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=40, context=getattr(_local, "ssl", None)) as r:
        return r.geturl()


def recolectar_falabella(tienda):
    base = f"https://{tienda['dominio']}/{tienda['sitio']}/search"
    ofertas, vistos, fallos = [], set(), 0
    for termino in tienda.get("terminos", TERMINOS_FALABELLA):
        busqueda = f"{base}?Ntt={urllib.parse.quote(termino)}"
        if tienda.get("busca_por_categoria"):
            try:
                busqueda = url_final(busqueda).split("#")[0]
            except Exception:
                continue
            if "/lista/" not in busqueda and "/category/" not in busqueda:
                continue  # la búsqueda no llevó a una categoría
        separador = "&" if "?" in busqueda else "?"
        for pagina in range(1, tienda.get("paginas_por_termino", 2) + 1):
            url = f"{busqueda}{separador}{FILTRO_50}&page={pagina}"
            try:
                m = NEXT_DATA.search(pedir(url, acepta="text/html"))
                resultados = json.loads(m.group(1))["props"]["pageProps"].get("results") or [] if m else []
            except Exception:
                fallos += 1
                if fallos >= 5 and not ofertas:
                    raise
                break
            if not resultados:
                break
            for r in resultados:
                pid = r.get("productId")
                if not pid or pid in vistos:
                    continue
                vistos.add(pid)
                precio, normal = precios_falabella(r.get("prices"))
                if calcular_descuento(precio, normal) < DESCUENTO_MINIMO:
                    continue
                imagenes = r.get("mediaUrls") or []
                tallas_oferta = [t.get("value") for v in r.get("variants") or [] for op in v.get("options") or []
                                 for t in op.get("sizes") or [] if t.get("available", True)]
                tallas_oferta += [op.get("label") for v in r.get("variants") or [] if ES_OPCION_TALLA.search(v.get("type") or "")
                                  for op in v.get("options") or []]
                ofertas.append(nueva_oferta(
                    tienda, pid, r.get("displayName"), r.get("brand", "").title(), termino, precio, normal,
                    imagenes[0] if imagenes else "", r.get("url") or "", tallas_oferta, r.get("productType") or ""))
            time.sleep(PAUSA_SEGUNDOS)
    return ofertas


# ---------------------------------------------------------------- Magento leyendo la grilla HTML (iO, Ash)
BLOQUE_MAGENTO = re.compile(r'<li[^>]*class="[^"]*\bproduct-item\b')


def leer_grilla_magento(tienda, texto):
    productos = []
    cortes = [m.start() for m in BLOQUE_MAGENTO.finditer(texto)] + [len(texto)]
    for ini, fin in zip(cortes, cortes[1:]):
        trozo = texto[ini:fin]
        pid = re.search(r'data-product-id="(\d+)"', trozo)
        final = re.search(r'data-price-amount="([0-9.]+)"\s+data-price-type="finalPrice"', trozo)
        antes = re.search(r'data-price-amount="([0-9.]+)"\s+data-price-type="oldPrice"', trozo)
        enlace = re.search(r'class="product-item-link"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*class="product-item-link"', trozo)
        nombre = re.search(r'class="product-item-link"[^>]*>(.*?)</a>', trozo, re.S)
        imagen = re.search(r'class="product-image-photo"[^>]*src="([^"]+)"|src="([^"]+)"[^>]*class="product-image-photo"', trozo)
        if not (pid and final and antes and enlace and nombre):
            continue
        texto_nombre = html.unescape(re.sub(r"<[^>]+>", " ", nombre.group(1)))
        tallas_oferta = re.findall(r'option-label="([^"]+)"[^>]*data-attribute-code="(?:size|talla)', trozo)
        productos.append(nueva_oferta(
            tienda, pid.group(1), re.sub(r"\s+", " ", texto_nombre).strip().capitalize(), tienda["nombre"], "",
            float(final.group(1)), float(antes.group(1)),
            html.unescape(next(g for g in imagen.groups() if g)) if imagen else "",
            html.unescape(next(g for g in enlace.groups() if g)), tallas_oferta))
    return productos


def recolectar_magento_html(tienda):
    """Recorre las categorías indicadas en tiendas.json, página por página (36 productos por página)."""
    ofertas, vistos, errores = [], set(), []
    for categoria in tienda["categorias"]:
        for pagina in range(1, tienda.get("max_paginas", 15) + 1):
            url = f"https://{tienda['dominio']}/{categoria}?p={pagina}&product_list_limit=36"
            try:
                productos = leer_grilla_magento(tienda, pedir(url, acepta="text/html"))
            except Exception as e:  # una categoría con problemas no bota las demás
                errores.append(e)
                break
            nuevos = [o for o in productos if o["id"] not in vistos]
            vistos.update(o["id"] for o in productos)
            ofertas += [o for o in nuevos if o["descuento"] >= DESCUENTO_MINIMO]
            if not nuevos:
                break  # Magento repite la última página cuando se acaban
            time.sleep(tienda.get("pausa", PAUSA_SEGUNDOS))
    if errores and not vistos:
        raise errores[0]
    return ofertas


# ---------------------------------------------------------------- PrestaShop leyendo el listado de rebajas (El Volcán)
def leer_listado_prestashop(tienda, texto):
    productos = []
    nombres = list(re.finditer(r'<span class="digi-product-name">(.*?)</span>', texto, re.S))
    for i, m in enumerate(nombres):
        antes = texto[max(0, m.start() - 2500):m.start()]
        despues = texto[m.end():nombres[i + 1].start() if i + 1 < len(nombres) else m.end() + 5000]
        enlace = re.findall(r'<a href="(https?://[^"]+\.html)"', antes)
        imagen = re.findall(r'<img[^>]+src="(https?://[^"]+)"', antes)
        marca = re.findall(r'<h3 class="digi-product-brand">(.*?)</h3>', antes)
        final = re.search(r'digi-product-price-final">\s*\$?\s*([0-9.]+)', despues)
        normal = re.search(r'class="regular-price">\s*\$?\s*([0-9.]+)', despues)
        pid = re.search(r'-(\d+)\.html$', enlace[-1]) if enlace else None
        if not (enlace and final and normal and pid):
            continue
        productos.append(nueva_oferta(
            tienda, pid.group(1), html.unescape(m.group(1)).strip(),
            html.unescape(marca[-1]).replace("\xa0", " ").strip() if marca else "", enlace[-1],
            a_numero(final.group(1)), a_numero(normal.group(1)), imagen[-1] if imagen else "", enlace[-1]))
    return productos


def recolectar_prestashop_html(tienda):
    ofertas, vistos = [], set()
    for pagina in range(1, tienda.get("max_paginas", 30) + 1):
        url = f"https://{tienda['dominio']}{tienda.get('listado', '/productos-rebajados')}?page={pagina}"
        productos = [o for o in leer_listado_prestashop(tienda, pedir(url, acepta="text/html")) if o["id"] not in vistos]
        if not productos:
            if pagina == 1:
                raise ValueError("el listado de rebajas llegó vacío")
            break
        vistos.update(o["id"] for o in productos)
        ofertas += [o for o in productos if o["descuento"] >= DESCUENTO_MINIMO]
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


RECOLECTORES = {"shopify": recolectar_shopify, "magento_html": recolectar_magento_html, "prestashop_html": recolectar_prestashop_html, "sfcc": recolectar_sfcc, "vtex": recolectar_vtex,
                "magento": recolectar_magento, "woo": recolectar_woo, "falabella": recolectar_falabella}


def explicar_error(e):
    """Traduce el error a algo entendible en datos/estado.json."""
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
    def revisar(tienda):
        _local.ssl = SSL_FLEXIBLE if tienda.get("ssl_flexible") else None
        inicio = time.time()
        try:
            ofertas = RECOLECTORES[tienda.get("tipo", "vtex")](tienda)
            print(f"✔ {tienda['nombre']}: {len(ofertas)} ofertas ({time.time() - inicio:.0f}s)", flush=True)
            return ofertas, {"tienda": tienda["nombre"], "ok": True, "ofertas": len(ofertas)}
        except Exception as e:  # una tienda caída no debe botar todo
            motivo = explicar_error(e)
            print(f"✘ {tienda['nombre']}: {motivo}", flush=True)
            return [], {"tienda": tienda["nombre"], "ok": False, "error": motivo}

    todas, estado = [], []
    with concurrent.futures.ThreadPoolExecutor(TIENDAS_A_LA_VEZ) as hilos:
        for ofertas, est in hilos.map(revisar, tiendas):
            todas.extend(ofertas)
            estado.append(est)

    # descartar precios de relleno ("antes $999.999") y rebajas imposibles (95% o más)
    todas = [o for o in todas
             if not re.fullmatch(r"9{5,}", str(o["precio_normal"])) and o["descuento"] < 95]

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
    escribir_json(ARCHIVO_SALIDA, {"actualizado": ahora, "total": len(ofertas), "ofertas": ofertas}, compacto=True)
    escribir_json(ARCHIVO_HISTORIAL, historial, compacto=True)
    print(f"Listo: {len(ofertas)} ofertas de {DESCUENTO_MINIMO}% o más.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
