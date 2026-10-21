#!/usr/bin/env bash
# Alertas: recibe el JSON crudo de smn_alertas.js y la fecha de hoy (AAAA-MM-DD).
# Genera una story por alerta de hoy/mañana en la zona foco, en salida/alertas/. Sin alertas: no genera nada.
set -euo pipefail
cd "$(dirname "$0")"
RAW="$1"; HOY="$2"
mkdir -p salida/alertas && rm -f salida/alertas/*.png
python3 alertas.py "$RAW" "$HOY" > salida/alertas/alertas.json
N=$(python3 -c "import json;print(len(json.load(open('salida/alertas/alertas.json'))))")
echo "alertas en zona foco: $N"
if [ "$N" -gt 0 ]; then python3 render.py alerta salida/alertas/alertas.json salida/alertas; fi
