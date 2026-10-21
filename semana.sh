#!/usr/bin/env bash
# Pronóstico semanal: baja el pron5d del SMN, resume Pilar y genera 3 stories en salida/semana/
set -euo pipefail
cd "$(dirname "$0")"
TMP=$(mktemp -d)
curl -sSf -m 60 -o "$TMP/pron5d.zip" "https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=pron5d"
unzip -o -q "$TMP/pron5d.zip" -d "$TMP"
TXT=$(ls "$TMP"/pronostico_5dias*.txt | head -1)
python3 parse_smn.py "$TXT" PILAR_OBS > "$TMP/semana.json"
python3 render.py semana "$TMP/semana.json" salida/semana
cp "$TMP/semana.json" salida/semana/semana.json
