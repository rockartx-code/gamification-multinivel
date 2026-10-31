/**
 * Guardas del informe 27 · §4: las pruebas 11 y 14 son **estructurales** — leen
 * las plantillas del propio repositorio y afirman cosas sobre ellas (que existe
 * un solo formulario de CLABE, que ningún `*ngFor` itera sobre un literal).
 *
 * El corredor de pruebas (`@angular/build:unit-test` con vitest) se ejecuta en
 * Node, así que `node:fs` está disponible en tiempo de ejecución; lo que falta
 * es su tipado, porque el proyecto no instala `@types/node` (y `tsconfig.app`
 * declara `"types": []` a propósito, para que el código de la aplicación no vea
 * las APIs de Node). Estas firmas mínimas son solo declaraciones: no añaden
 * código al paquete de la aplicación ni permiten usar Node desde `src/app`
 * salvo importándolo explícitamente en una prueba.
 */
declare module 'node:fs' {
  export function readFileSync(path: string, encoding: 'utf8'): string;
  export function readdirSync(
    path: string,
    options: { withFileTypes: true }
  ): { name: string; isDirectory(): boolean; isFile(): boolean }[];
}

declare module 'node:path' {
  export function join(...parts: string[]): string;
  export function resolve(...parts: string[]): string;
}

declare const process: { cwd(): string };
