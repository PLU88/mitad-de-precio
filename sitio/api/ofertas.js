// Entrega las ofertas solo a miembros aprobados con sesión activa.
import { responder, miembroConectado, ofertas } from "./_lib.js";

export default async function handler(req, res) {
  try {
    const m = await miembroConectado(req);
    if (!m) return responder(res, 401, { error: "Necesitas entrar con tu correo y código." });
    const datos = await ofertas();
    res.setHeader("Cache-Control", "private, no-store");
    return res.status(200).json(datos);
  } catch (e) {
    console.error(e);
    return responder(res, 500, { error: "No se pudieron cargar las ofertas. Intenta en unos minutos." });
  }
}
