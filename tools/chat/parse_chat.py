"""Separa un export de WhatsApp en publicaciones (texto + fotos).
Uso: parse_chat.py _chat.txt salida.json [DD-MM-AA]"""
import re, json, sys
txt = open(sys.argv[1], encoding="utf-8").read().replace("\u200e", "").replace("\r", "")
msgs = re.split(r"\n(?=\[\d\d-\d\d-\d\d, \d\d:\d\d:\d\d\] )", txt)
items = []
for m in msgs:
    h = re.match(r"\[(.+?)\] (.+?):\s?(.*)", m, re.S)
    if not h: continue
    fecha, quien, cuerpo = h.groups()
    if len(sys.argv) > 3 and not fecha.startswith(sys.argv[3]): continue
    fotos = re.findall(r"<adjunto: (.+?)>", cuerpo)
    texto = re.sub(r"<adjunto: .+?>", "", cuerpo).strip()
    if not fotos:
        if texto and "Eliminaste" not in texto: print("   (solo texto)", quien, fecha[10:15], texto.replace("\n", " / "))
        continue
    if texto:
        items.append({"quien": quien, "fecha": fecha, "texto": " / ".join(l.strip() for l in texto.splitlines() if l.strip()), "fotos": fotos})
    elif items and items[-1]["quien"] == quien:
        items[-1]["fotos"] += fotos
    else:
        items.append({"quien": quien, "fecha": fecha, "texto": "", "fotos": fotos})
json.dump(items, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
for i, it in enumerate(items, 1):
    print(f'{i:3d} {it["quien"][:6]:6s} {it["fecha"][10:15]} {len(it["fotos"])}f  {it["texto"]}')
