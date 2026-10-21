"""Genera las stories de clima de @butassihnos (1080x1920 PNG).
Uso:
  python3 render.py semana semana.json salida/      -> 3 stories del pronóstico semanal
  python3 render.py alerta alerta.json salida/      -> 1 story por alerta (lista o un objeto)

Zonas seguras de Instagram: los 250 px de arriba y de abajo quedan libres
(ahí van el encabezado de la story y la barra de respuesta).
"""
import base64
import html
import json
import os
import sys

from playwright.sync_api import sync_playwright

from mapa import svg_mapa

AQUI = os.path.dirname(os.path.abspath(__file__))
ICONOS = os.path.join(AQUI, "assets", "icons")
with open(os.path.join(AQUI, "assets", "logo.png"), "rb") as _f:
    LOGO = "data:image/png;base64," + base64.b64encode(_f.read()).decode()

ZONA_FOCO = ["TERCERO ARRIBA", "RIO SEGUNDO", "CALAMUCHITA"]
PILAR = (-63.88, -31.68)
GOLD = "#f0c031"
NIVELES = {
    3: ("Alerta amarilla", "#f0c031", "#173617"),
    4: ("Alerta naranja", "#f08c1e", "#1b1206"),
    5: ("Alerta roja", "#d93a2b", "#ffffff"),
}


def icono(nombre, clase="ic"):
    with open(os.path.join(ICONOS, nombre + ".svg")) as f:
        svg = f.read()
    svg = svg[svg.index("<svg"):]
    return svg.replace("<svg", f'<svg class="{clase}"', 1)


def e(t):
    return html.escape(str(t))


def mm_txt(mm):
    if mm == 0:
        return "0 mm"
    if mm < 1:
        return "&lt;1 mm"
    return f"{mm:.1f}".replace(".", ",") + " mm"


