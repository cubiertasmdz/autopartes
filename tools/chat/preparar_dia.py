#!/usr/bin/env python3
"""Prepara la carga de un día del chat STOCK, todo guardado en el proyecto (no en carpetas temporales).

Uso:  .venv/bin/python -I tools/chat/preparar_dia.py "<export.zip>" DD-MM-AA

Crea entrada/AAAA-MM-DD/ con:
  chat/_chat.txt + solo las fotos de ese día   (el zip trae toda la historia: no se copia entero)
  items.json      (salida de parse_chat.py)
  hoja_N.jpg      (hojas de contacto: 36 publicaciones por hoja, 1.ª foto, "#i nNÚMERO")
  duplicados.txt  (fotos repetidas por md5 dentro del día y contra días anteriores; números repetidos)
Después: escribir entrada/AAAA-MM-DD/ajustes.json y correr armar_opticas.py con esa carpeta.
"""
import collections
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]


def md5(b):
    return hashlib.md5(b).hexdigest()


def main():
    zpath, dia = sys.argv[1], sys.argv[2]  # dia = DD-MM-AA
    dd, mm, aa = dia.split("-")
    iso = f"20{aa}-{mm}-{dd}"
    base = ROOT / "entrada" / iso
    chat = base / "chat"
    chat.mkdir(parents=True, exist_ok=True)
    clave = f"-20{aa}-{mm}-{dd}-"
    previos = set()
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            nombre = Path(n).name
            if nombre == "_chat.txt":
                (chat / "_chat.txt").write_bytes(z.read(n))
            elif nombre.lower().endswith((".jpg", ".jpeg", ".png")):
                datos = z.read(n)
                if clave in nombre:
                    (chat / nombre).write_bytes(datos)
                else:
                    previos.add(md5(datos))
    items = base / "items.json"
    subprocess.run([sys.executable, "-I", str(ROOT / "tools/chat/parse_chat.py"), str(chat / "_chat.txt"), str(items), dia], check=True)
    d = json.loads(items.read_text())

    # hojas de contacto
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 30)
    except OSError:
        f = ImageFont.load_default()
    W, H = 300, 400
    for k in range(0, len(d), 36):
        c = Image.new("RGB", (6 * W, 6 * H), "white")
        dr = ImageDraw.Draw(c)
        for j, x in enumerate(d[k:k + 36]):
            if not x["fotos"]:
                continue
            im = Image.open(chat / x["fotos"][0]).convert("RGB")
            im.thumbnail((W - 6, H - 6))
            X, Y = (j % 6) * W, (j // 6) * H
            c.paste(im, (X, Y))
            dr.rectangle([X, Y, X + 160, Y + 36], fill="yellow")
            dr.text((X + 4, Y + 2), f"#{k + j + 1} n{x['texto'][:6]}", font=f, fill="black")
        c.save(base / f"hoja_{k // 36}.jpg", quality=75)

    # duplicados
    h = collections.defaultdict(list)
    for i, x in enumerate(d, 1):
        for fn in x["fotos"]:
            h[md5((chat / fn).read_bytes())].append(i)
    cuenta = collections.Counter(x["texto"] for x in d)
    lineas = [
        "Fotos repetidas dentro del día: " + str([v for v in h.values() if len(v) > 1]),
        "Fotos repetidas con días anteriores: " + str([v for k, v in h.items() if k in previos]),
        "Números repetidos: " + str({t: [i for i, x in enumerate(d, 1) if x["texto"] == t] for t, c in cuenta.items() if c > 1}),
    ]
    (base / "duplicados.txt").write_text("\n".join(lineas) + "\n")
    print(base)
    print(len(d), "publicaciones")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
