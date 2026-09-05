import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiCheckboxComponent } from '../../../components/ui-checkbox/ui-checkbox.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { UiModalComponent } from '../../../components/ui-modal/ui-modal.component';
import { LoteSaltoCodigo, PagoFila, PagoPeriodo, PagosMes } from '../../../models/pagos.model';
import { AdminControlService } from '../../../services/admin-control.service';
import { PagosService } from '../../../services/pagos.service';

type ModalPagos = 'lote' | 'deshacer' | 'pedir-clabe' | null;

const MOTIVO_SALTO: Record<LoteSaltoCodigo, string> = {
  CLABE_REQUIRED: 'sin CLABE registrada',
  ALREADY_PAID: 'ya estaba pagada',
  NO_CONFIRMED: 'sin comisión confirmada'
};

/**
 * Paquete A · "Pagos del mes" (doc 23 §1.2). Se monta al final de la sección
 * Clientes del back office. Todo lo que se confirma en pantalla se lee de la
 * respuesta del servidor, nunca del formulario.
 */
@Component({
  selector: 'app-pagos-mes',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiCheckboxComponent, UiFormFieldComponent, UiModalComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './pagos-mes.component.html'
})
export class PagosMesComponent implements OnInit, OnChanges {
  /** Mes contable AAAA-MM. Si no llega, el mes anterior al actual. */
  @Input() month = '';
  /** Quien no puede registrar pagos ve la tabla pero no los botones. */
  @Input() canRegister = true;

  monthKey = '';
  monthOptions: Array<{ value: string; label: string }> = [];
  /** Periodos y hora del servidor (17): ninguna fecha sale del navegador. */
  periodos: PagoPeriodo[] = [];
  serverNow = '';
  payoutDay = 10;
  periodosError = '';

  data: PagosMes | null = null;
  isLoading = false;
  loadError = '';
  /** Confirmación de la última acción, con los datos leídos de la respuesta. */
  confirmation = '';
  confirmationDetails: string[] = [];
  actionError = '';

  selected = new Set<string>();

  modal: ModalPagos = null;
  isSaving = false;
  modalError = '';

  loteFile: File | null = null;
  loteReference = '';

  targetRow: PagoFila | null = null;
  undoReason = '';

  constructor(
    private readonly pagos: PagosService,
    private readonly adminControl: AdminControlService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.cargarPeriodos();
  }

