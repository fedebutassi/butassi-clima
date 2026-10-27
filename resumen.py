"""Carrusel "La semana en el agro" para el feed de @butassihnos (1080x1350 PNG).
Sigue el design system de Butassi Hnos. para piezas sociales/pizarra: blanco sobre verde oscuro #1A4A1E,
verde logo #2E7D32, dorado institucional #D4A017 solo en el subrayado (nunca en títulos ni precios),
colores funcionales de la pizarra solo en la variación (▲ #4CAF50 · ▼ #E53935 · = #F5C518),
foto cálida de campo con lavado verde, tarjetas blancas con borde #DCE5DC y sombra verdosa.

Uso:
  python3 resumen.py resumen.json salida/resumen

resumen.json (lo arma la tarea del viernes con datos verificados en fuente primaria):
{
  "desde": "2026-10-26", "hasta": "2026-10-30",
  "precios": {
    "fecha_inicio": "2026-10-26", "fecha_cierre": "2026-10-30",
    "fuente": "Cámara Arbitral de Cereales de Rosario",          (opcional)
    "granos": [{"grano": "Soja", "inicio": 507000, "cierre": 512000, "estimativo": false}, ...]
  },
  "temas": [                                                     (0 a 2)
    {"etiqueta": "Campaña", "dato": "38 %", "dato_texto": "de la soja ya sembrada en Córdoba",
     "titulo": "...", "bajada": "...", "importa": "por qué le importa al productor de la zona (opcional)",
     "fuente": "Bolsa de Cereales de Córdoba", "fecha": "2026-10-29",
     "fondo": "siembra"}                                         (opcional; si falta, sale de la etiqueta)
  ],
  "muestra": false
}
Precio faltante: null -> "s/c" (sin cotización). La variación la calcula el script, nunca el JSON.
Si un texto no entra en la placa, el script falla con el nombre del campo para acortarlo.

Fondos: assets/fondos/<categoría>/*.jpg|jpeg|png|webp (ver assets/fondos/README.md).
  campo (tapa y cierre, y respaldo) · granos (precios) · siembra · cosecha · puerto · camiones · pulverizacion
Cada categoría puede tener varias fotos: rotan por semana y nunca se repite una foto en el mismo carrusel.
Si una categoría está vacía, usa campo y lo avisa por consola.
"""
import base64
import html
import io
import json
import os
import sys
import unicodedata
from datetime import date

from PIL import Image, ImageOps
from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
FONDOS_DIR = os.path.join(AQUI, "assets", "fondos")
with open(os.path.join(AQUI, "assets", "logo.png"), "rb") as _f:
    LOGO = "data:image/png;base64," + base64.b64encode(_f.read()).decode()

ANCHO, ALTO = 1080, 1350
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
LIMITES = {"etiqueta": 22, "dato": 12, "dato_texto": 60, "titulo": 80, "bajada": 200, "importa": 150, "fuente": 70}

# Etiqueta del tema -> fondo (sin tildes, en minúscula).
FONDO_POR_ETIQUETA = {
    "campana": "siembra", "siembra": "siembra", "cultivos": "siembra",
    "cosecha": "cosecha",
    "exportaciones": "puerto", "puertos": "puerto", "embarques": "puerto", "molienda": "puerto",
    "industria": "puerto",
    "comercializacion": "camiones", "ventas": "camiones", "logistica": "camiones", "fletes": "camiones",
    "agroquimicos": "pulverizacion", "insumos": "pulverizacion",
}
avisos = []


def e(t):
    return html.escape(str(t))


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower().strip()


def dia_corto(iso, minus=False):
    d = date.fromisoformat(iso)
    dia = DIAS[d.weekday()]
    return f"{dia.lower() if minus else dia} {d.day}/{d.month:02d}"


def pesos(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def variacion(ini, fin):
    """(texto, clase) o None si falta un precio."""
    if ini is None or fin is None:
        return None
    if fin == ini:
        return ("0 %", "igual")
    pct = (fin - ini) / ini * 100
    signo = "+" if pct > 0 else "−"
    # Un cambio menor a 0,1 % se muestra como 0,1 % para que no parezca "sin cambio".
    txt = f"{signo}{max(abs(pct), 0.1):.1f}".replace(".", ",") + " %"
    return (txt, "sube" if pct > 0 else "baja")


def flecha(tipo):
    if tipo == "igual":
        return ('<svg class="fl" viewBox="0 0 24 24"><rect x="4" y="7" width="16" height="3.2" rx="1.6"/>'
                '<rect x="4" y="13.8" width="16" height="3.2" rx="1.6"/></svg>')
    rot = "" if tipo == "sube" else ' transform="rotate(180 12 12)"'
    return f'<svg class="fl" viewBox="0 0 24 24"><path{rot} d="M12 3 L21 14 H15 V21 H9 V14 H3 Z"/></svg>'


_cache = {}
_usados = set()
SEMANA = 0  # se fija en placas() con la semana ISO de "hasta"


def _archivos(categoria):
    carpeta = os.path.join(FONDOS_DIR, categoria)
    if not os.path.isdir(carpeta):
        return []
    return sorted(os.path.join(carpeta, f) for f in os.listdir(carpeta)
                  if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))


