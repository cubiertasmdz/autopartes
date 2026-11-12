"""Hoja de contacto de publicaciones. Uso: hoja.py items.json desde hasta salida.jpg carpeta_fotos"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
items = json.load(open(sys.argv[1])); a, b = int(sys.argv[2]), int(sys.argv[3])
f = ImageFont.truetype(str(Path(__file__).resolve().parent.parent / "fonts" / "Barlow-Medium.ttf"), 20)
W, H = 400, 300; rows = list(range(a, b + 1))
hoja = Image.new("RGB", (4 * W, ((len(rows) + 1) // 2) * (H + 26)), "white"); d = ImageDraw.Draw(hoja)
for k, i in enumerate(rows):
    it = items[i - 1]; x0, y = (k % 2) * 2 * W, (k // 2) * (H + 26)
    d.text((x0 + 4, y + 2), f'{i} {it["quien"]} {it["fecha"][10:15]}: {it["texto"][:42]}', font=f, fill="black")
    for j, fo in enumerate(it["fotos"][:2]):
        im = ImageOps.exif_transpose(Image.open(sys.argv[5] + "/" + fo))
        if im.height > im.width: im = im.transpose(Image.ROTATE_90)
        im.thumbnail((W - 6, H)); hoja.paste(im, (x0 + j * W + 2, y + 26))
hoja.save(sys.argv[4], quality=80)