def lista(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px}
body{font-family:Inter,"SF Pro Display",system-ui,sans-serif;color:#fff;
  background:linear-gradient(165deg,#0f2611 0%,#173617 38%,#22512a 72%,#2f6330 100%);
  -webkit-font-smoothing:antialiased;position:relative;overflow:hidden}
.wrap{position:absolute;inset:0;padding:210px 72px 0}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:54px}
.eyebrow{font-size:30px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:rgba(255,255,255,.72)}
.rule{width:96px;height:6px;border-radius:9999px;background:#f0c031;margin-top:24px}
h1{margin-top:28px;font-size:96px;line-height:1.02;font-weight:800;letter-spacing:-.025em}
.sub{margin-top:22px;font-size:34px;color:rgba(255,255,255,.8);line-height:1.3}
.card{margin-top:40px;background:rgba(255,255,255,.085);border:1.5px solid rgba(255,255,255,.13);border-radius:44px;padding:8px 44px}
.cards{margin-top:44px}
.cards .card{padding:38px 44px;display:flex;gap:34px;align-items:flex-start;margin-top:24px}
.ic{width:64px;height:64px;flex:none;stroke:#fff;stroke-width:1.7}
.ic.rain{stroke:#9ccdf5}
.ct{font-size:40px;font-weight:700;line-height:1.15;letter-spacing:-.01em}
.cb{margin-top:10px;font-size:32px;line-height:1.35;color:rgba(255,255,255,.86)}
.cover{position:relative}
.cover .mapa{position:absolute;right:0;top:40px}
/* pie: fuente + marca, por encima de la barra de respuesta */
.pie{position:absolute;left:72px;right:72px;bottom:250px}
.fuente{font-size:24px;line-height:1.45;color:rgba(255,255,255,.6);padding-bottom:26px;margin-bottom:26px;border-bottom:1.5px solid rgba(255,255,255,.14)}
.marca{display:flex;align-items:baseline;gap:22px}
.logo{background:rgba(255,255,255,.96);border-radius:24px;padding:14px 24px;display:flex;box-shadow:0 10px 30px -10px rgba(0,0,0,.35)}
.logo img{height:58px;display:block}
.handle{font-size:32px;font-weight:700}
.web{font-size:30px;color:rgba(255,255,255,.72)}
/* día por día */
.row{display:grid;grid-template-columns:150px 230px 1fr;align-items:center;padding:30px 0;border-top:1.5px solid rgba(255,255,255,.12)}
.row:first-of-type{border-top:0}
.dname{font-size:42px;font-weight:700}
.dname small{display:block;font-size:25px;font-weight:500;color:rgba(255,255,255,.6);margin-top:2px}
.rain{display:flex;align-items:center;gap:14px;font-size:34px;font-weight:600}
.rain .ic{width:44px;height:44px}
.rain.dry{color:rgba(255,255,255,.55)}.rain.dry .ic{stroke:rgba(255,255,255,.45)}
.temps{display:grid;grid-template-columns:76px 1fr 80px;align-items:center;gap:20px;font-size:40px;font-weight:600}
.temps .mn{color:rgba(255,255,255,.6);text-align:right}
.bar{height:12px;border-radius:9999px;background:rgba(255,255,255,.16);position:relative}
.bar i{position:absolute;top:0;bottom:0;border-radius:9999px;background:linear-gradient(90deg,#c9d8a8,#f0c031)}
.wind{grid-column:2 / span 2;margin-top:10px;font-size:26px;color:rgba(255,255,255,.62);display:flex;gap:10px;align-items:center}
.wind .ic{width:30px;height:30px;stroke:rgba(255,255,255,.55);stroke-width:2}
.note{margin-top:22px;font-size:25px;line-height:1.4;color:rgba(255,255,255,.6)}
/* alerta */
.badge{display:inline-flex;align-items:center;gap:16px;padding:16px 28px;border-radius:9999px;font-size:30px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
.badge .ic{width:38px;height:38px;stroke-width:2.4}
.zonas{display:flex;gap:44px;align-items:center;padding:20px 0}
.leyenda{display:flex;flex-direction:column;gap:14px}
.chip{padding:12px 24px;border-radius:9999px;font-size:28px;font-weight:600;align-self:flex-start}
.ley-sin{font-size:24px;color:rgba(255,255,255,.6);display:flex;gap:10px;align-items:center;margin-top:8px}
.ley-sin i{width:22px;height:22px;border-radius:6px;border:1.5px solid rgba(255,255,255,.35);background:rgba(255,255,255,.07)}
.muestra{padding:10px 22px;border-radius:9999px;background:#d93a2b;font-size:24px;font-weight:800;letter-spacing:.08em}
"""


def pagina(cuerpo, fuente, muestra=False):
    top = (f'<div class="top"><div class="logo"><img src="{LOGO}" alt="Butassi Hermanos"></div>'
           + ('<div class="muestra">MUESTRA · NO PUBLICAR</div>' if muestra else "") + "</div>")
    pie = (f'<div class="pie"><div class="fuente">{fuente}</div>'
           f'<div class="marca"><div class="handle">@butassihnos</div><div class="web">butassihnos.com.ar</div></div></div>')
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body><div class="wrap">{top}{cuerpo}</div>{pie}</body></html>')


def rango(dias):
    a, b = dias[0], dias[-1]
    return f"{a['dia_corto']} {a['num']} al {b['dia_corto']} {b['num']}/{int(b['fecha'][5:7]):02d}"


def fuente_pron(datos, extra=""):
    f = datos["archivo"]
    emis = f"{f[6:8]}/{f[4:6]}" if f else ""
    return f"{extra}Pronóstico para Pilar (Río Segundo), referencia para la zona. Fuente: SMN, modelo de pronóstico · {emis}."


def tarjetas(filas):
    return "".join(
        f'<div class="card">{i}<div><div class="ct">{t}</div><div class="cb">{b}</div></div></div>'
        for i, t, b in filas)


def story_semana(datos):
    dias = datos["dias"]
    llueve = [d for d in dias if d["mm"] >= 1]
    total = round(sum(d["mm"] for d in dias), 1)
    if not llueve:
        c1 = (icono("droplet-off"), "Semana seca", "El pronóstico no marca lluvias de importancia en la zona.")
    elif len(llueve) == 1:
        d = llueve[0]
        c1 = (icono("cloud-rain", "ic rain"), f"Lluvia: {mm_txt(d['mm'])} el {d['dia'].lower()}",
              f"Concentrada a la {d['franja_lluvia']}. El resto de la semana, casi sin lluvia.")
    else:
        c1 = (icono("cloud-rain", "ic rain"), f"Lluvia: {mm_txt(total)} en la semana",
              "Repartida entre " + lista(f"{d['dia'].lower()} ({mm_txt(d['mm'])})" for d in llueve) + ".")
    cal = max(dias, key=lambda d: d["max"])
    fre = min(dias, key=lambda d: d["min"])
    frios = [d["dia"].lower() for d in dias if d["min"] == fre["min"]]
    if frios == [cal["dia"].lower()]:
        c2b = f"El {cal['dia'].lower()} marca la máxima y la mínima más baja de la semana."
    else:
        c2b = (f"Lo más cálido, el {cal['dia'].lower()} ({cal['max']}°). "
               f"Lo más fresco, {lista('el ' + f for f in frios)} ({fre['min']}°).")
    vie = max(dias, key=lambda d: d["viento_max"])
    filas = [c1, (icono("thermometer"), f"Entre {fre['min']}° y {cal['max']}°", c2b),
             (icono("wind"), f"Viento: más fuerte el {vie['dia'].lower()}",
              f"Hasta {vie['viento_max']} km/h, del {vie['viento_desde']}.")]
    mapa = svg_mapa({d: GOLD for d in ZONA_FOCO}, puntos=[PILAR], ancho=236, alto=280)
    return pagina(
        f'<div class="cover"><div class="eyebrow">Centro de Córdoba · {e(rango(dias))}</div><div class="rule"></div>'
        f'<h1>El clima<br>de la semana</h1>'
        f'<div class="sub">Tercero Arriba · Río Segundo<br>Calamuchita</div>'
        f'<div class="mapa">{mapa}</div></div>'
        f'<div class="cards">{tarjetas(filas)}</div>',
        fuente_pron(datos))


def story_dias(datos):
    dias = datos["dias"]
    lo = min(d["min"] for d in dias)
    hi = max(d["max"] for d in dias)
    span = max(hi - lo, 1)
    filas = ""
    for d in dias:
        izq = (d["min"] - lo) / span * 100
        der = (hi - d["max"]) / span * 100
        seco = d["mm"] < 1
        filas += (
            f'<div class="row"><div class="dname">{d["dia_corto"]}<small>{d["num"]}/{int(d["fecha"][5:7]):02d}</small></div>'
            f'<div class="rain{" dry" if seco else ""}">{icono("droplet-off" if seco else "droplets", "ic" if seco else "ic rain")}{mm_txt(d["mm"])}</div>'
            f'<div class="temps"><span class="mn">{d["min"]}°</span><div class="bar"><i style="left:{izq:.1f}%;right:{der:.1f}%"></i></div><span>{d["max"]}°</span></div>'
            f'<div></div><div class="wind">{icono("wind")}Viento hasta {d["viento_max"]} km/h del {d["viento_desde"]}</div></div>')
    return pagina(
        f'<div class="eyebrow">Pronóstico día por día</div><div class="rule"></div>'
        f'<div class="card" style="margin-top:48px">{filas}</div>'
        f'<div class="note">mm = lluvia acumulada en el día. Temperaturas mínima y máxima.</div>',
        fuente_pron(datos))


def story_planificar(datos):
    dias = datos["dias"]
    secos = [d["dia"].lower() for d in dias if d["mm"] < 1]
    vie = max(dias, key=lambda d: d["viento_max"])
    mn = min(d["min"] for d in dias)
    frescos = [d["dia"].lower() for d in dias if d["min"] == mn]
    llu = max(dias, key=lambda d: d["mm"])
    filas = [
        (icono("droplet-off"), "Días secos",
         (lista(secos).capitalize() + " (menos de 1 mm).") if secos else "Ninguno: hay lluvia todos los días."),
        (icono("wind"), "Día más ventoso", f"{vie['dia']}: hasta {vie['viento_max']} km/h del {vie['viento_desde']}."),
        (icono("thermometer"), "Mínima más baja", f"{lista(frescos).capitalize()}: {mn}°."),
        (icono("cloud-rain", "ic rain"), "Día con más lluvia",
         f"{llu['dia']} a la {llu['franja_lluvia']}: {mm_txt(llu['mm'])}." if llu["mm"] >= 1
         else "No hay días con lluvia de importancia."),
    ]
    return pagina(
        f'<div class="eyebrow">La semana en datos</div><div class="rule"></div>'
        f'<h1>Para planificar</h1>'
        f'<div class="cards">{tarjetas(filas)}</div>',
        fuente_pron(datos, "El pronóstico a 4–5 días puede cambiar. Si el SMN emite una alerta para la zona, la publicamos acá. "))


def story_alerta(a):
    """a: {dia, nivel(3|4|5), evento, franjas, localidades, zonas:[{depto, nivel}],
           mapa:{DEPTO: nivel} (opcional, toda la provincia), descripcion, emision, muestra}"""
    nombre, color, tinta = NIVELES[a["nivel"]]
    por_depto = a.get("mapa") or {z["depto"]: z["nivel"] for z in a["zonas"]}
    mapa = svg_mapa({d: NIVELES[n][1] for d, n in por_depto.items()}, ancho=320, alto=360)
    chips = "".join(
        f'<span class="chip" style="background:{NIVELES[z["nivel"]][1]};color:{NIVELES[z["nivel"]][2]}">{e(z["depto"])}</span>'
        for z in a["zonas"])
    return pagina(
        f'<div class="badge" style="background:{color};color:{tinta}">{icono("triangle-alert")}{nombre} · SMN</div>'
        f'<h1 style="margin-top:36px;font-size:104px">{e(a["evento"])}</h1>'
        f'<div class="sub" style="font-size:42px;font-weight:700;color:#fff">{e(a["dia"])} · {e(a["franjas"])}</div>'
        + (f'<div class="sub" style="margin-top:12px">{e(a["localidades"])}</div>' if a.get("localidades") else "")
        + f'<div class="card"><div class="zonas">{mapa}<div class="leyenda"><div class="ct" style="margin-bottom:8px">En la zona</div>{chips}'
        + ('<div class="ley-sin"><i></i>Sin alerta</div>' if len(por_depto) < 26 else '') + '</div></div></div>'
        f'<div class="card" style="padding:36px 44px"><div class="ct">Qué se espera</div><div class="cb">{e(a["descripcion"])}</div></div>',
        f"Fuente: SMN, alerta emitida {e(a['emision'])}.", muestra=a.get("muestra", False))


def renderizar(paginas, salida):
    os.makedirs(salida, exist_ok=True)
    rutas = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
        for nombre, contenido in paginas:
            pg.set_content(contenido, wait_until="load")
            pg.wait_for_timeout(150)
            ruta = os.path.join(salida, nombre)
            pg.screenshot(path=ruta, full_page=False)
            rutas.append(ruta)
        b.close()
    return rutas


if __name__ == "__main__":
    modo, archivo, salida = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(archivo) as f:
        datos = json.load(f)
    if modo == "semana":
        paginas = [("1-clima-semana.png", story_semana(datos)),
                   ("2-dia-por-dia.png", story_dias(datos)),
                   ("3-planificar.png", story_planificar(datos))]
    else:
        alertas = datos if isinstance(datos, list) else [datos]
        paginas = [(f"alerta-{i + 1}.png", story_alerta(a)) for i, a in enumerate(alertas)]
    for r in renderizar(paginas, salida):
        print(r)
