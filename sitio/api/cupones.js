// Cupones y códigos de descuento, solo para miembros (o para todos durante el período gratis).
// Junta los cupones que el recolector actualiza cada día (cifrados en la rama "datos")
// con los que la dueña agrega a mano desde el panel (por ejemplo, los que ve en Instagram).
import zlib from "node:zlib";
import { get } from "@vercel/blob";
import { responder, miembroConectado, descifrar } from "./_lib.js";
import { accesoGratis } from "./_gratis.js";

const FUENTE = process.env.CUPONES_URL || "https://raw.githubusercontent.com/PLU88/mitad-de-precio/datos/datos/cupones.enc";
let cache = { cuando: 0, datos: null };

export async function cuponesManuales() {
  const r = await get("cupones_manuales.json", { access: "private", useCache: false }).catch(() => null);
  if (!r || r.statusCode !== 200 || !r.stream) return { cupones: [] };
  const d = JSON.parse(await new Response(r.stream).text());
  return d && Array.isArray(d.cupones) ? d : { cupones: [] };
}

async function automaticos() {
  if (cache.datos && Date.now() - cache.cuando < 30 * 60e3) return cache.datos;
  const r = await fetch(FUENTE, { cache: "no-store" });
  if (!r.ok) return cache.datos || { actualizado: null, cupones: [] };
  const pem = (process.env.OFERTAS_CLAVE_PRIVADA || "").replace(/\\n/g, "\n");
  const datos = JSON.parse(zlib.gunzipSync(descifrar(await r.json(), pem)).toString("utf8"));
  cache = { cuando: Date.now(), datos };
  return datos;
}

export default async function handler(req, res) {
  try {
    const m = accesoGratis() || (await miembroConectado(req));
    if (!m) return responder(res, 401, { error: "Necesitas entrar con tu correo y código." });
    const [auto, manual] = await Promise.all([
      automaticos().catch((e) => { console.error(e); return { actualizado: null, cupones: [] }; }),
      cuponesManuales().catch(() => ({ cupones: [] })),
    ]);
    const hoy = new Date().toISOString().slice(0, 10);
    const propios = manual.cupones.filter((c) => !c.hasta || c.hasta >= hoy).map((c) => ({ ...c, propio: true }));
    res.setHeader("Cache-Control", "private, no-store");
    return res.status(200).json({ actualizado: auto.actualizado, cupones: [...propios, ...(auto.cupones || [])] });
  } catch (e) {
    console.error(e);
    return responder(res, 500, { error: "No se pudieron cargar los cupones. Intenta en unos minutos." });
  }
}
