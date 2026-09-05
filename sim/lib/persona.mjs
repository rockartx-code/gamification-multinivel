// Arnés de un agente-persona. Le da "ojos" (texto y controles visibles), "manos"
// (Playwright), un buzón de correo y una bitácora que se lleva sola: cuenta cada
// clic, cada tecla, cada pantalla y cuánto tardó en tocar algo después de que la
// pantalla apareció. No sabe nada de la app.
import { chromium } from 'playwright';
import fs from 'node:fs';

export const FRONT = 'http://localhost:4321';
export const API = 'http://localhost:4400';
const RAIZ = '/home/user/gamification-multinivel/sim';

// Se inyecta antes de cualquier script de la página. Cuenta la interacción real,
// venga del teclado, de un locator o de un clic directo.
const SONDA = () => {
  const w = window;
  if (w.__m) return;
  const leer = (k, x) => { try { return JSON.parse(sessionStorage.getItem(k)) ?? x; } catch { return x; } };
  const acc = leer('__m_acc', {});
  w.__m = {
    clics: acc.clics || 0, teclas: acc.teclas || 0, envios: acc.envios || 0,
    campos: acc.campos || {}, recargas: acc.recargas || 0, atrases: acc.atrases || 0,
    pantallas: leer('__m_pant', []), ultimoClic: null,
  };
  const persistir = () => {
    try {
      const { clics, teclas, envios, campos, recargas, atrases } = w.__m;
      sessionStorage.setItem('__m_acc', JSON.stringify({ clics, teclas, envios, campos, recargas, atrases }));
      sessionStorage.setItem('__m_pant', JSON.stringify(w.__m.pantallas.slice(-200)));
    } catch {}
  };
  const nuevaPantalla = (comoLlego) => {
    const p = { ruta: location.hash || location.pathname, desde: Date.now(), primerClicMs: null, clics: 0, comoLlego };
    w.__m.pantallas.push(p); persistir();
    return p;
  };
  const actual = () => w.__m.pantallas[w.__m.pantallas.length - 1];
  try {
    if (sessionStorage.getItem('__m_url') === location.href) { w.__m.recargas++; }
    sessionStorage.setItem('__m_url', location.href);
  } catch {}
  nuevaPantalla('carga');
  addEventListener('hashchange', () => nuevaPantalla('navegación'));
  addEventListener('popstate', () => {
    // El router dispara popstate al arrancar: solo cuenta como "atrás" si la
    // pantalla llevaba un rato abierta.
    const p = actual();
    if (p && Date.now() - p.desde > 1500) { w.__m.atrases++; nuevaPantalla('atrás'); }
  });
  addEventListener('click', (e) => {
    w.__m.clics++;
    const p = actual();
    if (p) { p.clics++; if (p.primerClicMs === null) p.primerClicMs = Date.now() - p.desde; }
    const et = (e.target.closest && e.target.closest('button,a,label,[role=button]')) || e.target;
    const t = ((et && (et.innerText || et.value)) || '').trim().slice(0, 60);
    if (t) w.__m.ultimoClic = t;
    persistir();
  }, true);
  addEventListener('keydown', (e) => {
    const t = e.target.tagName;
    if (t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') { w.__m.teclas++; persistir(); }
  }, true);
  addEventListener('change', (e) => {
    const el = e.target;
    const k = el.name || el.id || el.placeholder;
    if (k) { w.__m.campos[k] = true; persistir(); }
  }, true);
  addEventListener('submit', () => { w.__m.envios++; persistir(); }, true);
};

/**
 * Pone el reloj del navegador en la hora del mundo simulado (`GET /__sim/reloj`).
 *
 * Guarda 15 de `docs/qa/27` §4: sin esto la persona navega en la fecha real de la
 * máquina mientras el backend vive en 2027, y todo lo que la pantalla calcula con
 * `new Date()` —el mes contable, "días desde la última compra", el selector de
 * meses— sale de otro mundo. Cuatro hallazgos de la ronda 6 eran esto, no del
 * producto.
 *
 * Se llama ANTES de abrir la página, para que el reloj ya esté puesto en el primer
 * script que corra. El reloj queda **corriendo**, no congelado: `setSystemTime`
 * mueve el origen y el tiempo sigue fluyendo desde ahí (`setFixedTime` e `install`
 * lo detendrían y con él los temporizadores de la aplicación).
 *
 * @returns {Promise<Date|null>} la hora del mundo que se fijó, o null si no se pudo.
 */
export async function fijarRelojDelMundo(ctx, consola = []) {
  let iso;
  try { iso = await hoy(); }
  catch (e) { consola.push('RELOJ: no se pudo leer /__sim/reloj (' + String(e).slice(0, 80) + '); el navegador se queda en la hora real'); return null; }
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) { consola.push('RELOJ: /__sim/reloj devolvió una fecha ilegible: ' + String(iso).slice(0, 40)); return null; }
  if (ctx.clock && typeof ctx.clock.setSystemTime === 'function') {
    await ctx.clock.setSystemTime(t);            // Playwright >= 1.45
  } else {
    // Playwright sin `clock`: se desplaza Date a mano, con el mismo criterio.
    await ctx.addInitScript(`(() => {
      const Real = Date;
      const desfase = ${t.getTime()} - Real.now();
      function Falso(...a) {
        if (!(this instanceof Falso)) return new Real(Real.now() + desfase).toString();
        return a.length ? new Real(...a) : new Real(Real.now() + desfase);
      }
      Falso.prototype = Real.prototype;
      Falso.now = () => Real.now() + desfase;
      Falso.parse = Real.parse.bind(Real);
      Falso.UTC = Real.UTC.bind(Real);
      window.Date = Falso;
    })()`);
  }
  return t;
}

