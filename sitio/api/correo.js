// Reenvía a Gmail todo correo que llega a cualquier dirección @priveofertazos.cl.
// Resend recibe el correo y avisa aquí (webhook "email.received"); esta función lo lee y lo reenvía.
import crypto from "node:crypto";

const API = "https://api.resend.com";
const DOMINIO = "priveofertazos.cl";

function leerCuerpo(req) {
  return new Promise((ok, mal) => {
    const partes = [];
    req.on("data", (p) => partes.push(p));
    req.on("end", () => ok(Buffer.concat(partes).toString("utf8")));
    req.on("error", mal);
  });
}

// Comprueba que el aviso viene de Resend (firma Svix: "v1,<base64>").
export function firmaValida(secreto, id, momento, cuerpo, firmas) {
  if (!secreto || !id || !momento || !firmas) return false;
  if (Math.abs(Date.now() / 1000 - Number(momento)) > 600) return false;
  const clave = Buffer.from(secreto.replace(/^whsec_/, ""), "base64");
  const esperada = crypto.createHmac("sha256", clave).update(`${id}.${momento}.${cuerpo}`).digest();
  return String(firmas).split(" ").some((f) => {
    const [, valor] = f.split(",");
    const dada = Buffer.from(valor || "", "base64");
    return dada.length === esperada.length && crypto.timingSafeEqual(dada, esperada);
  });
}

function escapar(t) {
  return String(t || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function nombreYCorreo(remitente) {
  const m = String(remitente || "").match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/);
  return m ? { nombre: m[1].trim(), correo: m[2].trim() } : { nombre: "", correo: String(remitente || "").trim() };
}

async function api(ruta, clave, opciones = {}) {
  const r = await fetch(API + ruta, {
    ...opciones,
    headers: { Authorization: "Bearer " + clave, "Content-Type": "application/json", ...(opciones.headers || {}) },
  });
  const texto = await r.text();
  if (!r.ok) throw new Error(`Resend ${ruta} respondió ${r.status}: ${texto.slice(0, 300)}`);
  return texto ? JSON.parse(texto) : {};
}

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Método no permitido." });
  try {
    const cuerpo = await leerCuerpo(req);
    const h = req.headers;
    if (!firmaValida(process.env.RESEND_WEBHOOK_SECRETO, h["svix-id"], h["svix-timestamp"], cuerpo, h["svix-signature"])) {
      return res.status(401).json({ error: "Firma inválida." });
    }
    const evento = JSON.parse(cuerpo || "{}");
    if (evento.type !== "email.received") return res.status(200).json({ ok: true, ignorado: evento.type });

    const clave = process.env.RESEND_CLAVE_REENVIO, para = process.env.AVISAR_A;
    const id = evento.data && evento.data.email_id;
    if (!clave || !para || !id) return res.status(500).json({ error: "Falta configuración." });

    const correo = await api(`/emails/receiving/${id}`, clave);
    const de = nombreYCorreo(correo.from);
    if (de.correo.toLowerCase().endsWith("@" + DOMINIO)) {
      return res.status(200).json({ ok: true, ignorado: "remitente propio" }); // evita reenvíos en bucle
    }
    const destinos = [].concat(correo.to || []).join(", ");
    let adjuntos = [];
    try {
      const lista = await api(`/emails/receiving/${id}/attachments`, clave);
      adjuntos = (lista.data || []).filter((a) => a.download_url).slice(0, 10)
        .map((a) => ({ filename: a.filename || "adjunto", path: a.download_url }));
    } catch (e) {
      console.error("No se pudieron leer los adjuntos:", e.message);
    }

    const encabezado = `De: ${correo.from || "(sin remitente)"}\nPara: ${destinos}\n\n`;
    const htmlEncabezado =
      '<div style="font-family:Arial,sans-serif;font-size:13px;color:#555;border-bottom:1px solid #ddd;padding-bottom:8px;margin-bottom:12px">' +
      "Correo recibido en <b>" + escapar(destinos) + "</b><br>De: " + escapar(correo.from) + "</div>";
    await api("/emails", clave, {
      method: "POST",
      headers: { "Idempotency-Key": "reenvio-" + id }, // si Resend reintenta el aviso, no se duplica
      body: JSON.stringify({
        from: `${(de.nombre || de.correo).replace(/[<>":]/g, "").slice(0, 60)} vía Privé Ofertazos <reenvios@${DOMINIO}>`,
        to: [para],
        reply_to: de.correo,
        subject: correo.subject || "(sin asunto)",
        text: encabezado + (correo.text || "(este correo no tiene texto; ábrelo en versión HTML)"),
        html: htmlEncabezado + (correo.html || "<pre>" + escapar(correo.text || "") + "</pre>"),
        attachments: adjuntos.length ? adjuntos : undefined,
      }),
    });
    return res.status(200).json({ ok: true });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: "No se pudo reenviar." }); // Resend reintenta más tarde
  }
}
