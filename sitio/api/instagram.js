// Publica en Instagram (@priveofertazos) el carrusel y las historias del día.
// La llama Vercel una vez al día (ver vercel.json). También se puede llamar desde el panel (sesión de administración).
// Dos tipos de permiso (token):
//  - "EAA…": token de usuario del sistema de Meta (inicio de sesión unificado). No caduca. Usa graph.facebook.com.
//  - "IG…":  token de Instagram Login. Dura 60 días y se renueva solo cada semana. Usa graph.instagram.com.
// ?probar=1 solo revisa que el permiso funcione (no publica nada).
import { get, put } from "@vercel/blob";
import { esAdmin, responder } from "./_lib.js";

const VERSION = "v25.0";
let GRAPH = "https://graph.instagram.com/" + VERSION;
const ID_INSTAGRAM = process.env.IG_USER_ID || "17841480277275471"; // @priveofertazos
const RAW = "https://raw.githubusercontent.com/PLU88/mitad-de-precio/datos/datos/publicaciones/";
const ARCHIVO = "instagram.json";
const SIETE_DIAS = 7 * 864e5;

async function leerEstado() {
  const r = await get(ARCHIVO, { access: "private", useCache: false }).catch(() => null);
  if (!r || r.statusCode !== 200 || !r.stream) return { publicado: {} };
  return JSON.parse(await new Response(r.stream).text());
}

async function guardarEstado(estado) {
  await put(ARCHIVO, JSON.stringify(estado), {
    access: "private", addRandomSuffix: false, allowOverwrite: true, contentType: "application/json",
  });
}

async function graph(ruta, token, datos) {
  const url = new URL(ruta.startsWith("http") ? ruta : GRAPH + ruta);
  let opciones = { method: "GET" };
  if (datos) {
    opciones = { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...datos, access_token: token }) };
  } else {
    url.searchParams.set("access_token", token);
  }
  const r = await fetch(url, opciones);
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) throw new Error(`Instagram ${ruta.split("?")[0]}: ${(j.error && j.error.message) || r.status}`);
  return j;
}

const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));

async function listo(contenedor, token) {
  for (let i = 0; i < 12; i++) {
    const s = await graph(`/${contenedor}?fields=status_code`, token);
    if (s.status_code === "FINISHED") return;
    if (s.status_code === "ERROR" || s.status_code === "EXPIRED") throw new Error("Instagram no pudo procesar una imagen");
    await esperar(2500);
  }
  throw new Error("Instagram tardó demasiado en procesar las imágenes");
}

function hoyEnChile() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Santiago" }).format(new Date());
}

export default async function handler(req, res) {
  const cron = process.env.CRON_SECRET && req.headers.authorization === `Bearer ${process.env.CRON_SECRET}`;
  if (!cron && !esAdmin(req)) return responder(res, 401, { error: "No autorizado." });
  try {
    const estado = await leerEstado();
    estado.publicado = estado.publicado || {};
    let token = process.env.IG_TOKEN && process.env.IG_TOKEN.startsWith("EAA") ? process.env.IG_TOKEN : (estado.token || process.env.IG_TOKEN);
    if (!token) return responder(res, 200, { ok: false, motivo: "Todavía no hay permiso de Instagram (falta el token)." });
    const deMeta = token.startsWith("EAA");
    GRAPH = (deMeta ? "https://graph.facebook.com/" : "https://graph.instagram.com/") + VERSION;

    if (deMeta) {
      if (!estado.usuario || estado.usuario.id !== ID_INSTAGRAM) {
        const yo = await graph(`/${ID_INSTAGRAM}?fields=id,username`, token);
        estado.usuario = { id: yo.id, nombre: yo.username };
        await guardarEstado(estado);
      }
    } else if (!estado.renovado || Date.now() - Date.parse(estado.renovado) > SIETE_DIAS) {
      // renovar el permiso de Instagram Login (dura 60 días; se renueva cada semana)
      const nuevo = await graph(`https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token`, token);
      token = nuevo.access_token;
      estado.token = token;
      estado.renovado = new Date().toISOString();
      await guardarEstado(estado);
    }
    if (!estado.usuario) {
      const yo = await graph(`/me?fields=user_id,username`, token);
      estado.usuario = { id: yo.user_id || yo.id, nombre: yo.username };
      await guardarEstado(estado);
    }

    if (req.query && req.query.probar) {
      const info = await graph(`/${estado.usuario.id}?fields=username,media_count,followers_count`, token);
      return responder(res, 200, { ok: true, prueba: true, cuenta: info.username, publicaciones: info.media_count, seguidores: info.followers_count, tipo: deMeta ? "meta" : "instagram" });
    }
    const fecha = (req.query && req.query.fecha) || hoyEnChile();
    if (estado.publicado[fecha]) return responder(res, 200, { ok: true, motivo: "Lo de hoy ya está publicado.", fecha });
    const indice = await fetch(RAW + "indice.json?v=" + Date.now()).then((r) => r.json());
    const dia = (indice.dias || []).find((x) => x.fecha === fecha);
    if (!dia) return responder(res, 200, { ok: false, motivo: "Todavía no están las imágenes de hoy.", fecha });

    const id = estado.usuario.id;
    const base = RAW + fecha + "/";
    // carrusel: un contenedor por imagen y uno que las agrupa
    const hijos = [];
    for (const archivo of dia.carrusel.slice(0, 10)) {
      const c = await graph(`/${id}/media`, token, { image_url: base + archivo, is_carousel_item: true });
      hijos.push(c.id);
    }
    for (const h of hijos) await listo(h, token);
    const carrusel = await graph(`/${id}/media`, token, { media_type: "CAROUSEL", children: hijos.join(","), caption: dia.texto.slice(0, 2200) });
    await listo(carrusel.id, token);
    const publicado = await graph(`/${id}/media_publish`, token, { creation_id: carrusel.id });
    estado.publicado[fecha] = { carrusel: publicado.id, historias: [], cuando: new Date().toISOString() };
    await guardarEstado(estado);

    // historias (si alguna falla, el carrusel ya quedó publicado)
    for (const archivo of dia.historias || []) {
      try {
        const h = await graph(`/${id}/media`, token, { image_url: base + archivo, media_type: "STORIES" });
        await listo(h.id, token);
        const p = await graph(`/${id}/media_publish`, token, { creation_id: h.id });
        estado.publicado[fecha].historias.push(p.id);
      } catch (e) {
        console.error("Historia no publicada:", e.message);
      }
    }
    // guardar solo los últimos 30 días
    estado.publicado = Object.fromEntries(Object.entries(estado.publicado).sort().slice(-30));
    await guardarEstado(estado);
    return responder(res, 200, { ok: true, fecha, publicado: estado.publicado[fecha] });
  } catch (e) {
    console.error(e);
    return responder(res, 500, { ok: false, error: e.message });
  }
}