def elegir(categoria, ranura):
    """Elige un fondo de la categoría que no se haya usado en este carrusel.
    Rota por semana ISO: cada viernes cambia la foto, y la misma semana da siempre la misma."""
    pool = _archivos(categoria)
    if not pool:
        avisos.append(f"no hay fondos en assets/fondos/{categoria}/: usé campo")
        pool = _archivos("campo")
    if not pool:
        sys.exit("falta assets/fondos/campo/ (fondos de respaldo)")
    libres = [f for f in pool if f not in _usados] or pool
    ruta = libres[(SEMANA + ranura) % len(libres)]
    _usados.add(ruta)
    return fondo_uri(ruta)


def fondo_uri(ruta):
    """data URI del fondo recortado a 1080x1350."""
    if ruta in _cache:
        return _cache[ruta]
    im = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    if im.width < ANCHO * 0.6 or im.height < ALTO * 0.6:
        avisos.append(f"el fondo {os.path.basename(ruta)} es chico ({im.width}x{im.height}): puede verse pixelado")
    im = ImageOps.fit(im, (ANCHO, ALTO), Image.LANCZOS, centering=(0.5, 0.5))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84)
    _cache[ruta] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return _cache[ruta]


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px}
body{font-family:-apple-system,"SF Pro Display","Segoe UI",Roboto,Inter,system-ui,sans-serif;color:#fff;
  background:#1A4A1E;-webkit-font-smoothing:antialiased;position:relative;overflow:hidden}
.bg{position:absolute;inset:0;background-size:cover;background-position:center}
/* lavado verde de marca sobre la foto */
.ov{position:absolute;inset:0}
.ov.l-hero{background:linear-gradient(180deg,rgba(26,74,30,.82) 0%,rgba(46,125,50,.40) 50%,rgba(26,74,30,.30) 68%,rgba(26,74,30,.88) 100%)}
.ov.l-cierre{background:linear-gradient(180deg,rgba(26,74,30,.85) 0%,rgba(26,74,30,.55) 45%,rgba(26,74,30,.80) 70%,rgba(26,74,30,.92) 100%)}
.ov.l-dato{background:linear-gradient(180deg,rgba(26,74,30,.90) 0%,rgba(26,74,30,.78) 30%,rgba(26,74,30,.74) 60%,rgba(26,74,30,.90) 100%)}
.wrap{position:absolute;left:80px;right:80px;top:72px}
.wrap.full{bottom:210px;display:flex;flex-direction:column}
.abajo{margin-top:auto !important}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:56px}
.logo{background:rgba(255,255,255,.95);border-radius:20px;padding:12px 22px;display:flex;
  box-shadow:0 25px 50px -12px rgba(52,99,29,.30)}
