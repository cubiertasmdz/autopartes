#!/usr/bin/env python3
"""Arma el JSON para `catalogo.py nuevo` con las ópticas/faros posteados en el chat STOCK.

Uso:
  .venv/bin/python tools/chat/armar_opticas.py items.json carpeta_fotos DD/MM/AA salida.json [ajustes.json]

items.json  = salida de parse_chat.py (lista de {quien, fecha, texto, fotos}).
ajustes.json (opcional):
  {"skip": [n.º publicación...],            # no cargar (llantas, sin número, etc.)
   "corr": {"21": 345},                       # publicación -> n.º real (etiqueta de la foto)
   "traseros": [n.º publicación...],          # lente rojo/ahumado -> hoja FAROS TRASEROS (el resto = OPTICAS)
   "merge": {"32": 27},                       # SOLO si foto y número son iguales (ver regla en CLAUDE.md)
   "solo_primera_foto": [n.º publicación...],
   "notas": {"21": "chat decía 348, etiqueta 345"}}
Reglas: blanco/transparente = OPTICAS (delantera); rojo = FAROS TRASEROS. Fotos distintas con el mismo número -> se publican aparte.
"""
import datetime
import json
import re
import sys
from pathlib import Path

import openpyxl

EXCEL = Path.home() / "Downloads" / "Stock 2026.xlsx"
MARCAS = {"CITROEN": "Citroën", "BMW": "BMW", "RE": "Renault", "MERCEDES": "Mercedes-Benz", "VW": "Volkswagen", "": "Volkswagen"}
PREFIJOS = ("PEUGEOT ", "FIAT ", "FORD ", "TOYOTA ", "CHEVROLET ", "VOLKSWAGEN ", "RENAULT ", "HONDA ", "NISSAN ", "CITROEN ", "AUDI ", "MERCEDES ", "IVECO ", "KIA ", "HYUNDAI ", "JEEP ", "HONDA ")
# modelo del Excel -> (modelo público, observación)
MOD = {
    "PEUGEOT 208": ("208", None), "PEUGEOT 2008": ("2008", None), "PEUGEOT 308": ("308", None), "PEUGEOT 207": ("207", None),
    "PEUGEOT 206": ("206", None), "PEUGEOT 307": ("307", None), "PEUGEOT 408": ("408", None), "PEUGEOT 3008": ("3008", None),
    "PEUGEOT EXPERT": ("Expert", None), "BOXER": ("Boxer", None), "PARTNER": ("Partner", None), "PARTNER HDI": ("Partner", "Versión HDi."),
    "BERINGO": ("Berlingo", None), "BERLINGO": ("Berlingo", None),
    "FIAT PUNTO": ("Punto", None), "FIAT UNO WAY": ("Uno Way", None), "FIAT MOBI": ("Mobi", None), "FIAT TORO": ("Toro", None),
    "FIAT LINEA": ("Linea", None), "FIAT CUBO": ("Qubo", None), "GRAND SIENA": ("Grand Siena", None), "STRADA": ("Strada", None),
    "CRONOS": ("Cronos", None), "SIENA F4": ("Siena", "Versión F4 (Fire)."), "PALIO": ("Palio", None),
    "PALIO NOVO 326": ("Palio", "Palio Novo (326)."), "FIORINO/UNO": ("Fiorino", "También va en Uno (mismo modelo de óptica)."),
    "FIORINO": ("Fiorino", None), "REGATA": ("Regata", None),
    "CLIO 2": ("Clio", "Clio II."), "CLIO MIO": ("Clio Mío", None), "CLIO SPORT": ("Clio", "Versión Clio Sport."),
    "KANGOO 3": ("Kangoo", "Kangoo III."), "KANGOO": ("Kangoo", None), "MEGANE 3": ("Megane", "Megane III."), "CAPTUR": ("Captur", None),
    "FLUENCE GTI": ("Fluence", "Versión GT."), "SANDERO": ("Sandero", None), "KWID": ("Kwid", None), "DUSTER": ("Duster", None),
    "LOGAN 2": ("Logan", "Logan II."), "LOGAN": ("Logan", None), "LOGAN / SANDERO": ("Logan", "También va en Sandero (mismo modelo de óptica)."),
    "RENAULT 19": ("19", None),
    "FOCUS 3 FASE 2": ("Focus", "Focus III fase 2."), "FOCUS 2": ("Focus", "Focus II."), "FOCUS TITANIUM": ("Focus", "Versión Titanium."),
    "FOCUS 1 F2": ("Focus", "Focus I fase 2."), "FIESTA MAX AMBIENTE": ("Fiesta Max", "Versión Ambiente."),
    "FIESTA KD": ("Fiesta", "Fiesta Kinetic Design."), "FIESTA": ("Fiesta", "Fiesta Kinetic Design."),
    "FIESTA KD MEXICANO": ("Fiesta", "Fiesta Kinetic Design (mexicano)."), "FIESTA ONE": ("Fiesta One", None),
    "ECOSPORT KD": ("EcoSport", "EcoSport Kinetic Design."), "ECOSPORT": ("EcoSport", None), "ECOSPORT FASE 2": ("EcoSport", "EcoSport fase 2."),
    "RAPTOR": ("Ranger Raptor", None), "KUGA MKS": ("Kuga", None), "TERRITORY": ("Territory", None), "RANGER": ("Ranger", None),
    "RANGER FULL": ("Ranger", "Versión full."), "RANGER BASE": ("Ranger", "Versión base."), "MONDEO": ("Mondeo", None),
    "FORD KA": ("Ka", None), "FORD KA KD": ("Ka", "Ka Kinetic Design."), "FORD KA VIRAL": ("Ka", "Ka Viral."), "FORD KA TATOO": ("Ka", "Ka Tattoo."),
    "C4": ("C4", None), "C3": ("C3", None), "XSARA PICASSO": ("Xsara Picasso", None), "C3 AIRCROSS": ("C3 Aircross", None), "C4 LOUNGE": ("C4 Lounge", None),
    "SENTRA": ("Sentra", None), "ONIX": ("Onix", None), "PRISMA": ("Prisma", None),
    "HRV": ("HR-V", None), "HRC": ("HR-V", None), "CRV": ("CR-V", None), "S1": ("Serie 1", None), "SWA": ("SW4", None), "SW4": ("SW4", None),
    "500": ("500", None), "COROLLA CROSS": ("Corolla Cross", None), "GOL TREND": ("Gol Trend", None), "GOL AB9": ("Gol", "Gol AB9."),
    "UP!": ("Up!", None), "UP": ("Up!", None), "CELYSEE": ("C-Elysée", None), "SUZUKI FUN": ("Fun", "Chevrolet Suzuki Fun."),
    "FOX/VOYAGE": ("Fox", "También va en Voyage (mismo modelo de óptica)."), "POLO MSI": ("Polo", "Versión MSI."), "RAV 4": ("RAV4", None),
    "I10": ("i10", None), "W168 CLASE A": ("Clase A", "W168."), "E 350": ("Clase E", "E 350."), "E 400": ("Clase E", "E 400."),
    "B200": ("Clase B", "B200."), "SPRINTER": ("Sprinter", None), "VITO": ("Vito", None), "T-CROSS": ("T-Cross", None), "CR-V": ("CR-V", None), "HR-V": ("HR-V", None),
}