/**
 * Abre un navegador limpio con la bitácora enganchada.
 * @param {{movil?:boolean, perfil?:string, persona?:string, rol?:string}} opciones
 */
export async function abrirNavegador({ movil = false, perfil = 'persona', persona = perfil, rol = 'cliente' } = {}) {
  const navegador = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-sandbox'] });
  const dir = `${RAIZ}/perfiles/${perfil}`;
  fs.mkdirSync(dir, { recursive: true });
  const ctx = await navegador.newContext({
    viewport: movil ? { width: 390, height: 844 } : { width: 1366, height: 900 },
    isMobile: movil, hasTouch: movil,
    userAgent: movil ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1' : undefined,
    storageState: fs.existsSync(`${dir}/estado.json`) ? `${dir}/estado.json` : undefined,
  });
  await ctx.addInitScript(SONDA);
  const consola = [];
  // El navegador vive en el día del mundo simulado, no en el de la máquina.
  const relojDelMundo = await fijarRelojDelMundo(ctx, consola);
  const pagina = await ctx.newPage();
  pagina.on('pageerror', (e) => consola.push('JS: ' + String(e).slice(0, 160)));
  pagina.on('response', (r) => {
    if (r.url().includes(':4400') && r.status() >= 400) consola.push(`HTTP ${r.status()} ${r.request().method()} ${r.url().replace(API, '')}`);
  });
  pagina.on('dialog', (d) => consola.push(`DIÁLOGO DEL NAVEGADOR (${d.type()}): ${d.message().slice(0, 120)}`));

  const b = bitacora({ persona, rol, movil, consola });
  const cerrar = async () => {
    await b.absorber(pagina).catch(() => {});
    try { await ctx.storageState({ path: `${dir}/estado.json` }); } catch {}
    await navegador.close();
    return b.guardar();
  };
  return { navegador, ctx, pagina, consola, bitacora: b, cerrar, relojDelMundo };
}

/**
 * La bitácora de la persona. Lo que no se puede contar solo (lo que quería
 * hacer, lo que pensó, lo que preguntó, lo que sintió) se registra a mano;
 * el resto lo cuenta la sonda del navegador.
 */
