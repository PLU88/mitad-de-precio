// Panel de administración: entrar con la clave, ver solicitudes, aprobar, rechazar y quitar acceso.
import {
  responder, soloPost, claveAdminCorrecta, cookieAdmin, esAdmin, cookie, leerMiembros, guardarMiembros,
  normalizarCorreo, nuevoCodigo, hashCodigo, correoValido, texto, vigente, extenderAcceso, enviarCodigo,
  enviarCorreo, fechaCorta, DIAS_MEMBRESIA,
} from "./_lib.js";
import crypto from "node:crypto";
import { put } from "@vercel/blob";
import { cuponesManuales } from "./cupones.js";

const TIPOS_CUPON = ["Instagram", "Tiendas", "Bancos", "Telefonía", "Gas", "Otros"];

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

    if (accion === "cupones" || accion === "cupon_agregar" || accion === "cupon_quitar") {
      // Cupones que la dueña agrega a mano (por ejemplo, los que ve en Instagram)
      const d = await cuponesManuales();
      if (accion === "cupon_agregar") {
        const comercio = texto(cuerpo.comercio, 60), codigo = texto(cuerpo.codigo, 40).replace(/\s+/g, "");
        const titulo = texto(cuerpo.titulo, 140), hasta = /^\d{4}-\d{2}-\d{2}$/.test(cuerpo.hasta || "") ? cuerpo.hasta : "";
        if (comercio.length < 2) return responder(res, 400, { error: "Escribe la tienda o marca." });
        if (!codigo && titulo.length < 3) return responder(res, 400, { error: "Escribe el código o qué descuento es." });
        let url = texto(cuerpo.url, 300);
        if (url && !/^https?:\/\//i.test(url)) url = "https://" + url;
        const tipo = TIPOS_CUPON.includes(cuerpo.tipo) ? cuerpo.tipo : "Instagram";
        const pct = (titulo.match(/(\d{1,2})\s?%/) || [])[1];
        d.cupones.unshift({
          id: crypto.randomUUID(), t: tipo, f: texto(cuerpo.fuente, 60) || (tipo === "Instagram" ? "Instagram" : "Privé Ofertazos"),
          m: comercio, ti: titulo || "Código de descuento", d: texto(cuerpo.detalle, 220), c: codigo, u: url,
          hasta, v: hasta ? "Vence el " + fechaCorta(hasta + "T12:00:00Z") : "", x: pct ? pct + "%" : "",
          creado: new Date().toISOString(),
        });
      }
      if (accion === "cupon_quitar") d.cupones = d.cupones.filter((c) => c.id !== cuerpo.id);
      if (accion !== "cupones") {
        d.cupones = d.cupones.slice(0, 500);
        await put("cupones_manuales.json", JSON.stringify(d), { access: "private", addRandomSuffix: false, allowOverwrite: true, contentType: "application/json" });
      }
      return responder(res, 200, { ok: true, cupones: d.cupones });
    }

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