def num(x):
    try:
        return int(float(str(x).strip()))
    except (TypeError, ValueError):
        return None


def hojas():
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    O, F = {}, {}
    for r in wb["OPTICAS"].iter_rows(min_row=2, values_only=True):
        if num(r[0]) is not None:
            O[num(r[0])] = r[1:6]  # marca, modelo, lado, linea, obs
    for r in wb["FAROS TRASEROS"].iter_rows(min_row=2, values_only=True):
        if num(r[4]) is not None:
            F[num(r[4])] = r[:4]  # marca, modelo, int/ext, lado
    return O, F


def anios(l):
    if l is None:
        return None, None
    if isinstance(l, datetime.datetime):
        return l.year, 2000 + l.month
    s = str(l).strip().removesuffix(".0")
    m = re.match(r"^(\d{2,4})(?:/(\d{2,4}))?$", s)
    if not m:
        return None, None
    def y(v):
        v = int(v)
        return v if v > 1900 else (1900 + v if v > 50 else 2000 + v)
    a = y(m.group(1))
    b = y(m.group(2)) if m.group(2) else a
    return min(a, b), max(a, b)


def modelo(mod):
    """'SW4 L/05' -> ('SW4', 'Línea 2005', obs)."""
    m = str(mod).strip().removesuffix(".0").replace("L/|9", "L/19")
    ver = None
    mm = re.search(r"\s*L/(\w+)$", m)
    if mm:
        t = mm.group(1)
        m = m[:mm.start()]
        ver = {"N": "Línea nueva", "V": "Línea vieja"}.get(t) or (f"Línea {(1900 if int(t) > 50 else 2000) + int(t)}" if t.isdigit() else None)
    obs = None
    if m.startswith("ETIOS") and "COLA" in m:
        obs = "Versión sedán (con baúl)." if "CON COLA" in m else "Versión hatchback (cola corta)."
        m = "ETIOS"
    if m in MOD:
        mod_pub, nota = MOD[m]
    else:
        for pre in PREFIJOS:
            if m.startswith(pre):
                m = m[len(pre):]
                break
        mod_pub, nota = MOD.get(m) or (" ".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in m.split()), None)
    return mod_pub, ver, obs or nota


