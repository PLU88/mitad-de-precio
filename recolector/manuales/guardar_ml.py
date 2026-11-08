"""Guarda las ofertas de Mercado Libre juntadas en el navegador.

Uso: python3 recolector/manuales/guardar_ml.py /ruta/filas.json
filas.json = la lista que devuelve __mlExport (todas las partes unidas).
Cada fila: [nombre, url, imagen, precio, normal, vendedor, link_afiliada]
"""
import datetime as dt
import json
import os
import sys

MINIMO = 20  # si llegan menos, algo falló: no se reemplaza lo que hay

filas = json.load(open(sys.argv[1], encoding="utf-8"))
buenas = [f for f in filas
          if len(f) >= 7 and f[3] and f[4] and 1 - f[3] / f[4] >= 0.5 and str(f[6]).startswith("https://meli.la/")]
if len(buenas) < MINIMO:
    sys.exit(f"Solo {len(buenas)} ofertas válidas con link de afiliada; no se guardó nada.")

ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mercadolibre.json")
datos = {
    "fecha": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    "fuente": "mercadolibre.cl/ofertas (sesión de la dueña, 50% o más)",
    "afiliado": "Links meli.la generados con la etiqueta de afiliada pm20261107102520448 (7ª columna)",
    "ofertas": buenas,
}
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
print(f"Guardadas {len(buenas)} ofertas de Mercado Libre ({datos['fecha']}).")
