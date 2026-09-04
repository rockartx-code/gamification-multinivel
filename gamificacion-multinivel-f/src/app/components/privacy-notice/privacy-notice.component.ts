import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';

import { UiButtonComponent } from '../ui-button/ui-button.component';
import { PlanSocioService } from '../../services/plan-socio.service';

/**
 * Aviso de Privacidad del Usuario (H19).
 * Se muestra una sola vez en el primer acceso a la aplicación (o registro).
 * No incluye banner de cookies ni analítica, conforme al requerimiento.
 *
 * Paquete G · ronda 26, propuesta 9. Dos cambios:
 *
 * (a) Deja de ser un modal bloqueante a pantalla completa sobre todas las
 *     rutas y pasa a **banner inferior no bloqueante**. Le costó tiempo a 11 de
 *     las 12 personas de la ronda: Ximena y Fabiola le picaron dos y tres veces
 *     a "Ver cómo funciona" creyendo que el botón estaba roto, y Paulina creyó
 *     que "Iniciar sesión" no servía. La clave `privacy-notice-accepted-v1` se
 *     **conserva**: a quien ya aceptó no se le vuelve a preguntar.
 *
 * (b) El texto de modo cliente mentía —"No te pedimos datos bancarios ni
 *     fiscales" mientras el mismo carrito pide RFC, razón social, régimen, CP
 *     fiscal y uso de CFDI— y a Aurora, que entró justamente por la factura,
 *     casi le cuesta la compra: *"se me cae el estómago… si no piden datos
 *     fiscales, no hay RFC"*. Ahora se dice por etapas.
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
  /** El aviso completo, desplegado dentro del propio banner: no abre otra página. */
  expandido = false;
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

  alternarDetalle(): void {
    this.expandido = !this.expandido;
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
