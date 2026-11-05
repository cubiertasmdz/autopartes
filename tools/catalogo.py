#!/usr/bin/env python3
"""Herramienta del catálogo MZA AUTOPARTES (paragolpes, ópticas y parrillas).

Uso:  .venv/bin/python tools/catalogo.py <comando> [opciones]

Comandos:
  ver [texto] [--todos]              Lista productos (con datos internos). --todos incluye vendidos/ocultos.
  nuevo <archivo.json>               Carga un producto (o una lista de productos). Imprime los códigos.
  fotos <COD> <img...> [--reemplazar]  Comprime y copia fotos a fotos/<COD>/.
  sumar <COD> <n>                    Suma unidades (ingreso).
  reservar <COD> [--nota ".."]       Marca reservado (se sigue viendo con el cartel "Reservado").
  liberar <COD>                      Vuelve a disponible.
  venta <COD> [n] [--monto X] [--nota ".."]   Vende n (default 1). En 0 pasa a vendido y se oculta.
  precio <COD> <monto|no>            Cambia el precio (no = "Consultar precio").
  baja <COD> / alta <COD>            Oculta / vuelve a mostrar.
  editar <COD> campo=valor ...       Corrige datos (valor en JSON o texto; "a.b=valor" para un dato de categoría).
  build                              Genera los archivos públicos (data/, p/).
  resumen [--mes AAAA-MM]
  planilla | excel
  publicar "mensaje"                 build + commit + push.
"""
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV = ROOT / "privado"
STOCK = PRIV / "stock.json"
HIST = PRIV / "historial.json"
CONFIG = json.loads((ROOT / "tools" / "config.json").read_text())
FOTOS = ROOT / "fotos"
FONTS = ROOT / "tools" / "fonts"
PLANILLA = ROOT / "PLANILLA STOCK.xlsx"

# Lo que NUNCA sale al sitio público.
PRIVADOS = {"privado", "costo", "notas_privadas", "numero_interno", "proveedor", "prueba", "fuente"}


# ---------- datos ----------

def hoy():
    return dt.date.today()


def ahora():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def cargar():
    if not STOCK.exists():
        return {"siguiente": {}, "productos": []}
    return json.loads(STOCK.read_text())


def guardar(stock):
    PRIV.mkdir(exist_ok=True)
    STOCK.write_text(json.dumps(stock, ensure_ascii=False, indent=2) + "\n")


def historial():
    return json.loads(HIST.read_text()) if HIST.exists() else []


def registrar(tipo, p, cantidad=None, monto=None, detalle="", con_planilla=True):
    h = historial()
    h.append({"fecha": ahora(), "tipo": tipo, "codigo": p["codigo"], "producto": titulo(p),
              "cantidad": cantidad, "monto": monto, "detalle": detalle,
              "costo_unit": priv(p).get("costo"), "precio": p.get("precio")})
    PRIV.mkdir(exist_ok=True)
    HIST.write_text(json.dumps(h, ensure_ascii=False, indent=2) + "\n")
    if con_planilla:
        planilla()


def priv(p):
    return p.get("privado") or {}


def categoria(cat_id):
    for c in CONFIG["categorias"]:
        if c["id"] == cat_id:
            return c
    sys.exit(f"Categoría desconocida: {cat_id}")


def buscar(stock, cod):
    cod = cod.upper().replace(" ", "")
    if re.fullmatch(r"[A-Z]+\d+", cod):  # PG1 -> PG-001
        m = re.fullmatch(r"([A-Z]+)(\d+)", cod)
        cod = f"{m.group(1)}-{int(m.group(2)):03d}"
    for p in stock["productos"]:
        if p["codigo"] == cod:
            return p
    sys.exit(f"No existe el producto {cod}")


def pesos(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".") if n is not None else "—"


# ---------- textos ----------

def anios(p, sep="-"):
    d, h = p.get("anio_desde"), p.get("anio_hasta")
    if d and h and d != h:
        return f"{d}{sep}{h}"
    return str(d or h or "")


