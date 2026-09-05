import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { UiBadgeComponent } from '../ui-badge/ui-badge.component';
import { ALIAS_ESTADO, textoEstadoPedido } from '../../models/vocabulario.model'; // paquete G · ronda 26

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
  /**
   * Recolección en sucursal: cambia el texto, no el estado (paquete G · ronda 26).
   * Paulina llevaba 21 días sin saber en qué tienda estaba su pedido.
   */
  @Input() deliveryType = '';

  get displayStatus(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('inact')) {
        return 'Inactiva';
      }
      if (value.includes('activa') || value.includes('active')) {
        return 'Activa';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'En progreso';
      }
      return this.status || '-';
    }

    // Paquete G · ronda 26, propuesta 25: el texto sale del vocabulario único.
    // Julio contó cuatro nombres del mismo estado en cuatro pantallas; esta
    // insignia era uno de los cuatro ("Pagada", en femenino, contra "Pagado").
    return textoEstadoPedido(this.status, this.deliveryType) || '-';
  }

  get tone(): 'active' | 'inactive' | 'pending' | 'delivered' | 'danger' {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('inact')) {
        return 'inactive';
      }
      if (value.includes('activa') || value.includes('active')) {
        return 'active';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'pending';
      }
      return 'inactive';
    }

    if (value === 'pending') {
      return 'pending';
    }
    if (value === 'paid') {
      return 'active';
    }
    if (value === 'shipped' || value === 'delivered' || value === 'devuelto_validado') {
      return 'delivered';
    }
    if (value === 'cancelled' || value === 'devolucion_rechazada') {
      return 'danger';
    }
    if (value === 'en_devolucion') {
      return 'pending';
    }
    return 'inactive';
  }

  get iconClass(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('inact')) {
        return 'fa-user-xmark';
      }
      if (value.includes('activa') || value.includes('active')) {
        return 'fa-user-check';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'fa-hourglass-half';
      }
      return 'fa-user-xmark';
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
    if (value === 'cancelled' || value === 'devolucion_rechazada') {
      return 'fa-ban';
    }
    if (value === 'refunded') {
      return 'fa-money-bill-transfer';
    }
    if (value === 'en_devolucion') {
      return 'fa-rotate-left';
    }
    if (value === 'devuelto_validado') {
      return 'fa-box-open';
    }
    return 'fa-circle';
  }

  get levelClass(): string {
    const value = this.normalized;
    if (this.context === 'network') {
      if (value.includes('inact')) {
        return 'level-5';
      }
      if (value.includes('activa') || value.includes('active')) {
        return 'level-2';
      }
      if (value.includes('progreso') || value.includes('pending')) {
        return 'level-3';
      }
      return 'level-5';
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
    if (value === 'en_devolucion') {
      return 'level-3';
    }
    if (value === 'devuelto_validado') {
      return 'level-2';
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
    if (this.tone === 'danger') {
      // Las clases .badge.level-* pisarían el tono de peligro por especificidad.
      return '';
    }
    if (this.context === 'network' && this.activityClass) {
      return this.activityClass;
    }
    return this.levelClass;
  }

  private get normalized(): string {
    const value = String(this.status || '').toLowerCase();
    // Los alias históricos ("canceled", "in_return") pintan como su estado.
    return ALIAS_ESTADO[value] ?? value;
  }
}
