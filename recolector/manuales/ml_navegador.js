// Herramientas para renovar las ofertas de Mercado Libre desde el navegador
// integrado (con la sesión de afiliada de la dueña ya iniciada).
// Uso (en la pestaña https://www.mercadolibre.cl/afiliados/linkbuilder):
//   1) pegar este archivo completo con javascript_exec
//   2) await __mlScrape(25)        -> junta las ofertas de 50% o más
//   3) por cada lote: c = __prep(i) -> escribir el carácter c con el teclado
//      (computer type) y luego await __run()   (lotes de máximo 30)
//   4) __mlExport(n) -> JSON por partes para guardar con guardar_ml.py
(function () {
  var MAX = 150, LOTE = 30;

  window.__mlScrape = async function (maxPaginas) {
    var filas = [], vistos = {}, vacias = 0;
    for (var p = 1; p <= (maxPaginas || 25); p++) {
      var h;
      try {
        var r = await fetch("https://www.mercadolibre.cl/ofertas?page=" + p, { credentials: "include" });
        if (!r.ok) break;
        h = await r.text();
      } catch (e) { break; }
      var d = new DOMParser().parseFromString(h, "text/html");
      var cards = d.querySelectorAll(".poly-card");
      if (!cards.length) { if (++vacias > 1) break; continue; }
      cards.forEach(function (c) {
        var a = c.querySelector("a.poly-component__title");
        if (!a) return;
        var url = a.getAttribute("href").split("#")[0].split("?")[0];
        // Los avisos pagados apuntan a click1.mercadolibre.cl: el generador no los acepta
        if (!/^https:\/\/(www|articulo)\.mercadolibre\.cl\//.test(url)) return;
        var img = c.querySelector("img.poly-component__picture");
        var imagen = img ? (img.getAttribute("data-src") || img.getAttribute("src") || "") : "";
        if (imagen.indexOf("data:") === 0) imagen = "";
        function num(e) {
          if (!e) return 0;
          var m = (e.getAttribute("aria-label") || "").match(/(\d[\d.]*)\s*pesos/);
          if (m) return +m[1].replace(/\./g, "");
          var f = e.querySelector(".andes-money-amount__fraction");
          return f ? +f.textContent.replace(/\D/g, "") : 0;
        }
        var precio = num(c.querySelector(".poly-price__current .andes-money-amount"));
        var normal = num(c.querySelector("s.andes-money-amount--previous"));
        if (!precio || !normal || 1 - precio / normal < 0.5) return;
        var id = (url.replace("MLC-", "MLC").match(/MLC[U]?\d+/) || [url])[0];
        if (vistos[id]) return;
        vistos[id] = 1;
        var vend = (c.querySelector(".poly-component__seller") || {}).textContent || "";
        filas.push([a.textContent.trim(), url, imagen, precio, normal, vend.trim(), ""]);
      });
      if (filas.length >= MAX) break;
    }
    window.__mlRows = filas.slice(0, MAX);
    return { ofertas: window.__mlRows.length, lotes: Math.ceil(window.__mlRows.length / LOTE) };
  };

  // Deja en el cuadro todas las URLs del lote menos el último carácter.
  // Ese carácter (el que devuelve) hay que escribirlo con el teclado para que
  // la página active el botón "Generar".
  window.__prep = function (lote) {
    var i = lote * LOTE, filas = window.__mlRows.slice(i, i + LOTE);
    if (!filas.length) return null;
    var t = filas.map(function (f) { return f[1]; }).join("\n");
    var ta = document.getElementById("url-0");
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(ta, t.slice(0, -1));
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
    window.__cur = [i, filas.length];
    return t.slice(-1);
  };

  window.__run = async function () {
    var i = window.__cur[0], n = window.__cur[1];
    var ta = document.getElementById("url-0");
    var esperado = window.__mlRows.slice(i, i + n).map(function (f) { return f[1]; }).join("\n");
    if (ta.value !== esperado) return { error: "el cuadro no tiene las URLs esperadas" };
    var campo = function () { return document.getElementById("textfield-copyLink-1"); };
    var antes = campo() ? campo().value : "";
    var boton = Array.prototype.find.call(document.querySelectorAll("button"), function (b) { return /Generar/.test(b.textContent); });
    if (!boton || boton.disabled) return { error: "botón Generar desactivado" };
    boton.click();
    for (var k = 0; k < 40; k++) {
      await new Promise(function (r) { setTimeout(r, 500); });
      var v = campo() ? campo().value : "";
      if (v && v !== antes) {
        var links = v.split("\n");
        if (links.length !== n) return { error: "llegaron " + links.length + " links para " + n + " URLs" };
        links.forEach(function (l, j) { window.__mlRows[i + j][6] = l.trim(); });
        return { ok: n, listos: window.__mlRows.filter(function (f) { return f[6]; }).length };
      }
    }
    return { error: "sin respuesta", pagina: (document.body.innerText.split("Generar")[1] || "").slice(0, 300) };
  };

  // JSON compacto (URLs e imágenes relativas) partido en trozos de ~12 mil caracteres.
  window.__mlExport = function (parte) {
    var filas = window.__mlRows.filter(function (f) { return f[6]; }).map(function (f) {
      return [f[0], f[1].replace("https://www.mercadolibre.cl/", ""), f[2].replace("https://http2.mlstatic.com/", ""), f[3], f[4], f[5], f[6]];
    });
    var s = JSON.stringify(filas), TAM = 12000;
    return { partes: Math.ceil(s.length / TAM), texto: s.slice(parte * TAM, (parte + 1) * TAM) };
  };
})();
