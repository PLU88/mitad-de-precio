// Funciones compartidas: sesiones, miembros y descifrado de ofertas.
import crypto from "node:crypto";
import { get, put } from "@vercel/blob";

const SECRETO = process.env.SESSION_SECRET || "";
const FUENTE_OFERTAS =
  process.env.OFERTAS_URL || "https://raw.githubusercontent.com/PLU88/mitad-de-precio/datos/datos/ofertas.enc";
const ARCHIVO_MIEMBROS = "miembros.json";
const DIAS_SESION = 30;
const HORAS_ADMIN = 12;
const MAX_INTENTOS = 8;
const MAX_PENDIENTES = 300;
export const PRECIO = Number(process.env.PRECIO || 10000); // pesos chilenos
export const DIAS_MEMBRESIA = 30;

// ---------------------------------------------------------------- utilidades
export function firmar(texto) {
  return crypto.createHmac("sha256", SECRETO).update(texto).digest("base64url");
}

function igual(a, b) {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}

export function leerCookies(req) {
  const salida = {};
  (req.headers.cookie || "").split(";").forEach((par) => {
    const i = par.indexOf("=");
    if (i > 0) salida[par.slice(0, i).trim()] = decodeURIComponent(par.slice(i + 1).trim());
  });
  return salida;
}

export function cookie(nombre, valor, segundos) {
  return `${nombre}=${encodeURIComponent(valor)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${segundos}`;
}

export function normalizarCorreo(correo) {
  return String(correo || "").trim().toLowerCase();
}

export function correoValido(correo) {
  return /^[^\s@]{1,64}@[^\s@]{1,190}\.[a-z]{2,}$/i.test(correo);
}

export function texto(valor, largo) {
  return String(valor || "").replace(/[\u0000-\u001f]/g, " ").trim().slice(0, largo);
}

export function responder(res, codigo, datos, cookies) {
  res.setHeader("Cache-Control", "no-store");
  if (cookies && cookies.length) res.setHeader("Set-Cookie", cookies);
  res.status(codigo).json(datos);
}

export function soloPost(req, res) {
  if (req.method !== "POST") {
    responder(res, 405, { error: "Método no permitido." });
    return false;
  }
  return true;
}

// ---------------------------------------------------------------- miembros (archivo privado)
export async function leerMiembros() {
  const r = await get(ARCHIVO_MIEMBROS, { access: "private", useCache: false });
  if (!r || r.statusCode !== 200 || !r.stream) return { miembros: {} };
  const datos = JSON.parse(await new Response(r.stream).text());
  return datos && datos.miembros ? datos : { miembros: {} };
}

export async function guardarMiembros(datos) {
  await put(ARCHIVO_MIEMBROS, JSON.stringify(datos), {
    access: "private",
    addRandomSuffix: false,
    allowOverwrite: true,
    contentType: "application/json",
  });
}

export function contarPendientes(datos) {
  return Object.values(datos.miembros).filter((m) => m.estado === "pendiente").length;
}

export { MAX_PENDIENTES, MAX_INTENTOS };

// ---------------------------------------------------------------- códigos de acceso
const ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

export function nuevoCodigo() {
  let c = "";
  for (let i = 0; i < 8; i++) c += ALFABETO[crypto.randomInt(ALFABETO.length)];
  return c.slice(0, 4) + "-" + c.slice(4);
}

