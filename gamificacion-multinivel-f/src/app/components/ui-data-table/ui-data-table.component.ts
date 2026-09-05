import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, ContentChild, Input, OnDestroy, TemplateRef } from '@angular/core';

/** Mismo corte que `md:` de Tailwind: por debajo, tarjetas; por encima, filas. */
const DESKTOP_QUERY = '(min-width: 768px)';

/**
 * Tabla con dos presentaciones (tarjeta móvil y fila de escritorio) pero un
 * solo DOM por registro: antes las dos vivían juntas en la página, una oculta
 * por CSS, y `document.querySelectorAll` (y la persona que tabulaba o buscaba
 * un botón "Ver") encontraba cada acción dos veces. Ahora se pinta solo la
 * plantilla que corresponde al ancho actual y se cambia al redimensionar.
 */
@Component({
  selector: 'ui-data-table',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-data-table.component.html'
})
export class UiDataTableComponent<T = unknown> implements OnDestroy {
  @Input() rows: T[] = [];
  // Divisores visibles en tema claro (antes divide-white/10: invisibles)
  @Input() mobileDividerClass = 'divide-olive-20';
  @Input() desktopDividerClass = 'divide-olive-20';

  @ContentChild('mobileRow') mobileRowTpl?: TemplateRef<{ $implicit: T }>;
  @ContentChild('desktopHeader') desktopHeaderTpl?: TemplateRef<unknown>;
  @ContentChild('desktopRow') desktopRowTpl?: TemplateRef<{ $implicit: T }>;

  isDesktop = true;

  private readonly media: MediaQueryList | null;
  private readonly onMediaChange = (event: MediaQueryListEvent): void => {
    this.isDesktop = event.matches;
    this.cdr.markForCheck();
  };

  constructor(private readonly cdr: ChangeDetectorRef) {
    this.media = typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia(DESKTOP_QUERY)
      : null;
    if (this.media) {
      this.isDesktop = this.media.matches;
      this.media.addEventListener('change', this.onMediaChange);
    }
  }

  /** Si falta una de las dos plantillas se usa la otra en cualquier ancho. */
  get showDesktop(): boolean {
    if (!this.desktopRowTpl) {
      return false;
    }
    if (!this.mobileRowTpl) {
      return true;
    }
    return this.isDesktop;
  }

  ngOnDestroy(): void {
    this.media?.removeEventListener('change', this.onMediaChange);
  }
}
