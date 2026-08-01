import { Directive, ElementRef, HostListener, Renderer2 } from '@angular/core';

/**
 * Placeholder neutro (fondo `bg-sand-100` + icono genérico) para cuando el `src` de una imagen
 * de producto no resuelve. Antes, una imagen rota dejaba el `alt` text expuesto flotando en una
 * caja vacía (ver docs/ux/analisis-ui-ux-2026-08.md, hallazgo "Placeholder estándar para
 * imágenes rotas/ausentes"): sin fondo, sin ícono, sin ningún tratamiento visual.
 *
 * Uso: `<img [src]="product.img" [alt]="product.name" imgFallback />`
 *
 * El `alt` original se conserva (no se toca): sigue siendo el texto correcto para lectores de
 * pantalla incluso cuando la imagen visual es el placeholder.
 */
const FALLBACK_SVG = `
  <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <rect width="200" height="200" rx="24" fill="#f6f1e8"/>
    <g fill="none" stroke="#b4aea3" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">
      <rect x="40" y="54" width="120" height="92" rx="10"/>
      <circle cx="78" cy="86" r="10"/>
      <path d="M40 130l32-32 26 26 32-40 30 46"/>
    </g>
  </svg>
`;

export const IMG_FALLBACK_SRC = `data:image/svg+xml;utf8,${encodeURIComponent(FALLBACK_SVG)}`;

@Directive({
  selector: 'img[imgFallback]',
  standalone: true
})
export class ImgFallbackDirective {
  private applied = false;

  constructor(
    private readonly el: ElementRef<HTMLImageElement>,
    private readonly renderer: Renderer2
  ) {}

  @HostListener('error')
  onError(): void {
    if (this.applied) {
      // Evita loop infinito si el propio data-URI de fallback disparara error (no debería).
      return;
    }
    this.applied = true;
    const img = this.el.nativeElement;
    this.renderer.setAttribute(img, 'src', IMG_FALLBACK_SRC);
    this.renderer.addClass(img, 'img-fallback');
    this.renderer.setAttribute(img, 'data-img-fallback', 'true');
  }
}
