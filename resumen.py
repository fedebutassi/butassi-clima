"""Carrusel "La semana en el agro" para el feed de @butassihnos (1080x1350 PNG).
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
     "fuente": "Bolsa de Cereales de Córdoba", "fecha": "2026-10-29"}
  ],
  "muestra": false
}
Precio faltante: null -> "s/c" (sin cotización). La variación la calcula el script, nunca el JSON.
Si un texto no entra en la placa, el script falla con el nombre del campo para acortarlo.
"""
import html
import json
import os
import sys
from datetime import date

from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(AQUI, "assets", "logo.png"), "rb") as _f:
    import base64
    LOGO = "data:image/png;base64," + base64.b64encode(_f.read()).decode()

ANCHO, ALTO = 1080, 1350
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
SUBE, BAJA, IGUAL = "#7ad686", "#ff7a6b", "#f0c031"
LIMITES = {"etiqueta": 22, "dato": 12, "dato_texto": 60, "titulo": 80, "bajada": 200, "importa": 150, "fuente": 70}


def e(t):
    return html.escape(str(t))


def fecha(iso):
    d = date.fromisoformat(iso)
    return d


def dia_corto(iso, minus=False):
    d = fecha(iso)
    dia = DIAS[d.weekday()]
    return f"{dia.lower() if minus else dia} {d.day}/{d.month:02d}"


