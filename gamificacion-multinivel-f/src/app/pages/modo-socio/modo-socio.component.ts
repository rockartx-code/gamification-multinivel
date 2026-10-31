import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiDesgloseIvaComponent } from '../../components/ui-desglose-iva/ui-desglose-iva.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { UiTablaDescuentoComponent } from '../../components/ui-tabla-descuento/ui-tabla-descuento.component';
import {
  ActivacionModoSocioRespuesta,
  PlanGeneracion,
  PlanSocio,
  formatoPesos,
  formatoPorcentaje,
  formatoPuntos,
  textoBaseComision
} from '../../models/plan-socio.model';
import { AuthService } from '../../services/auth.service';
import { PlanSocioService } from '../../services/plan-socio.service';
import { UserDashboardControlService } from '../../services/user-dashboard-control.service';
import { SimuladorPlanComponent } from './simulador/simulador-plan.component';

/**
 * Landing "Modo socio" (paquete B, propuesta 2): una sola página que explica
 * el plan completo con los números reales de la configuración y un botón
 * para activar el modo socio. Ruta pública `/#/modo-socio`.
 */
@Component({
  selector: 'app-modo-socio',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    UiButtonComponent,
    UiHeaderComponent,
    UiFooterComponent,
    UiTablaDescuentoComponent,
    UiDesgloseIvaComponent,
    SimuladorPlanComponent
  ],
  templateUrl: './modo-socio.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ModoSocioComponent implements OnInit {
  readonly currentYear = new Date().getFullYear();
  readonly pesos = formatoPesos;
  readonly porcentaje = formatoPorcentaje;
  readonly puntos = formatoPuntos;

  plan: PlanSocio | null = null;
  isLoading = true;
  loadError = '';

  /** De dónde llegó la persona (`?desde=orden&id=ORD-…`). */
  desdeOrden = '';
  /** Llegó desde el carrito: "Seguir como cliente" regresa ahí, no a la portada. */
  desdeCarrito = false;

  isActivating = false;
  activationError = '';
  activated: ActivacionModoSocioRespuesta | null = null;

  /** Lo que la persona ya lleva comprado en el mes; siembra el simulador. */
  compraPropiaInicial = 0;

  constructor(
    private readonly planSocio: PlanSocioService,
    private readonly authService: AuthService,
    private readonly dashboardControl: UserDashboardControlService,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef,
    private readonly destroyRef: DestroyRef
  ) {}

  ngOnInit(): void {
    const query = this.route.snapshot.queryParamMap;
    if (query.get('desde') === 'orden') {
      this.desdeOrden = (query.get('id') ?? '').trim();
    }
    this.desdeCarrito = query.get('desde') === 'carrito';
    this.planSocio.plan$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (plan) => {
        this.plan = plan;
        this.isLoading = false;
        this.cdr.markForCheck();
        // "Cómo se calculan" tiene que caer en la sección, no en la portada
        // de la página (propuesta 23): se desplaza al ancla en cuanto hay
        // contenido que mostrar.
        this.irAlFragmento();
      },
      error: () => {
        this.isLoading = false;
        this.loadError = 'No pudimos cargar el plan en este momento. Intenta de nuevo en unos minutos.';
        this.cdr.markForCheck();
      }
    });
    // Con sesión, se confirma el modo real de la cuenta (la sesión puede ser anterior a esta ronda).
    if (this.authService.hasSession) {
      this.planSocio.modo().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (respuesta) => {
          // El simulador arranca con lo que ya lleva comprado este mes.
          this.compraPropiaInicial = respuesta.indicators?.monthSpend ?? 0;
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck()
      });
    }
  }

  /**
   * Desplaza a la sección del fragmento (`#/modo-socio#generaciones`).
   *
   * Se hace aquí y no solo con `anchorScrolling` del router porque el
   * contenido de la página llega después de `GET /catalog/plan`: cuando el
   * router intenta anclar, la sección todavía no existe en el DOM.
   */
  private irAlFragmento(): void {
    const fragmento = (this.route.snapshot.fragment ?? '').trim();
    if (!fragmento) {
      return;
    }
    setTimeout(() => {
      document.getElementById(fragmento)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  get haySesion(): boolean {
    return this.authService.hasSession;
  }

  get yaEsSocio(): boolean {
    return this.planSocio.modoActual === 'socio';
  }

  get nombre(): string {
    return (this.authService.currentUser?.name ?? '').trim();
  }

  get generaciones(): PlanGeneracion[] {
    return this.plan?.generaciones ?? [];
  }

  get primeraGeneracion(): PlanGeneracion | null {
    return this.generaciones[0] ?? null;
  }

  get segundaGeneracion(): PlanGeneracion | null {
    return this.generaciones[1] ?? null;
  }

  get diasAviso(): string {
    const dias = this.plan?.pago.bloqueo.avisos ?? [];
    if (!dias.length) {
      return '';
    }
    if (dias.length === 1) {
      return `el día ${dias[0]}`;
    }
    return `los días ${dias.slice(0, -1).join(', ')} y ${dias[dias.length - 1]}`;
  }

  get bonosDeRango(): boolean {
    return (this.plan?.rangos.length ?? 0) > 0;
  }

  /**
   * La frase de la base de la comisión con la compra de referencia del plan:
   * *"10 % de $960.00 netos, sin envío = $96.00"* (propuesta 37). El texto lo
   * arma la función única del modelo; aquí no se redacta nada.
   */
  get ejemploComision(): string {
    const gen1 = this.primeraGeneracion;
    const compra = this.plan?.baseComision?.compraEjemplo ?? 0;
    if (!gen1 || compra <= 0) {
      return '';
    }
    const canasta = this.plan?.baseComision?.canastaEjemplo ?? '';
    const frase = textoBaseComision(compra, gen1.rate, gen1.ejemplo.comision);
    return canasta ? `${frase} — esa compra existe: ${canasta}.` : frase;
  }

  /** La misma frase, por fila de la tabla de generaciones. */
  textoDeLaFila(g: PlanGeneracion): string {
    if (g.ejemplo.compraReferido <= 0) {
      return 'Sin catálogo con puntos no hay ejemplo que enseñar.';
    }
    return textoBaseComision(g.ejemplo.compraReferido, g.rate, g.ejemplo.comision);
  }

  listaDatos(que: string[]): string {
    if (!que.length) {
      return 'nada más';
    }
    return que.join(', ');
  }

  productosDe(ejemplo: PlanSocio['activacion']['ejemplos'][number]): string {
    return ejemplo.productos.map((p) => `${p.qty} × ${p.name} (${this.pesos(p.price)}, ${this.puntos(p.pc)} PC)`).join(' + ');
  }

  irAlPanel(): void {
    void this.router.navigate(['/dashboard']);
  }

  irARegistro(): void {
    void this.router.navigate(['/login'], { queryParams: { next: 'modo-socio' } });
  }

  activar(): void {
    if (!this.haySesion) {
      this.irARegistro();
      return;
    }
    if (this.isActivating) {
      return;
    }
    this.isActivating = true;
    this.activationError = '';
    this.cdr.markForCheck();
    this.planSocio
      .activarModoSocio({ acceptedPlanVersion: this.plan?.version })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (respuesta) => {
          this.isActivating = false;
          this.activated = respuesta;
          // El panel se vuelve a pedir al servidor para que aparezcan red, VP y comisiones.
          this.dashboardControl.reset();
          this.cdr.markForCheck();
        },
        error: (error: { status?: number; error?: { message?: string } }) => {
          this.isActivating = false;
          if (error?.status === 401) {
            this.activationError = 'Tu sesión caducó. Vuelve a entrar y activa el modo socio desde aquí.';
          } else {
            this.activationError = error?.error?.message || 'No pudimos activar el modo socio. Intenta de nuevo o escríbenos por WhatsApp.';
          }
          this.cdr.markForCheck();
        }
      });
  }
}
