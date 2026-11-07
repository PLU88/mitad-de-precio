// Sesión de miembros: consultar, ingresar, recuperar el código y salir. El acceso se compra en /api/pago.
import {
  responder, soloPost, normalizarCorreo, correoValido, leerMiembros, guardarMiembros,
  MAX_INTENTOS, hashCodigo, crearSesion, cookie, leerSesion, vigente, fechaCorta, nuevoCodigo, enviarCodigo, PRECIO,
} from "./_lib.js";

const sitio = (req) => "https://" + (req.headers["x-forwarded-host"] || req.headers.host || "priveofertazos.cl");

export default async function handler(req, res) {
  try {
    if (req.method === "GET") {
      const base = {
        precio: PRECIO,
        pagos: { mercadopago: Boolean(process.env.MP_ACCESS_TOKEN), flow: Boolean(process.env.FLOW_API_KEY && process.env.FLOW_SECRET_KEY) },
      };
      const ses = leerSesion(req);
      if (!ses) return responder(res, 200, { ...base, conectado: false });
      const m = (await leerMiembros()).miembros[ses.e];
      if (!m || m.version !== ses.v || m.estado !== "aprobado") return responder(res, 200, { ...base, conectado: false });
      if (!vigente(m)) {
        return responder(res, 200, { ...base, conectado: false, vencido: true, nombre: m.nombre, email: m.email, whatsapp: m.whatsapp || "" });
      }
      return responder(res, 200, { ...base, conectado: true, nombre: m.nombre, email: m.email, whatsapp: m.whatsapp || "", vence: m.vence });
    }
    if (!soloPost(req, res)) return;
    const cuerpo = req.body || {};
    const accion = cuerpo.accion;

    if (accion === "salir") {
      return responder(res, 200, { ok: true }, [cookie("mdp_sesion", "", 0)]);
    }

    const correo = normalizarCorreo(cuerpo.email);
    if (!correoValido(correo)) return responder(res, 400, { error: "Revisa tu correo: no parece válido." });

    if (accion === "solicitar") {
      return responder(res, 400, { error: "Ahora el acceso se activa al pagar. Usa el botón de pago." });
    }

    if (accion === "recuperar") {
      // Manda un código nuevo al correo del miembro (solo si su acceso está vigente). Las sesiones abiertas siguen.
      const datos = await leerMiembros();
      const m = datos.miembros[correo];
      const mensaje = "Si ese correo tiene acceso vigente, te enviamos un código nuevo. Revisa tu bandeja (y spam).";
      if (!m || m.estado !== "aprobado" || !vigente(m)) return responder(res, 200, { ok: true, mensaje });
      if (m.recuperado_en && Date.now() - Date.parse(m.recuperado_en) < 10 * 60e3) return responder(res, 200, { ok: true, mensaje });
      const codigo = nuevoCodigo();
      m.codigo_hash = hashCodigo(correo, codigo);
      m.intentos = 0;
      m.recuperado_en = new Date().toISOString();
      await guardarMiembros(datos);
      await enviarCodigo(m, codigo, sitio(req));
      return responder(res, 200, { ok: true, mensaje });
    }

    if (accion === "ingresar") {
      const datos = await leerMiembros();
      const m = datos.miembros[correo];
      const error = { error: "El correo o el código no coinciden. Revisa el mensaje con tu código." };
      if (!m || m.estado !== "aprobado" || !m.codigo_hash) return responder(res, 401, error);
      if ((m.intentos || 0) >= MAX_INTENTOS) {
        return responder(res, 423, { error: "Demasiados intentos. Usa «¿Olvidaste tu código?» para recibir uno nuevo." });
      }
      if (hashCodigo(correo, cuerpo.codigo) !== m.codigo_hash) {
        m.intentos = (m.intentos || 0) + 1;
        await guardarMiembros(datos);
        return responder(res, 401, error);
      }
      m.intentos = 0;
      if (!vigente(m)) {
        await guardarMiembros(datos);
        return responder(res, 402, {
          error: (m.vence ? "Tu acceso venció el " + fechaCorta(m.vence) + "." : "Ahora el acceso es pagado.") +
            " Renuévalo abajo y entras al tiro.",
          renovar: true, nombre: m.nombre, email: m.email, whatsapp: m.whatsapp || "",
        });
      }
      m.ultimo_ingreso = new Date().toISOString();
      await guardarMiembros(datos);
      return responder(res, 200, { ok: true, nombre: m.nombre, vence: m.vence }, [crearSesion(correo, m.version)]);
    }

    return responder(res, 400, { error: "Acción desconocida." });
  } catch (e) {
    console.error(e);
    return responder(res, 500, { error: "Algo falló. Intenta de nuevo en un momento." });
  }
}
