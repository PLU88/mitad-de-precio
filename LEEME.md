# Mitad de Precio — ofertas del retail chileno con 50% o más, solo para miembros

Sitio: **https://mitad-de-precio.vercel.app** · Panel de administración: **https://mitad-de-precio.vercel.app/admin.html**

El proyecto tiene tres partes:

1. **El recolector** (`recolector/recolectar.py`, en GitHub): cada 6 horas revisa las tiendas de
   `tiendas.json` y se queda con los productos con stock y 50% o más de descuento.
2. **El cifrado** (`recolector/cifrar.py`): guarda esas ofertas cifradas en `datos/ofertas.enc`.
   Solo el sitio en Vercel tiene la clave para leerlas, así que nadie puede verlas desde GitHub.
3. **El sitio de miembros** (carpeta `sitio/`, publicado en Vercel): la gente pide acceso, tú la
   apruebas en el panel, y entra con su correo y un código personal.

## Cómo aprobar miembros

1. Entra al panel con tu clave de administración.
2. En **Solicitudes** verás a quienes pidieron acceso. Toca **Aprobar**.
3. Aparece el código de esa persona. Toca **Enviar por WhatsApp** (o por correo, o **Copiar mensaje**).
   El código se muestra una sola vez; si se pierde, usa **Crear código nuevo**.
4. La persona entra una vez y queda conectada 30 días en ese aparato.

Para sacar a alguien: pestaña **Con acceso** → **Quitar acceso** (funciona al instante).
Si alguien se equivoca de código 8 veces seguidas, queda bloqueado hasta que le crees un código nuevo.

## Tiendas

Las tiendas están en `tiendas.json`. Para apagar una, cambia `"activa": true` por `"activa": false`
(ícono del lápiz en GitHub). Cada vuelta deja en `datos/estado.json` cuántas ofertas trajo cada tienda
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

En `sitio/index.html` busca `var AFILIADOS = {};` y agrega la regla de cada programa en el que te
aceptes. La página ya marca esos enlaces como patrocinados.

## Ajustes rápidos (en `recolector/recolectar.py`)

- `DESCUENTO_MINIMO = 50` — descuento mínimo que se guarda.
- `MAX_PAGINAS = 40` — cuántas páginas revisa por tienda como máximo.
- `PAUSA_SEGUNDOS = 1.0` — pausa entre consultas; no la bajes, para no molestar a las tiendas.
