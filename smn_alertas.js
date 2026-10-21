// Pegar en javascript_tool con la página https://www.smn.gob.ar/alertas_area?loc=811 abierta.
// Devuelve JSON con las alertas de todas las áreas de Córdoba (texto). Guardarlo como alertas_raw.json.
await new Promise(r => setTimeout(r, 3000));
const H = {"Accept": "application/json", "Authorization": "JWT " + localStorage.getItem('token')};
const out = {};
for (const id of [803,804,805,806,807,808,809,810,811,812,813,814,815,816]) {
  out[id] = await fetch(UrlWs + '/warning/alert/area/' + id, {headers: H}).then(r => r.json()).catch(e => ({error: String(e)}));
}
JSON.stringify(out)
