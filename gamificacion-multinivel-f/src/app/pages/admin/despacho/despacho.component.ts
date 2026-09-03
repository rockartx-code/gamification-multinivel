import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize, forkJoin, of, catchError } from 'rxjs';

import { UiBadgeComponent } from '../../../components/ui-badge/ui-badge.component';
import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiCheckboxComponent } from '../../../components/ui-checkbox/ui-checkbox.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { UiKpiCardComponent } from '../../../components/ui-kpi-card/ui-kpi-card.component';
import { UiModalComponent } from '../../../components/ui-modal/ui-modal.component';
import {
  BodegaResumen,
  CarrierIntegrationInfo,
  CierreResponse,
  DespachoEnviarResponse,
  DespachoPendiente,
  EnvioRezagado,
  PreferenciasDespacho,
  RastreoResponse,
  SurtidoResponse
} from '../../../models/despacho.model';
import { DespachoService } from '../../../services/despacho.service';

type GuiaDraft = { carrier: string; trackingNumber: string };
type Tone = 'success' | 'error' | 'info';

/**
 * Paquete D · Despacho en bloque (propuestas 9 y 13).
 *
 * Beto seleccionaba pedido por pedido, sumaba a mano 13 productos por 10 pedidos
 * y copiaba cada guía desde WhatsApp. Aquí: elige los pagados, calcula el surtido
 * contra la bodega (con semáforo y qué sucursal sí tiene lo que falta), captura o
 * importa las guías y despacha todo en una operación. Cada confirmación muestra
 * lo que el servidor guardó, no lo que se escribió en el formulario.
 */
@Component({
  selector: 'app-despacho',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiFormFieldComponent, UiCheckboxComponent, UiModalComponent, UiKpiCardComponent, UiBadgeComponent],
  templateUrl: './despacho.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [
    `@media print {
      .no-print { display: none !important; }
      .print-only { display: block !important; }
    }`
  ]
})
export class DespachoComponent implements OnInit {
  bodegas: BodegaResumen[] = [];
  stockId = '';
  preferencias: PreferenciasDespacho | null = null;
  isSavingDefault = false;

  pendientes: DespachoPendiente[] = [];
  rezagados: EnvioRezagado[] = [];
  integracion: CarrierIntegrationInfo | null = null;
  isLoading = false;
  loadError = '';

  seleccion = new Set<string>();
  surtido: SurtidoResponse | null = null;
  isCalculating = false;

  guias: Record<string, GuiaDraft> = {};
  csvText = '';
  csvMessage = '';
  generateLabels = false;

  isConfirmOpen = false;
  isSending = false;
  resultado: DespachoEnviarResponse | null = null;

  message = '';
  messageTone: Tone = 'info';

  rastreo: RastreoResponse | null = null;
  isTracking = false;
  cierre: CierreResponse | null = null;
  isClosing = false;

  constructor(private readonly despacho: DespachoService, private readonly cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.isLoading = true;
    forkJoin({
      bodegas: this.despacho.bodegas().pipe(catchError(() => of([] as BodegaResumen[]))),
      preferencias: this.despacho.preferencias().pipe(catchError(() => of(null as PreferenciasDespacho | null)))
    }).subscribe({
      next: ({ bodegas, preferencias }) => {
        this.bodegas = bodegas;
        this.preferencias = preferencias;
        const porDefecto = preferencias?.defaultStockId ?? '';
        this.stockId = porDefecto && bodegas.some((b) => b.id === porDefecto) ? porDefecto : (bodegas[0]?.id ?? '');
        this.loadPendientes();
      },
      error: () => {
        this.isLoading = false;
        this.loadError = 'No se pudieron cargar las bodegas. Recarga la página o avisa a sistemas.';
        this.requestViewUpdate();
      }
    });
  }

  // ── Datos ────────────────────────────────────────────────────────────────

