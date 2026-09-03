import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { UiBadgeComponent } from '../../../components/ui-badge/ui-badge.component';
import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { UiModalComponent } from '../../../components/ui-modal/ui-modal.component';
import { UiQtyStepperComponent } from '../../../components/ui-qty-stepper/ui-qty-stepper.component';
import { CustomerShippingAddress } from '../../../models/admin.model';
import { DashboardProduct } from '../../../models/user-dashboard.model';
import {
  Suscripcion,
  SuscripcionCambios,
  SuscripcionEntrega,
  SuscripcionPayload
} from '../../../models/suscripcion.model';
import { SuscripcionService } from '../../../services/suscripcion.service';

interface LineaBorrador {
  productId: string;
  name: string;
  price: number;
  quantity: number;
}

type AccionConfirmable = 'pause' | 'resume' | 'cancel';
type Opcion = { value: string | number; label: string };

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

/**
 * "Recibe esto cada mes" (paquete H, propuesta 14). La socia elige productos,
 * día del mes y dirección; el día indicado el sistema crea el pedido con el
 * descuento de su tramo y le manda el enlace de pago por correo. Sin cobro
 * automático. Lo monta I2 en la sección Órdenes del panel.
 */
@Component({
  selector: 'app-suscripcion',
  standalone: true,
  imports: [CommonModule, FormsModule, UiBadgeComponent, UiButtonComponent, UiFormFieldComponent, UiModalComponent, UiQtyStepperComponent],
  templateUrl: './suscripcion.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SuscripcionComponent implements OnInit, OnChanges {
  @Input() customerId = '';
  @Input() products: DashboardProduct[] = [];          // catálogo activo (id, name, price, vpPoints, img)
  @Input() addresses: CustomerShippingAddress[] = [];
  @Input() defaultAddressId = '';
  @Input() pickupStocks: Array<{ id: string; name: string; location: string }> = [];
  @Input() mode: 'cliente' | 'socio' = 'socio';
  @Output() changed = new EventEmitter<void>();         // tras crear/editar/pausar/cancelar

  suscripciones: Suscripcion[] = [];
  isLoading = false;
  loadError = '';

  isFormOpen = false;
  editingId: string | null = null;
  isSaving = false;
  formError = '';
  lineas: LineaBorrador[] = [];
  productoParaAgregar = '';
  dayOfMonth = '20';
  deliveryType: SuscripcionEntrega = 'delivery';
  shippingAddressId = '';
  pickupStockId = '';

  confirmacion: { accion: AccionConfirmable; sub: Suscripcion } | null = null;
  isConfirming = false;
  confirmError = '';

  message = '';
  messageTone: 'success' | 'error' = 'success';

  readonly dayOptions: Opcion[] = Array.from({ length: 28 }, (_, i) => ({ value: String(i + 1), label: `Día ${i + 1}` }));

  constructor(private readonly servicio: SuscripcionService, private readonly cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.cargar();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['customerId'] && !changes['customerId'].firstChange) {
      this.cargar();
    }
    if (changes['defaultAddressId'] && !this.shippingAddressId) {
      this.shippingAddressId = this.defaultAddressId || '';
    }
  }

  // ── Datos ──────────────────────────────────────────────────────────────────

  get activas(): Suscripcion[] {
    return this.suscripciones.filter((s) => s.status !== 'cancelled');
  }

  get productOptions(): Opcion[] {
    const usados = new Set(this.lineas.map((l) => l.productId));
    return this.products
      .filter((p) => p.inOnlineStore !== false && !usados.has(String(p.id)))
      .map((p) => ({ value: String(p.id), label: `${p.name} · ${this.formatMoney(p.price)}` }));
  }

  get addressOptions(): Opcion[] {
    return this.addresses.map((a) => ({
      value: a.id,
      label: `${a.label || 'Dirección'} · ${[a.street, a.number].filter(Boolean).join(' ') || a.address}, ${[a.city, a.state].filter(Boolean).join(', ')} ${a.postalCode || ''}`.trim()
    }));
  }

  get pickupOptions(): Opcion[] {
    return this.pickupStocks.map((s) => ({ value: s.id, label: `${s.name} · ${s.location}` }));
  }

  get totalLista(): number {
    return this.lineas.reduce((acc, l) => acc + l.price * l.quantity, 0);
  }

  get notaDescuento(): string {
    return this.mode === 'cliente'
      ? 'Como cliente pagas el precio de lista. Si activas el modo socio, cada pedido llevará el descuento de tu tramo.'
      : 'El descuento de tu tramo se aplica al generar cada pedido, así que el total suele ser menor al precio de lista.';
  }

  cargar(): void {
    if (!String(this.customerId || '').trim()) {
      this.suscripciones = [];
      return;
    }
    this.isLoading = true;
    this.loadError = '';
    this.servicio.listar()
      .pipe(finalize(() => { this.isLoading = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (subs) => { this.suscripciones = subs; },
        error: () => { this.loadError = 'No pudimos cargar tu suscripción. Vuelve a intentarlo en un momento.'; }
      });
  }

  // ── Formulario ─────────────────────────────────────────────────────────────

  abrirNueva(): void {
    this.editingId = null;
    this.lineas = [];
    this.productoParaAgregar = '';
    this.dayOfMonth = '20';
    this.deliveryType = this.addresses.length || !this.pickupStocks.length ? 'delivery' : 'pickup';
    this.shippingAddressId = this.defaultAddressId || this.addresses[0]?.id || '';
    this.pickupStockId = this.pickupStocks[0]?.id || '';
    this.formError = '';
    this.message = '';
    this.isFormOpen = true;
  }

  editar(sub: Suscripcion): void {
    this.editingId = sub.subscriptionId;
    this.lineas = (sub.items || []).map((i) => ({
      productId: String(i.productId),
      name: i.name,
      price: this.precioActual(String(i.productId), Number(i.price) || 0),
      quantity: Number(i.quantity) || 1
    }));
    this.productoParaAgregar = '';
    this.dayOfMonth = String(sub.dayOfMonth || 20);
    this.deliveryType = sub.deliveryType === 'pickup' ? 'pickup' : 'delivery';
    this.shippingAddressId = sub.shippingAddressId || this.defaultAddressId || this.addresses[0]?.id || '';
    this.pickupStockId = sub.pickupStockId || this.pickupStocks[0]?.id || '';
    this.formError = '';
    this.message = '';
    this.isFormOpen = true;
  }

  cerrarFormulario(): void {
    this.isFormOpen = false;
    this.editingId = null;
    this.formError = '';
  }

  agregarProducto(): void {
    const producto = this.products.find((p) => String(p.id) === String(this.productoParaAgregar));
    if (!producto) {
      return;
    }
    if (!this.lineas.some((l) => l.productId === String(producto.id))) {
      this.lineas = [...this.lineas, { productId: String(producto.id), name: producto.name, price: Number(producto.price) || 0, quantity: 1 }];
    }
    this.productoParaAgregar = '';
    this.formError = '';
  }

  cambiarCantidad(linea: LineaBorrador, qty: number): void {
    if (qty <= 0) {
      this.lineas = this.lineas.filter((l) => l !== linea);
      return;
    }
    this.lineas = this.lineas.map((l) => (l === linea ? { ...l, quantity: qty } : l));
  }

  quitarLinea(linea: LineaBorrador): void {
    this.lineas = this.lineas.filter((l) => l !== linea);
  }

  elegirEntrega(tipo: SuscripcionEntrega): void {
    this.deliveryType = tipo;
    this.formError = '';
  }

  guardar(): void {
    if (this.isSaving) {
      return;
    }
    const dia = Number(this.dayOfMonth);
    if (!this.lineas.length) {
      this.formError = 'Elige al menos un producto para recibir cada mes.';
      return;
    }
    if (!Number.isInteger(dia) || dia < 1 || dia > 28) {
      this.formError = 'Elige un día del mes entre 1 y 28.';
      return;
    }
    if (this.deliveryType === 'pickup' && !this.pickupStockId) {
      this.formError = 'Elige la sucursal donde vas a recoger tu pedido.';
      return;
    }
    if (this.deliveryType !== 'pickup' && !this.shippingAddressId) {
      this.formError = 'Elige una dirección de entrega. Si no tienes ninguna, guárdala al pagar tu próximo pedido (casilla "Guardar esta dirección" en el carrito) o elige recoger en sucursal.';
      return;
    }
    const items = this.lineas.map((l) => ({ productId: l.productId, quantity: l.quantity }));
    const entrega = this.deliveryType === 'pickup'
      ? { deliveryType: 'pickup' as SuscripcionEntrega, pickupStockId: this.pickupStockId }
      : { deliveryType: 'delivery' as SuscripcionEntrega, shippingAddressId: this.shippingAddressId };

    this.isSaving = true;
    this.formError = '';
    const peticion = this.editingId
      ? this.servicio.editar(this.editingId, { items, dayOfMonth: dia, ...entrega } as SuscripcionCambios)
      : this.servicio.crear({ customerId: this.customerId, items, dayOfMonth: dia, ...entrega } as SuscripcionPayload);
    const editando = Boolean(this.editingId);
    peticion
      .pipe(finalize(() => { this.isSaving = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (sub) => {
          // La confirmación dice lo que quedó guardado en el servidor, no lo que se llenó.
          this.mostrarMensaje(
            `${editando ? 'Suscripción actualizada' : 'Suscripción guardada'} (${sub.subscriptionId}): ${this.resumenItems(sub)}, cada día ${sub.dayOfMonth}. ` +
            `${editando ? 'Próximo' : 'Primer'} pedido el ${this.fechaLarga(sub.nextRunDate)}. Te mandamos un correo con el detalle.`
          );
          this.cerrarFormulario();
          this.actualizarLista(sub);
          this.changed.emit();
        },
        error: (err: unknown) => { this.formError = this.mensajeDeError(err, 'No pudimos guardar tu suscripción. Revisa los datos e inténtalo de nuevo.'); }
      });
  }

  // ── Pausar / reanudar / cancelar ───────────────────────────────────────────

  pedirConfirmacion(accion: AccionConfirmable, sub: Suscripcion): void {
    this.confirmacion = { accion, sub };
    this.confirmError = '';
    this.message = '';
  }

  cerrarConfirmacion(): void {
    this.confirmacion = null;
    this.confirmError = '';
  }

  get tituloConfirmacion(): string {
    switch (this.confirmacion?.accion) {
      case 'pause': return 'Pausar un mes';
      case 'resume': return 'Reanudar la suscripción';
      case 'cancel': return 'Cancelar la suscripción';
      default: return '';
    }
  }

  get efectoConfirmacion(): string {
    const sub = this.confirmacion?.sub;
    if (!sub) {
      return '';
    }
    switch (this.confirmacion?.accion) {
      case 'pause':
        return `No crearemos el pedido del ${this.fechaLarga(sub.nextRunDate)}. La suscripción se reanuda sola el mes siguiente; también puedes reanudarla antes desde aquí. No se cobra nada.`;
      case 'resume':
        return `Volveremos a crear tu pedido el día ${sub.dayOfMonth} de cada mes, a partir de la próxima fecha. Te mandaremos el enlace de pago por correo ese día.`;
      case 'cancel':
        return 'Ya no crearemos pedidos ni te cobraremos nada. Los pedidos que ya existen no cambian. Si cambias de opinión, puedes crear una suscripción nueva cuando quieras.';
      default:
        return '';
    }
  }

  get etiquetaConfirmacion(): string {
    switch (this.confirmacion?.accion) {
      case 'pause': return 'Sí, pausar un mes';
      case 'resume': return 'Sí, reanudar';
      case 'cancel': return 'Sí, cancelar';
      default: return 'Confirmar';
    }
  }

  confirmar(): void {
    if (!this.confirmacion || this.isConfirming) {
      return;
    }
    const { accion, sub } = this.confirmacion;
    const peticion = accion === 'pause'
      ? this.servicio.pausar(sub.subscriptionId)
      : accion === 'resume'
        ? this.servicio.reanudar(sub.subscriptionId)
        : this.servicio.cancelar(sub.subscriptionId);
    this.isConfirming = true;
    this.confirmError = '';
    peticion
      .pipe(finalize(() => { this.isConfirming = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (actualizada) => {
          if (accion === 'pause') {
            this.mostrarMensaje(`Suscripción ${actualizada.subscriptionId} en pausa hasta el ${this.fechaLarga(actualizada.pausedUntil)}. El próximo pedido será el ${this.fechaLarga(actualizada.nextRunDate)}. Te mandamos un correo.`);
          } else if (accion === 'resume') {
            this.mostrarMensaje(`Suscripción ${actualizada.subscriptionId} reanudada. Próximo pedido: ${this.fechaLarga(actualizada.nextRunDate)}. Te mandamos un correo.`);
          } else {
            this.mostrarMensaje(`Suscripción ${actualizada.subscriptionId} cancelada. No se creará ningún pedido más. Te mandamos un correo de confirmación.`);
          }
          this.cerrarConfirmacion();
          this.actualizarLista(actualizada);
          this.changed.emit();
        },
        error: (err: unknown) => { this.confirmError = this.mensajeDeError(err, 'No pudimos aplicar el cambio. Inténtalo de nuevo en un momento.'); }
      });
  }

  // ── Presentación ───────────────────────────────────────────────────────────

  estadoLabel(sub: Suscripcion): string {
    if (sub.status === 'paused') {
      return 'Pausada';
    }
    if (sub.status === 'cancelled') {
      return 'Cancelada';
    }
    return 'Activa';
  }

  estadoTone(sub: Suscripcion): 'active' | 'pending' | 'inactive' {
    if (sub.status === 'paused') {
      return 'pending';
    }
    if (sub.status === 'cancelled') {
      return 'inactive';
    }
    return 'active';
  }

  resumenItems(sub: Suscripcion): string {
    return (sub.items || []).map((i) => `${i.quantity} × ${i.name}`).join(', ');
  }

  totalListaDe(sub: Suscripcion): number {
    return (sub.items || []).reduce((acc, i) => acc + (Number(i.price) || 0) * (Number(i.quantity) || 0), 0);
  }

  entregaDe(sub: Suscripcion): string {
    if (sub.deliveryType === 'pickup') {
      const sucursal = this.pickupStocks.find((s) => s.id === sub.pickupStockId);
      return `Recoger en ${sub.pickupStockName || sucursal?.name || 'sucursal'}`;
    }
    const d = sub.shippingAddress;
    if (!d) {
      return 'Envío a domicilio';
    }
    const calle = [d.street, d.number].filter(Boolean).join(' ') || d.address || '';
    return `Envío a ${[d.label, calle, d.city, d.postalCode].filter(Boolean).join(', ')}`;
  }

  fechaLarga(iso?: string | null): string {
    if (!iso) {
      return 'próximamente';
    }
    const [anio, mes, dia] = String(iso).slice(0, 10).split('-').map(Number);
    if (!anio || !mes || !dia) {
      return String(iso);
    }
    return `${dia} de ${MESES[mes - 1] ?? ''}`;
  }

  formatMoney(value: number): string {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', minimumFractionDigits: 2 }).format(Number(value) || 0);
  }

  trackLinea(_: number, linea: LineaBorrador): string {
    return linea.productId;
  }

  trackSub(_: number, sub: Suscripcion): string {
    return sub.subscriptionId;
  }

  private precioActual(productId: string, respaldo: number): number {
    const producto = this.products.find((p) => String(p.id) === productId);
    return producto ? Number(producto.price) || respaldo : respaldo;
  }

  private actualizarLista(sub: Suscripcion): void {
    const existe = this.suscripciones.some((s) => s.subscriptionId === sub.subscriptionId);
    this.suscripciones = existe
      ? this.suscripciones.map((s) => (s.subscriptionId === sub.subscriptionId ? sub : s))
      : [sub, ...this.suscripciones];
  }

  private mostrarMensaje(texto: string, tone: 'success' | 'error' = 'success'): void {
    this.message = texto;
    this.messageTone = tone;
  }

  private mensajeDeError(error: unknown, fallback: string): string {
    const cuerpo = (error as { error?: { message?: string } } | null)?.error;
    if (cuerpo && typeof cuerpo.message === 'string' && cuerpo.message.trim()) {
      return cuerpo.message.trim();
    }
    return fallback;
  }

  private requestViewUpdate(): void {
    this.cdr.markForCheck();
  }
}
