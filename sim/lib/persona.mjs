// Arnés mínimo para un agente-persona. Todo lo que hace es abrir un navegador
// limpio y darle "ojos" (texto y controles visibles), "manos" (Playwright) y
// un buzón de correo. No sabe nada de la app.
import { chromium } from 'playwright';
import fs from 'node:fs';

export const FRONT = 'http://localhost:4321';
export const API = 'http://localhost:4400';

export async function abrirNavegador({ movil = false, perfil = 'persona' } = {}) {
  const navegador = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox'] });
  const dir = `/home/user/gamification-multinivel/sim/perfiles/${perfil}`;
  fs.mkdirSync(dir, { recursive: true });
  const ctx = await navegador.newContext({
    viewport: movil ? { width: 390, height: 844 } : { width: 1366, height: 900 },
    isMobile: movil, hasTouch: movil,
    userAgent: movil ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1' : undefined,
    storageState: fs.existsSync(`${dir}/estado.json`) ? `${dir}/estado.json` : undefined,
  });
  const pagina = await ctx.newPage();
  const consola = [];
  pagina.on('pageerror', (e) => consola.push('JS: ' + String(e).slice(0, 160)));
  pagina.on('response', (r) => { if (r.url().includes(':4400') && r.status() >= 400) consola.push(`HTTP ${r.status()} ${r.request().method()} ${r.url().replace(API, '')}`); });
  // Guarda la sesión al cerrar, como haría un navegador de verdad entre días.
  const cerrar = async () => { try { await ctx.storageState({ path: `${dir}/estado.json` }); } catch {} await navegador.close(); };
  return { navegador, ctx, pagina, consola, cerrar };
}

/** El texto tal y como lo leería una persona. */
export async function leer(pagina) {
  return (await pagina.innerText('body')).replace(/\n{3,}/g, '\n\n');
}

/** Botones, enlaces y campos visibles, con su etiqueta. */
export async function controles(pagina) {
  return pagina.evaluate(() => {
    const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
    const et = (el) => (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.title || '').trim().replace(/\s+/g, ' ').slice(0, 70);
    const out = { botones: [], enlaces: [], campos: [] };
    document.querySelectorAll('button').forEach((e) => visible(e) && out.botones.push(et(e)));
    document.querySelectorAll('a[href]').forEach((e) => visible(e) && out.enlaces.push(et(e) + ' → ' + e.getAttribute('href')));
    document.querySelectorAll('input,select,textarea').forEach((e) => visible(e) && out.campos.push({ tipo: e.type || e.tagName.toLowerCase(), etiqueta: et(e) }));
    return out;
  });
}

export async function captura(pagina, nombre) {
  const ruta = `/home/user/gamification-multinivel/sim/capturas/${nombre}.png`;
  await pagina.screenshot({ path: ruta, fullPage: false });
  return ruta;
}

/** El correo de esta persona. Es lo que la plataforma le ha mandado; nada más. */
export async function leerCorreo(correo) {
  const r = await fetch(`${API}/__sim/buzon/${encodeURIComponent(correo)}`);
  const lista = await r.json();
  return lista.map((m) => ({ n: m.n, fecha: m.fecha, asunto: m.asunto, texto: m.texto, enlaces: m.enlaces }));
}

/** Fecha "de hoy" en el mundo simulado. */
export async function hoy() {
  const r = await fetch(`${API}/__sim/reloj`); return (await r.json()).ahora;
}
