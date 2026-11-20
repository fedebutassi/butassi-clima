// Pegar en javascript_tool con la página https://www.smn.gob.ar/alertas_area?loc=811 abierta.
// Lee las alertas de todas las áreas de Córdoba desde lo que muestra la propia página del SMN
// (cada área se carga en un iframe del mismo sitio y se lee la tabla renderizada y los textos).
// No usa el token ni llama a la API directamente. Devuelve el mismo JSON que espera alertas.py
// (updated, warnings[date, events[id, levels]], reports[event_id, levels[level, description]]).
// Guardarlo como alertas_raw.json.
const AREAS = [803,804,805,806,807,808,809,810,811,812,813,814,815,816];
const EVENTOS = [41,37,42,39,47,40,46,54,45];   // orden de filas de la tabla del SMN
const ENC = {"tormenta":41,"lluvia":37,"nevada":42,"viento":39,"viento zonda":47,"niebla":40,"polvo":46,"humo":54,"ceniza volcánica":45};
const FOCO = [803, 808, 811];   // áreas con Tercero Arriba, Río Segundo y Calamuchita: si falla una, error
const BLANCO = "rgb(255, 255, 255)";   // celda sin dato (p. ej. franjas ya pasadas de hoy)
const COLOR = {"rgb(53, 199, 149)":1,"rgb(139, 134, 196)":2,"rgb(255, 211, 87)":3,"rgb(244, 149, 61)":4,"rgb(219, 84, 97)":5};
const NIVEL_TXT = {"Amarillo":3,"Naranja":4,"Rojo":5};
const FR = ["early_morning","morning","afternoon","night"];
const MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
const pad = n => String(n).padStart(2, "0");

function leerArea(doc) {
  const up = (doc.getElementById("dateupload") || {}).textContent || "";
  const m = up.match(/(\d{1,2}) de (\w+) de ([\d.]+).*?(\d{2}):(\d{2})/);
  if (!m) throw new Error("sin fecha de emisión");
  const anio = +m[3].replace(/\./g, ""), mes = MESES.indexOf(m[2]) + 1, dia = +m[1];
  const updated = `${anio}-${pad(mes)}-${pad(dia)}T${m[4]}:${m[5]}:00-03:00`;
  const warnings = [];
  doc.querySelectorAll("#matriz table").forEach(t => {
    const th = t.querySelector('th[colspan="4"]');
    if (!th) return;                       // columna de títulos
    const dnum = +th.textContent.trim().split(" ").pop();
    const f = new Date(anio, mes - 1, dia);
    let k = 0;
    while (f.getDate() !== dnum && k++ < 10) f.setDate(f.getDate() + 1);   // primer día con ese número desde la emisión
    if (f.getDate() !== dnum) throw new Error("día ilegible: " + th.textContent);
    const filas = [...t.querySelectorAll("tbody tr.fila")];
    const events = filas.map((tr, i) => {
      const levels = {};
      [...tr.querySelectorAll("td")].forEach((td, k) => {
        const c = td.style.backgroundColor;
        if (c && c !== BLANCO && !(c in COLOR)) throw new Error("color desconocido en la tabla: " + c);
        levels[FR[k]] = COLOR[c] ?? null;
      });
      return {id: EVENTOS[i], max_level: Math.max(0, ...Object.values(levels).filter(v => v)), levels};
    });
    // solo eventos con advertencia o alerta (nivel >= 2): el verde no aporta y alarga la salida
    warnings.push({date: `${f.getFullYear()}-${pad(f.getMonth() + 1)}-${pad(f.getDate())}`,
                   events: events.filter(e => e.max_level >= 2)});
  });
  const reports = [];
  doc.querySelectorAll("h5.titulo_anuncio").forEach(h => {
    const ev = ENC[h.textContent.replace(/^(Alerta|Advertencia) por /, "").trim().toLowerCase()];
    const levels = [];
    let n = h.nextElementSibling;
    while (n && n.matches("p.cuerpo_anuncio")) {
      const [cab, ...resto] = n.innerText.split("\n");
      const lv = NIVEL_TXT[cab.replace(":", "").trim()];
      if (lv) levels.push({level: lv, description: resto.join("\n").trim()});
      n = n.nextElementSibling;
    }
    if (ev) reports.push({event_id: ev, levels});
  });
  return {updated, warnings, reports};
}

function cargar(id) {
  return new Promise(res => {
    const fr = document.createElement("iframe");
    fr.style.cssText = "position:absolute;width:1200px;height:900px;left:-9999px";
    fr.src = "/alertas_area?loc=" + id;
    const fin = v => { fr.remove(); res(v); };
    const t0 = Date.now();
    fr.onload = () => {
      const tick = () => {
        try {
          const d = fr.contentDocument;
          const listo = d.querySelector("#matriz table") && /generado a las/.test((d.getElementById("dateupload") || {}).textContent || "");
          if (listo) return setTimeout(() => {
            try { fin(leerArea(d)); } catch (e) { fin({error: String(e)}); }
          }, 500);
        } catch (e) { return fin({error: String(e)}); }
        if (Date.now() - t0 > 25000) return fin({error: "timeout"});
        setTimeout(tick, 300);
      };
      tick();
    };
    setTimeout(() => fin({error: "timeout"}), 35000);   // por si el iframe nunca termina de cargar
    document.body.appendChild(fr);
  });
}

const out = {};
for (const id of AREAS) out[id] = await cargar(id);
const malas = AREAS.filter(id => out[id].error);
if (malas.length === AREAS.length) throw new Error("no pude leer ninguna área: " + out[AREAS[0]].error);
const focoMal = FOCO.filter(id => out[id].error);
if (focoMal.length) throw new Error("no pude leer áreas de la zona foco " + focoMal.map(id => id + " (" + out[id].error + ")").join(", "));
JSON.stringify(out)