export function hashCodigo(correo, codigo) {
  const limpio = String(codigo || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  return firmar("codigo|" + correo + "|" + limpio);
}

// ---------------------------------------------------------------- sesiones
export function crearSesion(correo, version) {
  const cuerpo = Buffer.from(JSON.stringify({ e: correo, v: version, x: Date.now() + DIAS_SESION * 864e5 })).toString("base64url");
  return cookie("mdp_sesion", cuerpo + "." + firmar("s|" + cuerpo), DIAS_SESION * 86400);
}

export function leerSesion(req) {
  const valor = leerCookies(req).mdp_sesion || "";
  const [cuerpo, firma] = valor.split(".");
  if (!cuerpo || !firma || !igual(firma, firmar("s|" + cuerpo))) return null;
  try {
    const s = JSON.parse(Buffer.from(cuerpo, "base64url").toString());
    return s.x > Date.now() ? s : null;
  } catch {
    return null;
  }
}

/** Devuelve el miembro aprobado dueño de la sesión, o null. */
export async function miembroConectado(req) {
  const s = leerSesion(req);
  if (!s) return null;
  const datos = await leerMiembros();
  const m = datos.miembros[s.e];
  return m && m.estado === "aprobado" && m.version === s.v && vigente(m) ? m : null;
}

/** ¿Tiene acceso pagado vigente? */
export function vigente(m) {
  return Boolean(m && m.vence && Date.parse(m.vence) > Date.now());
}

/** Suma días de acceso desde hoy o desde el vencimiento actual (si todavía no vence). */
export function extenderAcceso(m, dias = DIAS_MEMBRESIA) {
  const desde = vigente(m) ? Date.parse(m.vence) : Date.now();
  m.vence = new Date(desde + dias * 864e5).toISOString();
  m.estado = "aprobado";
  m.aprobado_en = m.aprobado_en || new Date().toISOString();
  return m.vence;
}

export function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString("es-CL", { day: "numeric", month: "long", year: "numeric", timeZone: "America/Santiago" });
}

export function cookieAdmin() {
  const x = String(Date.now() + HORAS_ADMIN * 36e5);
  return cookie("mdp_admin", x + "." + firmar("admin|" + x), HORAS_ADMIN * 3600);
}

export function esAdmin(req) {
  const [x, firma] = (leerCookies(req).mdp_admin || "").split(".");
  return Boolean(x && firma && igual(firma, firmar("admin|" + x)) && Number(x) > Date.now());
}

export function claveAdminCorrecta(clave) {
  const esperada = process.env.ADMIN_PASSWORD || "";
  return Boolean(esperada) && igual(firmar("p|" + String(clave || "")), firmar("p|" + esperada));
}

// ---------------------------------------------------------------- aviso por correo (Resend)
function escapar(t) {
  return String(t || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

/** Avisa a la dueña que llegó una solicitud nueva. Si falla, la solicitud igual queda guardada. */
export async function avisarSolicitud(m, sitio) {
  const clave = process.env.RESEND_API_KEY, para = process.env.AVISAR_A;
  if (!clave || !para) return;
  const panel = sitio + "/admin.html";
  const lineas = [
    "Nombre: " + m.nombre,
    "Correo: " + m.email,
    m.whatsapp ? "WhatsApp: " + m.whatsapp : "",
    m.mensaje ? "Cómo nos conoció: " + m.mensaje : "",
  ].filter(Boolean);
  const html =
    '<div style="font-family:Arial,sans-serif;font-size:15px;color:#1A1A2E;line-height:1.5">' +
    '<p style="font-family:Georgia,serif;font-style:italic;font-size:22px;margin:0">Privé <span style="font-family:Arial Black,Arial,sans-serif;font-style:normal;font-size:14px;letter-spacing:2px;color:#D61F69">OFERTAZOS</span></p>' +
    "<p><b>" + escapar(m.nombre) + "</b> pidió acceso.</p><p>" + lineas.map(escapar).join("<br>") + "</p>" +
    '<p><a href="' + panel + '" style="display:inline-block;background:#D61F69;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:bold">Abrir el panel para aprobar</a></p></div>';
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: "Bearer " + clave, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: process.env.AVISO_DESDE || "Privé Ofertazos <onboarding@resend.dev>",
        to: [para],
        reply_to: m.email,
        subject: "Nueva solicitud de acceso: " + m.nombre,
        text: m.nombre + " pidió acceso a Privé Ofertazos.\n\n" + lineas.join("\n") + "\n\nApruébala aquí: " + panel,
        html,
      }),
    });
    if (!r.ok) console.error("Resend respondió " + r.status + ": " + (await r.text()));
  } catch (e) {
    console.error("No se pudo enviar el aviso:", e);
  }
}

