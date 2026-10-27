# butassi-clima

Stories de clima (1080×1920) para @butassihnos: pronóstico semanal y alertas del SMN para la zona
de Butassi Hermanos (Río Tercero y Corralito, Tercero Arriba; también Río Segundo y Calamuchita).

## Requisitos
- Python 3 con `playwright` y Chromium (`pip install playwright && playwright install chromium`).
- Fuente Inter instalada (si no está, usa la del sistema).
- Acceso de red a `ssl.smn.gob.ar` (pronóstico). Las alertas se leen con el navegador de Claude Desktop.

## Pronóstico semanal
```
./semana.sh            # -> salida/semana/1-clima-semana.png, 2-dia-por-dia.png, 3-planificar.png
```
Fuente: datos abiertos del SMN (pron5d), estación PILAR_OBS (la más cercana a la zona; no hay punto en Río Tercero).
Es salida de modelo numérico: sin probabilidades ni "tormenta"; las piezas lo dicen en el pie.

## Alertas
1. Abrir https://www.smn.gob.ar/alertas_area?loc=811 en el navegador integrado y ejecutar `smn_alertas.js`.
2. Guardar el resultado como `alertas_raw.json`.
3. `./alerta.sh alertas_raw.json AAAA-MM-DD` → una story por alerta de hoy/mañana que toque la zona foco.

Niveles: 3 amarilla · 4 naranja · ≥5 roja. Eventos según el catálogo del propio SMN (41 tormentas, 37 lluvias, 39 viento…).
La descripción solo usa datos del texto oficial (mm, ráfagas, granizo).

## Resumen semanal (carrusel de feed, viernes)
```
./resumen.sh resumen.json   # -> salida/resumen/1-tapa.png, 2-precios.png, 3..-tema.png, N-cierre.png
```
Placas 1080×1350 (4:5): tapa, pizarra de Rosario lunes vs. viernes, 0 a 2 temas y cierre.
Sigue el design system de Butassi Hnos. (verdes de marca, dorado Cosecha como acento, tarjetas blancas)
con foto de fondo y lavado verde. Fondos en `assets/fondos/` (ver su README); si falta uno, usa `campo.jpg`.
`resumen.json` lo arma la tarea programada del viernes con datos verificados en fuente primaria;
el formato está documentado arriba de `resumen.py`. La variación de precios la calcula el script.
Si un texto es demasiado largo o no entra en la placa, el script termina con error y dice qué acortar.
Para probar: `./resumen.sh tests/resumen_muestra.json` (sale marcada "MUESTRA · NO PUBLICAR").

## Archivos
- `parse_smn.py` resumen diario del pron5d · `alertas.py` alertas → datos de story · `render.py` plantillas y PNG
- `mapa.py` mapa de departamentos (geometrías IGN en `assets/`) · `assets/logo.png` logo · `assets/icons/` Lucide (ISC)
- `tests/` datos reales de ejemplo (21/10/2026) para probar sin red.