def pesos(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def variacion(ini, fin):
    """(texto, color, flecha) o None si falta un precio."""
    if ini is None or fin is None:
        return None
    if fin == ini:
        return ("0 %", IGUAL, "igual")
    pct = (fin - ini) / ini * 100
    signo = "+" if pct > 0 else "−"
    # Un cambio menor a 0,1 % se muestra como 0,1 % para que no parezca "sin cambio".
    txt = f"{signo}{max(abs(pct), 0.1):.1f}".replace(".", ",") + " %"
    return (txt, SUBE if pct > 0 else BAJA, "sube" if pct > 0 else "baja")


def flecha(tipo, color):
    if tipo == "igual":
        return (f'<svg class="fl" viewBox="0 0 24 24"><rect x="4" y="7" width="16" height="3.2" rx="1.6" fill="{color}"/>'
                f'<rect x="4" y="13.8" width="16" height="3.2" rx="1.6" fill="{color}"/></svg>')
    rot = "" if tipo == "sube" else ' transform="rotate(180 12 12)"'
    return (f'<svg class="fl" viewBox="0 0 24 24"><path{rot} d="M12 3 L21 14 H15 V21 H9 V14 H3 Z" fill="{color}"/></svg>')


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px}
body{font-family:Inter,"SF Pro Display",system-ui,sans-serif;color:#fff;
  background:linear-gradient(160deg,#0f2611 0%,#173617 40%,#22512a 75%,#2f6330 100%);
  -webkit-font-smoothing:antialiased;position:relative;overflow:hidden}
.wrap{position:absolute;left:80px;right:80px;top:72px}
.wrap.full{bottom:210px;display:flex;flex-direction:column}
.abajo{margin-top:auto !important}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:56px}
.logo{background:rgba(255,255,255,.96);border-radius:22px;padding:12px 22px;display:flex;box-shadow:0 10px 30px -10px rgba(0,0,0,.35)}
.logo img{height:52px;display:block}
.cont{font-size:26px;font-weight:600;color:rgba(255,255,255,.6);letter-spacing:.04em}
.eyebrow{font-size:28px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:rgba(255,255,255,.72)}
.rule{width:96px;height:6px;border-radius:9999px;background:#f0c031;margin-top:22px}
h1{margin-top:26px;font-size:72px;line-height:1.04;font-weight:800;letter-spacing:-.025em}
h1.xl{font-size:136px;line-height:.96;margin-top:40px}
.sub{margin-top:26px;font-size:34px;line-height:1.35;color:rgba(255,255,255,.82)}
.card{margin-top:40px;background:rgba(255,255,255,.085);border:1.5px solid rgba(255,255,255,.13);border-radius:40px;padding:10px 40px}
.temas{display:flex;flex-wrap:wrap;gap:16px}
.temas-t{font-size:24px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.55);margin-bottom:18px}
.pill{padding:14px 26px;border-radius:9999px;border:1.5px solid rgba(255,255,255,.28);font-size:28px;font-weight:600}
.desliza{position:absolute;right:80px;bottom:72px;font-size:30px;font-weight:700;color:#f0c031;display:flex;gap:12px;align-items:center}
/* precios */
.tabla{width:100%;border-collapse:collapse}
.tabla th{font-size:24px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:rgba(255,255,255,.55);text-align:right;padding:26px 0 18px}
.tabla th:first-child{text-align:left}
.tabla td{padding:24px 0;border-top:1.5px solid rgba(255,255,255,.12);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tabla td.g{text-align:left;font-size:38px;font-weight:700}
.tabla td.ini{font-size:30px;color:rgba(255,255,255,.62);padding-right:8px}
.tabla td.fin{font-size:38px;font-weight:700;padding-left:24px}
.var{display:inline-flex;align-items:center;justify-content:flex-end;gap:10px;font-size:30px;font-weight:700;min-width:190px}
.fl{width:34px;height:34px;flex:none}
.sc{color:rgba(255,255,255,.5);font-weight:500}
.nota{margin-top:18px;font-size:24px;color:rgba(255,255,255,.6)}
/* tema */
.chip{display:inline-block;padding:12px 26px;border-radius:9999px;background:#f0c031;color:#173617;font-size:26px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
.dato{margin-top:40px;font-size:150px;line-height:.95;font-weight:800;letter-spacing:-.03em;color:#f0c031}
.dato-t{margin-top:14px;font-size:34px;font-weight:600;color:rgba(255,255,255,.85)}
.t2{margin-top:44px;font-size:58px;line-height:1.1;font-weight:800;letter-spacing:-.02em}
.b2{margin-top:24px;font-size:34px;line-height:1.42;color:rgba(255,255,255,.86)}
.t2.solo{font-size:68px;margin-top:40px}
.imp{padding:34px 40px}
.imp-t{font-size:24px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#f0c031}
.imp-b{margin-top:12px;font-size:32px;line-height:1.4;font-weight:500}
/* cierre */
.handle-xl{margin-top:44px;font-size:76px;font-weight:800;letter-spacing:-.02em;color:#f0c031}
.agenda .fila{display:flex;justify-content:space-between;align-items:baseline;padding:28px 0;border-top:1.5px solid rgba(255,255,255,.12);font-size:36px}
.agenda .fila:first-child{border-top:0}
.agenda .fila b{font-weight:700}
.agenda .fila span{color:rgba(255,255,255,.7);font-size:32px}
/* pie */
.pie{position:absolute;left:80px;right:80px;bottom:64px}
.fuente{font-size:22px;line-height:1.45;color:rgba(255,255,255,.58);padding-bottom:22px;margin-bottom:22px;border-bottom:1.5px solid rgba(255,255,255,.14)}
.marca{display:flex;align-items:baseline;gap:22px}
.handle{font-size:28px;font-weight:700}
.web{font-size:26px;color:rgba(255,255,255,.7)}
.muestra{padding:10px 22px;border-radius:9999px;background:#d93a2b;font-size:22px;font-weight:800;letter-spacing:.08em}
"""


def pagina(n, total, cuerpo, fuente, muestra=False, extra="", full=False, marca=True):
    derecha = ('<div class="muestra">MUESTRA · NO PUBLICAR</div>' if muestra
               else f'<div class="cont">{n}/{total}</div>')
    top = f'<div class="top"><div class="logo"><img src="{LOGO}" alt="Butassi Hermanos"></div>{derecha}</div>'
    pie = ""
    if fuente or marca:
        pie = ('<div class="pie">' + (f'<div class="fuente">{fuente}</div>' if fuente else "")
               + ('<div class="marca"><div class="handle">@butassihnos</div><div class="web">butassihnos.com.ar</div></div>'
                  if marca else "") + '</div>')
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body><div class="wrap{" full" if full else ""}">{top}{cuerpo}</div>{extra}{pie}</body></html>')


def placa_tapa(d, total):
    etiquetas = ["Precios"] + [t["etiqueta"] for t in d.get("temas", [])]
    pills = "".join(f'<span class="pill">{e(x)}</span>' for x in etiquetas)
    desliza = '<div class="desliza">Deslizá <span>→</span></div>'
    return pagina(1, total,
                  f'<div class="eyebrow">Resumen semanal · {e(dia_corto(d["desde"]))} al {e(dia_corto(d["hasta"]))}</div>'
                  f'<div class="rule"></div><h1 class="xl">La semana<br>en el agro</h1>'
                  f'<div class="sub">Lo que pasó en el mercado y en el campo, contado simple.</div>'
                  f'<div class="abajo"><div class="temas-t">En este resumen</div><div class="temas">{pills}</div></div>',
                  "", d.get("muestra", False), extra=desliza, full=True)


def placa_precios(d, n, total):
    p = d["precios"]
    filas, estimativo = "", False
    for g in p["granos"]:
        ini, fin = g.get("inicio"), g.get("cierre")
        v = variacion(ini, fin)
        marca = "*" if g.get("estimativo") else ""
        estimativo = estimativo or bool(g.get("estimativo"))
        var = (f'<span class="var" style="color:{v[1]}">{flecha(v[2], v[1])}{v[0]}</span>' if v
               else '<span class="var sc">—</span>')
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
                  fuente, d.get("muestra", False))


def placa_tema(d, t, n, total):
    dato = ""
    if t.get("dato"):
        dato = f'<div class="dato">{e(t["dato"])}</div>'
        if t.get("dato_texto"):
            dato += f'<div class="dato-t">{e(t["dato_texto"])}</div>'
    importa = ""
    if t.get("importa"):
        importa = (f'<div class="abajo card imp"><div class="imp-t">Para el productor de la zona</div>'
                   f'<div class="imp-b">{e(t["importa"])}</div></div>')
    return pagina(n, total,
                  f'<div><span class="chip">{e(t["etiqueta"])}</span></div>{dato}'
                  f'<div class="t2{"" if dato else " solo"}">{e(t["titulo"])}</div><div class="b2">{e(t["bajada"])}</div>'
                  f'{importa}',
                  f'Fuente: {e(t["fuente"])}, {e(dia_corto(t["fecha"], True))}.', d.get("muestra", False), full=True)


def placa_cierre(d, n, total):
    agenda = ('<div class="card agenda">'
              '<div class="fila"><b>Lunes a viernes</b><span>Pizarra de Rosario</span></div>'
              '<div class="fila"><b>Lunes</b><span>Clima de la semana</span></div>'
              '<div class="fila"><b>Viernes</b><span>Resumen semanal</span></div></div>')
    return pagina(n, total,
                  f'<div class="eyebrow">Todas las semanas</div><div class="rule"></div>'
                  f'<h1>La info del agro de la zona, en un solo lugar</h1>{agenda}'
                  f'<div class="abajo handle-xl">Seguinos en<br>@butassihnos</div>'
                  f'<div class="web" style="margin-top:14px">butassihnos.com.ar</div>',
                  "", d.get("muestra", False), full=True, marca=False)


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
            pg.wait_for_timeout(150)
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
    rutas, problemas = renderizar(placas(datos), salida)
    for r in rutas:
        print(r)
    if problemas:
        sys.exit("PLACAS CON PROBLEMAS (no publicar):\n- " + "\n- ".join(problemas))
