// Cuenta las visitas a la página (sin guardar datos personales).
// La página avisa una vez por carga: { nuevo } es true la primera vez del día en ese navegador.
import { get, put } from "@vercel/blob";
import { responder } from "./_lib.js";

const ARCHIVO = "visitas.json";
const DIAS = 120;

export async function leerVisitas() {
  const r = await get(ARCHIVO, { access: "private", useCache: false }).catch(() => null);
  if (!r || r.statusCode !== 200 || !r.stream) return { dias: {} };
  const d = JSON.parse(await new Response(r.stream).text());
  return d && d.dias ? d : { dias: {} };
}

export function diaChile(fecha = new Date()) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Santiago" }).format(fecha);
}

export default async function handler(req, res) {
  if (req.method !== "POST") return responder(res, 405, { error: "Método no permitido." });
  // no contar robots ni vistas previas de links
  const ua = String(req.headers["user-agent"] || "");
  if (!ua || /bot|crawl|spider|preview|facebookexternalhit|whatsapp|curl|python|vercel/i.test(ua)) return responder(res, 200, { ok: true });
  try {
    const cuerpo = req.body || {};
    const d = await leerVisitas();
    const hoy = diaChile();
    const x = d.dias[hoy] || { visitas: 0, personas: 0, cupones: 0, celular: 0, instagram: 0 };
    if (cuerpo.pagina === "cupones") x.cupones = (x.cupones || 0) + 1;  // abrió la sección Cupones
    else x.visitas += 1;
    if (cuerpo.pagina !== "cupones" && cuerpo.nuevo) {
      x.personas += 1;
      if (/Mobi|Android|iPhone/i.test(ua)) x.celular = (x.celular || 0) + 1;
      if (/Instagram/i.test(ua) || /instagram/i.test(String(cuerpo.desde || ""))) x.instagram = (x.instagram || 0) + 1;
    }
    d.dias[hoy] = x;
    const fechas = Object.keys(d.dias).sort();
    for (const f of fechas.slice(0, Math.max(0, fechas.length - DIAS))) delete d.dias[f];
    await put(ARCHIVO, JSON.stringify(d), { access: "private", addRandomSuffix: false, allowOverwrite: true, contentType: "application/json" });
    return responder(res, 200, { ok: true });
  } catch (e) {
    console.error(e);
    return responder(res, 200, { ok: false });
  }
}
