// Guarda 15 (docs/qa/27 §4): el reloj del navegador del arnés tiene que ser el
// reloj del mundo simulado. Abre UN navegador con `abrirNavegador` —el mismo
// camino que usan las personas—, entra a la tienda y compara el `new Date()` de
// la página con `GET /__sim/reloj`.
//
// Falla si:
//   · el navegador se desvía más de un día del mundo (el caso real: el mundo en
//     2027 y la persona midiendo en la fecha de la máquina);
//   · el reloj queda congelado (`setFixedTime` o `install` matarían los
//     temporizadores de la aplicación y con ellos media pantalla).
//
// No deja rastro: borra la bitácora y el perfil que crea al pasar.
// Imprime una sola línea, "OK …" o "FALLA …", que `sim/comprobar.sh` reexpone.
import fs from 'node:fs';
import { abrirNavegador, hoy, FRONT } from './persona.mjs';

const RAIZ = '/home/user/gamification-multinivel/sim';
const PERFIL = 'comprobador-reloj';
const PERSONA = 'Comprobador del reloj';
const DIA_MS = 86400000;
const TOLERANCIA_DIAS = 1;

let veredicto = null;
let bitacoraEscrita = null;

async function comprobar() {
  const mundoAntes = await hoy().catch(() => null);
  if (!mundoAntes) return 'FALLA el mundo no da la hora en GET /__sim/reloj: el arnés no puede fijar el reloj del navegador';

  const { pagina, cerrar } = await abrirNavegador({ perfil: PERFIL, persona: PERSONA, rol: 'cliente' });
  let primera, mundo, avanceMs;
  try {
    await pagina.goto(`${FRONT}/#/tienda`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    primera = await pagina.evaluate(() => new Date().toISOString());
    mundo = await hoy();
    await pagina.waitForTimeout(1500);
    const segunda = await pagina.evaluate(() => new Date().toISOString());
    avanceMs = new Date(segunda) - new Date(primera);
  } finally {
    bitacoraEscrita = await cerrar().catch(() => null);
  }

  const desvioDias = Math.abs(new Date(primera) - new Date(mundo)) / DIA_MS;
  if (desvioDias > TOLERANCIA_DIAS) {
    return `FALLA el navegador vive en ${primera} y el mundo en ${mundo} (${desvioDias.toFixed(1)} días de desvío): revisa fijarRelojDelMundo() en sim/lib/persona.mjs`;
  }
  if (avanceMs < 500) {
    return `FALLA el reloj del navegador está congelado (${avanceMs} ms en 1.5 s): usa clock.setSystemTime, no setFixedTime ni install`;
  }
  return `OK el navegador está en la hora del mundo (${primera} vs ${mundo}) y el reloj corre`;
}

try {
  veredicto = await comprobar();
} catch (e) {
  veredicto = 'FALLA no se pudo comprobar el reloj del navegador: ' + String((e && e.message) || e).replace(/\s+/g, ' ').slice(0, 160);
}

// Ni bitácora ni perfil: esto es una comprobación, no una ronda.
try {
  if (bitacoraEscrita) fs.rmSync(bitacoraEscrita, { force: true });
  fs.rmSync(`${RAIZ}/metricas/${PERSONA.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.json`, { force: true });
  fs.rmSync(`${RAIZ}/perfiles/${PERFIL}`, { recursive: true, force: true });
} catch {}

console.log(veredicto);
process.exit(veredicto.startsWith('OK') ? 0 : 1);
