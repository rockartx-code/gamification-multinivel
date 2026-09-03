import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';

import { UiButtonComponent } from '../ui-button/ui-button.component';
import { PlanSocioService } from '../../services/plan-socio.service';

/**
 * Aviso de Privacidad del Usuario (H19).
 * Se muestra una sola vez en el primer acceso a la aplicación (o registro).
 * No incluye banner de cookies ni analítica, conforme al requerimiento.
 */
@Component({
  selector: 'app-privacy-notice',
  standalone: true,
  imports: [CommonModule, UiButtonComponent],
  templateUrl: './privacy-notice.component.html'
})
export class PrivacyNoticeComponent implements OnInit {
  private readonly storageKey = 'privacy-notice-accepted-v1';
  visible = false;
  /** Paquete B: en modo cliente (o sin sesión) el aviso no habla de red, comisiones ni datos bancarios. */
  @Input() mode: 'cliente' | 'socio' | 'auto' = 'auto';

  constructor(private readonly planSocio: PlanSocioService) {}

  get modoEfectivo(): 'cliente' | 'socio' {
    if (this.mode !== 'auto') {
      return this.mode;
    }
    return this.planSocio.modoActual === 'socio' ? 'socio' : 'cliente';
  }

  ngOnInit(): void {
    try {
      this.visible = localStorage.getItem(this.storageKey) !== 'true';
    } catch {
      this.visible = true;
    }
  }

  accept(): void {
    this.visible = false;
    try {
      localStorage.setItem(this.storageKey, 'true');
    } catch {
      // ignore storage errors
    }
  }
}
