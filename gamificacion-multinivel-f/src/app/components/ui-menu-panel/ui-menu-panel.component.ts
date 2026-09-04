import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';

import { AdminMenuEntry, adminMenuVisible } from '../../models/privileges.model';
import { AuthService } from '../../services/auth.service';
import { UiButtonComponent } from '../ui-button/ui-button.component';
import { SidebarLink, UiSidebarNavComponent } from '../ui-sidebar-nav/ui-sidebar-nav.component';

/**
 * El menú del back office y el botón de cerrar sesión, para las pantallas que
 * son componentes aparte (Despacho en bloque y Seguimiento de hoy).
 *
 * La propuesta 33 hizo que el de almacén y la coach empiecen su día justo en
 * esas dos pantallas, y eran las únicas sin `ui-sidebar-nav`: Toño abría sesión
 * y su única navegación era «Volver a Pedidos», sin menú y sin «Cerrar sesión».
 */
@Component({
  selector: 'ui-menu-panel',
  standalone: true,
  imports: [CommonModule, UiButtonComponent, UiSidebarNavComponent],
  template: `
    <div class="flex flex-col gap-3">
      <div class="grain relative overflow-hidden rounded-3xl border border-olive-30 bg-ivory-80 p-4">
        <div class="text-xs text-gray-600">Navegación</div>
        <ui-sidebar-nav [links]="links" [activeId]="activeId" (linkSelect)="abrir($event)"></ui-sidebar-nav>
      </div>
      <ui-button size="sm" variant="ghost" ariaLabel="Cerrar sesión" (pressed)="cerrarSesion()">
        <i class="fa-solid fa-right-from-bracket" aria-hidden="true"></i>
        Cerrar sesión
      </ui-button>
    </div>
  `
})
export class UiMenuPanelComponent {
  /** Id de la entrada encendida ("despacho", "seguimiento", …). */
  @Input() activeId = '';

  constructor(private readonly auth: AuthService, private readonly router: Router) {}

  // Se cachea por identidad del usuario: devolver arreglos nuevos en cada ciclo
  // de detección de cambios vuelve a pintar el menú en bucle (NG0103).
  private cache: { usuario: unknown; links: SidebarLink[]; entradas: AdminMenuEntry[] } | null = null;

  private construir(): void {
    const usuario = this.auth.currentUser;
    if (this.cache?.usuario === usuario) {
      return;
    }
    const links: SidebarLink[] = [];
    const entradas: AdminMenuEntry[] = [];
    for (const grupo of adminMenuVisible(usuario?.privileges, this.auth.isSuperUser(usuario))) {
      links.push({ id: `heading-${grupo.label}`, icon: '', label: grupo.label, heading: true });
      for (const entrada of grupo.entries) {
        links.push({ id: entrada.id, icon: entrada.icon, label: entrada.label, subtitle: '' });
        entradas.push(entrada);
      }
    }
    this.cache = { usuario, links, entradas };
  }

  private get entradas(): AdminMenuEntry[] {
    this.construir();
    return this.cache!.entradas;
  }

  get links(): SidebarLink[] {
    this.construir();
    return this.cache!.links;
  }

  abrir(id: string): void {
    const entrada = this.entradas.find((e) => e.id === id);
    if (entrada) {
      this.router.navigateByUrl(entrada.route);
    }
  }

  cerrarSesion(): void {
    this.auth.logout();
    this.router.navigateByUrl('/login');
  }
}
