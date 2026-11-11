// Junta las ofertas de Zara Chile (40% o más) desde el navegador.
// Zara bloquea a los servidores, así que esto se corre en una pestaña abierta en
// https://www.zara.com/cl/ y el resultado se guarda con guardar_zara.py.
//
// Uso (en la consola de la página o con la herramienta de JavaScript):
//   1) pegar este archivo completo
//   2) await __zaraScrape()        -> {categorias, productos, ofertas}
//   3) __zaraExport(0), __zaraExport(1)...  -> trozos de texto JSON (unirlos)
//
// Cada fila: [nombre, url, imagen, precio, normal, "", "", pistas]

window.__zaraScrape = async function () {
  const BASE = "/cl/es";
  const OFERTA = /rebaja|sale|special price|precios-especiales|precios especiales|outlet|oferta/i;
  const SECCION = { WOMAN: "MUJER", MAN: "HOMBRE", KID: "NIÑOS", KIDS: "NIÑOS" };
  const arbol = await (await fetch(BASE + "/categories?ajax=true")).json();
  const hojas = new Map();
  (function recorrer(cats, ruta, dentro) {
    for (const c of cats || []) {
      const r = ruta + "/" + c.name;
      const es = dentro || OFERTA.test(c.name + " " + ((c.seo && c.seo.keyword) || ""));
      if (es && !(c.subcategories || []).length) hojas.set(c.id, r);
      recorrer(c.subcategories, r, es);
    }
  })(arbol.categories, "", false);

  const filas = [], vistos = new Set();
  let productos = 0;
  for (const [id, ruta] of hojas) {
    let d = {};
    try { d = await (await fetch(`${BASE}/category/${id}/products?ajax=true`)).json(); } catch (e) { continue; }
    for (const g of d.productGroups || []) for (const el of g.elements || []) for (const c of el.commercialComponents || []) {
      if (!c.price) continue;
      productos++;
      if (!c.oldPrice || Math.round((1 - c.price / c.oldPrice) * 100) < 40) continue;
      const clave = c.name + "|" + c.price;  // mismo producto en otro color
      if (vistos.has(clave)) continue;
      vistos.add(clave);
      const seo = c.seo || {};
      let url = `https://www.zara.com/cl/es/${seo.keyword || "producto"}-p${seo.seoProductId || ""}.html`;
      if (seo.discernProductId) url += `?v1=${seo.discernProductId}`;
      const colores = (c.detail && c.detail.colors) || [];
      const medios = (colores[0] && colores[0].xmedia) || c.xmedia || [];
      const img = medios.find(m => (m.type || "image") === "image" && m.url);
      const nombre = c.name.charAt(0) + c.name.slice(1).toLowerCase();
      const pistas = [ruta, SECCION[String(c.sectionName || "").toUpperCase()] || "", c.familyName || "", c.subfamilyName || ""].join(" ");
      filas.push([nombre, url, img ? img.url.replace("{width}", "750") : "", c.price, c.oldPrice, "", "", pistas]);
    }
    await new Promise(r => setTimeout(r, 150));
  }
  window.__zaraFilas = { productos, categorias: hojas.size, filas };
  return { categorias: hojas.size, productos, ofertas: filas.length };
};

window.__zaraExport = function (parte) {
  const texto = JSON.stringify(window.__zaraFilas);
  const T = 12000;
  return { partes: Math.ceil(texto.length / T), texto: texto.slice(parte * T, (parte + 1) * T) };
};
