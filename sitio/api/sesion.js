// Sesión de miembros: consultar, pedir acceso, ingresar y salir.
import {
  responder, soloPost, normalizarCorreo, correoValido, texto, leerMiembros, guardarMiembros,
  contarPendientes, MAX_PENDIENTES, MAX_INTENTOS, hashCodigo, crearSesion, cookie, miembroConectado, avisarSolicitud,
} from "./_lib.js";

export default async function handler(req, res) {
  try {
    if (req.method === "GET") {
      const m = await miembroConectado(req);
      return responder(res, 200, m ? { conectado: true, nombre: m.nombre } : { conectado: false });
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
      const nombre = texto(cuerpo.nombre, 80);
      if (nombre.length < 2) return responder(res, 400, { error: "Escribe tu nombre." });
      const datos = await leerMiembros();
      const actual = datos.miembros[correo];
      if (actual && actual.estado === "aprobado") {
        return responder(res, 200, { ok: true, mensaje: "Ese correo ya tiene acceso. Entra con tu código." });
      }
      if (actual && actual.estado === "pendiente") {
        return responder(res, 200, { ok: true, mensaje: "Ya recibimos tu solicitud. Te avisaremos cuando sea aprobada." });
      }
      if (contarPendientes(datos) >= MAX_PENDIENTES) {
        return responder(res, 503, { error: "Hay muchas solicitudes en espera. Intenta de nuevo en unos días." });
      }
      datos.miembros[correo] = {
        email: correo,
        nombre,
        whatsapp: texto(cuerpo.whatsapp, 20).replace(/[^0-9+]/g, ""),
        mensaje: texto(cuerpo.mensaje, 300),
        estado: "pendiente",
        creado: new Date().toISOString(),
        version: 0,
        intentos: 0,
      };
      await guardarMiembros(datos);
      await avisarSolicitud(datos.miembros[correo], "https://" + (req.headers["x-forwarded-host"] || req.headers.host || "priveofertazos.cl"));
      return responder(res, 200, { ok: true, mensaje: "¡Listo! Recibimos tu solicitud. Te avisaremos cuando sea aprobada." });
    }

    if (accion === "ingresar") {
      const datos = await leerMiembros();
      const m = datos.miembros[correo];
      const error = { error: "El correo o el código no coinciden. Revisa el mensaje con tu código." };
      if (!m || m.estado !== "aprobado" || !m.codigo_hash) return responder(res, 401, error);
      if ((m.intentos || 0) >= MAX_INTENTOS) {
        return responder(res, 423, { error: "Demasiados intentos. Pide un código nuevo a quien te dio acceso." });
      }
      if (hashCodigo(correo, cuerpo.codigo) !== m.codigo_hash) {
        m.intentos = (m.intentos || 0) + 1;
        await guardarMiembros(datos);
        return responder(res, 401, error);
      }
      m.intentos = 0;
      m.ultimo_ingreso = new Date().toISOString();
      await guardarMiembros(datos);
      return responder(res, 200, { ok: true, nombre: m.nombre }, [crearSesion(correo, m.version)]);
    }

    return responder(res, 400, { error: "Acción desconocida." });
  } catch (e) {
    console.error(e);
    return responder(res, 500, { error: "Algo falló. Intenta de nuevo en un momento." });
  }
}