.logo img{height:52px;display:block}
.cont{font-size:26px;font-weight:600;color:rgba(255,255,255,.75);letter-spacing:.04em}
.eyebrow{font-size:26px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.85)}
.rule{width:96px;height:6px;border-radius:9999px;background:#D4A017;margin-top:22px}
h1{margin-top:26px;font-size:72px;line-height:1.08;font-weight:700;letter-spacing:-.01em}
h1.xl{font-size:132px;line-height:1;margin-top:40px}
.sub{margin-top:26px;font-size:34px;line-height:1.4;color:rgba(255,255,255,.9)}
/* tarjeta blanca de marca */
.card{margin-top:40px;background:#fff;color:#1A4A1E;border:2px solid #DCE5DC;border-radius:28px;
  padding:10px 40px;box-shadow:0 20px 25px -5px rgba(52,99,29,.16),0 8px 10px -6px rgba(52,99,29,.10)}
.card.barra{position:relative;overflow:hidden;padding-top:42px}
.card.barra:before{content:"";position:absolute;left:0;right:0;top:0;height:10px;
  background:linear-gradient(135deg,#4CAF50,#2E7D32)}
.temas{display:flex;flex-wrap:wrap;gap:16px}
.temas-t{font-size:24px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.75);margin-bottom:18px}
.pill{padding:14px 28px;border-radius:9999px;background:rgba(255,255,255,.95);color:#2E7D32;font-size:28px;font-weight:600}
.desliza{position:absolute;right:80px;bottom:72px;font-size:30px;font-weight:700;color:#fff;display:flex;gap:12px;align-items:center}
/* precios */
.tabla{width:100%;border-collapse:collapse}
.tabla th{font-size:22px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#687068;text-align:right;padding:26px 0 16px}
.tabla th:first-child{text-align:left}
.tabla td{padding:22px 0;border-top:2px solid #DCE5DC;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tabla td.g{text-align:left;font-size:36px;font-weight:700;color:#1A4A1E}
.tabla td.ini{font-size:29px;color:#687068;padding-right:8px}
.tabla td.fin{font-size:36px;font-weight:700;padding-left:22px;color:#1A4A1E}
.var{display:inline-flex;align-items:center;gap:8px;font-size:27px;font-weight:700;padding:9px 18px 9px 14px;border-radius:9999px}
.var.sube{background:#4CAF50;color:#1A4A1E;fill:#1A4A1E}
.var.baja{background:#E53935;color:#fff;fill:#fff}
.var.igual{background:#F5C518;color:#1A4A1E;fill:#1A4A1E}
.fl{width:28px;height:28px;flex:none}
.sc{color:#687068;font-weight:500}
.nota{margin-top:18px;font-size:23px;color:rgba(255,255,255,.8)}
/* tema */
.chip{display:inline-block;padding:12px 26px;border-radius:9999px;background:#fff;color:#2E7D32;font-size:25px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.dato{margin-top:40px;font-size:150px;line-height:.95;font-weight:700;letter-spacing:-.02em;color:#fff}
.dato-t{margin-top:14px;font-size:34px;font-weight:600;color:rgba(255,255,255,.92)}
.t2{margin-top:44px;font-size:56px;line-height:1.12;font-weight:700;letter-spacing:-.01em}
.t2.solo{font-size:66px;margin-top:40px}
.b2{margin-top:24px;font-size:33px;line-height:1.45;color:rgba(255,255,255,.9)}
.imp{padding-bottom:34px}
.imp-t{font-size:22px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#2E7D32}
.imp-b{margin-top:12px;font-size:31px;line-height:1.42;font-weight:500;color:#1A4A1E}
/* cierre */
.handle-xl{font-size:76px;font-weight:700;letter-spacing:-.01em;color:#fff;line-height:1.08}
.agenda .fila{display:flex;justify-content:space-between;align-items:baseline;padding:26px 0;border-top:2px solid #DCE5DC;font-size:34px}
.agenda .fila:first-child{border-top:0}
.agenda .fila b{font-weight:700;color:#1A4A1E}
.agenda .fila span{color:#2E7D32;font-size:31px;font-weight:600}
/* pie */
.pie{position:absolute;left:80px;right:80px;bottom:64px}
.fuente{font-size:22px;line-height:1.45;color:rgba(255,255,255,.78);padding-bottom:22px;margin-bottom:22px;border-bottom:1.5px solid rgba(255,255,255,.22)}
.marca{display:flex;align-items:baseline;gap:22px}
.handle{font-size:28px;font-weight:700}
.web{font-size:26px;color:rgba(255,255,255,.85)}
.muestra{padding:10px 22px;border-radius:9999px;background:#B91C1C;font-size:22px;font-weight:700;letter-spacing:.08em}
"""


def pagina(n, total, cuerpo, fuente, fondo_uri, lavado, muestra=False, extra="", full=False, marca=True):
    derecha = ('<div class="muestra">MUESTRA · NO PUBLICAR</div>' if muestra
               else f'<div class="cont">{n}/{total}</div>')
    top = f'<div class="top"><div class="logo"><img src="{LOGO}" alt="Butassi Hermanos"></div>{derecha}</div>'
    pie = ""
    if fuente or marca:
        pie = ('<div class="pie">' + (f'<div class="fuente">{fuente}</div>' if fuente else "")
               + ('<div class="marca"><div class="handle">@butassihnos</div><div class="web">butassihnos.com.ar</div></div>'
                  if marca else "") + '</div>')
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
            f'<div class="bg" style="background-image:url({fondo_uri})"></div><div class="ov l-{lavado}"></div>'
            f'<div class="wrap{" full" if full else ""}">{top}{cuerpo}</div>{extra}{pie}</body></html>')


def placa_tapa(d, total):
    etiquetas = ["Precios"] + [t["etiqueta"] for t in d.get("temas", [])]
    pills = "".join(f'<span class="pill">{e(x)}</span>' for x in etiquetas)
    desliza = '<div class="desliza">Deslizá <span>→</span></div>'
    return pagina(1, total,
                  f'<div class="eyebrow">Resumen semanal · {e(dia_corto(d["desde"]))} al {e(dia_corto(d["hasta"]))}</div>'
                  f'<div class="rule"></div><h1 class="xl">La semana<br>en el agro</h1>'
                  f'<div class="sub">Lo que pasó en el mercado y en el campo,<br>contado simple.</div>'
                  f'<div class="abajo"><div class="temas-t">En este resumen</div><div class="temas">{pills}</div></div>',
                  "", elegir("campo", 0), "hero", d.get("muestra", False), extra=desliza, full=True)


def placa_precios(d, n, total):
    p = d["precios"]
    filas, estimativo = "", False
    for g in p["granos"]:
        ini, fin = g.get("inicio"), g.get("cierre")
        v = variacion(ini, fin)
        marca = "*" if g.get("estimativo") else ""
        estimativo = estimativo or bool(g.get("estimativo"))
        var = f'<span class="var {v[1]}">{flecha(v[1])}{v[0]}</span>' if v else '<span class="sc">—</span>'
        filas += (f'<tr><td class="g">{e(g["grano"])}</td>'
                  f'<td class="ini">{pesos(ini) if ini is not None else "<span class=sc>s/c</span>"}</td>'
                  f'<td class="fin">{marca}{pesos(fin) if fin is not None else "<span class=sc>s/c</span>"}</td>'
                  f'<td>{var}</td></tr>')
    notas = ["Precios en pesos por tonelada."]
    if estimativo:
        notas.append("*Precio estimativo.")
    if any(g.get("inicio") is None or g.get("cierre") is None for g in p["granos"]):
        notas.append("s/c: sin cotización ese día.")
    fuente = (f"Fuente: {e(p.get('fuente', 'Cámara Arbitral de Cereales de Rosario'))}, "
              f"pizarra del {e(dia_corto(p['fecha_inicio'], True))} y del {e(dia_corto(p['fecha_cierre'], True))}.")
    return pagina(n, total,
                  f'<div class="eyebrow">Pizarra de Rosario</div><div class="rule"></div>'
                  f'<h1>Cómo se movieron<br>los precios</h1>'
                  f'<div class="card"><table class="tabla"><tr><th>Grano</th><th>{e(dia_corto(p["fecha_inicio"]))}</th>'
                  f'<th>{e(dia_corto(p["fecha_cierre"]))}</th><th>Variación</th></tr>{filas}</table></div>'
                  f'<div class="nota">{" ".join(notas)}</div>',
                  fuente, elegir("granos", 1), "dato", d.get("muestra", False))


def placa_tema(d, t, n, total):
    dato = ""
    if t.get("dato"):
        dato = f'<div class="dato">{e(t["dato"])}</div>'
        if t.get("dato_texto"):
            dato += f'<div class="dato-t">{e(t["dato_texto"])}</div>'
    importa = ""
    if t.get("importa"):
        importa = (f'<div class="abajo card barra imp"><div class="imp-t">Para el productor de la zona</div>'
                   f'<div class="imp-b">{e(t["importa"])}</div></div>')
    nombre = t.get("fondo") or FONDO_POR_ETIQUETA.get(sin_tildes(t["etiqueta"]), "campo")
    bg = elegir(nombre, n)
    return pagina(n, total,
                  f'<div><span class="chip">{e(t["etiqueta"])}</span></div>{dato}'
                  f'<div class="t2{"" if dato else " solo"}">{e(t["titulo"])}</div><div class="b2">{e(t["bajada"])}</div>'
                  f'{importa}',
                  f'Fuente: {e(t["fuente"])}, {e(dia_corto(t["fecha"], True))}.', bg, "dato",
                  d.get("muestra", False), full=True)


def placa_cierre(d, n, total):
    agenda = ('<div class="card agenda">'
              '<div class="fila"><b>Lunes a viernes</b><span>Pizarra de Rosario</span></div>'
              '<div class="fila"><b>Lunes</b><span>Clima de la semana</span></div>'
              '<div class="fila"><b>Viernes</b><span>Resumen semanal</span></div></div>')
    return pagina(n, total,
                  f'<div class="eyebrow">Todas las semanas</div><div class="rule"></div>'
                  f'<h1>La info del agro de la zona,<br>en un solo lugar</h1>{agenda}'
                  f'<div class="abajo handle-xl">Seguinos en<br>@butassihnos</div>'
                  f'<div class="web" style="margin-top:14px">butassihnos.com.ar</div>',
                  "", elegir("campo", 7), "cierre", d.get("muestra", False), full=True, marca=False)


def validar(d):
    errores = []
    for k in ("desde", "hasta", "precios"):
        if k not in d:
            errores.append(f"falta '{k}'")
    p = d.get("precios", {})
    for k in ("fecha_inicio", "fecha_cierre", "granos"):
        if k not in p:
            errores.append(f"falta 'precios.{k}'")
    for i, g in enumerate(p.get("granos", [])):
        for k in ("inicio", "cierre"):
            v = g.get(k)
            if v is not None and not isinstance(v, (int, float)):
                errores.append(f"precios.granos[{i}].{k} tiene que ser número o null")
    temas = d.get("temas", [])
    if len(temas) > 2:
        errores.append("máximo 2 temas")
    for i, t in enumerate(temas):
        for k in ("etiqueta", "titulo", "bajada", "fuente", "fecha"):
            if not t.get(k):
                errores.append(f"temas[{i}] sin '{k}'")
        for k, lim in LIMITES.items():
            if t.get(k) and len(str(t[k])) > lim:
                errores.append(f"temas[{i}].{k} tiene {len(str(t[k]))} caracteres (máx. {lim}): acortalo")
    if errores:
        sys.exit("resumen.json inválido:\n- " + "\n- ".join(errores))


def placas(d):
    global SEMANA
    SEMANA = date.fromisoformat(d["hasta"]).isocalendar()[1]
    _usados.clear()
    temas = d.get("temas", [])
    total = 3 + len(temas)
    out = [("1-tapa.png", placa_tapa(d, total)), ("2-precios.png", placa_precios(d, 2, total))]
    for i, t in enumerate(temas):
        out.append((f"{3 + i}-tema.png", placa_tema(d, t, 3 + i, total)))
    out.append((f"{total}-cierre.png", placa_cierre(d, total, total)))
    return out


# Detecta texto que se pisa con el pie o se sale de la placa.
CHEQUEO = """() => {
  const pieEl = document.querySelector('.pie');
  const pie = pieEl ? pieEl.getBoundingClientRect().top : 1350 - 64;
  const wrap = document.querySelector('.wrap');
  let maxDer = 0, maxAbajo = 0;
  wrap.querySelectorAll('*').forEach(el => { const r = el.getBoundingClientRect();
    maxDer = Math.max(maxDer, r.right); maxAbajo = Math.max(maxAbajo, r.bottom); });
  const desl = document.querySelector('.desliza');
  return {contenido: maxAbajo, pie: pie, derecha: maxDer,
          desborda: wrap.scrollHeight > wrap.clientHeight + 1,
          desliza: desl ? desl.getBoundingClientRect().top : null};
}"""


def renderizar(paginas, salida):
    os.makedirs(salida, exist_ok=True)
    rutas, problemas = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=1)
        for nombre, contenido in paginas:
            pg.set_content(contenido, wait_until="load")
            pg.wait_for_timeout(200)
            m = pg.evaluate(CHEQUEO)
            limite = m["pie"] - 24
            if m["desliza"] is not None:
                limite = min(limite, m["desliza"] - 16)
            if m["desborda"] or m["contenido"] > limite:
                problemas.append(f"{nombre}: el texto no entra (llega a {m['contenido']:.0f}px, el pie empieza en "
                                 f"{limite:.0f}px). Acortá titulo, bajada o importa de esa placa y volvé a correr.")
            if m["derecha"] > ANCHO - 70:
                problemas.append(f"{nombre}: hay texto que se sale por la derecha ({m['derecha']:.0f}px)")
            ruta = os.path.join(salida, nombre)
            pg.screenshot(path=ruta, full_page=False)
            rutas.append(ruta)
        b.close()
    return rutas, problemas


if __name__ == "__main__":
    archivo, salida = sys.argv[1], sys.argv[2]
    with open(archivo) as f:
        datos = json.load(f)
    validar(datos)
    paginas = placas(datos)
    rutas, problemas = renderizar(paginas, salida)
    for r in rutas:
        print(r)
    for a in dict.fromkeys(avisos):
        print("AVISO:", a, file=sys.stderr)
    if problemas:
        sys.exit("PLACAS CON PROBLEMAS (no publicar):\n- " + "\n- ".join(problemas))
