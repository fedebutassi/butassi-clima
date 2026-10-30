"""Pizarra diaria de precios de @butassihnos (1080x1920 PNG, stories y estado de WhatsApp).
Mismo diseño que la pizarra de siempre, con el logo más chico y @butassihnos junto a la web.

Uso:
  python3 pizarra.py pizarra.json                 -> salida/pizarra/pizarra-AAAA-MM-DD.png
  python3 pizarra.py pizarra.json mi-archivo.png

pizarra.json:
{
  "valores": "2026-10-26",          día al que corresponden los precios (pizarra de la Cámara)
  "publicacion": "2026-10-27",      día en que se publica (opcional: si falta, hoy)
  "granos": [
    {"grano": "Soja",    "precio": 555000, "tendencia": "igual"},
    {"grano": "Maíz",    "precio": 281000, "tendencia": "sube"},
    {"grano": "Girasol", "precio": 811960, "tendencia": "sube", "estimativo": true},
    {"grano": "Trigo",   "precio": 326000, "tendencia": "baja"},
    {"grano": "Sorgo",   "precio": 291100, "anterior": 290000}
  ]
}
"tendencia" es sube | baja | igual. Si no se pasa, el script la calcula: con "anterior" (precio del día
previo) o, si tampoco está, con el último día guardado en pizarras/historial.json. Cada pizarra
generada se agrega al historial (commitealo para que el día siguiente compare bien).
Precio null -> "s/c" sin flecha.
Granos con ícono: soja, maíz, girasol, trigo, sorgo.
"""
import base64
import html
import json
import os
import sys
import unicodedata
from datetime import date

from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(AQUI, "assets", "pizarra")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
ANCHO, ALTO = 1080, 1920
HISTORIAL = os.path.join(AQUI, "pizarras", "historial.json")


def leer_historial():
    try:
        with open(HISTORIAL) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def completar_anteriores(d, hist):
    """Si un grano no trae tendencia ni anterior, la saca del último día previo guardado en el historial."""
    previos = sorted(k for k in hist if k < d["valores"])
    for g in d["granos"]:
        if g.get("tendencia") or g.get("anterior") is not None or g.get("precio") is None:
            continue
        for dia in reversed(previos):
            v = hist[dia].get(clave(g["grano"]))
            if v is not None:
                g["anterior"] = v
                g["_dia_anterior"] = dia
                break


def guardar_historial(d, hist):
    dia = {clave(g["grano"]): g.get("precio") for g in d["granos"]}
    est = [clave(g["grano"]) for g in d["granos"] if g.get("estimativo")]
    if est:
        dia["estimativos"] = est
    hist[d["valores"]] = dia
    os.makedirs(os.path.dirname(HISTORIAL), exist_ok=True)
    with open(HISTORIAL, "w") as f:
        json.dump(dict(sorted(hist.items())), f, ensure_ascii=False, indent=1)


