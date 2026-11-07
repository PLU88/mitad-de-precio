// Cobro de la membresía ($10.000 por 30 días) con Mercado Pago o Flow (Webpay, Servipag, Mach, transferencia).
//
//   POST /api/pago {accion:"crear", proveedor:"mercadopago"|"flow", nombre, email, whatsapp}
//        → { url } a la que se envía a la persona para pagar.
//   GET  /api/pago?estado=<id>      → la página pregunta cómo va el pago; si está pagado, abre la sesión.
//   POST /api/pago?aviso=mp         → aviso de Mercado Pago (webhook).
//   POST /api/pago?aviso=flow       → aviso de Flow (urlConfirmation).
//   POST /api/pago?volver=<id>      → Flow devuelve aquí a la persona (urlReturn); se la manda al sitio.
//
// Nunca se confía en lo que dice el navegador: el estado del pago siempre se consulta a Mercado Pago o a Flow.
import crypto from "node:crypto";
import { get, put } from "@vercel/blob";
import {
  responder, normalizarCorreo, correoValido, texto, leerMiembros, guardarMiembros, nuevoCodigo, hashCodigo,
  crearSesion, extenderAcceso, enviarCodigo, enviarCorreo, fechaCorta, PRECIO, DIAS_MEMBRESIA,
} from "./_lib.js";

const ARCHIVO = "pagos.json";
const ASUNTO = `Acceso Privé Ofertazos por ${DIAS_MEMBRESIA} días`;
const FLOW_API = process.env.FLOW_API_URL || "https://www.flow.cl/api";
const clp = (n) => "$" + Number(n).toLocaleString("es-CL");

function sitio(req) {
  return "https://" + (req.headers["x-forwarded-host"] || req.headers.host || "priveofertazos.cl");
}

async function leerPagos() {
  const r = await get(ARCHIVO, { access: "private", useCache: false }).catch(() => null);
  if (!r || r.statusCode !== 200 || !r.stream) return { pagos: {} };
  return JSON.parse(await new Response(r.stream).text());
}

async function guardarPagos(datos) {
  // quedarse con los últimos 2.000 pagos para que el archivo no crezca sin fin
  const ids = Object.keys(datos.pagos).sort((a, b) => String(datos.pagos[b].creado).localeCompare(String(datos.pagos[a].creado)));
  for (const id of ids.slice(2000)) delete datos.pagos[id];
  await put(ARCHIVO, JSON.stringify(datos), { access: "private", addRandomSuffix: false, allowOverwrite: true, contentType: "application/json" });
}

async function leerFormulario(req) {
  if (req.body && typeof req.body === "object") return req.body;
  const partes = [];
  for await (const p of req) partes.push(p);
  return Object.fromEntries(new URLSearchParams(Buffer.concat(partes).toString("utf8")));
}

// ---------------------------------------------------------------- Flow
export function firmaFlow(params, secreto) {
  const texto = Object.keys(params).filter((k) => k !== "s").sort().map((k) => k + params[k]).join("");
  return crypto.createHmac("sha256", secreto).update(texto).digest("hex");
}

async function flow(ruta, params, metodo = "GET") {
  const p = { apiKey: process.env.FLOW_API_KEY, ...params };
  p.s = firmaFlow(p, process.env.FLOW_SECRET_KEY);
  const cuerpo = new URLSearchParams(p).toString();
  const r = metodo === "GET"
    ? await fetch(`${FLOW_API}${ruta}?${cuerpo}`)
    : await fetch(`${FLOW_API}${ruta}`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: cuerpo });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`Flow ${ruta}: ${j.message || r.status}`);
  return j;
}

