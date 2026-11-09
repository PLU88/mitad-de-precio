// Entrega las ofertas a miembros con sesión activa (o a todos durante el período gratis).
// El archivo ya viene comprimido (gzip), así cabe en el límite de tamaño de Vercel y llega más rápido.
import { responder, miembroConectado, ofertas } from "./_lib.js";
import { accesoGratis } from "./_gratis.js";

export default async function handler(req, res) {
  try {
    const m = accesoGratis() || (await miembroConectado(req));
    if (!m) return responder(res, 401, { error: "Necesitas entrar con tu correo y código." });
    const comprimido = await ofertas();
    res.setHeader("Cache-Control", "private, no-store");
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.setHeader("Content-Encoding", "gzip");
    return res.status(200).send(comprimido);
  } catch (e) {
    console.error(e);
    return responder(res, 500, { error: "No se pudieron cargar las ofertas. Intenta en unos minutos." });
  }
}