def b64(ruta, mime):
    with open(ruta, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def clave(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower().strip()


def fecha_larga(iso, con_anio=False):
    d = date.fromisoformat(iso)
    txt = f"{d.day} de {MESES[d.month - 1]}"
    return f"{txt} de {d.year}" if con_anio else txt


def pesos(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def tendencia(g):
    if g.get("precio") is None:
        return None
    t = g.get("tendencia")
    if t:
        if t not in ("sube", "baja", "igual"):
            sys.exit(f"tendencia inválida en {g['grano']}: '{t}' (sube | baja | igual)")
        return t
    if g.get("anterior") is not None:
        return "sube" if g["precio"] > g["anterior"] else "baja" if g["precio"] < g["anterior"] else "igual"
    sys.exit(f"falta 'tendencia' o 'anterior' en {g['grano']} (y no hay un día previo en {HISTORIAL})")


FLECHAS = {
    "sube": '<svg class="fl" viewBox="0 0 40 40"><path d="M20 4 L36 36 H4 Z" fill="#228B22"/></svg>',
    "baja": '<svg class="fl" viewBox="0 0 40 40"><path d="M4 4 H36 L20 36 Z" fill="#DC3545"/></svg>',
    "igual": ('<svg class="fl" viewBox="0 0 40 40"><rect x="6" y="11" width="28" height="6" rx="1" fill="#FFC107"/>'
              '<rect x="6" y="23" width="28" height="6" rx="1" fill="#FFC107"/></svg>'),
}

CSS = """
@font-face{font-family:"Open Sans";src:url(%FUENTE%) format("truetype");font-weight:300 800;font-stretch:75% 100%}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px}
body{background:#0A300E;color:#fff;font-family:"Open Sans",Arial,sans-serif;-webkit-font-smoothing:antialiased;
  display:flex;flex-direction:column;align-items:center;padding-top:150px}
.logo{height:170px;display:block}
.rule{width:864px;height:4px;background:#fff;margin-top:36px}
h1{margin-top:18px;font-size:76px;font-weight:700;letter-spacing:.01em;line-height:1.1}
.valores{margin-top:14px;font-size:34px;font-weight:600;color:#FFC107}
.pub{margin-top:14px;font-size:28px;font-weight:400}
table{margin-top:48px;width:812px;border-collapse:collapse}
th{font-size:44px;font-weight:700;letter-spacing:.02em;padding:0 0 14px;text-align:left;border-bottom:4px solid #fff}
th.p{text-align:right;padding-right:34px}
td{height:150px;border-bottom:4px solid #fff;vertical-align:middle}
td.ic{width:132px;text-align:center}
td.ic img{display:block;margin:0 auto;max-height:118px}
td.g{font-size:54px;font-weight:400;padding-left:12px}
td.pr{font-size:50px;font-weight:400;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
td.in{width:62px;text-align:right}
.fl{width:30px;height:30px;display:inline-block;vertical-align:middle;margin-left:6px}
.sc{color:rgba(255,255,255,.6)}
.pie{margin-top:40px;text-align:center;font-size:36px;line-height:1.75}
.redes{font-size:30px;display:flex;align-items:center;justify-content:center;gap:16px}
.redes .sep{opacity:.7}
.ig{display:inline-flex;align-items:center;gap:8px;font-weight:700}
.ig svg{width:30px;height:30px}
"""

IG = ('<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
      '<rect x="2.5" y="2.5" width="19" height="19" rx="5.5"/><circle cx="12" cy="12" r="4.3"/>'
      '<circle cx="17.6" cy="6.4" r="1.1" fill="#fff" stroke="none"/></svg>')


def armar(d):
    granos = d["granos"]
    filas, hay_estimativo = "", False
    for g in granos:
        k = clave(g["grano"])
        icono_ruta = os.path.join(ASSETS, f"{k}.png")
        icono = f'<img src="{b64(icono_ruta, "image/png")}" alt="">' if os.path.exists(icono_ruta) else ""
        t = tendencia(g)
        est = "*" if g.get("estimativo") else ""
        hay_estimativo = hay_estimativo or bool(g.get("estimativo"))
        precio = f"{est}{pesos(g['precio'])}" if g.get("precio") is not None else '<span class="sc">s/c</span>'
        filas += (f'<tr><td class="ic">{icono}</td><td class="g">{html.escape(g["grano"])}</td>'
                  f'<td class="pr">{precio}</td><td class="in">{FLECHAS[t] if t else ""}</td></tr>')
    publicacion = d.get("publicacion") or date.today().isoformat()
    pie = ""
    if hay_estimativo:
        pie += "<div>*Precio estimativo</div>"
    pie += "<div>Fuente: CAC - BCR - Bco. Nación</div>"
    pie += (f'<div class="redes"><span>www.butassihnos.com.ar</span><span class="sep">·</span>'
            f'<span class="ig">{IG}@butassihnos</span></div>')
    css = CSS.replace("%FUENTE%", b64(os.path.join(AQUI, "assets", "fonts", "OpenSans.ttf"), "font/ttf"))
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{css}</style></head><body>'
            f'<img class="logo" src="{b64(os.path.join(ASSETS, "logo-verde.png"), "image/png")}" alt="Butassi Hermanos">'
            f'<div class="rule"></div><h1>PIZARRA DE ROSARIO</h1>'
            f'<div class="valores">*Valores correspondientes al {fecha_larga(d["valores"])}</div>'
            f'<div class="pub">{fecha_larga(publicacion, True).capitalize()}</div>'
            f'<table><tr><th colspan="2">PRODUCTO</th><th class="p" colspan="2">PRECIO</th></tr>{filas}</table>'
            f'<div class="pie">{pie}</div></body></html>')


def renderizar(contenido, ruta):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=1)
        pg.set_content(contenido, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(200)
        fondo_pie = pg.evaluate("document.querySelector('.pie').getBoundingClientRect().bottom")
        pg.screenshot(path=ruta, full_page=False)
        b.close()
    # Instagram tapa los últimos ~250 px de una story con la barra de respuesta.
    if fondo_pie > ALTO - 250:
        print(f"AVISO: el pie termina en {fondo_pie:.0f}px y puede quedar tapado en stories", file=sys.stderr)


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        datos = json.load(f)
    salida = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        AQUI, "salida", "pizarra", f"pizarra-{datos['valores']}.png")
    hist = leer_historial()
    completar_anteriores(datos, hist)
    renderizar(armar(datos), salida)
    guardar_historial(datos, hist)
    for g in datos["granos"]:
        if g.get("_dia_anterior"):
            print(f"{g['grano']}: comparado con {g['_dia_anterior']} ({tendencia(g)})", file=sys.stderr)
    print(salida)