def marca_pub(m):
    m = str(m or "").strip()
    return MARCAS.get(m, m.capitalize())


def main():
    items, carpeta, fecha, salida = sys.argv[1:5]
    aj = json.loads(Path(sys.argv[5]).read_text()) if len(sys.argv) > 5 else {}
    skip = set(aj.get("skip", []))
    corr = {int(k): v for k, v in aj.get("corr", {}).items()}
    traseros = set(aj.get("traseros", []))
    merge = {int(k): v for k, v in aj.get("merge", {}).items()}
    primera = set(aj.get("solo_primera_foto", []))
    notas = {int(k): v for k, v in aj.get("notas", {}).items()}
    O, F = hojas()
    d = json.loads(Path(items).read_text())
    dd, mm_, aa = fecha.split("/")
    fiso = f"20{aa}-{mm_}-{dd}"
    out = {}
    for i, x in enumerate(d, 1):
        if i in skip:
            continue
        fotos = [str(Path(carpeta) / f) for f in (x["fotos"][:1] if i in primera else x["fotos"])]
        hora = x["fecha"][-8:-3]
        if merge.get(i) in out:
            out[merge[i]]["fotos_origen"] += fotos
            continue
        n = corr.get(i) or num(x["texto"])
        if n is None:
            sys.exit(f"#{i} sin número: agregarlo a skip o corr")
        trasero = i in traseros
        fila = (F if trasero else O).get(n)
        if fila is None:
            sys.exit(f"#{i} n.º {n} no está en la hoja {'FAROS TRASEROS' if trasero else 'OPTICAS'}")
        p = {"categoria": "optica", "posicion": "trasero" if trasero else "delantero", "condicion": "usado", "cantidad": 1}
        if trasero:
            marca, mod, tipo, lado = fila
            mod_pub, ver, obs = modelo(mod)
            p.update(marca=marca_pub(marca), modelo=mod_pub)
            op = {}
            if lado:
                op["lado"] = {"IZQ": "izquierdo", "DER": "derecho"}[str(lado).strip()]
            tipo = str(tipo).strip().upper()
            if tipo in ("INTERIOR", "EXTERIOR"):
                p["pieza"] = "Faro"
                op["trasera_ubicacion"] = tipo.lower()
            elif tipo == "GUIÑE":
                p["pieza"], p["posicion"], obs = "Guiño", "delantero", "Guiño de esquina color ámbar."
            elif tipo == "ANTINIEBLA":
                p["pieza"], obs = "Faro antiniebla", "Va en el paragolpes trasero."
            elif tipo == "TERCER STOP":
                p["pieza"] = "Tercer stop"
            else:
                sys.exit(f"#{i} tipo raro en FAROS: {tipo}")
            hoja = "FAROS TRASEROS"
            interno = f"Faro {n}"
        else:
            marca, mod, lado, linea, ob = fila
            if mod is None:
                sys.exit(f"#{i} n.º {n}: fila vacía en OPTICAS (agregar a skip)")
            mod_pub, ver, obs = modelo(mod)
            op = {"lado": {"IZQ": "izquierdo", "DER": "derecho"}[str(lado).strip()]} if lado else {}
            p.update(marca=marca_pub(marca), modelo=mod_pub)
            if str(mod).strip() == "SEAT":  # el Excel dice VOLKSWAGEN / SEAT
                p.update(marca="Seat", modelo=None)
                obs = "Consultanos con tu auto y te confirmamos si va."
            a, b = anios(linea)
            if a:
                p["anio_desde"], p["anio_hasta"] = a, b
            if str(linea).strip() in ("L/V", "L/N"):
                ver = {"L/V": "Línea vieja", "L/N": "Línea nueva"}[str(linea).strip()]
            et, det = [], []
            o = (ob or "").upper()
            if "HALOGENA" in o:
                op["tipo_luz"] = "halógena"
            for clave, txt in (("LUPA", "Con lupa"), ("FONDO NEGRO", "Fondo negro"), ("FONDO CROMADO", "Fondo cromado"),
                               ("ARO NEGRO", "Aro negro"), ("LED", "Con LED"), ("NARANJA", "Giro naranja")):
                if clave in o:
                    et.append(txt)
            if "SUPERIOR" in o:
                p["pieza"] = "Faro superior"
            if "INFERIOR" in o:
                p["pieza"] = "Faro inferior"
            if "ANTINIEBLA" in o:
                p["pieza"] = "Faro antiniebla"
            if "CARCASA" in o:
                det.append("Detalle en la carcasa")
            if "SOPORTE" in o:
                det.append("Detalle en soporte")
            if "ACRILICO" in o:
                det.append("Detalle en el acrílico")
            if o.strip() == "DETALLES":
                det.append("Tiene detalles (ver fotos)")
            if et:
                p["etiquetas"] = et
            if det:
                p["detalle_estado"] = det
            hoja = "OPTICAS"
            interno = f"Óptica {n}"
        if ver:
            p["version"] = ver
        p["optica"] = op
        if obs:
            p["observaciones"] = obs
        fuente = f"Chat STOCK {fecha} #{i} ({x['quien']} {hora}) + Excel Stock 2026 hoja {hoja} n.º {n}"
        if i in notas:
            fuente += f" ({notas[i]})"
        p["privado"] = {"numero_interno": interno, "fuente": fuente}
        p["fecha_ingreso"] = fiso
        p["fotos_origen"] = fotos
        out[i] = p
    lista = list(out.values())
    Path(salida).write_text(json.dumps(lista, ensure_ascii=False, indent=1))
    print(len(lista), "piezas")
    for p in lista:
        print(p["privado"]["numero_interno"], p.get("pieza") or "", p["posicion"], p["marca"], p["modelo"], p.get("version") or "",
              p.get("anio_desde") or "", p.get("anio_hasta") or "", p["optica"].get("lado", ""), p.get("etiquetas") or "",
              p.get("detalle_estado") or "", p.get("observaciones") or "", len(p["fotos_origen"]))


if __name__ == "__main__":
    main()
