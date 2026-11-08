// Sesión de miembros: consultar, ingresar, recuperar el código y salir. El acceso se compra en /api/pago.
import {
  responder, soloPost, normalizarCorreo, correoValido, leerMiembros, guardarMiembros,
  MAX_INTENTOS, hashCodigo, crearSesion, cookie, leerSesion, vigente, fechaCorta, nuevoCodigo, enviarCodigo, PRECIO,
  texto, avisarSolicitud,
} from "./_lib.js";

// Datos para transferir: variable TRANSFERENCIA en Vercel, una línea por dato con el formato "Etiqueta: valor".
function datosTransferencia() {
  return String(process.env.TRANSFERENCIA || "").split(/\r?\n|\|/).map((l) => l.trim()).filter(Boolean).map((l) => {
    const i = l.indexOf(":");
    return i > 0 ? [l.slice(0, i).trim(), l.slice(i + 1).trim()] : ["", l];
  });
}

const sitio = (req) => "https://" + (req.headers["x-forwarded-host"] || req.headers.host || "priveofertazos.cl");

export default async function handler(req, res) {
  try {
    if (req.method === "GET") {
      const base = {
        precio: PRECIO,
        pagos: { transferencia: true },
        transferencia: { datos: datosTransferencia() },
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

    if (accion === "solicitar" || accion === "transferi") {
      // La persona avisa que transfirió: queda "por aprobar" y la dueña recibe un correo para revisarlo en el panel.
      const nombre = texto(cuerpo.nombre, 80);
      if (nombre.length < 2) return responder(res, 400, { error: "Escribe tu nombre." });
      const datos = await leerMiembros();
      const actual = datos.miembros[correo];
      const listo = "¡Gracias! Recibimos tu aviso. Apenas confirmemos la transferencia te enviamos tu código a " + correo + ".";
      if (actual && actual.aviso_transferencia && Date.now() - Date.parse(actual.aviso_transferencia) < 30 * 60e3) {
        return responder(res, 200, { ok: true, mensaje: listo });
      }
      const whatsapp = texto(cuerpo.whatsapp, 20).replace(/[^0-9+]/g, "");
      const m = actual || { email: correo, creado: new Date().toISOString(), version: 0, intentos: 0 };
      m.nombre = nombre;
      if (whatsapp) m.whatsapp = whatsapp;
      if (m.estado !== "aprobado") m.estado = "pendiente";
      m.aviso_transferencia = new Date().toISOString();
      m.mensaje = "Avisó que transfirió $" + PRECIO.toLocaleString("es-CL") + (m.estado === "aprobado" ? " (renovación: usa «Sumar/Dar 30 días»)" : "");
      datos.miembros[correo] = m;
      await guardarMiembros(datos);
      await avisarSolicitud(m, sitio(req));
      return responder(res, 200, { ok: true, mensaje: listo });
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
