import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { UiBadgeComponent } from '../ui-badge/ui-badge.component';

@Component({
  selector: 'ui-status-badge',
  standalone: true,
  imports: [CommonModule, UiBadgeComponent],
  templateUrl: './ui-status-badge.component.html'
})
export class UiStatusBadgeComponent {
  @Input() status = '';
  @Input() context: 'order' | 'network' = 'order';
  @Input() showIcon = true;

  get displayStatus(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      // Importante: 'inact'/'inactive' se comprueba ANTES que 'activa'/'active' porque
      // "inactiva".includes("activa") === true — si el orden fuera al revés, todo miembro
      // "Inactiva" caería en la rama "Activa".
      if (value.includes('inact') || value.includes('inactive')) {
        return 'Inactiva';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'En progreso';
      }
      if (value.includes('activa') || value.includes('active')) {
        return 'Activa';
      }
      return this.status || '-';
    }

    if (value === 'pending') {
      return 'Pendiente';
    }
    if (value === 'paid') {
      return 'Pagada';
    }
    if (value === 'shipped') {
      return 'Enviada';
    }
    if (value === 'delivered') {
      return 'Entregada';
    }
    if (value === 'cancelled' || value === 'canceled') {
      return 'Cancelado';
    }
    if (value === 'refunded') {
      return 'Reembolsado';
    }
    if (value === 'en_devolucion') {
      return 'Por devolver';
    }
    if (value === 'devuelto_validado') {
      return 'Devuelto';
    }
    if (value === 'devolucion_rechazada') {
      return 'Dev. rechazada';
    }
    return this.status || '-';
  }

  get tone(): 'active' | 'inactive' | 'pending' | 'delivered' | 'danger' {
    const value = this.normalized;
    if (this.context === 'network') {
      // Mismo orden que displayStatus(): 'inact' antes que 'activa' (ver nota ahí).
      if (value.includes('inact') || value.includes('inactive')) {
        return 'inactive';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'pending';
      }
      if (value.includes('activa') || value.includes('active')) {
        return 'active';
      }
      return 'inactive';
    }

    if (value === 'pending') {
      return 'pending';
    }
    if (value === 'paid') {
      return 'active';
    }
    if (value === 'shipped' || value === 'delivered') {
      return 'delivered';
    }
    // Estados negativos/de error del flujo de devoluciones (ver docs/ux/analisis-ui-ux-2026-08.md,
    // hallazgo "Badges de estado"): antes caían todos en 'inactive' (mismo tono neutro/dorado que
    // "Pendiente"/"Por devolver"), sin ninguna señal de alerta pese a existir --color-danger.
    if (value === 'cancelled' || value === 'canceled' || value === 'devuelto_validado' || value === 'devolucion_rechazada') {
      return 'danger';
    }
    return 'inactive';
  }

  get iconClass(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      // Mismo orden que displayStatus(): 'inact' antes que 'activa' (ver nota ahí).
      if (value.includes('inact') || value.includes('inactive')) {
        return 'fa-user-xmark';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'fa-hourglass-half';
      }
      return 'fa-user-check';
    }

    if (value === 'pending') {
      return 'fa-hourglass-half';
    }
    if (value === 'delivered') {
      return 'fa-circle-check';
    }
    if (value === 'shipped') {
      return 'fa-truck-fast';
    }
    if (value === 'paid') {
      return 'fa-receipt';
    }
    if (value === 'cancelled' || value === 'canceled') {
      return 'fa-ban';
    }
    if (value === 'refunded') {
      return 'fa-rotate-left';
    }
    if (value === 'en_devolucion') {
      return 'fa-truck-ramp-box';
    }
    if (value === 'devuelto_validado') {
      return 'fa-box-open';
    }
    if (value === 'devolucion_rechazada') {
      return 'fa-circle-xmark';
    }
    return 'fa-circle';
  }

  get levelClass(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      // Mismo orden que displayStatus(): 'inact' antes que 'activa' (ver nota ahí).
      if (value.includes('inact') || value.includes('inactive')) {
        return 'level-5';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'level-3';
      }
      return 'level-2';
    }
    if (value === 'delivered') {
      return 'level-1';
    }
    if (value === 'shipped') {
      return 'level-2';
    }
    if (value === 'paid') {
      return 'level-3';
    }
    if (value === 'pending') {
      return 'level-4';
    }
    return 'level-5';
  }

  get activityClass(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('inactiv') || value.includes('inactive')) {
        return 'status-inactive';
      }
      if (value.includes('activa') || value.includes('active')) {
        return 'status-active';
      }
      return '';
    }
    if (value === 'delivered') {
      return 'status-active';
    }
    if (value === 'pending') {
      return 'status-inactive';
    }
    return '';
  }

  get representationClass(): string {
    if (this.context === 'network' && this.activityClass) {
      return this.activityClass;
    }
    // `.badge.level-N` tiene más especificidad CSS que `.badge-danger` (dos clases vs. una),
    // así que combinarlas pintaría siempre el tono dorado/gris de `levelClass` encima del rojo
    // de peligro. Para tono 'danger' no se agrega levelClass: solo `badge-danger` gobierna el
    // color (ver ui-badge.component.ts → toneClass).
    if (this.tone === 'danger') {
      return '';
    }
    return this.levelClass;
  }

  private get normalized(): string {
    return String(this.status || '').toLowerCase();
  }
}
