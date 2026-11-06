"""Sondeo temporal: prueba el lector de grillas Magento en Surprice, Kliper y Todo Moda."""
import sys, re
sys.path.insert(0, "recolector")
import recolectar as r
for tienda, rutas in [({"id": "surprice", "nombre": "Surprice", "dominio": "www.surprice.cl"}, ["ofertas", "ofertas/liquidacion", "cyber"]),
                      ({"id": "kliper", "nombre": "Kliper", "dominio": "www.kliper.cl"}, ["ofertas", "cyber"]),
                      ({"id": "todomoda", "nombre": "Todo Moda", "dominio": "cl.todomoda.com"}, ["flash-sale.html"])]:
    for ruta in rutas:
        for p in (1, 2):
            url = f"https://{tienda['dominio']}/{ruta}?p={p}&product_list_limit=36"
            try:
                t = r.pedir(url, acepta="text/html")
                prods = r.leer_grilla_magento(tienda, t)
                print(f"[{tienda['nombre']} {ruta} p{p}] bloques={len(r.BLOQUE_MAGENTO.findall(t))} items={t.count('product-item-info')} leidos={len(prods)} con50={sum(o['descuento']>=50 for o in prods)}")
                if prods and p == 1: print("    ej:", prods[0])
                if not prods and p == 1:
                    i = t.find('product-item-info'); print("    trozo:", re.sub(r"\s+", " ", t[max(0, i-300):i+1800]))
            except Exception as e:
                print(f"[{tienda['nombre']} {ruta} p{p}] ERROR {e}")