export function bitacora({ persona, rol = 'cliente', movil = false, consola = [] }) {
  const t0 = Date.now();
  const datos = {
    persona, rol, dispositivo: movil ? 'celular' : 'escritorio',
    inicio: new Date().toISOString(),
    tareas: [], emociones: [], preguntas: [], estetica: null,
    totales: { clics: 0, teclas: 0, envios: 0, campos: 0, pantallas: 0, recargas: 0, atrases: 0 },
    pantallas: [], erroresEnPantalla: [], consola: [], notas: [],
  };
  let tareaActual = null;
  let ultimoEvento = t0;
  const seg = () => Math.round((Date.now() - t0) / 1000);
  const desdeUltimo = () => { const d = Math.round((Date.now() - ultimoEvento) / 1000); ultimoEvento = Date.now(); return d; };

  const api = {
    datos,
    /** Lo que la persona quiere lograr ahora, con sus palabras. */
    tarea(quiero, { esperaba = null } = {}) {
      if (tareaActual) api.abandonar('empezó otra cosa sin terminar esta');
      tareaActual = {
        quiero, esperaba, t: seg(), segundos: null, logrado: null,
        clicsBase: datos.totales.clics, teclasBase: datos.totales.teclas,
        clics: null, teclas: null, pantallasBase: datos.totales.pantallas, pantallas: null,
        pensamientos: [], dudas: [], atorones: [], preguntas: [], reintentos: 0,
        facilidad: null, confianza: null, comentario: null,
      };
      datos.tareas.push(tareaActual);
      return tareaActual;
    },
    /** Lo que está razonando ANTES de actuar. El tiempo desde el evento anterior es lo que tardó en entender. */
    pensar(texto) {
      const p = { texto, segundosDesdeLoAnterior: desdeUltimo(), t: seg() };
      (tareaActual ? tareaActual.pensamientos : (datos.notas)).push(p);
      return p;
    },
    /** Algo que no entiende de la pantalla. */
    duda(texto, pantalla = null) {
      const d = { texto, pantalla, t: seg() };
      (tareaActual ? tareaActual.dudas : datos.notas).push(d);
      return d;
    },
    /** Le picó y no pasó nada, o no encuentra por dónde seguir. */
    atoron(texto, pantalla = null) {
      const a = { texto, pantalla, t: seg() };
      (tareaActual ? tareaActual.atorones : datos.notas).push(a);
      return a;
    },
    /** Tuvo que volver a intentar lo mismo. */
    reintento(motivo) {
      if (tareaActual) { tareaActual.reintentos++; tareaActual.atorones.push({ texto: 'reintento: ' + motivo, t: seg() }); }
    },
    /** Preguntó a alguien: 'soporte', 'superior', 'patrocinadora', 'familiar'. */
    preguntar(aQuien, texto) {
      const q = { aQuien, texto, t: seg(), tarea: tareaActual?.quiero || null };
      datos.preguntas.push(q);
      if (tareaActual) tareaActual.preguntas.push(q);
      return q;
    },
    /** Cómo se siente y por qué. intensidad 1..5 */
    sentir(emocion, intensidad, porque) {
      datos.emociones.push({ emocion, intensidad, porque, t: seg(), tarea: tareaActual?.quiero || null });
    },
    /** Cierra la tarea. facilidad 1..7 (1 muy difícil), confianza 1..5 (¿quedó guardado?). */
    async lograr(pagina, { facilidad = null, confianza = null, comentario = null } = {}) {
      return api._cerrar(pagina, true, { facilidad, confianza, comentario });
    },
    async abandonar(motivo, pagina = null, { facilidad = null } = {}) {
      return api._cerrar(pagina, false, { facilidad, comentario: motivo });
    },
    async _cerrar(pagina, logrado, extra) {
      if (!tareaActual) return null;
      if (pagina) await api.absorber(pagina);
      const t = tareaActual;
      t.logrado = logrado;
      t.segundos = seg() - t.t;
      t.clics = datos.totales.clics - t.clicsBase;
      t.teclas = datos.totales.teclas - t.teclasBase;
      t.pantallas = datos.totales.pantallas - t.pantallasBase;
      Object.assign(t, extra);
      tareaActual = null;
      return t;
    },
    /** Lee los contadores del navegador y los acumula. Se llama solo al cerrar tarea y al cerrar el navegador. */
    async absorber(pagina) {
      let m;
      try { m = await pagina.evaluate(() => window.__m && JSON.parse(JSON.stringify(window.__m))); } catch { return; }
      if (!m) return;
      datos.totales.clics = m.clics;
      datos.totales.teclas = m.teclas;
      datos.totales.envios = m.envios;
      datos.totales.campos = Object.keys(m.campos || {}).length;
      datos.totales.recargas = m.recargas;
      datos.totales.atrases = m.atrases;
      for (const p of m.pantallas || []) {
        const ya = datos.pantallas.find((x) => x.ruta === p.ruta && x.desde === p.desde);
        if (ya) continue;
        // Una recarga sobre la misma ruta se registra dos veces (hashchange + carga);
        // es la misma pantalla para la persona.
        const ult = datos.pantallas[datos.pantallas.length - 1];
        if (ult && ult.ruta === p.ruta && Math.abs(p.desde - ult.desde) < 2500) {
          ult.clics += p.clics; ult.primerClicMs = ult.primerClicMs ?? p.primerClicMs; continue;
        }
        datos.pantallas.push({ ruta: p.ruta, desde: p.desde, primerClicMs: p.primerClicMs, clics: p.clics, comoLlego: p.comoLlego });
      }
      datos.totales.pantallas = datos.pantallas.length;
    },
    /** Mensajes de error visibles en esta pantalla (validaciones, "no se pudo", etc.). */
    async errores(pagina) {
      const vistos = await pagina.evaluate(() => {
        const re = /(obligatorio|requerid|inválid|invalid|no se pudo|error|expirad|incorrect|debe tener|no encontr)/i;
        const out = [];
        document.querySelectorAll('body *').forEach((el) => {
          if (el.children.length) return;
          const t = (el.innerText || '').trim();
          if (t && t.length < 160 && re.test(t)) out.push(t.replace(/\s+/g, ' '));
        });
        return [...new Set(out)].slice(0, 12);
      }).catch(() => []);
      for (const t of vistos) {
        if (!datos.erroresEnPantalla.some((e) => e.texto === t)) {
          datos.erroresEnPantalla.push({ texto: t, t: seg(), tarea: tareaActual?.quiero || null });
        }
      }
      return vistos;
    },
    /** Opinión estética y emocional. Todo 1..10 salvo lo que se indique. */
    opinar({ primeraImpresion, confianzaQueTransmite, legibilidad, coherencia, sensacionMovil = null,
             tresAdjetivos = [], mejorPantalla = null, peorPantalla = null, seParece = null,
             recomendarias = null, volverias = null, comentario = null }) {
      datos.estetica = { primeraImpresion, confianzaQueTransmite, legibilidad, coherencia, sensacionMovil,
        tresAdjetivos, mejorPantalla, peorPantalla, seParece, recomendarias, volverias, comentario };
    },
    guardar() {
      datos.fin = new Date().toISOString();
      datos.duracionMin = Math.round((Date.now() - t0) / 60000);
      datos.consola = consola.slice(0, 200);
      fs.mkdirSync(`${RAIZ}/metricas`, { recursive: true });
      const ruta = `${RAIZ}/metricas/${persona.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.json`;
      fs.writeFileSync(ruta, JSON.stringify(datos, null, 1));
      return ruta;
    },
  };
  return api;
}