  loadPendientes(): void {
    this.isLoading = true;
    this.loadError = '';
    this.despacho
      .pendientes(this.stockId || undefined)
      .pipe(finalize(() => { this.isLoading = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (res) => {
          this.pendientes = res.orders ?? [];
          this.rezagados = res.staleShipped ?? [];
          this.integracion = res.carrierIntegration ?? null;
          const vivos = new Set(this.pendientes.map((p) => p.id));
          this.seleccion.forEach((id) => { if (!vivos.has(id)) { this.seleccion.delete(id); } });
          this.surtido = null;
        },
        error: (err) => { this.loadError = this.resolveError(err, 'No se pudieron cargar los pedidos pagados.'); }
      });
  }

  get stockOptions(): Array<{ value: string; label: string }> {
    return this.bodegas.map((b) => ({ value: b.id, label: b.location ? `${b.name} · ${b.location}` : b.name }));
  }

  get selectedStock(): BodegaResumen | null {
    return this.bodegas.find((b) => b.id === this.stockId) ?? null;
  }

  get selectedStockName(): string {
    return this.selectedStock?.name ?? this.stockId;
  }

  onStockChange(stockId: string): void {
    this.stockId = stockId;
    this.surtido = null;
    this.message = '';
  }

  get isDefaultStock(): boolean {
    return !!this.stockId && this.preferencias?.defaultStockId === this.stockId;
  }

  saveDefaultStock(): void {
    if (!this.stockId || this.isSavingDefault) {
      return;
    }
    this.isSavingDefault = true;
    this.despacho
      .guardarPreferencias(this.stockId)
      .pipe(finalize(() => { this.isSavingDefault = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (prefs) => {
          this.preferencias = prefs;
          this.notify(`Listo: tu bodega por defecto ahora es ${prefs.stockName ?? prefs.defaultStockId}. Stocks, Caja y Despacho abrirán con ella.`, 'success');
        },
        error: (err) => this.notify(this.resolveError(err, 'No se pudo guardar la bodega por defecto.'), 'error')
      });
  }

  // ── Selección ────────────────────────────────────────────────────────────

  get selectedOrders(): DespachoPendiente[] {
    return this.pendientes.filter((p) => this.seleccion.has(p.id));
  }

  get allSelected(): boolean {
    return this.pendientes.length > 0 && this.pendientes.every((p) => this.seleccion.has(p.id));
  }

  isSelected(id: string): boolean {
    return this.seleccion.has(id);
  }

  toggle(id: string, checked: boolean): void {
    if (checked) {
      this.seleccion.add(id);
    } else {
      this.seleccion.delete(id);
    }
    this.surtido = null;
  }

  toggleAll(checked: boolean): void {
    this.seleccion = checked ? new Set(this.pendientes.map((p) => p.id)) : new Set<string>();
    this.surtido = null;
  }

  totalUnits(order: DespachoPendiente): number {
    return (order.items ?? []).reduce((acc, it) => acc + Number(it.quantity || 0), 0);
  }

  itemsLabel(order: DespachoPendiente): string {
    return (order.items ?? []).map((it) => `${it.quantity} × ${it.name}`).join(', ');
  }

  // ── Surtido ──────────────────────────────────────────────────────────────

  calcularSurtido(): void {
    if (!this.stockId || this.seleccion.size === 0 || this.isCalculating) {
      return;
    }
    this.isCalculating = true;
    this.message = '';
    this.despacho
      .surtido(this.stockId, Array.from(this.seleccion))
      .pipe(finalize(() => { this.isCalculating = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (res) => {
          this.surtido = res;
          if (res.canDispatch) {
            this.notify(`Surtido completo en ${res.stockName}: ${res.lines.length} productos para ${res.orderCount} pedidos, todo alcanza.`, 'success');
          } else {
            this.notify(res.reasons.length ? res.reasons.join(' ') : 'Hay pedidos que no se pueden despachar; revisa la lista.', 'error');
          }
        },
        error: (err) => this.notify(this.resolveError(err, 'No se pudo calcular el surtido.'), 'error')
      });
  }

  get surtidoIsCurrent(): boolean {
    if (!this.surtido) {
      return false;
    }
    const calculados = new Set(this.surtido.orderIds ?? []);
    const bloqueados = new Set((this.surtido.blockedOrders ?? []).map((b) => b.orderId));
    const actuales = Array.from(this.seleccion);
    return this.surtido.stockId === this.stockId
      && actuales.length === calculados.size + bloqueados.size
      && actuales.every((id) => calculados.has(id) || bloqueados.has(id));
  }

  get shortLines(): number {
    return (this.surtido?.lines ?? []).filter((l) => l.status === 'short').length;
  }

  elsewhereLabel(line: { elsewhere: Array<{ name: string; available: number }> }): string {
    return line.elsewhere.map((e) => `${e.name} tiene ${e.available}`).join(' · ');
  }

  imprimirLista(): void {
    window.print();
  }

  // ── Guías ────────────────────────────────────────────────────────────────

  guia(orderId: string): GuiaDraft {
    if (!this.guias[orderId]) {
      this.guias[orderId] = { carrier: '', trackingNumber: '' };
    }
    return this.guias[orderId];
  }

  setGuia(orderId: string, campo: string, valor: string): void {
    const draft = this.guia(orderId);
    if (campo === 'carrier') {
      draft.carrier = String(valor ?? '').trim();
    } else {
      draft.trackingNumber = String(valor ?? '').trim();
    }
  }

  hasTracking(orderId: string): boolean {
    return !!this.guias[orderId]?.trackingNumber?.trim();
  }

  get missingTracking(): DespachoPendiente[] {
    return this.selectedOrders.filter((p) => !this.hasTracking(p.id));
  }

  get canGenerateLabels(): boolean {
    return !!this.integracion?.enabled;
  }

  importCsv(): void {
    const texto = this.csvText.trim();
    if (!texto) {
      this.csvMessage = 'Pega el contenido del CSV (orderId,carrier,tracking) o elige el archivo.';
      return;
    }
    const conocidos = new Set(this.pendientes.map((p) => p.id));
    let cargadas = 0;
    const desconocidos: string[] = [];
    let seleccionCambio = false;
    texto.split(/\r?\n/).forEach((linea) => {
      const celdas = linea.split(/[,;\t]/).map((c) => c.trim());
      if (!celdas[0] || ['orderid', 'pedido', 'folio', 'order', 'id'].includes(celdas[0].toLowerCase())) {
        return;
      }
      const [orderId, carrier = '', tracking = ''] = celdas;
      if (!conocidos.has(orderId)) {
        desconocidos.push(orderId);
        return;
      }
      this.guias[orderId] = { carrier, trackingNumber: tracking };
      if (!this.seleccion.has(orderId)) {
        this.seleccion.add(orderId);
        seleccionCambio = true;
      }
      cargadas += 1;
    });
    // Capturar guías no invalida el surtido: solo si el CSV sumó pedidos a la selección.
    if (seleccionCambio) {
      this.surtido = null;
    }
    this.csvMessage = `${cargadas} guía(s) cargadas en la lista`
      + (desconocidos.length ? `; sin pedido pagado pendiente: ${desconocidos.join(', ')}.` : '.');
  }

  onCsvFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const archivo = input.files?.[0];
    if (!archivo) {
      return;
    }
    const lector = new FileReader();
    lector.onload = () => {
      this.csvText = String(lector.result ?? '');
      this.importCsv();
      input.value = '';
      this.requestViewUpdate();
    };
    lector.readAsText(archivo);
  }

  // ── Despachar ────────────────────────────────────────────────────────────

  /** Motivo escrito por el que "Despachar" no está disponible; vacío si sí lo está. */
  get dispatchBlockReason(): string {
    if (!this.stockId) {
      return 'Elige la bodega desde la que sale la mercancía.';
    }
    if (this.seleccion.size === 0) {
      return 'Selecciona al menos un pedido pagado.';
    }
    if (!this.surtido || !this.surtidoIsCurrent) {
      return 'Primero pulsa "Calcular surtido" para confirmar que la bodega tiene todo lo seleccionado.';
    }
    if (!this.surtido.canDispatch) {
      return this.surtido.reasons.length ? this.surtido.reasons.join(' ') : 'Ningún pedido de la selección se puede despachar.';
    }
    const sinGuia = this.missingTracking;
    if (sinGuia.length && !(this.generateLabels && this.canGenerateLabels)) {
      const folios = sinGuia.map((p) => p.id).join(', ');
      return `Faltan guías en ${folios}. Captúralas en la tabla, importa el CSV${this.canGenerateLabels ? ' o marca "Generar guías con la paquetería"' : ''}.`;
    }
    return '';
  }

  get canDispatch(): boolean {
    return !this.dispatchBlockReason && !this.isSending;
  }

  get dispatchableOrders(): DespachoPendiente[] {
    const aptos = new Set(this.surtido?.orderIds ?? []);
    return this.selectedOrders.filter((p) => aptos.has(p.id));
  }

  openConfirm(): void {
    if (!this.canDispatch) {
      return;
    }
    this.isConfirmOpen = true;
  }

  closeConfirm(): void {
    this.isConfirmOpen = false;
  }

  enviar(): void {
    if (!this.canDispatch) {
      return;
    }
    this.isSending = true;
    const shipments = this.dispatchableOrders.map((p) => ({
      orderId: p.id,
      carrier: this.guia(p.id).carrier,
      trackingNumber: this.guia(p.id).trackingNumber
    }));
    this.despacho
      .enviar({ stockId: this.stockId, shipments, generateLabels: this.generateLabels && this.canGenerateLabels })
      .pipe(finalize(() => { this.isSending = false; this.isConfirmOpen = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (res) => {
          this.resultado = res;
          res.shipped.forEach((s) => { delete this.guias[s.orderId]; });
          const folios = res.shipped.map((s) => `${s.orderId} (${s.carrier} ${s.trackingNumber})`).join(', ');
          if (res.shipped.length) {
            this.notify(`Se despacharon ${res.shipped.length} pedido(s) desde ${res.stockName}: ${folios}.`
              + (res.failed.length ? ` No se pudieron despachar ${res.failed.length}; el motivo está abajo.` : ''), res.failed.length ? 'info' : 'success');
          } else {
            this.notify('No se despachó ningún pedido; revisa los motivos abajo.', 'error');
          }
          this.loadPendientes();
        },
        error: (err) => {
          const cuerpo = (err?.error ?? {}) as Partial<SurtidoResponse> & { code?: string; message?: string };
          if (cuerpo.code === 'STOCK_SHORT' && cuerpo.lines) {
            this.surtido = {
              stockId: cuerpo.stockId ?? this.stockId,
              stockName: cuerpo.stockName ?? this.selectedStockName,
              canDispatch: false,
              lines: cuerpo.lines,
              reasons: cuerpo.reasons ?? [],
              blockedOrders: cuerpo.blockedOrders ?? [],
              orderIds: cuerpo.orderIds ?? [],
              orderCount: cuerpo.orderCount ?? 0
            };
          }
          this.notify(this.resolveError(err, 'No se pudo despachar el bloque.'), 'error');
        }
      });
  }

  // ── Paquetería: rastreo y cierre ─────────────────────────────────────────

  rastrear(orderIds?: string[]): void {
    if (this.isTracking) {
      return;
    }
    this.isTracking = true;
    this.despacho
      .rastrear(orderIds?.length ? { orderIds } : {})
      .pipe(finalize(() => { this.isTracking = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (res) => {
          this.rastreo = res;
          if (!res.enabled) {
            this.notify(res.message ?? 'El rastreo automático está apagado.', 'info');
            return;
          }
          const entregados = res.delivered.map((d) => `${d.orderId}${d.signedBy ? ` (${d.signedBy})` : ''}`).join(', ');
          this.notify(`Se consultaron ${res.checked} envío(s): ${res.delivered.length} entregado(s)${entregados ? ` — ${entregados}` : ''}, ${res.inTransit.length} en camino, ${res.errors.length} con incidencia.`, 'success');
          if (res.delivered.length) {
            this.loadPendientes();
          }
        },
        error: (err) => this.notify(this.resolveError(err, 'No se pudo consultar la paquetería.'), 'error')
      });
  }

  cerrar(): void {
    if (this.isClosing) {
      return;
    }
    this.isClosing = true;
    this.despacho
      .cerrar({})
      .pipe(finalize(() => { this.isClosing = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (res) => {
          this.cierre = res;
          if (!res.enabled) {
            this.notify(res.message ?? 'El cierre automático está apagado.', 'info');
            return;
          }
          this.notify(`Cierre ejecutado: se preguntó "¿te llegó?" a ${res.asked.length} cliente(s)${res.asked.length ? ` (${res.asked.join(', ')})` : ''} y se cerraron ${res.closed.length} pedido(s)${res.closed.length ? ` (${res.closed.join(', ')})` : ''}.`, 'success');
          if (res.closed.length || res.asked.length) {
            this.loadPendientes();
          }
        },
        error: (err) => this.notify(this.resolveError(err, 'No se pudo ejecutar el cierre.'), 'error')
      });
  }

  // ── Utilidades ───────────────────────────────────────────────────────────

  money(value: number | string | null | undefined): string {
    const n = Number(value ?? 0);
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number.isFinite(n) ? n : 0);
  }

  trackById(_index: number, item: { id: string }): string {
    return item.id;
  }

  private notify(message: string, tone: Tone): void {
    this.message = message;
    this.messageTone = tone;
    this.requestViewUpdate();
  }

  private resolveError(err: unknown, fallback: string): string {
    const cuerpo = (err as { error?: { message?: string } } | null)?.error;
    const texto = cuerpo?.message;
    return typeof texto === 'string' && texto.trim() ? texto.trim() : fallback;
  }

  private requestViewUpdate(): void {
    this.cdr.markForCheck();
  }
}