def pieza(p):
    """'Paragolpes trasero', 'Óptica delantera', 'Parrilla', 'Spoiler delantero'."""
    cat = categoria(p["categoria"])
    nombre = p.get("pieza") or cat["singular"].capitalize()
    pos = p.get("posicion") or ""
    if cat.get("femenino") and not p.get("pieza"):
        pos = {"delantero": "delantera", "trasero": "trasera"}.get(pos, pos)
    if p["categoria"] == "parrilla":
        pos = ""
    return " ".join(x for x in [nombre, pos] if x)


def titulo(p):
    return " ".join(x for x in [pieza(p), p.get("marca"), p.get("modelo")] if x)


def descripcion_corta(p):
    return " ".join(x for x in [titulo(p), anios(p)] if x)


def si_no(v, si, no):
    return si if v is True else no if v is False else None


def caracteristicas(p):
    """Etiquetas de la ficha y valores para los filtros propios de cada categoría."""
    c = p.get(p["categoria"]) or {}
    tags, filtros = [], {}

    def add(clave, texto, filtro=None):
        if texto:
            tags.append(texto)
            filtros[clave] = filtro or texto

    if p["categoria"] == "paragolpes":
        s = c.get("sensores")
        if s is True:
            add("sensores", "Con sensores" + (f' ({c["sensores_agujeros"]} agujeros)' if c.get("sensores_agujeros") else ""), "Con sensores")
        else:
            add("sensores", si_no(s, "", "Sin sensores"))
        a = c.get("antiniebla")
        if a is True:
            extra = {True: " (con rejillas/tapas)", False: " (sin rejillas/tapas)"}.get(c.get("antiniebla_incluye_rejillas"), "")
            add("antiniebla", "Con faros antiniebla" + extra, "Con faros antiniebla")
        else:
            add("antiniebla", si_no(a, "", "Sin faros antiniebla"))
        add("ojos_de_gato", si_no(c.get("ojos_de_gato"), "Con ojos de gato", "Sin ojos de gato"))
        add("lavafaros", si_no(c.get("lavafaros"), "Con lavafaros", None))
        add("camara", si_no(c.get("camara"), "Con lugar para cámara", None))
        add("gancho", si_no(c.get("gancho_remolque"), "Con agujero/tapa de gancho", None))
        add("molduras", si_no(c.get("molduras_cromadas"), "Con molduras cromadas", None))
        add("alma", si_no(c.get("alma_refuerzo"), "Incluye alma/refuerzo", None))
        add("rejillas", si_no(c.get("rejillas_inferiores"), "Incluye rejillas inferiores", "Sin rejillas inferiores"))
    elif p["categoria"] == "optica":
        lado = {"izquierdo": "Lado izquierdo (conductor)", "derecho": "Lado derecho (acompañante)"}.get(c.get("lado"))
        add("lado", lado, {"izquierdo": "Izquierda", "derecho": "Derecha"}.get(c.get("lado")))
        if p.get("posicion") == "delantero":
            luz = {"halógena": "Halógena", "xenón": "Xenón", "led": "LED"}.get((c.get("tipo_luz") or "").lower())
            add("tipo_luz", luz)
            add("drl", si_no(c.get("drl"), "Con luz diurna (DRL)", "Sin luz diurna"))
            add("motor", si_no(c.get("motor_regulacion"), "Con motor de regulación", "Sin motor de regulación"))
        else:
            add("ubicacion", {"exterior": "Exterior (en la carrocería)", "interior": "Interior (baúl/portón)"}.get(c.get("trasera_ubicacion")),
                {"exterior": "Exterior", "interior": "Interior"}.get(c.get("trasera_ubicacion")))
            add("tipo_luz", {"común": "Común", "comun": "Común", "led": "LED"}.get((c.get("trasera_tipo") or "").lower()))
        if c.get("soportes"):
            add("soportes", f'Soportes {c["soportes"]}')
        if c.get("lente"):
            add("lente", f'Lente {c["lente"]}')
        add("lamparas", si_no(c.get("incluye_lamparas_fichas"), "Incluye lámparas y fichas", "Sin lámparas ni fichas"))
    elif p["categoria"] == "parrilla":
        add("emblema", si_no(c.get("emblema"), "Con emblema", "Sin emblema"))
        add("camara_radar", si_no(c.get("camara_radar"), "Con lugar para cámara/radar", None))
        if c.get("terminacion"):
            add("terminacion_parrilla", c["terminacion"].capitalize())
    return tags, filtros