// ---------------------------------------------------------------- Mercado Pago
async function mp(ruta, cuerpo) {
  const r = await fetch("https://api.mercadopago.com" + ruta, {
    method: cuerpo ? "POST" : "GET",
    headers: { Authorization: "Bearer " + process.env.MP_ACCESS_TOKEN, "Content-Type": "application/json" },
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`Mercado Pago ${ruta}: ${j.message || r.status}`);
  return j;
}

// ---------------------------------------------------------------- activar la membresía
async function confirmarPago(id, proveedor, monto, referencia, base) {
  const datos = await leerPagos();
  const pago = datos.pagos[id];
  if (!pago) throw new Error("Pago desconocido: " + id);
  if (pago.estado === "pagado") return pago; // el aviso puede llegar más de una vez
  if (Number(monto) < PRECIO) {
    // no se activa: se avisa a la dueña para que lo revise a mano
    console.error(`Monto incorrecto en el pago ${id}: ${monto}`);
    if (pago.estado !== "revisar") {
      pago.estado = "revisar"; pago.monto_recibido = Number(monto);
      await guardarPagos(datos);
      await enviarCorreo({ para: process.env.AVISAR_A, asunto: `Revisar pago de ${pago.nombre}: llegó ${clp(monto)}`,
        texto: `El pago ${id} de ${pago.nombre} (${pago.email}) llegó por ${clp(monto)} en vez de ${clp(PRECIO)}, así que no se activó el acceso. Revísalo en ${proveedor === "flow" ? "Flow" : "Mercado Pago"} y, si corresponde, dale acceso desde el panel.` });
    }
    return pago;
  }

  const miembros = await leerMiembros();
  const previo = miembros.miembros[pago.email] || {};
  const m = {
    ...previo, email: pago.email, nombre: pago.nombre || previo.nombre || pago.email,
    whatsapp: pago.whatsapp || previo.whatsapp || "", creado: previo.creado || new Date().toISOString(),
    version: previo.version || 0, intentos: 0,
  };
  extenderAcceso(m, DIAS_MEMBRESIA);
  const codigo = nuevoCodigo();
  m.codigo_hash = hashCodigo(m.email, codigo);
  m.pagos = [...(previo.pagos || []), id].slice(-24);
  m.mensaje = previo.mensaje || "Pagó con " + (proveedor === "flow" ? "Flow" : "Mercado Pago");
  miembros.miembros[m.email] = m;
  await guardarMiembros(miembros);

  Object.assign(pago, { estado: "pagado", pagado_en: new Date().toISOString(), monto: Number(monto), referencia: String(referencia), vence: m.vence });
  await guardarPagos(datos);

  await enviarCodigo(m, codigo, base);
  await enviarCorreo({
    para: process.env.AVISAR_A,
    asunto: `Nuevo pago: ${m.nombre} (${clp(monto)})`,
    texto: `${m.nombre} (${m.email}) pagó ${clp(monto)} con ${proveedor === "flow" ? "Flow" : "Mercado Pago"}.\nSu acceso vence el ${fechaCorta(m.vence)}.\n\nPanel: ${base}/admin.html`,
    responderA: m.email,
  });
  return pago;
}

async function marcar(id, estado) {
  const datos = await leerPagos();
  if (datos.pagos[id] && datos.pagos[id].estado !== "pagado") {
    datos.pagos[id].estado = estado;
    await guardarPagos(datos);
  }
}

// Revisa con el proveedor cómo va un pago (por si el aviso no ha llegado).
async function revisar(pago, base) {
  if (pago.proveedor === "flow" && pago.token) {
    const st = await flow("/payment/getStatus", { token: pago.token });
    if (st.status === 2) return confirmarPago(pago.id, "flow", st.amount, st.flowOrder, base);
    if (st.status === 3 || st.status === 4) await marcar(pago.id, "rechazado");
  }
  if (pago.proveedor === "mercadopago") {
    const r = await mp(`/v1/payments/search?external_reference=${encodeURIComponent(pago.id)}&sort=date_created&criteria=desc`);
    const aprobado = (r.results || []).find((x) => x.status === "approved");
    if (aprobado) return confirmarPago(pago.id, "mercadopago", aprobado.transaction_amount, aprobado.id, base);
    if ((r.results || []).length && r.results.every((x) => ["rejected", "cancelled"].includes(x.status))) await marcar(pago.id, "rechazado");
  }
  return null;
}

// ---------------------------------------------------------------- manejador
export default async function handler(req, res) {
  const q = req.query || {};
  const base = sitio(req);
  try {
    // ----- avisos de los proveedores
    if (q.aviso === "flow") {
      const { token } = await leerFormulario(req);
      if (!token) return res.status(400).send("falta token");
      const st = await flow("/payment/getStatus", { token });
      if (st.status === 2) await confirmarPago(st.commerceOrder, "flow", st.amount, st.flowOrder, base);
      else if (st.status === 3 || st.status === 4) await marcar(st.commerceOrder, "rechazado");
      return res.status(200).send("ok");
    }
    if (q.aviso === "mp") {
      const cuerpo = req.body && typeof req.body === "object" ? req.body : {};
      const tipo = cuerpo.type || q.type || q.topic;
      const idPago = (cuerpo.data && cuerpo.data.id) || q["data.id"] || q.id;
      if (tipo === "payment" && idPago) {
        const p = await mp(`/v1/payments/${idPago}`);
        if (p.status === "approved" && p.currency_id === "CLP") await confirmarPago(p.external_reference, "mercadopago", p.transaction_amount, p.id, base);
        else if (["rejected", "cancelled"].includes(p.status)) await marcar(p.external_reference, "rechazado");
      }
      return res.status(200).json({ ok: true });
    }
    if (q.volver) {
      // Flow vuelve con un POST: se revisa el pago y se manda a la persona a la página
      const datos = await leerPagos();
      const pago = datos.pagos[q.volver];
      if (pago) await revisar(pago, base).catch((e) => console.error(e));
      res.setHeader("Location", `${base}/?pago=${encodeURIComponent(q.volver)}`);
      return res.status(303).end();
    }

    // ----- la página pregunta por su pago
    if (req.method === "GET" && q.estado) {
      const datos = await leerPagos();
      let pago = datos.pagos[q.estado];
      if (!pago) return responder(res, 404, { error: "No encontramos ese pago." });
      if (pago.estado !== "pagado") pago = (await revisar(pago, base).catch((e) => { console.error(e); return null; })) || pago;
      if (pago.estado !== "pagado") return responder(res, 200, { estado: pago.estado });
      // pagado: abrir la sesión en este navegador (solo durante las primeras 24 horas)
      const cookies = [];
      if (Date.now() - Date.parse(pago.pagado_en) < 864e5) {
        const miembros = await leerMiembros();
        const m = miembros.miembros[pago.email];
        if (m) cookies.push(crearSesion(m.email, m.version));
      }
      return responder(res, 200, { estado: "pagado", vence: pago.vence, email: pago.email }, cookies);
    }

    // ----- crear un pago
    if (req.method !== "POST") return responder(res, 405, { error: "Método no permitido." });
    const cuerpo = req.body || {};
    if (cuerpo.accion !== "crear") return responder(res, 400, { error: "Acción desconocida." });
    const email = normalizarCorreo(cuerpo.email), nombre = texto(cuerpo.nombre, 80);
    if (!correoValido(email)) return responder(res, 400, { error: "Revisa tu correo: no parece válido." });
    if (nombre.length < 2) return responder(res, 400, { error: "Escribe tu nombre." });
    const proveedor = cuerpo.proveedor === "flow" ? "flow" : "mercadopago";
    if (proveedor === "flow" && !(process.env.FLOW_API_KEY && process.env.FLOW_SECRET_KEY)) {
      return responder(res, 503, { error: "El pago con Flow todavía no está disponible. Prueba con Mercado Pago." });
    }
    if (proveedor === "mercadopago" && !process.env.MP_ACCESS_TOKEN) {
      return responder(res, 503, { error: "El pago con Mercado Pago todavía no está disponible. Prueba con Flow." });
    }

    const id = "p" + crypto.randomBytes(12).toString("base64url");
    const pago = {
      id, proveedor, email, nombre, whatsapp: texto(cuerpo.whatsapp, 20).replace(/[^0-9+]/g, ""),
      monto: PRECIO, estado: "pendiente", creado: new Date().toISOString(),
    };
    let url;
    if (proveedor === "flow") {
      const r = await flow("/payment/create", {
        commerceOrder: id, subject: ASUNTO, currency: "CLP", amount: String(PRECIO), email,
        urlConfirmation: `${base}/api/pago?aviso=flow`, urlReturn: `${base}/api/pago?volver=${id}`,
        timeout: String(3 * 86400),
      }, "POST");
      pago.token = r.token;
      url = `${r.url}?token=${r.token}`;
    } else {
      const r = await mp("/checkout/preferences", {
        items: [{ id: "membresia-30", title: ASUNTO, quantity: 1, unit_price: PRECIO, currency_id: "CLP" }],
        payer: { email, name: nombre },
        external_reference: id,
        notification_url: `${base}/api/pago?aviso=mp`,
        back_urls: { success: `${base}/?pago=${id}`, pending: `${base}/?pago=${id}`, failure: `${base}/?pago=${id}` },
        auto_return: "approved",
        statement_descriptor: "PRIVEOFERTAZOS",
        expires: true,
        expiration_date_to: new Date(Date.now() + 3 * 864e5).toISOString(),
      });
      pago.preferencia = r.id;
      url = r.init_point;
    }
    const datos = await leerPagos();
    datos.pagos[id] = pago;
    await guardarPagos(datos);
    return responder(res, 200, { ok: true, url, id });
  } catch (e) {
    console.error(e);
    if (q.aviso) return res.status(500).send("error"); // el proveedor reintenta
    return responder(res, 500, { error: "No pudimos iniciar el pago. Intenta de nuevo en un momento." });
  }
}
