"""Mapa SVG de los departamentos de Córdoba (geometrías IGN).
svg_mapa(colores={"TERCERO ARRIBA": "#f0c031"}, puntos=[(-63.88, -31.68)], ancho=..., alto=...)
"""
import json
import math
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
_GEO = None


def norm(nombre):
    s = nombre.upper().strip()
    for a, b in zip("ÁÉÍÓÚÜ", "AEIOUU"):
        s = s.replace(a, b)
    return s


def _geo():
    global _GEO
    if _GEO is None:
        with open(os.path.join(AQUI, "assets", "cordoba-departamentos.geojson")) as f:
            _GEO = json.load(f)["features"]
    return _GEO


def _anillos(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [r for poly in geom["coordinates"] for r in poly]


def svg_mapa(colores, puntos=(), ancho=400, alto=480, relleno="rgba(255,255,255,.07)",
             borde="rgba(255,255,255,.35)", grosor=1.4, margen=6):
    feats = _geo()
    todos = [p for f in feats for r in _anillos(f["geometry"]) for p in r]
    lon0, lon1 = min(p[0] for p in todos), max(p[0] for p in todos)
    lat0, lat1 = min(p[1] for p in todos), max(p[1] for p in todos)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    w, h = (lon1 - lon0) * k, lat1 - lat0
    esc = min((ancho - 2 * margen) / w, (alto - 2 * margen) / h)
    ox = (ancho - w * esc) / 2
    oy = (alto - h * esc) / 2

    def xy(lon, lat):
        return ox + (lon - lon0) * k * esc, oy + (lat1 - lat) * esc

    colores = {norm(k2): v for k2, v in colores.items()}
    base, arriba = [], []
    for f in feats:
        nombre = norm(f["properties"]["departamento"])
        d = []
        for r in _anillos(f["geometry"]):
            pts, ult = [], None
            for lon, lat in r:
                x, y = xy(lon, lat)
                if ult is None or abs(x - ult[0]) + abs(y - ult[1]) > 1.2:
                    pts.append(f"{x:.1f} {y:.1f}")
                    ult = (x, y)
            if len(pts) > 2:
                d.append("M" + "L".join(pts) + "Z")
        color = colores.get(nombre)
        path = (f'<path d="{"".join(d)}" fill="{color or relleno}" stroke="{borde}" '
                f'stroke-width="{grosor}" stroke-linejoin="round"/>')
        (arriba if color else base).append(path)
    marcas = ""
    for lon, lat in puntos:
        x, y = xy(lon, lat)
        marcas += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="rgba(255,255,255,.25)"/>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#ffffff"/>')
    return (f'<svg viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" xmlns="http://www.w3.org/2000/svg">'
            + "".join(base) + "".join(arriba) + marcas + "</svg>")
