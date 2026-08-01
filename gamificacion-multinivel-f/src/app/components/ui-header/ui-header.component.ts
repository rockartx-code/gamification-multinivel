import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'ui-header',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-header.component.html'
})
export class UiHeaderComponent {
  @Input() variant: 'landing' | 'dashboard' | 'admin' | 'default' = 'default';
  @Input() containerClass = 'mx-auto flex items-center justify-between gap-4 px-4 py-3';

  get headerClass(): string {
    const base = 'border-b border-olive-20 bg-sand-200-90 backdrop-blur';
    if (this.variant === 'landing') {
      return `sticky top-0 z-40 ${base}`;
    }
    if (this.variant === 'dashboard' || this.variant === 'admin') {
      // `backdrop-blur` crea un stacking context propio (backdrop-filter, como filter, aísla su
      // contenido); sin `position` + `z-index` explícitos en el propio <header>, ese contexto
      // queda "atrapado" al nivel de un elemento estático y cualquier hijo posicionado dentro de
      // <main> (p. ej. la sección de contenido, position:relative con z-index:auto) lo pinta
      // encima sin importar el z-index interno del dropdown móvil — el menú hamburguesa de Admin
      // quedaba inclickeable detrás del contenido. Mismo z-50 que ya usa el header del Dashboard.
      return `sticky top-0 z-50 ${base}`;
    }
    return base;
  }

  get desktopLogoClass(): string {
    if (this.variant === 'landing') {
      return 'h-10 w-auto sm:h-12 md:h-14';
    }
    if (this.variant === 'dashboard' || this.variant === 'admin') {
      return 'hidden h-10 w-auto md:block';
    }
    return 'h-15 w-40';
  }

  get showMiniLogo(): boolean {
    return this.variant === 'dashboard' || this.variant === 'admin';
  }
}