  /**
   * WP-A · propuesta 17: los meses los manda el servidor. Renata recargó la
   * página tres veces y marzo de 2027 ya no estaba en el selector, porque los
   * doce meses se armaban con `new Date()` del navegador.
   */
  private cargarPeriodos(): void {
    this.pagos.getPeriodos().subscribe({
      next: (datos) => {
        this.serverNow = datos.serverNow;
        this.payoutDay = datos.payoutDay ?? 10;
        this.periodos = datos.periodos ?? [];
        this.monthOptions = this.periodos.map((p) => ({ value: p.monthKey, label: p.label }));
        this.monthKey = this.month || datos.defaultMonth;
        this.ensureMonthOption(this.monthKey);
        this.requestViewUpdate();
        this.load();
      },
      error: () => {
        // Sin periodos no se inventa un mes con el reloj del navegador: se dice.
        this.periodosError = 'No pudimos leer los meses con comisiones. Se muestra el mes que venía seleccionado.';
        this.monthKey = this.month || this.monthKey;
        this.ensureMonthOption(this.monthKey);
        this.requestViewUpdate();
        if (this.monthKey) {
          this.load();
        }
      }
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['month'] && !changes['month'].firstChange && this.month && this.month !== this.monthKey) {
      this.monthKey = this.month;
      this.ensureMonthOption(this.monthKey);
      this.selected.clear();
      this.clearMessages();
      this.load();
    }
  }

  /** Si llega un mes por `Input` que el servidor no listó (aún sin datos), se añade. */
  private ensureMonthOption(key: string): void {
    if (!key || this.monthOptions.some((o) => o.value === key)) {
      return;
    }
    this.monthOptions = [...this.monthOptions, { value: key, label: this.labelForMonth(key) }]
      .sort((a, b) => (a.value < b.value ? 1 : a.value > b.value ? -1 : 0));
  }

  /** El periodo del mes en pantalla, tal como lo publicó el servidor. */
  get periodoActivo(): PagoPeriodo | null {
    return this.periodos.find((p) => p.monthKey === this.monthKey) ?? null;
  }

  /** "Ninguna pantalla se planta sola en un mes sin datos sin decirlo" (17). */
  get avisoMesSinDatos(): string {
    if (!this.monthKey || this.isLoading || !this.periodos.length || this.periodoActivo) {
      return '';
    }
    return `En ${this.monthLabel} no hay comisiones registradas. Los meses con movimientos son ${this.periodos.map((p) => p.label).join(', ')}.`;
  }

  // ─── Carga ────────────────────────────────────────────────────────────

  load(): void {
    if (!this.monthKey) {
      return;
    }
    this.isLoading = true;
    this.loadError = '';
    this.pagos
      .getPagosMes(this.monthKey)
      .pipe(
        finalize(() => {
          this.isLoading = false;
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (data) => {
          this.data = data;
          // Solo se pueden seleccionar filas que sigan listas.
          const listas = new Set(data.rows.filter((r) => r.status === 'listo').map((r) => r.customerId));
          this.selected = new Set([...this.selected].filter((id) => listas.has(id)));
          this.requestViewUpdate();
        },
        error: (error: unknown) => {
          this.data = null;
          this.loadError = this.errorMessage(error, 'No se pudo cargar la lista de pagos. Intenta de nuevo.');
          this.requestViewUpdate();
        }
      });
  }

  onMonthChange(value: string): void {
    if (!value || value === this.monthKey) {
      return;
    }
    this.monthKey = value;
    this.selected.clear();
    this.clearMessages();
    this.load();
  }

  // ─── Derivados ────────────────────────────────────────────────────────

  get rows(): PagoFila[] {
    return this.data?.rows ?? [];
  }

  get readyRows(): PagoFila[] {
    return this.rows.filter((r) => r.status === 'listo');
  }

  get selectedRows(): PagoFila[] {
    return this.readyRows.filter((r) => this.selected.has(r.customerId));
  }

  get selectedTotal(): number {
    return this.selectedRows.reduce((sum, r) => sum + r.amount, 0);
  }

  get allReadySelected(): boolean {
    return this.readyRows.length > 0 && this.readyRows.every((r) => this.selected.has(r.customerId));
  }

  get monthLabel(): string {
    return this.labelForMonth(this.monthKey);
  }

  isSelected(row: PagoFila): boolean {
    return this.selected.has(row.customerId);
  }

  toggleRow(row: PagoFila, checked: boolean): void {
    if (row.status !== 'listo') {
      return;
    }
    if (checked) {
      this.selected.add(row.customerId);
    } else {
      this.selected.delete(row.customerId);
    }
    this.requestViewUpdate();
  }

  toggleAll(checked: boolean): void {
    this.selected = checked ? new Set(this.readyRows.map((r) => r.customerId)) : new Set();
    this.requestViewUpdate();
  }

  trackByCustomer(_index: number, row: PagoFila): string {
    return row.customerId;
  }

  statusLabel(status: PagoFila['status']): string {
    if (status === 'listo') return 'Lista para depositar';
    if (status === 'sin_clabe') return 'Sin CLABE';
    if (status === 'por_confirmar') return 'Nada que depositar aún';
    return 'Pagada';
  }

  statusClass(status: PagoFila['status']): string {
    if (status === 'listo') return 'badge badge-compact level-1 status-active';
    if (status === 'sin_clabe') return 'badge badge-compact level-3';
    if (status === 'por_confirmar') return 'badge badge-compact level-2';
    return 'badge badge-compact level-5 status-inactive';
  }

  /** El pedido que frena un importe y cuántos días lleva parado (18). */
  frenoTexto(freno: PagoFila['frenoPorConfirmar']): string {
    if (!freno) {
      return '';
    }
    const dias = freno.dias === 1 ? '1 día' : `${freno.dias} días`;
    const otros = freno.pedidos > 1 ? ` y ${freno.pedidos - 1} pedido${freno.pedidos > 2 ? 's' : ''} más` : '';
    return `Pedido ${freno.orderId}${otros} · ${dias} · ${freno.texto}`;
  }

  /**
   * WP-A · propuesta 35: el botón apagado dice el número, no solo que no hay.
   * *"No hay socias listas para depositar este mes · 1 espera CLABE ($135.00)"*.
   */
  get motivoExportacionApagada(): string {
    if (this.isSaving) {
      return 'Guardando…';
    }
    if (this.readyRows.length) {
      return '';
    }
    const partes: string[] = [];
    const sinClabe = this.data?.totals?.sinClabe;
    const porConfirmar = this.data?.totals?.porConfirmar ?? 0;
    if (sinClabe?.count) {
      partes.push(`${sinClabe.count} ${sinClabe.count === 1 ? 'espera' : 'esperan'} CLABE (${this.formatMoney(sinClabe.amount)})`);
    }
    if (porConfirmar > 0) {
      partes.push(`${this.formatMoney(porConfirmar)} por confirmar`);
    }
    const detalle = partes.length ? ` · ${partes.join(' · ')}` : '';
    return `No hay socias listas para depositar este mes${detalle}.`;
  }

  get hayPendientes(): boolean {
    return (this.data?.totals?.sinClabe?.count ?? 0) > 0 || (this.data?.totals?.porConfirmarFilas?.count ?? 0) > 0;
  }

  formatMoney(value: number): string {
    return `$${(value ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  formatDate(value?: string | null): string {
    if (!value) return '';
    const date = new Date(value);
    return isNaN(date.getTime()) ? value : date.toLocaleDateString('es-MX', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  // ─── Exportar CSV ─────────────────────────────────────────────────────

  exportCsv(): void {
    if (!this.readyRows.length || this.isSaving) {
      return;
    }
    this.clearMessages();
    this.isSaving = true;
    this.pagos
      .descargarDispersionCsv(this.monthKey)
      .pipe(
        finalize(() => {
          this.isSaving = false;
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (csv) => {
          const lineas = csv.split(/\r?\n/).filter((l) => l.trim().length > 0).length - 1;
          this.downloadText(csv, `dispersion-${this.monthKey}.csv`);
          this.confirmation = `Archivo dispersion-${this.monthKey}.csv descargado con ${lineas} ${lineas === 1 ? 'depósito' : 'depósitos'} por ${this.formatMoney(this.data?.totals.listo.amount ?? 0)}. Súbelo al portal del banco; después registra aquí el comprobante.`;
        },
        error: (error: unknown) => {
          this.actionError = this.errorMessage(error, 'No se pudo generar el archivo de dispersión.');
        }
      });
  }

  /** WP-A · propuesta 35: el anexo de las que faltan, como segundo archivo. */
  exportPendientesCsv(): void {
    if (!this.hayPendientes || this.isSaving) {
      return;
    }
    this.clearMessages();
    this.isSaving = true;
    this.pagos
      .descargarPendientesCsv(this.monthKey)
      .pipe(
        finalize(() => {
          this.isSaving = false;
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (csv) => {
          const lineas = csv.split(/\r?\n/).filter((l) => l.trim().length > 0).length - 1;
          this.downloadText(csv, `pendientes-${this.monthKey}.csv`);
          this.confirmation = `Archivo pendientes-${this.monthKey}.csv descargado con ${lineas} ${lineas === 1 ? 'socia' : 'socias'} que todavía no se pueden depositar, con el motivo de cada una. No es el archivo del banco: ese lleva solo a las listas.`;
        },
        error: (error: unknown) => {
          this.actionError = this.errorMessage(error, 'No se pudo generar el anexo de pendientes.');
        }
      });
  }

  // ─── Modales ──────────────────────────────────────────────────────────

  openLote(): void {
    if (!this.canRegister || !this.selectedRows.length) {
      return;
    }
    this.clearMessages();
    this.loteFile = null;
    this.loteReference = '';
    this.modalError = '';
    this.modal = 'lote';
    this.requestViewUpdate();
  }

  openUndo(row: PagoFila): void {
    if (!this.canRegister) {
      return;
    }
    this.clearMessages();
    this.targetRow = row;
    this.undoReason = '';
    this.modalError = '';
    this.modal = 'deshacer';
    this.requestViewUpdate();
  }

  openPedirClabe(row: PagoFila): void {
    if (!this.canRegister) {
      return;
    }
    this.clearMessages();
    this.targetRow = row;
    this.modalError = '';
    this.modal = 'pedir-clabe';
    this.requestViewUpdate();
  }

  closeModal(): void {
    if (this.isSaving) {
      return;
    }
    this.modal = null;
    this.targetRow = null;
    this.loteFile = null;
    this.modalError = '';
    this.requestViewUpdate();
  }

  updateLoteFile(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.loteFile = target.files?.[0] ?? null;
    this.modalError = '';
    this.requestViewUpdate();
  }

  // ─── Acciones ─────────────────────────────────────────────────────────

  confirmLote(): void {
    const filas = this.selectedRows;
    if (!this.canRegister || !filas.length || this.isSaving) {
      return;
    }
    if (!this.loteFile) {
      this.modalError = 'Adjunta el comprobante de la transferencia (PDF o imagen) para poder registrar el pago.';
      this.requestViewUpdate();
      return;
    }
    const file = this.loteFile;
    const monthKey = this.monthKey;
    this.isSaving = true;
    this.modalError = '';
    this.requestViewUpdate();
    this.readFileAsBase64(file)
      .then((contentBase64) => {
        this.pagos
          .registrarLote({
            monthKey,
            customerIds: filas.map((r) => r.customerId),
            name: file.name,
            contentType: file.type || 'application/octet-stream',
            contentBase64,
            bankReference: this.loteReference.trim() || undefined
          })
          .pipe(
            finalize(() => {
              this.isSaving = false;
              this.requestViewUpdate();
            })
          )
          .subscribe({
            next: (r) => {
              const nombres = new Map(filas.map((f) => [f.customerId, f.name]));
              this.confirmation = `Lote ${r.batchId}: ${r.paid.length} ${r.paid.length === 1 ? 'comisión marcada' : 'comisiones marcadas'} como pagadas por ${this.formatMoney(r.totalPaid)}. El comprobante quedó ligado a cada una y se avisó por correo a cada socia.`;
              this.confirmationDetails = [
                ...r.paid.map((p) => `${nombres.get(p.customerId) ?? p.customerId}: ${this.formatMoney(p.amount)} · pagada`),
                ...r.skipped.map((s) => `${nombres.get(s.customerId) ?? s.customerId}: no se marcó (${MOTIVO_SALTO[s.code] ?? s.code})`)
              ];
              this.selected.clear();
              this.modal = null;
              this.load();
              this.refreshAdmin();
            },
            error: (error: unknown) => {
              this.modalError = this.errorMessage(error, 'No se pudo registrar el lote. Revisa el archivo e intenta de nuevo.');
            }
          });
      })
      .catch(() => {
        this.isSaving = false;
        this.modalError = 'No se pudo leer el archivo del comprobante.';
        this.requestViewUpdate();
      });
  }

  confirmUndo(): void {
    const row = this.targetRow;
    if (!this.canRegister || !row || this.isSaving) {
      return;
    }
    const motivo = this.undoReason.trim();
    if (motivo.length < 5) {
      this.modalError = 'Escribe el motivo (por ejemplo: "se transfirió a otra cuenta"). Queda guardado junto al comprobante anulado.';
      this.requestViewUpdate();
      return;
    }
    this.isSaving = true;
    this.modalError = '';
    this.requestViewUpdate();
    this.pagos
      .deshacerPago(row.customerId, this.monthKey, motivo)
      .pipe(
        finalize(() => {
          this.isSaving = false;
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (r) => {
          this.confirmation = `El pago de ${row.name} del mes ${this.labelForMonth(r.monthKey)} volvió a pendiente: ${r.receiptsVoided} ${r.receiptsVoided === 1 ? 'comprobante anulado' : 'comprobantes anulados'}${r.batchId ? ` (era del lote ${r.batchId}; las demás filas del lote no se tocaron)` : ''}.`;
          this.confirmationDetails = [];
          this.modal = null;
          this.targetRow = null;
          this.load();
          this.refreshAdmin();
        },
        error: (error: unknown) => {
          this.modalError = this.errorMessage(error, 'No se pudo deshacer el pago.');
        }
      });
  }

  confirmPedirClabe(): void {
    const row = this.targetRow;
    if (!this.canRegister || !row || this.isSaving) {
      return;
    }
    this.isSaving = true;
    this.modalError = '';
    this.requestViewUpdate();
    this.pagos
      .pedirClabe(row.customerId, this.monthKey)
      .pipe(
        finalize(() => {
          this.isSaving = false;
          this.requestViewUpdate();
        })
      )
      .subscribe({
        next: (r) => {
          const canal = r.channel === 'email+panel' ? `por correo (${r.email}) y con un aviso en su panel` : 'con un aviso en su panel (tiene "no contactar": no se mandó correo)';
          this.confirmation = `Recordatorio de CLABE enviado a ${r.name} ${canal}. Quedó anotado en su ficha.`;
          this.confirmationDetails = [];
          this.modal = null;
          this.targetRow = null;
          this.load();
        },
        error: (error: unknown) => {
          this.modalError = this.errorMessage(error, 'No se pudo enviar el recordatorio.');
        }
      });
  }

  // ─── Utilidades ───────────────────────────────────────────────────────

  private refreshAdmin(): void {
    // La lista de Clientes y "Acciones urgentes" leen otros endpoints: se recargan.
    this.adminControl.load().subscribe({ next: () => this.requestViewUpdate(), error: () => undefined });
  }

  private clearMessages(): void {
    this.confirmation = '';
    this.confirmationDetails = [];
    this.actionError = '';
  }

  private labelForMonth(key: string): string {
    const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
    const m = Number(key?.slice(5, 7));
    return m >= 1 && m <= 12 ? `${meses[m - 1]} ${key.slice(0, 4)}` : key;
  }

  private readFileAsBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = String(reader.result ?? '');
        const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : '';
        base64 ? resolve(base64) : reject(new Error('archivo vacío'));
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  }

  private downloadText(content: string, fileName: string): void {
    // BOM para que Excel abra el CSV con acentos correctos.
    const blob = new Blob(['\ufeff' + content], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  private errorMessage(error: unknown, fallback: string): string {
    const err = error as { error?: { message?: string; code?: string } };
    const message = err?.error?.message;
    return typeof message === 'string' && message.trim() ? message.trim() : fallback;
  }

  private requestViewUpdate(): void {
    this.cdr.markForCheck();
  }
}
