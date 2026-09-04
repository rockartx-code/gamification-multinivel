import { readFileSync } from 'node:fs';

/**
 * Guarda 14 del informe 27 (§4) · «el botón "Ver" que no abre».
 *
 * La tira de pestañas de Pedidos recreaba sus nueve botones en **cada ciclo de
 * detección de cambios**, porque el `*ngFor` iteraba sobre un literal de array
 * escrito dentro de la plantilla (identidad nueva en cada lectura) y ninguna
 * tabla declaraba `trackBy`. Ese es el sustrato del botón que se pulsa y no
 * abre: el elemento bajo el dedo se destruye y se vuelve a crear entre el
 * `mousedown` y el `click`. La corrección que propone el §3 es mover la lista a
 * una constante del componente.
 *
 * Dos reglas, leídas directamente de la plantilla del back office:
 *
 *  1. Ningún `*ngFor` itera sobre un literal (`[…]` o `{…}`) escrito en la
 *     plantilla: la lista vive en el componente, con una sola identidad.
 *  2. Toda tabla dinámica declara `trackBy`. Se cuentan como tabla las filas
 *     `<tr *ngFor>` y las listas paginadas (`paged…`), que son las que se
 *     repintan enteras en cada ciclo y donde viven los botones de acción.
 */

const PLANTILLA = 'src/app/pages/admin/admin.component.html';

interface Bucle {
  linea: number;
  etiqueta: string;
  iterado: string;
  expresion: string;
  trackBy: boolean;
}

function buclesDe(html: string): Bucle[] {
  const bucles: Bucle[] = [];
  const re = /<([a-zA-Z][\w-]*)\b[^>]*?\*ngFor\s*=\s*"([\s\S]*?)"[^>]*>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    const expresion = m[2].replace(/\s+/g, ' ').trim();
    const tras = expresion.split(/\bof\b/)[1] ?? '';
    bucles.push({
      linea: html.slice(0, m.index).split('\n').length,
      etiqueta: m[1],
      iterado: (tras.split(';')[0] ?? '').trim(),
      expresion,
      trackBy: /trackBy\s*:/.test(expresion)
    });
  }
  return bucles;
}

/** Una fila de tabla: `<tr>` o un renglón de una lista paginada. */
function esTablaDinamica(bucle: Bucle): boolean {
  return bucle.etiqueta === 'tr' || /^paged/.test(bucle.iterado);
}

function describir(bucles: Bucle[]): string[] {
  return bucles.map((b) => `${PLANTILLA}:${b.linea} <${b.etiqueta}> ${b.iterado}`);
}

describe('Guarda 14 · las tablas del back office', () => {
  const html = readFileSync(PLANTILLA, 'utf8');
  const bucles = buclesDe(html);

  it('encuentra los *ngFor de la plantilla (la prueba no se está midiendo el vacío)', () => {
    expect(bucles.length).toBeGreaterThan(30);
  });

  it('ningún *ngFor itera sobre un literal escrito en la plantilla', () => {
    const literales = bucles.filter((b) => /^[[{]/.test(b.iterado));
    expect(describir(literales)).toEqual([]);
  });

  it('toda tabla dinámica declara trackBy', () => {
    const sinTrackBy = bucles.filter((b) => esTablaDinamica(b) && !b.trackBy);
    expect(describir(sinTrackBy)).toEqual([]);
  });
});
