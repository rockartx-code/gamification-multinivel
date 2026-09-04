import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AdminOrder, AdminOrderItem } from '../../models/admin.model';
import {
  DevolucionArchivo,
  DevolucionCategoriaEvidencia,
  DevolucionDetalle,
  DevolucionMotivo,
  DevolucionSolicitudPayload,
  DevolucionSolicitudResponse
} from '../../models/devoluciones.model';
import { ApiService } from '../../services/api.service';
import { DevolucionesService } from '../../services/devoluciones.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiQtyStepperComponent } from '../../components/ui-qty-stepper/ui-qty-stepper.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';

type Paso = 1 | 2 | 3 | 4;

interface MotivoOpcion {
  value: DevolucionMotivo;
  label: string;
  hint: string;
  /** Plazo desde la entrega, en palabras. */
  plazo: string;
  /** Quién paga el envío de regreso. */
  envio: string;
  /** Qué fotos se piden y por qué. */
  evidencia: string;
}

/**
 * Asistente de devolución (propuesta 18): qué devuelves → motivo → evidencia
 * según el motivo → cuánto, cuándo y a dónde vuelve tu dinero. Después de
 * solicitarla, la misma página muestra el estado de la solicitud.
 */
@Component({
  selector: 'app-order-devolucion',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiFormFieldComponent, UiQtyStepperComponent, UiFooterComponent],
  templateUrl: './order-devolucion.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class OrderDevolucionComponent implements OnInit {
  orderId = '';
  order: AdminOrder | null = null;
  isLoading = true;
  isSubmitting = false;
  isLoadingDetalle = false;
  error = '';
  step: Paso = 1;
  result: DevolucionSolicitudResponse | null = null;
  /** Estado de una solicitud ya registrada (misma página, después de solicitar). */
  detalle: DevolucionDetalle | null = null;

  /** Cantidad a devolver por producto (0..comprada). */
  cantidades: Record<string, number> = {};

  motivo: DevolucionMotivo | '' = '';
  descripcion = '';
  /** Ticket de paquetería del envío de regreso, si la clienta lo pagó. */
  returnShippingCost = '';

  archivos: Record<DevolucionCategoriaEvidencia, DevolucionArchivo[]> = {
    fotos_paquete_cerrado: [], fotos_producto: [], fotos_empaque: [], fotos_guia_envio: []
  };
  nombres: Record<DevolucionCategoriaEvidencia, string[]> = {
    fotos_paquete_cerrado: [], fotos_producto: [], fotos_empaque: [], fotos_guia_envio: []
  };

  /** Plazo y medio que se prometen antes de que el servidor responda con los suyos. */
  readonly plazoPorOmision = '3 a 5';
  readonly medioPorOmision = 'mismo medio de pago';

  readonly motivos: MotivoOpcion[] = [
    {
      value: 'DANADO_DEFECTUOSO',
      label: 'Llegó dañado o no funciona',
      hint: 'El producto llegó roto, golpeado, abierto o en mal estado.',
      plazo: 'Tienes 48 horas desde la entrega.',
      envio: 'El envío de regreso lo pagamos nosotros: guarda tu ticket, te lo reembolsamos.',
      evidencia: 'Necesitamos tres fotos: del producto, del empaque y de la guía de envío.'
    },
    {
      value: 'ERROR_ENVIO',
      label: 'Me llegó otra cosa',
      hint: 'Recibiste un producto distinto o una cantidad diferente a la que pediste.',
      plazo: 'Tienes 48 horas desde la entrega.',
      envio: 'El envío de regreso lo pagamos nosotros: guarda tu ticket, te lo reembolsamos.',
      evidencia: 'Necesitamos tres fotos: del producto, del empaque y de la guía de envío.'
    },
    {
      value: 'DESISTIMIENTO',
      label: 'Ya no lo quiero',
      hint: 'Cambiaste de opinión y el paquete sigue cerrado.',
      plazo: 'Tienes 7 días desde la entrega.',
      envio: 'El envío de regreso corre por tu cuenta y no se reembolsa el envío original.',
      evidencia: 'Basta una foto del paquete cerrado donde se vea la guía.'
    }
  ];

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly api: ApiService,
    private readonly devoluciones: DevolucionesService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.orderId = this.route.snapshot.paramMap.get('idOrden') ?? '';
    if (!this.orderId) { void this.router.navigate(['/dashboard']); return; }

    this.api.getOrder(this.orderId)
      .pipe(finalize(() => { this.isLoading = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (order) => {
          this.order = order;
          this.cantidades = {};
          for (const item of this.items) {
            this.cantidades[this.clave(item)] = 0;
          }
          if (order?.returnRequestId || this.enFlujoDeDevolucion(order?.status)) {
            this.cargarDetalle();
          } else if ((order?.status ?? '') !== 'delivered') {
            this.error = 'Solo se puede pedir la devolución de un pedido ya entregado.';
          }
        },
        error: () => { this.error = 'No pudimos cargar tu pedido. Intenta de nuevo en un momento.'; }
      });
  }

  requestViewUpdate(): void { this.cdr.markForCheck(); }

  // ── Datos del pedido ──────────────────────────────────────────────────────

  get items(): AdminOrderItem[] { return this.order?.items ?? []; }
  clave(item: AdminOrderItem): string { return String(item.productId); }
  cantidadDe(item: AdminOrderItem): number { return this.cantidades[this.clave(item)] ?? 0; }

  setCantidad(item: AdminOrderItem, qty: number): void {
    const max = Number(item.quantity) || 0;
    this.cantidades = { ...this.cantidades, [this.clave(item)]: Math.max(0, Math.min(max, qty)) };
  }

  devolverTodo(): void {
    const todas: Record<string, number> = {};
    for (const item of this.items) { todas[this.clave(item)] = Number(item.quantity) || 0; }
    this.cantidades = todas;
  }

  quitarTodo(): void {
    const nada: Record<string, number> = {};
    for (const item of this.items) { nada[this.clave(item)] = 0; }
    this.cantidades = nada;
  }

  get lineasSeleccionadas(): Array<{ item: AdminOrderItem; quantity: number }> {
    return this.items
      .map((item) => ({ item, quantity: this.cantidadDe(item) }))
      .filter((l) => l.quantity > 0);
  }

  get totalUnidades(): number { return this.lineasSeleccionadas.reduce((s, l) => s + l.quantity, 0); }

  get esTodoElPedido(): boolean {
    return this.items.length > 0 && this.items.every((item) => this.cantidadDe(item) === (Number(item.quantity) || 0));
  }

  get orderIsDelivered(): boolean { return this.order?.status === 'delivered'; }

  enFlujoDeDevolucion(status?: string): boolean {
    return ['en_devolucion', 'devuelto_validado', 'devolucion_rechazada', 'refunded'].includes(status ?? '');
  }

  // ── Reembolso estimado (el servidor lo confirma en la respuesta) ──────────

  /** Proporción neto/bruto del pedido: aplica el descuento y el cupón a cada unidad. */
  private get factorNeto(): number {
    const o = this.order;
    if (!o) return 1;
    const bruto = Number(o.grossSubtotal ?? 0);
    const neto = Number(o.netTotal ?? 0);
    if (bruto > 0 && neto >= 0) return neto / bruto;
    return Math.max(0, 1 - Number(o.discountRate ?? 0));
  }

  netoUnitario(item: AdminOrderItem): number {
    return this.redondear(Number(item.price ?? 0) * this.factorNeto);
  }

  get productosEstimado(): number {
    if (this.esTodoElPedido) return this.redondear(Number(this.order?.netTotal ?? this.order?.total ?? 0));
    return this.redondear(this.lineasSeleccionadas.reduce((s, l) => s + this.netoUnitario(l.item) * l.quantity, 0));
  }

  get empresaPaga(): boolean { return this.motivo !== '' && this.motivo !== 'DESISTIMIENTO'; }

  get envioRegresoEstimado(): number {
    const v = Number(this.returnShippingCost);
    return this.empresaPaga && Number.isFinite(v) && v > 0 ? this.redondear(v) : 0;
  }

  get envioOriginalEstimado(): number {
    return this.empresaPaga && this.esTodoElPedido ? this.redondear(Number(this.order?.shippingCost ?? 0)) : 0;
  }

  get reembolsoEstimado(): number {
    return this.redondear(this.productosEstimado + this.envioRegresoEstimado + this.envioOriginalEstimado);
  }

  // ── Pasos ─────────────────────────────────────────────────────────────────

  get canProceedStep1(): boolean { return this.totalUnidades > 0; }
  get canProceedStep2(): boolean { return this.motivo !== ''; }
  get esDesistimiento(): boolean { return this.motivo === 'DESISTIMIENTO'; }
  get canProceedStep3(): boolean {
    if (this.esDesistimiento) return this.archivos.fotos_paquete_cerrado.length > 0;
    return this.archivos.fotos_producto.length > 0 &&
           this.archivos.fotos_empaque.length > 0 &&
           this.archivos.fotos_guia_envio.length > 0;
  }
  get motivoActual(): MotivoOpcion | null { return this.motivos.find((m) => m.value === this.motivo) ?? null; }
  get motivoLabel(): string { return this.motivoActual?.label ?? ''; }
  get totalArchivos(): number {
    return (Object.keys(this.archivos) as DevolucionCategoriaEvidencia[]).reduce((s, k) => s + this.archivos[k].length, 0);
  }

  readonly nombresPasos = ['¿Qué devuelves?', 'Motivo', 'Evidencia', 'Tu reembolso'];

  nextStep(): void {
    if (this.step === 1 && this.canProceedStep1) this.step = 2;
    else if (this.step === 2 && this.canProceedStep2) this.step = 3;
    else if (this.step === 3 && this.canProceedStep3) this.step = 4;
    this.error = '';
  }

  prevStep(): void {
    if (this.step > 1) { this.step = (this.step - 1) as Paso; this.error = ''; }
  }

  seleccionarMotivo(m: DevolucionMotivo): void {
    this.motivo = m;
  }

  onFilesChange(categoria: DevolucionCategoriaEvidencia, event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!files.length) return;
    // Una sola foto en desistimiento: la clienta no tiene que elegir cuántas.
    const seleccion = categoria === 'fotos_paquete_cerrado' ? files.slice(0, 1) : files;

    const resultados: DevolucionArchivo[] = [];
    const nombres: string[] = [];
    let pendientes = seleccion.length;

    seleccion.forEach((file) => {
      nombres.push(file.name);
      const reader = new FileReader();
      reader.onload = () => {
        const raw = reader.result as string;
        const [meta, contentBase64] = raw.split(',');
        const contentType = (meta?.match(/:(.*?);/) ?? [])[1] ?? 'image/jpeg';
        resultados.push({ contentBase64: contentBase64 ?? '', contentType, fileName: file.name });
        if (--pendientes === 0) {
          this.archivos = { ...this.archivos, [categoria]: resultados };
          this.nombres = { ...this.nombres, [categoria]: nombres };
          this.requestViewUpdate();
        }
      };
      reader.readAsDataURL(file);
    });
  }

  submit(): void {
    if (!this.canProceedStep1 || !this.canProceedStep3 || !this.motivo || this.isSubmitting) return;
    this.isSubmitting = true;
    this.error = '';

    const evidence = this.esDesistimiento
      ? { fotos_paquete_cerrado: this.archivos.fotos_paquete_cerrado }
      : {
          fotos_producto: this.archivos.fotos_producto,
          fotos_empaque: this.archivos.fotos_empaque,
          fotos_guia_envio: this.archivos.fotos_guia_envio
        };
    const payload: DevolucionSolicitudPayload = {
      motivo: this.motivo,
      descripcion: this.descripcion.trim() || undefined,
      lines: this.lineasSeleccionadas.map((l) => ({ productId: l.item.productId, quantity: l.quantity })),
      evidence,
      returnShippingCost: this.envioRegresoEstimado > 0 ? this.envioRegresoEstimado : undefined
    };

    this.devoluciones.solicitar(this.orderId, payload)
      .pipe(finalize(() => { this.isSubmitting = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (res) => { this.result = res; },
        error: (err: { error?: { message?: string; code?: string } }) => {
          this.error = err?.error?.message || 'No pudimos registrar tu solicitud. Revisa tu conexión e intenta de nuevo.';
        }
      });
  }

  // ── Estado de la solicitud ────────────────────────────────────────────────

  cargarDetalle(): void {
    this.isLoadingDetalle = true;
    this.devoluciones.detalle(this.orderId)
      .pipe(finalize(() => { this.isLoadingDetalle = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (detalle) => { this.detalle = detalle; this.result = null; },
        error: () => { this.error = 'No pudimos cargar el estado de tu devolución. Intenta de nuevo en un momento.'; }
      });
  }

  get estadoDetalle(): { label: string; tono: string; icono: string; texto: string } | null {
    const d = this.detalle;
    if (!d) return null;
    if (d.orderStatus === 'refunded' || d.refundedAt) {
      return {
        label: 'Reembolsada', tono: 'border-green-200 bg-green-50 text-green-800', icono: 'fa-solid fa-money-bill-transfer',
        texto: `Te devolvimos ${this.formatMoney(d.refundAmount ?? d.refund.suggested ?? 0)} al ${d.refund.method}. Según tu banco puede tardar hasta 2 días hábiles en reflejarse.`
      };
    }
    if (d.status === 'DEVUELTO_VALIDADO') {
      return {
        label: 'Validada', tono: 'border-green-200 bg-green-50 text-green-800', icono: 'fa-solid fa-check',
        texto: `Ya recibimos y revisamos tu paquete. Te devolvemos ${this.formatMoney(d.refund.suggested ?? 0)} al ${d.refund.method}, en ${d.refund.businessDays} días hábiles.`
      };
    }
    if (d.status === 'DEVOLUCION_RECHAZADA') {
      return {
        label: 'No procedió', tono: 'border-red-200 bg-red-50 text-red-800', icono: 'fa-solid fa-circle-info',
        texto: d.rejectionReason ? `Motivo: ${d.rejectionReason}.` : 'El paquete no cumplió las condiciones de devolución.'
      };
    }
    return {
      label: 'Pendiente', tono: 'border-amber-200 bg-amber-50 text-amber-800', icono: 'fa-solid fa-truck',
      texto: `Estamos esperando tu paquete. Cuando lo revisemos te devolvemos ${this.formatMoney(d.refund.suggested ?? 0)} al ${d.refund.method}, en ${d.refund.businessDays} días hábiles.`
    };
  }

  get fotosDetalle(): string[] {
    const ev = this.detalle?.evidence ?? {};
    return (Object.keys(ev) as DevolucionCategoriaEvidencia[]).flatMap((k) => ev[k] ?? []);
  }

  // ── Utilidades ────────────────────────────────────────────────────────────

  formatMoney(v?: number | null): string {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(v ?? 0);
  }

  private redondear(v: number): number { return Math.round((v + Number.EPSILON) * 100) / 100; }
}