def visible(p):
    return p.get("activo", True) and p.get("publicacion", "disponible") != "vendido" and int(p.get("cantidad", 0)) > 0


# ---------- versión pública ----------

def fotos_de(p):
    carpeta = FOTOS / p["codigo"]
    if not carpeta.is_dir():
        return []
    def orden(f):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", f.name)]
    return [f"fotos/{p['codigo']}/{f.name}" for f in sorted(carpeta.iterdir(), key=orden)
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]


def publico(p):
    tags, filtros = caracteristicas(p)
    url = CONFIG["sitio_url"] + f'p/{p["codigo"]}/'
    estado_txt = None
    if p.get("condicion") == "nuevo":
        estado_txt = "Nuevo"
    elif p.get("condicion") == "usado":
        estado_txt = "Usado" + (": " + ", ".join(d.lower() for d in p.get("detalle_estado", [])) if p.get("detalle_estado") else "")
    terminacion = p.get("terminacion") or ""
    if p.get("color") and p["color"].lower() not in terminacion.lower():
        terminacion = f'{terminacion} ({p["color"]})' if terminacion else p["color"]
    return {
        "codigo": p["codigo"],
        "categoria": p["categoria"],
        "titulo": titulo(p),
        "posicion": p.get("posicion"),
        "marca": p.get("marca"),
        "modelo": p.get("modelo"),
        "version": p.get("version"),
        "anio_desde": p.get("anio_desde"),
        "anio_hasta": p.get("anio_hasta"),
        "anios": anios(p, "–"),
        "compatibles": p.get("compatibles", []),
        "origen": {"original": "Original", "alternativo": "Alternativo"}.get(p.get("origen")),
        "condicion": p.get("condicion"),
        "estado_txt": estado_txt,
        "terminacion": terminacion or None,
        "precio": p.get("precio"),
        "cantidad": int(p["cantidad"]),
        "publicacion": p.get("publicacion", "disponible"),
        "oem": p.get("oem"),
        "observaciones": p.get("observaciones") or "",
        "caracteristicas": tags,
        "filtros": filtros,
        "fotos": fotos_de(p),
        "alta": p.get("fecha_ingreso"),
        "wa": f"Hola, me interesa el producto {p['codigo']} - {descripcion_corta(p)}. ¿Sigue disponible?",
        "url": url,
    }


# ---------- build ----------

def esc(s):
    return html.escape(str(s), quote=True)


