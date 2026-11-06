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

## Tiendas

Las tiendas están en `tiendas.json`. Para apagar una, cambia `"activa": true` por `"activa": false`
(ícono del lápiz en GitHub). Cada vuelta deja en `docs/estado.json` cuántas ofertas trajo cada tienda
o por qué falló.

**Activas (10):** Hites, Fashion's Park, Hush Puppies, Under Armour, Crocs, Vans, Lippi, Merrell,
Blockstore y Lounge.

**Agregar una tienda Shopify** (muchas marcas chilenas lo son): abre
`https://LA-TIENDA.cl/products.json` en el navegador. Si ves texto que empieza con `{"products":`,
sirve. Agrega una línea así:

```json
{"id": "mitienda", "nombre": "Mi Tienda", "dominio": "www.mitienda.cl", "tipo": "shopify", "activa": true},
```

**No se pueden leer por ahora** (quedan anotadas con `"tipo": "especial"` y el motivo):

- Bloquean consultas automáticas: Paris, Easy, Ripley, Tottus, Nike, Adidas, Zara, H&M, Unimarc,
  Decathlon y The North Face.
- Usan plataformas propias sin catálogo público: Falabella, Homecenter Sodimac, Lider, Jumbo,
  Santa Isabel, Casaideas, Puma, abc/La Polar, Tricot, Farmacias Ahumada y Mercado Libre.

Para algunas de ellas existen servicios de datos de pago (por ejemplo Apify).

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
- `MAX_PAGINAS = 40` — cuántas páginas revisa por tienda como máximo.
- `PAUSA_SEGUNDOS = 1.0` — pausa entre consultas; no la bajes, para no molestar a las tiendas.
