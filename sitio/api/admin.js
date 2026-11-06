// Panel de administración: entrar con la clave, ver solicitudes, aprobar, rechazar y quitar acceso.
import {
  responder, soloPost, claveAdminCorrecta, cookieAdmin, esAdmin, cookie, leerMiembros, guardarMiembros,
  normalizarCorreo, nuevoCodigo, hashCodigo,
} from "./_lib.js";

function publico(m) {
  return {
    email: m.email, nombre: m.nombre, whatsapp: m.whatsapp || "", mensaje: m.mensaje || "",
    estado: m.estado, creado: m.creado, aprobado_en: m.aprobado_en || null,
    ultimo_ingreso: m.ultimo_ingreso || null, bloqueado: (m.intentos || 0) >= 8,
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

    const m = datos.miembros[normalizarCorreo(cuerpo.email)];
    if (!m) return responder(res, 404, { error: "No encontré a esa persona." });

    if (accion === "aprobar" || accion === "nuevo_codigo") {
      const codigo = nuevoCodigo();
      m.estado = "aprobado";
      m.codigo_hash = hashCodigo(m.email, codigo);
      m.version = (m.version || 0) + 1; // cierra sesiones anteriores
      m.intentos = 0;
      m.aprobado_en = m.aprobado_en || new Date().toISOString();
      await guardarMiembros(datos);
      return responder(res, 200, { ok: true, codigo, miembro: publico(m) });
    }
    if (accion === "rechazar" || accion === "quitar") {
      m.estado = "rechazado";
      m.codigo_hash = null;
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
