#!/usr/bin/env bash
# Resumen semanal: lee resumen.json (armado por la tarea del viernes) y genera el carrusel en salida/resumen/
set -euo pipefail
cd "$(dirname "$0")"
ENTRADA="${1:-resumen.json}"
rm -rf salida/resumen
python3 resumen.py "$ENTRADA" salida/resumen
cp "$ENTRADA" salida/resumen/resumen.json
