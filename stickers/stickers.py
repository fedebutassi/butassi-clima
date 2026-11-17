"""Stickers impresos (calcos) de Butassi Hnos.

Uso:  python3 stickers/stickers.py            -> stickers/salida/*.png (300 dpi, fondo transparente)
                                                  stickers/salida/plancha-A4.pdf (todos, tamaño real)
Cada sticker lleva un borde blanco de 3 mm que funciona como línea de corte (troquel por contorno).
Colores del sistema social de Butassi: verde oscuro #1A4A1E, verde logo #2E7D32,
dorado institucional #D4A017 solo en la bajada "Servicios de Apoyo Agrícola".
"""
import base64
import os

from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SALIDA = os.path.join(AQUI, "salida")
DPI = 300
ESCALA = DPI / 96  # px CSS -> px a 300 dpi


def b64(ruta):
    with open(ruta, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


LOGO = b64(os.path.join(RAIZ, "assets", "logo.png"))
LOGO_B = b64(os.path.join(AQUI, "logo-blanco.png"))
QR = b64(os.path.join(AQUI, "qr-instagram.png"))
FUENTE = b64(os.path.join(RAIZ, "assets", "fonts", "OpenSans.ttf")).replace("image/png", "font/ttf")

IG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
      'stroke-linejoin="round"><rect x="2.5" y="2.5" width="19" height="19" rx="5.5"/><circle cx="12" cy="12" r="4.3"/>'
      '<circle cx="17.6" cy="6.4" r="1.1" fill="currentColor" stroke="none"/></svg>')

CSS = f"""
@font-face{{font-family:"Open Sans";src:url({FUENTE}) format("truetype");font-weight:300 800;font-stretch:75% 100%}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{background:transparent}}
body{{font-family:"Open Sans",Arial,sans-serif;-webkit-font-smoothing:antialiased}}
.s{{display:inline-block;background:#fff;padding:3mm;box-shadow:none}}
.verde{{background:#1A4A1E;color:#fff}}
"""

# Cada sticker: (archivo, ancho_mm, alto_mm, html interno). El borde blanco de 3 mm se suma por fuera.
STICKERS = [
    ("1-logo", 90, 42, f"""
<div class="s" style="border-radius:9mm">
 <div style="width:90mm;height:42mm;border-radius:6mm;border:1.2mm solid #2E7D32;display:flex;align-items:center;justify-content:center;background:#fff">
  <img src="{LOGO}" style="width:72mm">
 </div></div>"""),

    ("2-sello", 70, 70, f"""
<div class="s" style="border-radius:50%">
 <div class="verde" style="width:70mm;height:70mm;border-radius:50%;position:relative;display:flex;align-items:center;justify-content:center">
  <svg viewBox="0 0 700 700" style="position:absolute;inset:0;width:100%;height:100%">
   <defs>
    <path id="arr" d="M 95 350 A 255 255 0 0 1 605 350"/>
    <path id="aba" d="M 70 350 A 280 280 0 0 0 630 350"/>
   </defs>
   <circle cx="350" cy="350" r="318" fill="none" stroke="#fff" stroke-width="6"/>
   <circle cx="350" cy="350" r="222" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="3"/>
   <text font-family="Open Sans" font-weight="700" font-size="31" letter-spacing="3" fill="#D4A017" text-anchor="middle">
    <textPath href="#arr" startOffset="50%">SERVICIOS DE APOYO AGRÍCOLA</textPath></text>
   <text font-family="Open Sans" font-weight="600" font-size="30" letter-spacing="5" fill="#fff" text-anchor="middle">
    <textPath href="#aba" startOffset="50%">RÍO TERCERO · CORRALITO</textPath></text>
   <circle cx="80" cy="350" r="7" fill="#D4A017"/><circle cx="620" cy="350" r="7" fill="#D4A017"/>
  </svg>
  <img src="{LOGO_B}" style="width:36mm;position:relative">
 </div></div>"""),

    ("3-qr-instagram", 60, 82, f"""
<div class="s" style="border-radius:8mm">
 <div class="verde" style="width:60mm;height:82mm;border-radius:5mm;display:flex;flex-direction:column;align-items:center;padding:5mm 5mm 0">
  <img src="{LOGO_B}" style="width:38mm">
  <div style="margin-top:3mm;font-size:13pt;font-weight:700;letter-spacing:.02em">Seguinos</div>
  <div style="font-size:7.5pt;opacity:.85;text-align:center;line-height:1.3">Pizarra de Rosario todos los días</div>
  <div style="margin-top:3mm;background:#fff;border-radius:3mm;padding:3mm"><img src="{QR}" style="width:30mm;display:block"></div>
  <div style="margin-top:3mm;display:flex;align-items:center;gap:1.5mm;font-size:11pt;font-weight:700">
   <span style="width:4.6mm;height:4.6mm;display:inline-block">{IG}</span>@butassihnos</div>
 </div></div>"""),

    ("4-camioneta", 150, 50, f"""
<div class="s" style="border-radius:9mm">
 <div class="verde" style="width:150mm;height:50mm;border-radius:6mm;display:flex;align-items:center;padding:0 9mm;gap:9mm">
  <img src="{LOGO_B}" style="width:62mm">
  <div style="width:.5mm;height:30mm;background:rgba(255,255,255,.4)"></div>
  <div style="display:flex;flex-direction:column;gap:1.6mm">
   <div style="font-size:15pt;font-weight:700;line-height:1.15">Cereales<br>Agroquímicos</div>
   <div style="font-size:7.5pt;font-weight:700;letter-spacing:.06em;color:#D4A017">SERVICIOS DE APOYO AGRÍCOLA</div>
   <div style="font-size:9pt;display:flex;align-items:center;gap:1.4mm">
    <span style="width:3.6mm;height:3.6mm;display:inline-block">{IG}</span><b>@butassihnos</b></div>
   <div style="font-size:8.5pt;opacity:.9">butassihnos.com.ar</div>
  </div>
 </div></div>"""),
]


def pagina(cuerpo):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{cuerpo}</body></html>'


def main():
    os.makedirs(SALIDA, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(device_scale_factor=ESCALA, viewport={"width": 800, "height": 800})
        for nombre, *_ , html in STICKERS:
            pg.set_content(pagina(f'<div id="x" style="display:inline-block">{html}</div>'), wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            ruta = os.path.join(SALIDA, f"{nombre}.png")
            pg.locator("#x").screenshot(path=ruta, omit_background=True)
            print(ruta)
        # Plancha A4 a tamaño real, para imprenta o para imprimir de prueba.
        cuerpo = "".join(f'<div style="display:inline-block;margin:4mm;vertical-align:top">{h}</div>' for *_, h in STICKERS)
        pg.set_content(pagina(f'<div style="padding:8mm">{cuerpo}</div>'), wait_until="load")
        pg.evaluate("document.fonts.ready")
        pdf = os.path.join(SALIDA, "plancha-A4.pdf")
        pg.pdf(path=pdf, format="A4", print_background=True)
        print(pdf)
        b.close()


if __name__ == "__main__":
    main()