/** El texto tal y como lo leería una persona. */
export async function leer(pagina) {
  return (await pagina.innerText('body')).replace(/\n{3,}/g, '\n\n');
}

/** Botones, enlaces y campos visibles, con su etiqueta. Marca los deshabilitados y su motivo. */
export async function controles(pagina) {
  return pagina.evaluate(() => {
    const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
    const et = (el) => (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.title || '').trim().replace(/\s+/g, ' ').slice(0, 70);
    const out = { botones: [], deshabilitados: [], enlaces: [], campos: [] };
    document.querySelectorAll('button').forEach((e) => {
      if (!visible(e)) return;
      if (e.disabled || e.getAttribute('aria-disabled') === 'true') out.deshabilitados.push(et(e) + (e.title ? ` — motivo: ${e.title}` : ' — SIN MOTIVO'));
      else out.botones.push(et(e));
    });
    document.querySelectorAll('a[href]').forEach((e) => visible(e) && out.enlaces.push(et(e) + ' → ' + e.getAttribute('href')));
    document.querySelectorAll('input,select,textarea').forEach((e) => visible(e) && out.campos.push({ tipo: e.type || e.tagName.toLowerCase(), etiqueta: et(e) }));
    return out;
  });
}

export async function captura(pagina, nombre) {
  const ruta = `${RAIZ}/capturas/${nombre}.png`;
  fs.mkdirSync(`${RAIZ}/capturas`, { recursive: true });
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