/** Envía un correo con Resend. Si falla, solo queda en el registro (nunca bota la operación). */
export async function enviarCorreo({ para, asunto, texto, html, responderA }) {
  const clave = process.env.RESEND_API_KEY;
  if (!clave || !para) return false;
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: "Bearer " + clave, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: process.env.AVISO_DESDE || "Privé Ofertazos <onboarding@resend.dev>",
        to: [para], subject: asunto, text: texto, html, reply_to: responderA || process.env.AVISAR_A,
      }),
    });
    if (!r.ok) console.error("Resend respondió " + r.status + ": " + (await r.text()));
    return r.ok;
  } catch (e) {
    console.error("No se pudo enviar el correo:", e);
    return false;
  }
}

const CABECERA_CORREO =
  '<p style="font-family:Georgia,serif;font-style:italic;font-size:24px;margin:0 0 12px;color:#1A1A2E">Privé ' +
  '<span style="font-family:Arial Black,Arial,sans-serif;font-style:normal;font-size:15px;letter-spacing:2px;color:#D61F69">OFERTAZOS</span></p>';

export async function enviarCodigo(m, codigo, sitio) {
  const vence = fechaCorta(m.vence);
  const texto = `¡Hola ${m.nombre.split(" ")[0]}! Tu acceso a Privé Ofertazos está activo hasta el ${vence}.\n\n` +
    `Para entrar desde cualquier celular o computador, ve a ${sitio} y usa:\nCorreo: ${m.email}\nCódigo: ${codigo}\n\n` +
    "El código es personal, no lo compartas. Si tienes dudas, responde este correo.";
  const html = '<div style="font-family:Arial,sans-serif;font-size:15px;color:#1A1A2E;line-height:1.5">' + CABECERA_CORREO +
    "<p>¡Hola " + escapar(m.nombre.split(" ")[0]) + "! Tu acceso está activo hasta el <b>" + escapar(vence) + "</b>.</p>" +
    "<p>Para entrar desde cualquier celular o computador usa:</p>" +
    '<p style="background:#F7F3EE;border-radius:10px;padding:14px 16px">Correo: <b>' + escapar(m.email) + '</b><br>Código: <b style="font-size:22px;letter-spacing:2px">' + escapar(codigo) + "</b></p>" +
    '<p><a href="' + sitio + '" style="display:inline-block;background:#D61F69;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:bold">Entrar a Privé Ofertazos</a></p>' +
    '<p style="color:#6B6B7B;font-size:13px">El código es personal, no lo compartas. Si tienes dudas, responde este correo.</p></div>';
  return enviarCorreo({ para: m.email, asunto: "Tu acceso a Privé Ofertazos", texto, html });
}

// ---------------------------------------------------------------- ofertas cifradas
let cache = { cuando: 0, datos: null };

export function descifrar(sobre, privadaPem) {
  const clave = crypto.privateDecrypt(
    { key: privadaPem, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash: "sha256" },
    Buffer.from(sobre.k, "base64")
  );
  const todo = Buffer.from(sobre.d, "base64");
  const descifrador = crypto.createDecipheriv("aes-256-gcm", clave, Buffer.from(sobre.n, "base64"));
  descifrador.setAuthTag(todo.subarray(todo.length - 16));
  // Devuelve el JSON todavía comprimido (gzip): se envía tal cual al navegador, que lo descomprime solo.
  return Buffer.concat([descifrador.update(todo.subarray(0, todo.length - 16)), descifrador.final()]);
}

export async function ofertas() {
  if (cache.datos && Date.now() - cache.cuando < 10 * 60 * 1000) return cache.datos;
  const r = await fetch(FUENTE_OFERTAS, { cache: "no-store" });
  if (!r.ok) throw new Error("No se pudieron descargar las ofertas (" + r.status + ")");
  const pem = (process.env.OFERTAS_CLAVE_PRIVADA || "").replace(/\\n/g, "\n");
  const datos = descifrar(await r.json(), pem);
  cache = { cuando: Date.now(), datos };
  return datos;
}
