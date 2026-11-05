(function () {
  "use strict";

  const $ = (s) => document.querySelector(s);
  const VACIO = { posicion: "", marca: "", modelo: "", anio: "", condicion: "", pmin: "", pmax: "", extra: {} };
  const estado = { datos: null, tab: null, q: "", orden: "recientes", solo: null, abierto: false, ...structuredClone(VACIO) };

  // filtros propios de cada categoría (las claves salen de "filtros" de cada producto)
  const EXTRA = {
    paragolpes: [["sensores", "Sensores"], ["antiniebla", "Faros antiniebla"], ["ojos_de_gato", "Ojos de gato"],
      ["rejillas", "Rejillas inferiores"], ["lavafaros", "Lavafaros"], ["camara", "Cámara"], ["gancho", "Gancho de remolque"],
      ["molduras", "Molduras cromadas"], ["alma", "Alma / refuerzo"]],
    optica: [["lado", "Lado"], ["tipo_luz", "Tipo de luz"], ["drl", "Luz diurna (DRL)"], ["motor", "Motor de regulación"],
      ["ubicacion", "Ubicación (traseras)"], ["lente", "Lente"], ["soportes", "Soportes"], ["lamparas", "Lámparas y fichas"]],
    parrilla: [["emblema", "Emblema"], ["terminacion_parrilla", "Terminación"], ["camara_radar", "Cámara / radar"]],
  };
  const ICONO_WA = '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path fill="currentColor" d="M12 2.2A9.8 9.8 0 0 0 3.6 17l-1.4 4.8 4.9-1.3A9.8 9.8 0 1 0 12 2.2Zm0 1.8a8 8 0 1 1-4.1 14.9l-.3-.2-2.9.8.8-2.8-.2-.3A8 8 0 0 1 12 4Zm-3.3 4c-.2 0-.5 0-.7.3-.3.3-1 1-1 2.4s1 2.8 1.2 3c.1.2 2 3.2 5 4.4 2.5 1 3 .8 3.5.7.6 0 1.8-.7 2-1.4.3-.7.3-1.3.2-1.4l-.5-.3-1.8-.9c-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.6.1a6.6 6.6 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.5l-.8-2c-.2-.5-.4-.4-.6-.4h-.5Z"/></svg>';
  const ICONO_COMPARTIR = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICONO_SI = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICONO_NO = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 12h12" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>';
  const ICONO_ZOOM = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const FLECHA = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const AUTO = '<svg viewBox="0 0 64 64" width="80" height="80" aria-hidden="true"><path d="M8 40v-7l7-12h34l7 12v7z" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"/><circle cx="19" cy="42" r="6" fill="currentColor"/><circle cx="45" cy="42" r="6" fill="currentColor"/></svg>';

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pesos = (n) => "$" + Math.round(n).toLocaleString("es-AR");
  const wa = (texto) => `https://wa.me/${estado.datos.sitio.whatsapp}?text=${encodeURIComponent(texto)}`;
  const norm = (s) => String(s ?? "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const unicos = (arr) => [...new Set(arr.filter(Boolean))].sort((a, b) => a.localeCompare(b, "es", { numeric: true }));
  const cat = () => estado.datos.categorias.find((c) => c.id === estado.tab);

  // ---------- búsqueda y filtros ----------
  function pajar(p) {
    return p._pajar || (p._pajar = norm([p.codigo, p.codigo.replace("-", ""), p.titulo, p.marca, p.modelo, p.version,
      p.compatibles.join(" "), p.observaciones, p.caracteristicas.join(" "), p.terminacion, p.origen, p.estado_txt, p.oem].join(" ")));
  }
  const enAnios = (p, a) => p.anio_desde && a >= p.anio_desde && a <= (p.anio_hasta || p.anio_desde);
  function coincide(p) {
    const palabras = norm(estado.q).split(/[^a-z0-9ñ]+/).filter(Boolean);
    return palabras.every((w) => {
      if (/^(19|20)\d\d$/.test(w)) return enAnios(p, +w) || pajar(p).includes(w);
      return pajar(p).includes(w);
    });
  }
  function pasa(p, salvo) {
    const f = estado;
    if (salvo !== "posicion" && f.posicion && p.posicion !== f.posicion) return false;
    if (salvo !== "marca" && f.marca && p.marca !== f.marca) return false;
    if (salvo !== "modelo" && f.modelo && p.modelo !== f.modelo) return false;
    // año: entran las piezas cuyo rango lo incluye y las que todavía no tienen años cargados
    if (f.anio && /^\d{4}$/.test(f.anio) && p.anio_desde && !enAnios(p, +f.anio)) return false;
    if (f.condicion && p.condicion !== f.condicion) return false;
    if (f.pmin && !(p.precio >= +f.pmin)) return false;
    if (f.pmax && !(p.precio <= +f.pmax)) return false;
    for (const [k, v] of Object.entries(f.extra)) if (v && salvo !== k && p.filtros[k] !== v) return false;
    return true;
  }
  const deTab = (tab) => estado.datos.productos.filter((p) => p.categoria === tab && coincide(p));
  function activos() {
    const f = estado;
    return [f.marca, f.modelo, f.anio, f.condicion, f.pmin, f.pmax].filter(Boolean).length + Object.values(f.extra).filter(Boolean).length;
  }
  function ordenar(lista) {
    const sinPrecio = (p) => (p.precio ? 0 : 1);
    if (estado.orden === "precio-asc") return lista.sort((a, b) => sinPrecio(a) - sinPrecio(b) || a.precio - b.precio);
    if (estado.orden === "precio-desc") return lista.sort((a, b) => sinPrecio(a) - sinPrecio(b) || b.precio - a.precio);
    return lista; // ya vienen de más nuevo a más viejo
  }

  // ---------- render ----------
  function opciones(valores, sel, todos) {
    return `<option value="">${todos}</option>` + valores.map((v) => `<option value="${esc(v)}"${v === sel ? " selected" : ""}>${esc(v)}</option>`).join("");
  }
  function renderControles() {
    const cats = estado.datos.categorias;
    $("#tabs").innerHTML = cats.map((c) => `
      <button class="tab" role="tab" data-tab="${c.id}" aria-selected="${c.id === estado.tab}">
        ${esc(c.nombre)} <span class="n">(${deTab(c.id).length})</span>
      </button>`).join("");
    const base = deTab(estado.tab);
    const conPos = estado.tab !== "parrilla";
    const fem = estado.tab === "optica";
    $("#chips").style.display = conPos ? "" : "none";
    $("#chips").innerHTML = [["", fem ? "Todas" : "Todos"], ["delantero", fem ? "Delanteras" : "Delanteros"], ["trasero", fem ? "Traseras" : "Traseros"]]
      .map(([v, t]) => {
        const hay = !v || base.some((p) => p.posicion === v && pasa(p, "posicion"));
        return `<button class="chip" data-posicion="${v}" aria-pressed="${v === estado.posicion}" ${hay || v === estado.posicion ? "" : "disabled"}>${t}</button>`;
      }).join("");

    $("#f-marca").innerHTML = opciones(unicos(base.filter((p) => pasa(p, "marca")).map((p) => p.marca)), estado.marca, "Todas");
    $("#f-modelo").innerHTML = opciones(unicos(base.filter((p) => pasa(p, "modelo") && (!estado.marca || p.marca === estado.marca)).map((p) => p.modelo)), estado.modelo, "Todos");
    $("#f-modelo").disabled = !estado.marca;
    $("#f-anio").value = estado.anio;
    $("#f-condicion").value = estado.condicion;
    $("#f-pmin").value = estado.pmin;
    $("#f-pmax").value = estado.pmax;
    $("#f-extra").innerHTML = (EXTRA[estado.tab] || []).map(([k, nombre]) => {
      const vals = unicos(base.filter((p) => pasa(p, k)).map((p) => p.filtros[k]));
      if (!vals.length && !estado.extra[k]) return "";
      return `<label class="filtro"><span>${esc(nombre)}</span><select data-extra="${k}" class="${estado.extra[k] ? "activo" : ""}">${opciones(vals, estado.extra[k] || "", "Todos")}</select></label>`;
    }).join("");
    for (const id of ["#f-marca", "#f-modelo", "#f-anio", "#f-condicion", "#f-pmin", "#f-pmax"]) {
      $(id).classList.toggle("activo", !!$(id).value);
    }
    const n = activos();
    $("#btn-filtros").innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M4 6h16M7 12h10M10 18h4" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>Filtros${n ? ` <b>${n}</b>` : ""}`;
    $("#btn-filtros").setAttribute("aria-expanded", estado.abierto);
    $("#panel").hidden = !estado.abierto;
    $("#f-orden").value = estado.orden;
  }

  function tarjeta(p) {
    const fotos = p.fotos.length
      ? `<div class="fotos">${p.fotos.map((f, i) => `<img src="${esc(f)}" alt="${esc(p.titulo)} — foto ${i + 1}" loading="lazy" decoding="async" onload="this.classList.add('cargada')" data-ampliar="${esc(p.codigo)}" data-i="${i}">`).join("")}</div>
         <button class="ampliar" data-ampliar="${esc(p.codigo)}" data-i="0" aria-label="Ampliar fotos">${ICONO_ZOOM}</button>
         ${p.fotos.length > 1 ? `<span class="contador">1/${p.fotos.length}</span>
         <button class="flecha izq" aria-label="Foto anterior">${FLECHA}</button><button class="flecha der" aria-label="Foto siguiente">${FLECHA}</button>` : ""}`
      : `<div class="sin-foto">${AUTO}<span>Foto a confirmar</span></div>`;
    const datos = [
      ["Años", p.anios || "Consultar"],
      ["También sirve para", p.compatibles.join(", ")],
      ["Estado", p.estado_txt],
      ["Origen", p.origen],
      ["Terminación", p.terminacion],
      ["N.º de parte", p.oem],
      ["Cantidad", p.cantidad > 1 ? `${p.cantidad} unidades` : ""],
    ].filter(([, v]) => v);
    const precio = p.precio
      ? `<span class="monto">${pesos(p.precio)}</span>${p.cantidad > 1 ? `<span class="por">c/u</span>` : ""}`
      : `<span class="consultar-precio">Consultar precio</span>`;
    const reservado = p.publicacion === "reservado";
    return `
    <article class="card${estado.solo === p.codigo ? " destacada" : ""}${reservado ? " reservada" : ""}" id="${esc(p.codigo)}">
      <div class="media">
        ${fotos}
        ${reservado ? `<span class="cinta">Reservado</span>` : ""}
      </div>
      <div class="cuerpo">
        <p class="codigo">Código <b>${esc(p.codigo)}</b></p>
        <h2>${esc(p.titulo)}</h2>
        <dl class="datos">${datos.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>
        ${p.caracteristicas.length ? `<ul class="tags">${p.caracteristicas.map((t) => {
          const no = /^sin /i.test(t);
          return `<li class="${no ? "no" : "si"}">${no ? ICONO_NO : ICONO_SI}${esc(t)}</li>`;
        }).join("")}</ul>` : ""}
        ${p.observaciones ? `<p class="detalle">${esc(p.observaciones)}</p>` : ""}
        <div class="precio"><div class="precio-linea">${precio}</div>
          ${reservado ? `<p class="aviso-reserva">Está reservado. Consultanos: si se libera, te avisamos.</p>` : ""}
        </div>
        <a class="btn btn-wa" href="${wa(p.wa)}" target="_blank" rel="noopener">${ICONO_WA}Consultar por WhatsApp</a>
        <button class="btn btn-compartir" data-compartir="${esc(p.codigo)}">${ICONO_COMPARTIR}Compartir</button>
      </div>
    </article>`;
  }

  function vacio() {
    const c = cat();
    const q = estado.q.trim();
    const texto = `Hola, estoy buscando ${c.singular}${q ? ` para ${q}` : ""}. ¿Tienen o les puede entrar?`;
    return `<div class="vacio">
      <h2>No encontramos ${esc(c.plural)} con esos datos</h2>
      <p>Probá con menos filtros o escribinos: si no lo tenemos, te avisamos apenas entre.</p>
      ${activos() || estado.posicion ? `<button class="btn btn-borde" data-limpiar>Limpiar filtros</button>` : ""}
      <a class="btn btn-wa" href="${wa(texto)}" target="_blank" rel="noopener">${ICONO_WA}Consultar por WhatsApp</a>
    </div>`;
  }

  function render() {
    renderControles();
    let lista;
    if (estado.solo) {
      const p = estado.datos.productos.find((x) => x.codigo === estado.solo);
      if (!p) { estado.solo = null; avisoVendido = true; return render(); }
      $("#aviso").innerHTML = `<div class="aviso"><p>Te compartieron este producto</p><button class="link-btn" data-ver-todo>Ver todo el stock</button></div>`;
      lista = [p];
    } else {
      $("#aviso").innerHTML = avisoVendido ? `<div class="aviso"><p>Ese producto ya se vendió 🙌 Mirá el resto del stock.</p></div>` : "";
      lista = ordenar(deTab(estado.tab).filter((p) => pasa(p)));
    }
    const hayFiltros = activos() || estado.posicion || estado.q.trim();
    $("#resultados").innerHTML = estado.solo ? "" : `<b>${lista.length}</b> ${lista.length === 1 ? "resultado" : "resultados"}${hayFiltros ? ` <button class="link-btn" data-limpiar>Limpiar filtros</button>` : ""}`;
    $("#lista").innerHTML = lista.length ? lista.map(tarjeta).join("") : vacio();
  }
  let avisoVendido = false;

  // ---------- galería ampliada ----------
  function abrirGaleria(codigo, i) {
    const p = estado.datos.productos.find((x) => x.codigo === codigo);
    if (!p || !p.fotos.length) return;
    const g = $("#galeria");
    g.querySelector(".g-fotos").innerHTML = p.fotos.map((f, k) => `<img src="${esc(f)}" alt="${esc(p.titulo)} — foto ${k + 1}">`).join("");
    g.querySelector(".g-titulo").textContent = `${p.codigo} · ${p.titulo}`;
    g.hidden = false;
    document.body.style.overflow = "hidden";
    const cont = g.querySelector(".g-fotos");
    requestAnimationFrame(() => { cont.scrollLeft = cont.clientWidth * i; contarGaleria(); });
    g.querySelector(".g-cerrar").focus();
  }
  function cerrarGaleria() {
    $("#galeria").hidden = true;
    document.body.style.overflow = "";
  }
  function contarGaleria() {
    const f = $("#galeria .g-fotos");
    $("#galeria .g-n").textContent = `${Math.round(f.scrollLeft / f.clientWidth) + 1}/${f.children.length}`;
  }

  // ---------- eventos ----------
  function avisar(txt) {
    const t = document.createElement("div");
    t.className = "toast"; t.textContent = txt;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2200);
  }
  function limpiar() { Object.assign(estado, structuredClone(VACIO)); $("#q").value = ""; estado.q = ""; }
  const salirFicha = () => { if (estado.solo) { estado.solo = null; history.replaceState(null, "", location.pathname); } avisoVendido = false; };

  document.addEventListener("click", async (e) => {
    const t = e.target;
    const tab = t.closest("[data-tab]");
    if (tab) { estado.tab = tab.dataset.tab; const q = estado.q; limpiar(); estado.q = q; $("#q").value = q; salirFicha(); return render(); }
    const chip = t.closest("[data-posicion]");
    if (chip) { estado.posicion = chip.dataset.posicion; salirFicha(); return render(); }
    if (t.closest("#btn-filtros")) { estado.abierto = !estado.abierto; return renderControles(); }
    if (t.closest("[data-limpiar]")) { limpiar(); salirFicha(); return render(); }
    if (t.closest("[data-ver-todo]")) { salirFicha(); return render(); }
    const amp = t.closest("[data-ampliar]");
    if (amp) return abrirGaleria(amp.dataset.ampliar, +amp.dataset.i);
    if (t.closest(".g-cerrar") || t.classList.contains("g-fotos")) return cerrarGaleria();
    const gf = t.closest(".g-flecha");
    if (gf) { const f = $("#galeria .g-fotos"); f.scrollBy({ left: (gf.classList.contains("der") ? 1 : -1) * f.clientWidth, behavior: "smooth" }); return; }
    const flecha = t.closest(".flecha");
    if (flecha) {
      const f = flecha.parentElement.querySelector(".fotos");
      f.scrollBy({ left: (flecha.classList.contains("der") ? 1 : -1) * f.clientWidth, behavior: "smooth" });
      return;
    }
    const comp = t.closest("[data-compartir]");
    if (comp) {
      const p = estado.datos.productos.find((x) => x.codigo === comp.dataset.compartir);
      const titulo = `${p.codigo} · ${p.titulo}`;
      if (navigator.share) {
        try { await navigator.share({ title: titulo, text: titulo, url: p.url }); } catch (_) {}
      } else {
        try { await navigator.clipboard.writeText(p.url); avisar("Link copiado"); }
        catch (_) { window.open(`https://wa.me/?text=${encodeURIComponent(titulo + " " + p.url)}`, "_blank"); }
      }
    }
  });
  document.addEventListener("keydown", (e) => {
    if ($("#galeria").hidden) return;
    if (e.key === "Escape") cerrarGaleria();
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      const f = $("#galeria .g-fotos");
      f.scrollBy({ left: (e.key === "ArrowRight" ? 1 : -1) * f.clientWidth, behavior: "smooth" });
    }
  });

  document.addEventListener("scroll", (e) => {
    const f = e.target;
    if (!(f instanceof Element)) return;
    if (f.classList.contains("g-fotos")) return contarGaleria();
    if (!f.classList.contains("fotos")) return;
    const c = f.parentElement.querySelector(".contador");
    if (c) c.textContent = `${Math.round(f.scrollLeft / f.clientWidth) + 1}/${f.children.length}`;
  }, true);

  document.addEventListener("change", (e) => {
    const t = e.target;
    const map = { "f-marca": "marca", "f-modelo": "modelo", "f-condicion": "condicion", "f-orden": "orden" };
    if (map[t.id]) {
      estado[map[t.id]] = t.value;
      if (t.id === "f-marca") estado.modelo = "";
    } else if (t.dataset.extra) {
      estado.extra[t.dataset.extra] = t.value;
    } else return;
    salirFicha(); render();
  });
  let espera;
  const enInput = (id, campo) => $(id).addEventListener("input", (e) => {
    clearTimeout(espera);
    espera = setTimeout(() => {
      estado[campo] = e.target.value.trim(); salirFicha();
      if (campo === "q") autoTab();
      render();
      const el = document.getElementById(id.slice(1)); el.focus(); // el panel se redibuja: no perder el cursor
    }, 250);
  });
  enInput("#q", "q"); enInput("#f-anio", "anio"); enInput("#f-pmin", "pmin"); enInput("#f-pmax", "pmax");
  $("#buscador").addEventListener("submit", (e) => {
    e.preventDefault();
    estado.q = $("#q").value; salirFicha(); autoTab(); render();
    $("#q").blur();
    $("#barra").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });

  // si la búsqueda no da nada en la pestaña actual pero sí en otra, cambia de pestaña
  function autoTab() {
    if (deTab(estado.tab).length) return;
    const otra = estado.datos.categorias.find((c) => deTab(c.id).length);
    if (otra) { estado.tab = otra.id; estado.extra = {}; estado.posicion = ""; }
  }

  // ---------- inicio ----------
  fetch("data/productos.json?t=" + Date.now(), { cache: "no-store" })
    .then((r) => r.json())
    .then((d) => {
      estado.datos = d;
      estado.solo = new URLSearchParams(location.search).get("p");
      const p = d.productos.find((x) => x.codigo === estado.solo);
      const cuantos = (c) => d.productos.filter((x) => x.categoria === c.id).length;
      estado.tab = p ? p.categoria : d.categorias.reduce((a, c) => (cuantos(c) > cuantos(a) ? c : a)).id;
      $("#wa-pie").href = wa("Hola, estoy buscando una pieza que no vi en el catálogo: ");
      render();
      if (p) setTimeout(() => $("#barra").scrollIntoView(), 50);
    })
    .catch(() => {
      $("#lista").innerHTML = '<p class="cargando">No se pudo cargar el stock. Probá recargar la página.</p>';
    });
})();
