"""Guarda las ofertas de Zara juntadas en el navegador con zara_navegador.js.

Uso: python3 recolector/manuales/guardar_zara.py /ruta/zara.json
zara.json = lo que devuelve __zaraExport (todas las partes unidas):
  {"productos": N, "categorias": N, "filas": [[nombre, url, imagen, precio, normal, "", "", pistas], ...]}

Si hay pocas ofertas (o ninguna) igual se guarda: Zara a veces no tiene descuentos grandes.
Solo se rechaza si la revisión vio muy pocos productos, porque eso indica que algo falló.
"""
import datetime as dt
import json
import os
import sys

MINIMO_PRODUCTOS = 50

datos = json.load(open(sys.argv[1], encoding="utf-8"))
if datos.get("productos", 0) < MINIMO_PRODUCTOS:
    sys.exit(f"La revisión solo vio {datos.get('productos', 0)} productos; algo falló y no se guardó nada.")
buenas = [f for f in datos["filas"]
          if len(f) >= 5 and f[3] and f[4] and round((1 - f[3] / f[4]) * 100) >= 40 and str(f[1]).startswith("https://www.zara.com/")]

ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zara.json")
salida = {
    "fecha": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    "fuente": f"zara.com/cl (categorías de precios especiales y rebajas; {datos['productos']} productos revisados)",
    "ofertas": buenas,
}
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False, separators=(",", ":"))
print(f"Guardadas {len(buenas)} ofertas de Zara ({salida['fecha']}).")