def pagina_compartir(p, pub):
    """Página chica por producto: vista previa en WhatsApp y redirige a la ficha."""
    base = CONFIG["sitio_url"]
    destino = f"../../?p={p['codigo']}"
    if pub:
        tit = f'{pub["titulo"]} {pub["anios"]}'.strip()
        desc = " · ".join(x for x in [pub["estado_txt"], pesos(pub["precio"]) if pub["precio"] else "Consultar precio",
                                       "Reservado" if pub["publicacion"] == "reservado" else ""] if x)
        img = base + pub["fotos"][0] if pub["fotos"] else base + "assets/og.jpg"
    else:
        tit, desc, img = CONFIG["titulo"], "Este producto ya no está disponible. Mirá el resto del stock.", base + "assets/og.jpg"
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>{esc(tit)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:type" content="product">
<meta property="og:title" content="{esc(tit)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(img)}">
<meta property="og:url" content="{esc(base + 'p/' + p['codigo'] + '/')}">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={destino}">
<script>location.replace("{destino}")</script>
</head><body><a href="{destino}">Ver producto</a></body></html>
"""


def og_imagen():
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (1200, 630), "#111111")
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(str(FONTS / "BarlowCondensed-Bold.ttf"), 112)
    mid = ImageFont.truetype(str(FONTS / "BarlowCondensed-Bold.ttf"), 58)
    small = ImageFont.truetype(str(FONTS / "Barlow-Medium.ttf"), 38)
    d.rectangle([0, 0, 1200, 18], fill="#FFC400")
    d.text((80, 100), "MZA AUTOPARTES\nCATÁLOGO", font=big, fill="white", spacing=4)
    d.text((80, 380), "PARAGOLPES, ÓPTICAS Y PARRILLAS USADAS", font=mid, fill="#FFC400")
    d.text((80, 490), CONFIG["ubicacion"] + (" · Hacemos envíos" if CONFIG.get("envios") else ""), font=small, fill="#BDBDBD")
    logo = Image.open(ROOT / "assets" / "logo.png").resize((220, 220), Image.LANCZOS)
    im.paste(logo, (900, 70), logo)
    im.save(ROOT / "assets" / "og.jpg", quality=82, optimize=True, progressive=True)


def build(silencioso=False):
    stock = cargar()
    productos = [publico(p) for p in stock["productos"] if visible(p)]
    productos.sort(key=lambda x: (x["alta"] or "", x["codigo"]), reverse=True)
    salida = {
        "actualizado": ahora(),
        "sitio": {k: CONFIG[k] for k in ["titulo", "whatsapp", "whatsapp_visible", "ubicacion", "envios", "sitio_url"]},
        "categorias": [{k: c[k] for k in ["id", "prefijo", "nombre", "singular", "plural"]} for c in CONFIG["categorias"]],
        "productos": productos,
    }
    texto = json.dumps(salida, ensure_ascii=False, indent=1)
    for campo in PRIVADOS:  # control de seguridad
        if f'"{campo}"' in texto:
            sys.exit(f"ERROR: el campo privado '{campo}' iba a publicarse. Cancelado.")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "productos.json").write_text(texto + "\n")
    carpeta = ROOT / "p"
    shutil.rmtree(carpeta, ignore_errors=True)
    pubs = {x["codigo"]: x for x in productos}
    for p in stock["productos"]:
        d = carpeta / p["codigo"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(pagina_compartir(p, pubs.get(p["codigo"])))
    if not (ROOT / "assets" / "og.jpg").exists():
        og_imagen()
    if not silencioso:
        print(f"Build OK: {len(productos)} productos visibles.")


# ---------- fotos ----------

def procesar_fotos(cod, rutas, reemplazar=False, stock=None):
    from PIL import Image, ImageOps
    stock_propio = stock is None
    stock = stock or cargar()
    p = buscar(stock, cod)
    carpeta = FOTOS / p["codigo"]
    if reemplazar:
        shutil.rmtree(carpeta, ignore_errors=True)
    carpeta.mkdir(parents=True, exist_ok=True)
    n = max([int(f.stem) for f in carpeta.glob("*.jpg") if f.stem.isdigit()], default=0)
    for ruta in rutas:
        n += 1
        im = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")  # endereza y descarta EXIF (GPS, etc.)
        im.thumbnail((1280, 1280), Image.LANCZOS)
        destino = carpeta / f"{n}.jpg"
        im.save(destino, "JPEG", quality=72, optimize=True, progressive=True)
        print(f"fotos/{p['codigo']}/{destino.name}  {destino.stat().st_size // 1024} KB")
    if stock_propio:
        guardar(stock)


# ---------- movimientos ----------

def opciones(args):
    pos, op, i = [], {}, 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                op[a[2:]] = args[i + 1]
                i += 2
            else:
                op[a[2:]] = True
                i += 1
        else:
            pos.append(a)
            i += 1
    return pos, op


def num(s):
    return float(str(s).replace("$", "").replace(".", "").replace(",", "."))


def cmd_nuevo(ruta):
    datos = json.loads(Path(ruta).read_text())
    lista = datos if isinstance(datos, list) else [datos]
    stock = cargar()
    for d in lista:
        cat = categoria(d["categoria"])
        sig = stock.setdefault("siguiente", {})
        n = sig.get(cat["prefijo"], 1)
        sig[cat["prefijo"]] = n + 1
        d = {"codigo": f'{cat["prefijo"]}-{n:03d}', **d}
        fotos = d.pop("fotos_origen", [])
        d.setdefault("cantidad", 1)
        d.setdefault("publicacion", "disponible")
        d.setdefault("activo", True)
        d.setdefault("fecha_ingreso", hoy().isoformat())
        stock["productos"].append(d)
        if fotos:
            procesar_fotos(d["codigo"], fotos, stock=stock)
        registrar("ingreso", d, int(d["cantidad"]),
                  int(d["cantidad"]) * priv(d)["costo"] if priv(d).get("costo") else None,
                  f'Alta. {pesos(d.get("precio")) if d.get("precio") else "Consultar precio"}', con_planilla=False)
        print(d["codigo"], titulo(d))
    guardar(stock)
    planilla()


def cmd_sumar(cod, n):
    stock = cargar()
    p = buscar(stock, cod)
    p["cantidad"] = int(p["cantidad"]) + int(n)
    if p.get("publicacion") == "vendido":
        p["publicacion"] = "disponible"
    guardar(stock)
    registrar("ingreso", p, int(n), None, f'Se suman. Ahora hay {p["cantidad"]}')
    print(f'{p["codigo"]}: ahora {p["cantidad"]}')


def cmd_publicacion(cod, estado, op):
    stock = cargar()
    p = buscar(stock, cod)
    p["publicacion"] = estado
    guardar(stock)
    registrar({"reservado": "reserva", "disponible": "liberado"}[estado], p, None, None, op.get("nota", ""))
    print(f'{p["codigo"]}: {estado}')


def cmd_venta(cod, n, op):
    stock = cargar()
    p = buscar(stock, cod)
    n = int(n)
    if n > int(p["cantidad"]):
        sys.exit(f'Solo hay {p["cantidad"]} de {p["codigo"]}')
    monto = num(op["monto"]) if "monto" in op else (n * p["precio"] if p.get("precio") else None)
    p["cantidad"] = int(p["cantidad"]) - n
    if p["cantidad"] == 0:
        p["publicacion"] = "vendido"
    elif p.get("publicacion") == "reservado":
        p["publicacion"] = "disponible"
    guardar(stock)
    registrar("venta", p, n, monto, op.get("nota", "") + (" — vendido, se oculta" if p["cantidad"] == 0 else ""))
    print(f'{p["codigo"]}: vendidas {n} por {pesos(monto)}. Quedan {p["cantidad"]}.')


def cmd_precio(cod, valor):
    stock = cargar()
    p = buscar(stock, cod)
    antes = p.get("precio")
    if valor in ("no", "0", "consultar"):
        p.pop("precio", None)
    else:
        p["precio"] = num(valor)
    guardar(stock)
    registrar("precio", p, None, None, f'{pesos(antes)} → {pesos(p.get("precio"))}')
    print(f'{p["codigo"]}: {pesos(antes)} → {pesos(p.get("precio"))}')


def cmd_activo(cod, activo):
    stock = cargar()
    p = buscar(stock, cod)
    p["activo"] = activo
    guardar(stock)
    registrar("alta" if activo else "baja", p)
    print(f'{p["codigo"]}: {"visible" if activo else "oculto"}')


def cmd_editar(cod, pares):
    stock = cargar()
    p = buscar(stock, cod)
    cambios = []
    for par in pares:
        k, v = par.split("=", 1)
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            pass
        destino, claves = p, k.split(".")
        for c in claves[:-1]:
            destino = destino.setdefault(c, {})
        if v is None:
            destino.pop(claves[-1], None)
        else:
            destino[claves[-1]] = v
        cambios.append(f"{k}={v}")
    guardar(stock)
    registrar("edicion", p, None, None, "; ".join(cambios))
    print(f'{p["codigo"]}: ' + "; ".join(cambios))


def cmd_ver(texto, todos):
    for p in cargar()["productos"]:
        if not todos and not visible(p):
            continue
        if texto and texto.lower() not in json.dumps(p, ensure_ascii=False).lower():
            continue
        tags, _ = caracteristicas(p)
        print(f'{p["codigo"]}  {descripcion_corta(p):48s} n.º int {priv(p).get("numero_interno") or "-":6}'
              f' {pesos(p.get("precio")) if p.get("precio") else "consultar":>10}  {p.get("publicacion")}'
              f'  fotos {len(fotos_de(p))}  {", ".join(tags)}')


def cmd_resumen(mes):
    stock = cargar()
    vis = [p for p in stock["productos"] if visible(p)]
    print(f"RESUMEN — {hoy().strftime('%d/%m/%Y')}\n")
    for cat in CONFIG["categorias"]:
        ps = [p for p in vis if p["categoria"] == cat["id"]]
        if ps:
            print(f'{cat["nombre"].upper()}: {len(ps)} publicados ({sum(p.get("publicacion") == "reservado" for p in ps)} reservados), '
                  f'{sum(int(p["cantidad"]) for p in ps)} unidades, valor {pesos(sum(int(p["cantidad"]) * (p.get("precio") or 0) for p in ps))}, '
                  f'{sum(not p.get("precio") for p in ps)} sin precio')
    mes = mes or hoy().strftime("%Y-%m")
    ventas = [h for h in historial() if h["tipo"] == "venta" and h["fecha"].startswith(mes)]
    print(f"\nVENTAS DE {mes}: {len(ventas)} operaciones, {pesos(sum(h['monto'] or 0 for h in ventas))}")
    for h in ventas:
        print(f'   {h["fecha"][:10]}  {h["codigo"]} {h["producto"]} — {pesos(h["monto"])}')


def planilla(destino=None):
    """Planilla Excel: stock (mismos datos que la web + privados), movimientos y resumen."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    stock, hist, wb = cargar(), historial(), Workbook()

    def hoja(ws, cols, filas, dinero=()):
        ws.append(cols)
        for f in filas:
            ws.append(f)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="111111")
            c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[1].height = 32
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions
        for i, col in enumerate(ws.columns, 1):
            ws.column_dimensions[get_column_letter(i)].width = min(42, max(10, max(len(str(c.value or "")) for c in col) + 2))
            if cols[i - 1] in dinero:
                for c in col[1:]:
                    c.number_format = '"$"#,##0'

    vendidas, ultima = {}, {}
    for m in hist:
        if m["tipo"] == "venta":
            vendidas[m["codigo"]] = vendidas.get(m["codigo"], 0) + (m["cantidad"] or 0)
            ultima[m["codigo"]] = m["fecha"][:10]
    cols = ["Código", "N.º interno", "Categoría", "Pieza", "Marca", "Modelo", "Versión", "Años", "Compatibles",
            "Original / Alt.", "Condición", "Detalle estado", "Terminación / color", "Características", "OEM",
            "Observaciones (web)", "Publicación", "En la web", "Stock", "Vendidas", "Costo c/u", "Precio",
            "Ganancia c/u", "Fotos", "Fecha ingreso", "Última venta", "Link", "Notas privadas", "Origen del dato"]
    filas = []
    for p in stock["productos"]:
        pub = publico(p)
        pr = priv(p)
        filas.append([
            p["codigo"], pr.get("numero_interno"), categoria(p["categoria"])["singular"].capitalize(), pieza(p),
            p.get("marca"), p.get("modelo"), p.get("version"), anios(p), ", ".join(p.get("compatibles", [])) or None,
            pub["origen"], p.get("condicion"), ", ".join(p.get("detalle_estado", [])) or None, pub["terminacion"],
            ", ".join(pub["caracteristicas"]) or None, p.get("oem"), p.get("observaciones"),
            p.get("publicacion"), "Sí" if visible(p) else "No", int(p["cantidad"]), vendidas.get(p["codigo"], 0),
            pr.get("costo"), p.get("precio"),
            p["precio"] - pr["costo"] if p.get("precio") and pr.get("costo") else None,
            len(pub["fotos"]), p.get("fecha_ingreso"), ultima.get(p["codigo"]), pub["url"], pr.get("notas"), pr.get("fuente"),
        ])
    ws = wb.active
    ws.title = "Stock"
    hoja(ws, cols, filas, dinero={"Costo c/u", "Precio", "Ganancia c/u"})
    gris = PatternFill("solid", fgColor="E6E6E6")
    for fila in ws.iter_rows(min_row=2):
        if fila[17].value == "No":
            for c in fila:
                c.fill = gris

    nombres = {"ingreso": "INGRESO", "venta": "VENTA", "reserva": "RESERVA", "liberado": "VUELVE A DISPONIBLE",
               "baja": "BAJA", "alta": "ALTA", "precio": "Cambio de precio", "edicion": "Corrección"}
    filas = [[m["fecha"], nombres.get(m["tipo"], m["tipo"]), m["codigo"], m["producto"], m.get("cantidad"), m.get("monto"),
              m.get("costo_unit"), (m["monto"] - (m["cantidad"] or 1) * m["costo_unit"]) if m["tipo"] == "venta" and m.get("monto") and m.get("costo_unit") else None,
              m.get("detalle")] for m in hist]
    hoja(wb.create_sheet("Movimientos"), ["Fecha", "Movimiento", "Código", "Producto", "Cantidad", "Monto", "Costo c/u", "Ganancia", "Detalle"],
         filas, dinero={"Monto", "Costo c/u", "Ganancia"})

    vis = [p for p in stock["productos"] if visible(p)]
    mes = hoy().strftime("%Y-%m")
    vm = [m for m in hist if m["tipo"] == "venta" and m["fecha"].startswith(mes)]
    filas = [["Actualizado", ahora()],
             ["Publicados", len(vis)],
             ["Reservados", sum(p.get("publicacion") == "reservado" for p in vis)],
             ["Sin precio", sum(not p.get("precio") for p in vis)],
             ["Valor del stock (precio de venta)", sum(int(p["cantidad"]) * (p.get("precio") or 0) for p in vis)],
             [f"Ventas de {mes} (cantidad)", sum(m["cantidad"] or 0 for m in vm)],
             [f"Ventas de {mes} (monto)", sum(m["monto"] or 0 for m in vm)]]
    for cat in CONFIG["categorias"]:
        filas.append([f'{cat["nombre"]} publicados', sum(p["categoria"] == cat["id"] for p in vis)])
    r = wb.create_sheet("Resumen", 0)
    hoja(r, ["Dato", "Valor"], filas)
    r.column_dimensions["A"].width, r.column_dimensions["B"].width = 38, 28
    for fila in r.iter_rows(min_row=2):
        if "Valor" in fila[0].value or "monto" in fila[0].value:
            fila[1].number_format = '"$"#,##0'
    destino = destino or PLANILLA
    try:
        wb.save(destino)
    except PermissionError:
        alt = destino.with_name(destino.stem + " (nueva).xlsx")
        wb.save(alt)
        print(f"AVISO: la planilla estaba abierta; se guardó como {alt.name}")
    return destino


