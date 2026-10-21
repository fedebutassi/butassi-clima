"""Convierte las alertas crudas del SMN (salida de smn_alertas.js) en datos para story_alerta.
Uso: python3 alertas.py alertas_raw.json AAAA-MM-DD > alertas.json
Solo genera alertas para HOY y MAÑANA (respecto de la fecha dada) que toquen la zona foco.
Salida: lista (vacía si no hay nada para publicar).
"""
import json
import re
import sys
from datetime import date, timedelta

# Áreas del SMN en Córdoba -> departamentos (georef del SMN)
AREAS = {
    803: ["Calamuchita", "Santa María"],          # zonas bajas
    804: ["Cruz del Eje", "Minas"],               # zonas bajas
    805: ["Capital"],
    806: ["Colón", "Totoral"],                    # zonas bajas
    807: ["General Roca", "Presidente Roque Sáenz Peña"],
    808: ["Calamuchita", "Río Cuarto"],           # zonas serranas
    809: ["General San Martín", "Marcos Juárez", "Unión"],
    810: ["Juárez Celman", "Río Cuarto"],         # zonas bajas
    811: ["Río Primero", "Río Segundo", "Tercero Arriba"],
    812: ["San Justo"],
    813: ["Cruz del Eje", "Minas", "Pocho", "San Alberto", "San Javier"],  # serranas
    814: ["Pocho", "San Alberto", "San Javier"],
    815: ["Ischilín", "Río Seco", "Sobremonte", "Tulumba"],
    816: ["Punilla", "Colón", "Totoral", "Santa María"],                   # serranas
}
FOCO = ["Tercero Arriba", "Río Segundo", "Calamuchita"]  # Butassi: Río Tercero y Corralito (Tercero Arriba)
LOCALIDADES = {"Tercero Arriba": ["Río Tercero", "Corralito", "Almafuerte"],
               "Río Segundo": ["Oncativo", "Pilar"],
               "Calamuchita": ["Santa Rosa de Calamuchita", "Embalse"]}
# Catálogo oficial (matriz_alertas_area.js del SMN)
EVENTOS = {41: "Tormentas", 37: "Lluvias", 42: "Nevadas", 39: "Viento", 47: "Viento zonda",
           40: "Niebla", 46: "Polvo", 54: "Humo", 45: "Ceniza volcánica"}
NOMBRE_NIVEL = {3: "Amarilla", 4: "Naranja", 5: "Roja"}
FRANJAS = [("early_morning", "madrugada"), ("morning", "mañana"), ("afternoon", "tarde"), ("night", "noche")]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def nivel(v):
    return min(v, 5) if v and v >= 3 else 0


def resumen_reporte(texto):
    """Extrae solo datos presentes en el texto oficial: mm, ráfagas, granizo."""
    partes = []
    mm = re.search(r"entre (\d+) y (\d+) ?mm", texto)
    if mm:
        partes.append(f"entre {mm.group(1)} y {mm.group(2)} mm")
    raf = re.search(r"(?:ráfagas|rafagas)[^.]*?(\d+) ?km/h", texto)
    if raf:
        partes.append(f"ráfagas de hasta {raf.group(1)} km/h")
    if "granizo" in texto.lower():
        partes.append("granizo")
    if not partes:
        return texto.split(".")[0] + "."
    if len(partes) == 1:
        return partes[0]
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def procesar(raw, hoy):
    fechas = {hoy.isoformat(): "hoy", (hoy + timedelta(days=1)).isoformat(): "mañana"}
    salida = []
    emision = None
    for f, cuando in fechas.items():
        # depto -> evento -> nivel ; franjas por evento en zona foco ; reportes por evento/nivel
        por_evento = {}
        for aid, data in raw.items():
            aid = int(aid)
            if not isinstance(data, dict) or "warnings" not in data:
                continue
            emision = emision or data.get("updated")
            reportes = {(r["event_id"], l["level"]): l["description"]
                        for r in data.get("reports", []) for l in r["levels"]}
            for w in data["warnings"]:
                if w["date"] != f:
                    continue
                for ev in w["events"]:
                    niveles = {k: nivel(ev["levels"].get(k)) for k, _ in FRANJAS}
                    mx = max(niveles.values())
                    if not mx:
                        continue
                    e = por_evento.setdefault(ev["id"], {"deptos": {}, "foco": {}, "franjas": set(), "reportes": {}})
                    for d in AREAS.get(aid, []):
                        e["deptos"][d] = max(e["deptos"].get(d, 0), mx)
                        if d in FOCO:
                            e["foco"][d] = max(e["foco"].get(d, 0), mx)
                            e["franjas"].update(k for k, v in niveles.items() if v)
                            if (ev["id"], mx) in reportes:
                                e["reportes"].setdefault(mx, {})[d] = reportes[(ev["id"], mx)]
        for ev_id, e in por_evento.items():
            if not e["foco"]:
                continue
            dia = date.fromisoformat(f)
            lineas = []
            for lv in sorted(e["reportes"], reverse=True):
                deptos = list(e["reportes"][lv])
                texto = next(iter(e["reportes"][lv].values()))
                quien = deptos[0] if len(deptos) == 1 else " y ".join(deptos)
                lineas.append(f"{NOMBRE_NIVEL[lv]} en {quien}: {resumen_reporte(texto)}.")
            locs = [l for d in FOCO if d in e["foco"] for l in LOCALIDADES[d]][:4]
            salida.append({
                "fecha": f,
                "cuando": cuando,
                "dia": f"{DIAS[dia.weekday()]} {dia.day}",
                "nivel": max(e["foco"].values()),
                "evento": EVENTOS.get(ev_id, "Alerta meteorológica"),
                "franjas": unir([n for k, n in FRANJAS if k in e["franjas"]]),
                "localidades": " · ".join(locs),
                "zonas": [{"depto": d, "nivel": e["foco"][d]} for d in FOCO if d in e["foco"]],
                "mapa": e["deptos"],
                "descripcion": " ".join(lineas),
                "emision": emision_txt(emision),
            })
    return salida


def unir(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]


def emision_txt(iso):
    if not iso:
        return ""
    return f"{iso[8:10]}/{iso[5:7]} {iso[11:16]}"


if __name__ == "__main__":
    with open(sys.argv[1]) as fh:
        raw = json.load(fh)
    hoy = date.fromisoformat(sys.argv[2])
    print(json.dumps(procesar(raw, hoy), ensure_ascii=False, indent=1))
