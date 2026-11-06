// Funciones compartidas: sesiones, miembros y descifrado de ofertas.
import crypto from "node:crypto";
import zlib from "node:zlib";
import { get, put } from "@vercel/blob";

const SECRETO = process.env.SESSION_SECRET || "";
const FUENTE_OFERTAS =
  process.env.OFERTAS_URL || "https://raw.githubusercontent.com/PLU88/mitad-de-precio/main/datos/ofertas.enc";
const ARCHIVO_MIEMBROS = "miembros.json";
const DIAS_SESION = 30;
const HORAS_ADMIN = 12;
const MAX_INTENTOS = 8;
const MAX_PENDIENTES = 300;

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
  return m && m.estado === "aprobado" && m.version === s.v ? m : null;
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
  const comprimido = Buffer.concat([descifrador.update(todo.subarray(0, todo.length - 16)), descifrador.final()]);
  return JSON.parse(zlib.gunzipSync(comprimido).toString("utf8"));
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