def cmd_excel():
    (ROOT / "exportes").mkdir(exist_ok=True)
    ruta = planilla(ROOT / "exportes" / f"stock-{dt.datetime.now().strftime('%Y-%m-%d_%H%M')}.xlsx")
    planilla()
    print(ruta)


def cmd_publicar(mensaje):
    build()
    def git(*a, check=True):
        return subprocess.run(["git", *a], cwd=ROOT, check=check, capture_output=True, text=True)
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("Sin cambios para publicar.")
        return
    git("commit", "-m", mensaje)
    r = git("push", check=False)
    if r.returncode:
        sys.exit("ERROR al publicar:\n" + r.stderr)
    print("Publicado:", mensaje)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, (pos, op) = sys.argv[1], opciones(sys.argv[2:])
    acciones = {
        "ver": lambda: cmd_ver(pos[0] if pos else "", op.get("todos")),
        "nuevo": lambda: cmd_nuevo(pos[0]),
        "fotos": lambda: procesar_fotos(pos[0], pos[1:], op.get("reemplazar")),
        "sumar": lambda: cmd_sumar(pos[0], pos[1]),
        "reservar": lambda: cmd_publicacion(pos[0], "reservado", op),
        "liberar": lambda: cmd_publicacion(pos[0], "disponible", op),
        "venta": lambda: cmd_venta(pos[0], pos[1] if len(pos) > 1 else 1, op),
        "precio": lambda: cmd_precio(pos[0], pos[1]),
        "baja": lambda: cmd_activo(pos[0], False),
        "alta": lambda: cmd_activo(pos[0], True),
        "editar": lambda: cmd_editar(pos[0], pos[1:]),
        "build": build,
        "resumen": lambda: cmd_resumen(op.get("mes")),
        "planilla": lambda: print(planilla()),
        "excel": cmd_excel,
        "og": og_imagen,
        "publicar": lambda: cmd_publicar(pos[0] if pos else "Actualización del catálogo"),
    }
    acciones.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
