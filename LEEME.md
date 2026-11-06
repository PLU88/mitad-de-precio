# Mitad de Precio — ofertas del retail chileno con 50% o más

Este proyecto tiene dos partes que funcionan solas y gratis en GitHub:

1. **El recolector** (`recolector/recolectar.py`): cada 6 horas revisa las tiendas de
   `tiendas.json`, se queda con los productos con stock y 50% o más de descuento, y guarda el
   resultado en `docs/ofertas.json`.
2. **La página web** (`docs/index.html`): muestra esas ofertas con filtros de 50/60/70/80%,
   tienda, categoría y búsqueda. Si todavía no hay ofertas reales, muestra datos de demostración.

No necesitas servidor ni instalar nada en tu computador.

## Puesta en marcha (unos 20 minutos)

1. **Crea una cuenta en GitHub** en github.com (gratis).
2. **Crea un repositorio nuevo**: botón verde "New", nombre `mitad-de-precio`, marca **Public**, "Create repository".
3. **Sube los archivos**: en el repositorio, "uploading an existing file", arrastra *todo el contenido*
   de esta carpeta (incluida la carpeta oculta `.github`) y presiona "Commit changes".
   - Si tu computador oculta la carpeta `.github`, créala a mano en GitHub: "Add file" → "Create new file"
     y escribe como nombre `.github/workflows/actualizar.yml`; pega el contenido de ese archivo.
4. **Publica la página**: Settings → Pages → "Deploy from a branch" → rama `main`, carpeta `/docs` → Save.
   En un par de minutos tu sitio estará en `https://TU-USUARIO.github.io/mitad-de-precio/`.
5. **Enciende el recolector**: pestaña Actions → si lo pide, "I understand… enable" → elige
   "Actualizar ofertas" → "Run workflow". Tarda unos minutos.
6. **Revisa el resultado**: abre `docs/estado.json` en el repositorio. Cada tienda aparece con
   `"ok": true` (y cuántas ofertas encontró) o `"ok": false` (con el motivo).

Desde ahí se actualiza solo cada 6 horas.

## Agregar o quitar tiendas

Edita `tiendas.json` directamente en GitHub (ícono del lápiz). Cada tienda es una línea:

```json
{"id": "mitienda", "nombre": "Mi Tienda", "dominio": "www.mitienda.cl", "tipo": "vtex", "activa": true}
```

**¿Cómo saber si una tienda sirve?** Abre en tu navegador:
`https://www.LA-TIENDA.cl/api/catalog_system/pub/products/search?_from=0&_to=0`
Si ves texto con llaves `{ }` y datos del producto, la tienda usa VTEX y funciona con este recolector.
Si ves la página normal o un error, no sirve (por ahora). Para desactivar una tienda pon `"activa": false`.

La lista tiene dos grupos:

- **Con `"activa": true`**: 23 tiendas candidatas (Paris, Unimarc, Casaideas, Nike, Tricot, Corona,
  farmacias, marcas deportivas y otras). El recolector prueba cada una; las que no usen VTEX o bloqueen
  la consulta aparecen con `"ok": false` y un motivo en `docs/estado.json`, y simplemente se saltan.
- **Con `"tipo": "especial"`**: Falabella, Homecenter Sodimac, Tottus, Ripley, Lider, Zara, H&M,
  Adidas y Mercado Libre. Usan sistemas propios, casi siempre con protección contra programas
  automáticos, y este recolector no puede leerlas. Quedan anotadas para sumarlas más adelante con un
  servicio de datos de pago (como Apify) o un adaptador hecho a medida.

## Qué significan las etiquetas

- **Precio más bajo en 30 días**: hoy está más barato que cualquier día que lo hayamos visto en el último mes.
- **Descuento dudoso**: llevamos 7 días o más viendo el producto y nunca se cobró algo cercano al
  "precio normal" con que la tienda calcula el %. Suele ser un precio "inflado".

Ambas necesitan unos días de historial para empezar a aparecer.

## Ganar comisiones (opcional)

En `docs/index.html` busca `var AFILIADOS = {};` y agrega la regla de cada programa en el que te
aceptes. La página ya marca esos enlaces como patrocinados.

## Ajustes rápidos (en `recolector/recolectar.py`)

- `DESCUENTO_MINIMO = 50` — descuento mínimo que se guarda.
- `MAX_PAGINAS = 40` — cuántas páginas de 50 productos revisa por tienda.
- `PAUSA_SEGUNDOS = 1.0` — pausa entre consultas; no la bajes, para no molestar a las tiendas.
