import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, Input, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { AhorroSocio, PlanTramo, calcularAhorroConTramos, formatoPesos, formatoPorcentaje } from '../../models/plan-socio.model';
import { PlanSocioService } from '../../services/plan-socio.service';

/**
 * "En modo socio habrías ahorrado $X en esta compra" (paquete B). Sin género (§4.17).
 *
 * Se monta bajo el total en tienda, carrito y confirmación de pedido. Calcula
 * con la tabla real del plan (`GET /catalog/plan`, cacheado); en modo socio
 * no pinta nada.
 */
@Component({
  selector: 'ui-ahorro-socio',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './ui-ahorro-socio.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UiAhorroSocioComponent implements OnInit {
  /** Bruto de la compra. */
  @Input() gross = 0;
  @Input() monthNet = 0;
  @Input() mode: 'cliente' | 'socio' | 'invitado' = 'invitado';
  @Input() variant: 'inline' | 'card' = 'inline';
  /** Para el enlace `?desde=orden&id=`. */
  @Input() orderId?: string;
  /** Si el pedido ya trae el ahorro guardado, se usa ese en vez de recalcular. */
  @Input() savedSavings?: number | null;
  @Input() savedNextRate?: number | null;
  @Input() savedNextMissing?: number | null;

  readonly pesos = formatoPesos;
  readonly porcentaje = formatoPorcentaje;
  private tramos: PlanTramo[] | null = null;
  planFallo = false;

  constructor(
    private readonly planSocio: PlanSocioService,
    private readonly cdr: ChangeDetectorRef,
    private readonly destroyRef: DestroyRef
  ) {}

  ngOnInit(): void {
    this.planSocio.plan$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (plan) => {
        this.tramos = plan.descuento.tramos;
        this.cdr.markForCheck();
      },
      error: () => {
        this.planFallo = true;
        this.cdr.markForCheck();
      }
    });
  }

  get visible(): boolean {
    return this.mode !== 'socio' && (Number(this.gross) || 0) > 0;
  }

  get ahorro(): AhorroSocio | null {
    if (this.savedSavings != null && Number.isFinite(Number(this.savedSavings))) {
      const savings = Number(this.savedSavings);
      const nextRate = Number(this.savedNextRate ?? 0);
      const nextMissing = Number(this.savedNextMissing ?? 0);
      return {
        gross: Number(this.gross) || 0,
        monthNet: Number(this.monthNet) || 0,
        projected: (Number(this.gross) || 0) + (Number(this.monthNet) || 0),
        rate: 0,
        savings,
        nextTier: nextRate > 0 && nextMissing > 0 ? { rate: nextRate, missing: nextMissing } : null
      };
    }
    if (!this.tramos) {
      return null;
    }
    return calcularAhorroConTramos(this.tramos, Number(this.gross) || 0, Number(this.monthNet) || 0);
  }

  get enlace(): unknown[] {
    return ['/modo-socio'];
  }

  get enlaceQuery(): Record<string, string> | null {
    return this.orderId ? { desde: 'orden', id: this.orderId } : null;
  }

  get frase(): string {
    const ahorro = this.ahorro;
    if (!ahorro) {
      return '';
    }
    if (ahorro.savings > 0) {
      return `En modo socio habrías ahorrado ${this.pesos(ahorro.savings)} en esta compra.`;
    }
    if (ahorro.nextTier) {
      return `En modo socio, con ${this.pesos(ahorro.nextTier.missing)} más de compra este mes tendrías ${this.porcentaje(ahorro.nextTier.rate)} de descuento.`;
    }
    return '';
  }
}
