"""Lee el pronóstico a 5 días de datos abiertos del SMN (pron5d) y resume por día
para una estación. Uso: python3 parse_smn.py pronostico_5diasAAAAMMDD.txt [ESTACION] > semana.json
"""
import json
import re
import sys
from collections import OrderedDict
from datetime import date

MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
         "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
PUNTOS = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]
# franja según la hora del registro
FRANJA = {0: "madrugada", 3: "madrugada", 6: "mañana", 9: "mañana",
          12: "tarde", 15: "tarde", 18: "noche", 21: "noche"}
FILA = re.compile(r"(\d{2})/([A-Z]{3})/(\d{4})\s+(\d{2})Hs\.\s+(-?[\d.]+)\s+(\d+)\s*\|\s*(\d+)\s+([\d.]+)")


def leer_estacion(path, estacion):
    with open(path, encoding="latin-1") as f:
        lineas = [l.strip() for l in f]
    filas, dentro = [], False
    for s in lineas:
        if s == estacion:
            dentro = True
            continue
        if not dentro:
            continue
        m = FILA.match(s)
        if m:
            d, mes, a, h, t, ddir, vel, mm = m.groups()
            filas.append({"fecha": date(int(a), MESES[mes], int(d)), "hora": int(h),
                          "temp": float(t), "dir": int(ddir), "vel": int(vel), "mm": float(mm)})
        elif filas and re.fullmatch(r"[A-Z0-9_]+", s):
            break
    if not filas:
        raise SystemExit(f"No encontré la estación {estacion} en {path}")
    return filas


def punto_cardinal(grados):
    return PUNTOS[int((grados % 360) / 45 + 0.5) % 8]


def etiqueta_lluvia(mm):
    if mm == 0:
        return "Sin lluvia"
    if mm < 1:
        return "Casi sin lluvia"
    if mm < 5:
        return "Lluvias débiles"
    if mm < 15:
        return "Lluvias moderadas"
    return "Lluvias fuertes"


def resumir(filas):
    dias = OrderedDict()
    for r in filas:
        d = dias.setdefault(r["fecha"], {"temps": [], "mm": 0.0, "viento": (0, 0), "franjas": {}})
        d["temps"].append(r["temp"])
        d["mm"] += r["mm"]
        fr = FRANJA[r["hora"]]
        d["franjas"][fr] = d["franjas"].get(fr, 0.0) + r["mm"]
        if r["vel"] > d["viento"][0]:
            d["viento"] = (r["vel"], r["dir"])
    salida = []
    for f, d in dias.items():
        if len(d["temps"]) < 8:  # día incompleto: no se resume
            continue
        mm = round(d["mm"], 1)
        franja_lluvia = max(d["franjas"], key=d["franjas"].get) if mm >= 1 else None
        salida.append({
            "fecha": f.isoformat(),
            "dia": DIAS[f.weekday()],
            "dia_corto": DIAS_CORTOS[f.weekday()],
            "num": f.day,
            "min": round(min(d["temps"])),
            "max": round(max(d["temps"])),
            "mm": mm,
            "lluvia": etiqueta_lluvia(mm),
            "franja_lluvia": franja_lluvia,
            "viento_max": d["viento"][0],
            "viento_desde": punto_cardinal(d["viento"][1]),
        })
    return salida


if __name__ == "__main__":
    path = sys.argv[1]
    estacion = sys.argv[2] if len(sys.argv) > 2 else "PILAR_OBS"
    emision = re.search(r"(\d{8})", path)
    print(json.dumps({"estacion": estacion,
                      "archivo": emision.group(1) if emision else None,
                      "dias": resumir(leer_estacion(path, estacion))},
                     ensure_ascii=False, indent=1))
