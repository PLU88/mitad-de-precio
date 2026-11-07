// Panel de administración: entrar con la clave, ver solicitudes, aprobar, rechazar y quitar acceso.
import {
  responder, soloPost, claveAdminCorrecta, cookieAdmin, esAdmin, cookie, leerMiembros, guardarMiembros,
  normalizarCorreo, nuevoCodigo, hashCodigo, correoValido, texto, vigente, extenderAcceso, enviarCodigo,
  enviarCorreo, fechaCorta, DIAS_MEMBRESIA,
} from "./_lib.js";

const sitio = (req) => "https://" + (req.headers["x-forwarded-host"] || req.headers.host || "priveofertazos.cl");

function publico(m) {
  return {
    email: m.email, nombre: m.nombre, whatsapp: m.whatsapp || "", mensaje: m.mensaje || "",
    estado: m.estado, creado: m.creado, aprobado_en: m.aprobado_en || null,
    ultimo_ingreso: m.ultimo_ingreso || null, bloqueado: (m.intentos || 0) >= 8,
    vence: m.vence || null, vigente: vigente(m), pagos: (m.pagos || []).length,
  };
}

export default async function handler(req, res) {
  try {
    if (!soloPost(req, res)) return;
    const cuerpo = req.body || {};
    const accion = cuerpo.accion;

    if (accion === "entrar") {
      await new Promise((r) => setTimeout(r, 400)); // frena intentos de adivinar la clave
      if (!claveAdminCorrecta(cuerpo.clave)) return responder(res, 401, { error: "Clave incorrecta." });
      return responder(res, 200, { ok: true }, [cookieAdmin()]);
    }
    if (accion === "salir") return responder(res, 200, { ok: true }, [cookie("mdp_admin", "", 0)]);
    if (!esAdmin(req)) return responder(res, 401, { error: "Tu sesión de administración terminó. Entra de nuevo." });

    const datos = await leerMiembros();
    if (accion === "listar") {
      const lista = Object.values(datos.miembros).map(publico)
        .sort((a, b) => String(b.creado).localeCompare(String(a.creado)));
      return responder(res, 200, { miembros: lista });
    }

    if (accion === "agregar") {
      // Para quien pidió acceso por Instagram u otro medio: queda aprobada de inmediato.
      const correo = normalizarCorreo(cuerpo.email), nombre = texto(cuerpo.nombre, 80);
      if (!correoValido(correo)) return responder(res, 400, { error: "Revisa el correo: no parece válido." });
      if (nombre.length < 2) return responder(res, 400, { error: "Escribe el nombre." });
      const previo = datos.miembros[correo];
      datos.miembros[correo] = {
        ...(previo || {}),
        email: correo, nombre,
        whatsapp: texto(cuerpo.whatsapp, 20).replace(/[^0-9+]/g, "") || (previo && previo.whatsapp) || "",
        mensaje: texto(cuerpo.mensaje, 300) || (previo && previo.mensaje) || "",
        estado: "pendiente", creado: (previo && previo.creado) || new Date().toISOString(),
        version: (previo && previo.version) || 0, intentos: 0,
      };
    }

    const m = datos.miembros[normalizarCorreo(cuerpo.email)];
    if (!m) return responder(res, 404, { error: "No encontré a esa persona." });

    if (accion === "aprobar" || accion === "nuevo_codigo" || accion === "agregar") {
      // aprobar / agregar a mano = pagó por otro medio (transferencia, Instagram): 30 días de acceso
      const codigo = nuevoCodigo();
      if (accion !== "nuevo_codigo" || !vigente(m)) extenderAcceso(m, DIAS_MEMBRESIA);
      m.estado = "aprobado";
      m.codigo_hash = hashCodigo(m.email, codigo);
      m.version = (m.version || 0) + 1; // cierra sesiones anteriores
      m.intentos = 0;
      m.aprobado_en = m.aprobado_en || new Date().toISOString();
      await guardarMiembros(datos);
      const enviado = await enviarCodigo(m, codigo, sitio(req));
      return responder(res, 200, { ok: true, codigo, enviado, miembro: publico(m) });
    }
    if (accion === "dar_dias") {
      // Renovación pagada por fuera (por ejemplo, transferencia): suma 30 días sin cambiar su código.
      extenderAcceso(m, DIAS_MEMBRESIA);
      m.intentos = 0;
      await guardarMiembros(datos);
      const vence = fechaCorta(m.vence);
      await enviarCorreo({
        para: m.email,
        asunto: "Renovamos tu acceso a Privé Ofertazos",
        texto: `¡Hola ${m.nombre.split(" ")[0]}! Tu acceso a Privé Ofertazos quedó activo hasta el ${vence}. Entra en ${sitio(req)} con tu correo y tu código de siempre.`,
      });
      return responder(res, 200, { ok: true, miembro: publico(m) });
    }
    if (accion === "rechazar" || accion === "quitar") {
      m.estado = "rechazado";
      m.codigo_hash = null;
      m.vence = null;
      m.version = (m.version || 0) + 1;
      await guardarMiembros(datos);
      return responder(res, 200, { ok: true, miembro: publico(m) });
    }
    if (accion === "borrar") {
      delete datos.miembros[m.email];
      await guardarMiembros(datos);
      return responder(res, 200, { ok: true });
    }
    return responder(res, 400, { error: "Acción desconocida." });
  } catch (e) {
    console.error(e);
    return responder(res, 500, { error: "Algo falló. Intenta de nuevo en un momento." });
  }
}
