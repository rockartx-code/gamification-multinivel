import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { UiKpiCardComponent } from '../../../components/ui-kpi-card/ui-kpi-card.component';
import { ResumenTurno } from '../../../models/despacho.model';
import { AuthService } from '../../../services/auth.service';
import { DespachoService } from '../../../services/despacho.service';

/**
 * Paquete D · Resumen automático de turno (propuesta 23a).
 *
 * Beto y Nadia redactaban a mano el mensaje de cierre con folios, guías y
 * contadores. Aquí se arma solo desde la bitácora: qué despachó, entregó,
 * recibió y registró cada persona, con enlace a cada folio y un botón para
 * copiar el texto listo para WhatsApp. La gerente elige de quién es el turno;
 * un empleado ve el suyo.
 */
@Component({
  selector: 'app-resumen-turno',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiFormFieldComponent, UiKpiCardComponent],
  templateUrl: './resumen-turno.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ResumenTurnoComponent implements OnInit {
  userId = '';
  date = this.today();
  resumen: ResumenTurno | null = null;
  team: Array<{ id: string; name: string }> = [];
  isLoading = false;
  error = '';
  copyMessage = '';
  copyFailed = false;

  // --- Entregar el turno por correo (paquete F · ronda 26, propuesta 30) ---
  correoDestino = '';
  enviando = false;
  errorEnvio = '';
  mensajeEnvio = '';
  reenviarPendiente = false;

  constructor(
    private readonly despacho: DespachoService,
    private readonly auth: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.userId = String(this.auth.currentUser?.userId ?? '');
    this.load();
  }

  get teamOptions(): Array<{ value: string; label: string }> {
    return this.team.map((e) => ({ value: e.id, label: e.name }));
  }

  get canPickUser(): boolean {
    return this.team.length > 0;
  }

  load(): void {
    if (this.isLoading) {
      return;
    }
    this.isLoading = true;
    this.error = '';
    this.copyMessage = '';
    this.mensajeEnvio = '';
    this.errorEnvio = '';
    this.reenviarPendiente = false;
    this.despacho
      .resumenTurno(this.userId || undefined, this.date || undefined)
      .pipe(finalize(() => { this.isLoading = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (res) => {
          this.resumen = res;
          if (res.team?.length) {
            this.team = res.team;
          }
          if (!this.userId) {
            this.userId = res.user.id;
          }
        },
        error: (err) => {
          this.resumen = null;
          this.error = this.resolveError(err, 'No se pudo armar el resumen. Revisa la fecha o vuelve a intentarlo.');
        }
      });
  }

  /** ¿Hay a quién mandárselo sin escribir el correo a mano? */
  get correoConfigurado(): boolean {
    return Boolean(this.resumen?.notifyEmailConfigured);
  }

  /** Si ya se entregó, se dice a quién y cuándo, en vez de mandarlo dos veces. */
  get yaEntregado(): string {
    const r = this.resumen;
    if (!r?.notifiedTo || !r?.notifiedAt) {
      return '';
    }
    return `Este turno ya se le entregó a ${r.notifiedTo} el ${this.fechaLarga(r.notifiedAt)}.`;
  }

  /** Por qué no se puede enviar todavía. Vacío si se puede. */
  motivoEnvioDeshabilitado(): string {
    if (this.enviando) return 'Enviando el resumen…';
    if (!this.resumen) return 'Espera a que se arme el resumen.';
    if (this.isEmpty) return 'Este turno no tiene movimientos que reportar.';
    if (!this.correoConfigurado && !this.correoDestino.trim()) {
      return 'Escribe el correo de tu gerente, o pídele que lo configure en Configuración → Punto de venta.';
    }
    return '';
  }

  enviar(): void {
    const motivo = this.motivoEnvioDeshabilitado();
    if (motivo) {
      this.errorEnvio = motivo;
      this.requestViewUpdate();
      return;
    }
    this.enviando = true;
    this.errorEnvio = '';
    this.mensajeEnvio = '';
    this.despacho
      .enviarResumenTurno({
        userId: this.userId || undefined,
        date: this.date || undefined,
        email: this.correoDestino.trim() || undefined,
        reenviar: this.reenviarPendiente || undefined
      })
      .pipe(finalize(() => { this.enviando = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (res) => {
          this.reenviarPendiente = false;
          if (res.sent) {
            this.mensajeEnvio = `Resumen entregado a ${res.to}. Queda escrito quién lo recibió y a qué hora.`;
            if (this.resumen) {
              this.resumen = { ...this.resumen, notifiedTo: res.to, notifiedAt: res.sentAt };
            }
          } else {
            // Ya se había entregado: no se manda dos veces sin decirlo.
            this.mensajeEnvio = res.message ?? `Este turno ya se le entregó a ${res.to}.`;
            this.reenviarPendiente = true;
          }
          this.requestViewUpdate();
        },
        error: (err) => {
          this.errorEnvio = this.resolveError(err, 'No se pudo enviar el resumen. Inténtalo de nuevo.');
          this.requestViewUpdate();
        }
      });
  }

  fechaLarga(valor: string | null | undefined): string {
    if (!valor) return '';
    const d = new Date(valor);
    return Number.isNaN(d.getTime()) ? String(valor) : d.toLocaleString('es-MX', { dateStyle: 'long', timeStyle: 'short' });
  }

  onUserChange(userId: string): void {
    this.userId = userId;
    this.load();
  }

  onDateChange(date: string): void {
    this.date = date;
    if (date) {
      this.load();
    }
  }

  get isEmpty(): boolean {
    const c = this.resumen?.counters ?? {};
    return !!this.resumen && Object.values(c).every((n) => !n);
  }

  copy(): void {
    const texto = this.resumen?.text ?? '';
    if (!texto) {
      return;
    }
    const portapapeles = typeof navigator !== 'undefined' ? navigator.clipboard : undefined;
    if (!portapapeles?.writeText) {
      this.copyFailed = true;
      this.copyMessage = 'Tu navegador no deja copiar automáticamente: selecciona el texto de abajo y cópialo.';
      this.requestViewUpdate();
      return;
    }
    portapapeles.writeText(texto).then(
      () => {
        this.copyFailed = false;
        this.copyMessage = `Resumen copiado (${texto.split('\n').length} líneas). Pégalo en WhatsApp.`;
        this.requestViewUpdate();
      },
      () => {
        this.copyFailed = true;
        this.copyMessage = 'No se pudo copiar automáticamente: selecciona el texto de abajo y cópialo.';
        this.requestViewUpdate();
      }
    );
  }

  money(value: number | string | null | undefined): string {
    const n = Number(value ?? 0);
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number.isFinite(n) ? n : 0);
  }

  actionLabel(action: string): string {
    const etiquetas: Record<string, string> = {
      'despacho.enviar': 'Despacho en bloque',
      'order.note': 'Nota en pedido',
      'order.cancel': 'Cancelación de pedido',
      'order.create': 'Pedido creado',
      'order.refund': 'Reembolso',
      'order.return_inspected': 'Devolución revisada',
      'pos.sale_voided': 'Venta de caja anulada',
      'product.save': 'Producto guardado',
      'config.app.update': 'Configuración cambiada'
    };
    return etiquetas[action] ?? action;
  }

  private today(): string {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;
  }

  private resolveError(err: unknown, fallback: string): string {
    const texto = (err as { error?: { message?: string } } | null)?.error?.message;
    return typeof texto === 'string' && texto.trim() ? texto.trim() : fallback;
  }

  private requestViewUpdate(): void {
    this.cdr.markForCheck();
  }
}
