#!/usr/bin/env python3
"""
Recolector de ofertas del retail chileno (descuentos de 50% o más).

Cómo funciona, en simple:
  1. Lee la lista de tiendas en tiendas.json.
  2. A cada tienda le pide su catálogo público ordenado por "mayor descuento".
     (Muchas tiendas chilenas usan la plataforma VTEX, que publica ese catálogo
     sin clave ni login: es lo mismo que usa la propia página de la tienda.)
  3. Se queda con los productos con stock y descuento >= 50%.
  4. Guarda el historial de precios para detectar descuentos "inflados".
  5. Escribe docs/ofertas.json, que es lo que muestra la página web.

Solo usa Python estándar: no hay que instalar nada.
Uso:  python recolector/recolectar.py
"""
import datetime as dt
import json
import os
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
POR_PAGINA = 50                # VTEX entrega como máximo 50 productos por consulta
MAX_PAGINAS = 40               # tope por tienda (40 x 50 = 2.000 productos revisados)
PAUSA_SEGUNDOS = 1.0           # pausa entre consultas, para no sobrecargar a la tienda
DIAS_HISTORIAL = 60
USER_AGENT = "OfertasChileBot/1.0 (recolector de ofertas; contacto en el sitio)"


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


def pedir_json(url, intentos=3):
    """Descarga una URL y la interpreta como JSON. Devuelve None si no es JSON."""
    ultimo_error = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                cuerpo = r.read().decode("utf-8", errors="replace")
            try:
                return json.loads(cuerpo)
            except json.JSONDecodeError:
                return None  # respondió HTML u otra cosa: no es VTEX
        except urllib.error.HTTPError as e:
            ultimo_error = e
            if e.code in (400, 403, 404):
                raise  # no tiene sentido reintentar
        except (urllib.error.URLError, TimeoutError) as e:
            ultimo_error = e
        time.sleep(2 * (i + 1))
    raise ultimo_error


# ---------------------------------------------------------------- VTEX
def url_busqueda_vtex(tienda, desde, hasta):
    params = {"O": "OrderByBestDiscountDESC", "_from": desde, "_to": hasta}
    if tienda.get("canal"):
        params["sc"] = tienda["canal"]
    return (
        f"https://{tienda['dominio']}/api/catalog_system/pub/products/search?"
        + urllib.parse.urlencode(params)
    )


def categoria_principal(producto):
    cats = producto.get("categories") or []
    if not cats:
        return "Otros"
    # VTEX entrega rutas tipo "/Tecnología/Celulares/"; la más corta es la raíz
    raiz = min(cats, key=len).strip("/").split("/")[0]
    return raiz or "Otros"


def mejor_oferta_vtex(producto, tienda):
    """Devuelve la mejor oferta (mayor descuento con stock) de un producto, o None."""
    mejor = None
    for item in producto.get("items") or []:
        imagenes = item.get("images") or []
        imagen = imagenes[0].get("imageUrl") if imagenes else ""
        for vendedor in item.get("sellers") or []:
            oferta = vendedor.get("commertialOffer") or {}
            precio = oferta.get("Price") or 0
            normal = oferta.get("ListPrice") or 0
            if oferta.get("AvailableQuantity", 0) <= 0:
                continue
            if precio <= 0 or normal <= precio:
                continue
            descuento = round((1 - precio / normal) * 100)
            if mejor is None or descuento > mejor["descuento"]:
                enlace = producto.get("link") or (
                    f"https://{tienda['dominio']}/{producto.get('linkText', '')}/p"
                )
                mejor = {
                    "id": f"{tienda['id']}-{producto.get('productId')}",
                    "tienda": tienda["nombre"],
                    "nombre": (producto.get("productName") or "").strip(),
                    "marca": producto.get("brand") or "",
                    "categoria": categoria_principal(producto),
                    "precio": int(round(precio)),
                    "precio_normal": int(round(normal)),
                    "descuento": descuento,
                    "imagen": imagen,
                    "url": enlace,
                    "vendedor": vendedor.get("sellerName") or "",
                }
    return mejor


def recolectar_vtex(tienda):
    ofertas = []
    for pagina in range(MAX_PAGINAS):
        desde = pagina * POR_PAGINA
        hasta = desde + POR_PAGINA - 1
        datos = pedir_json(url_busqueda_vtex(tienda, desde, hasta))
        if datos is None or not isinstance(datos, list):
            if pagina == 0:
                raise ValueError("no respondió como tienda VTEX")
            break
        if not datos:
            break
        sobre_umbral = 0
        for producto in datos:
            o = mejor_oferta_vtex(producto, tienda)
            if o and o["descuento"] >= DESCUENTO_MINIMO:
                ofertas.append(o)
                sobre_umbral += 1
        # La lista viene ordenada por descuento: si una página entera ya no
        # tiene ofertas sobre el umbral, las siguientes tampoco.
        if sobre_umbral == 0:
            break
        time.sleep(PAUSA_SEGUNDOS)
    return ofertas


RECOLECTORES = {"vtex": recolectar_vtex}


def explicar_error(e):
    """Traduce el error a algo entendible en docs/estado.json."""
    if isinstance(e, urllib.error.HTTPError):
        if e.code == 403:
            return "La tienda bloqueó la consulta (error 403). Desactívala en tiendas.json."
        if e.code == 404:
            return "La tienda no tiene catálogo VTEX (error 404): usa otra plataforma."
        return f"La tienda respondió con error {e.code}."
    if isinstance(e, ValueError):
        return "No respondió como tienda VTEX: usa otra plataforma o bloquea consultas."
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

    historial = leer_json(ARCHIVO_HISTORIAL, {})
    for o in ofertas:
        evaluar_con_historial(o, historial.get(o["id"], []), hoy)
    actualizar_historial(historial, ofertas, hoy)

    ofertas.sort(key=lambda o: (-o["descuento"], o["precio"]))
    ahora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    escribir_json(ARCHIVO_SALIDA, {"actualizado": ahora, "total": len(ofertas), "ofertas": ofertas})
    escribir_json(ARCHIVO_HISTORIAL, historial)
    escribir_json(ARCHIVO_ESTADO, {"actualizado": ahora, "tiendas": estado})
    print(f"Listo: {len(ofertas)} ofertas de {DESCUENTO_MINIMO}% o más.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
