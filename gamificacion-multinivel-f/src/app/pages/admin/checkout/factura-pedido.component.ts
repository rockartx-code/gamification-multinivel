import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { AdminOrder } from '../../../models/admin.model';
import { FacturaEmitida } from '../../../models/checkout.model';
import { CheckoutService } from '../../../services/checkout.service';

/**
 * Paquete C · bloque de factura dentro del detalle de un pedido del back office.
 * Muestra los datos fiscales que dejó el cliente y permite marcar la factura
 * como emitida (folio y PDF opcionales). La confirmación lee lo que guardó el servidor.
 */
@Component({
  selector: 'app-factura-pedido',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiFormFieldComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div *ngIf="order.invoiceStatus === 'solicitada' || order.invoiceStatus === 'emitida'"
      class="mt-2 rounded-lg border px-2 py-1.5 text-xs"
      [ngClass]="order.invoiceStatus === 'emitida' ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-sky-200 bg-sky-50 text-sky-900'">
      <div class="font-semibold">
        <i class="fa-solid fa-file-invoice mr-1" aria-hidden="true"></i>
        {{ order.invoiceStatus === 'emitida' ? 'Factura emitida' : 'Factura solicitada' }}
        <span *ngIf="order.invoiceRequestedAt" class="font-normal text-gray-600"> · pedida el {{ order.invoiceRequestedAt | date: 'dd/MM/yyyy HH:mm' }}</span>
      </div>
      <div *ngIf="order.invoiceData as d" class="mt-1 grid gap-0.5 sm:grid-cols-2">
        <div><span class="text-gray-600">RFC:</span> <span class="font-mono font-semibold">{{ d.rfc }}</span></div>
        <div><span class="text-gray-600">Razón social:</span> {{ d.razonSocial }}</div>
        <div><span class="text-gray-600">Régimen:</span> {{ d.regimenFiscal }}</div>
        <div><span class="text-gray-600">CP fiscal:</span> {{ d.cpFiscal }}</div>
        <div><span class="text-gray-600">Uso CFDI:</span> {{ d.usoCfdi }}</div>
        <div><span class="text-gray-600">Enviar a:</span> {{ d.email }}</div>
      </div>

      <ng-container *ngIf="order.invoiceStatus === 'emitida'">
        <div class="mt-1">
          <span *ngIf="order.invoiceFolio">Folio fiscal: <span class="font-mono font-semibold">{{ order.invoiceFolio }}</span> · </span>
          <span *ngIf="order.invoiceIssuedAt">emitida el {{ order.invoiceIssuedAt | date: 'dd/MM/yyyy HH:mm' }}</span>
          <a *ngIf="order.invoiceFileUrl" [href]="order.invoiceFileUrl" target="_blank" rel="noopener" class="ml-1 underline">Ver archivo</a>
        </div>
      </ng-container>

      <ng-container *ngIf="order.invoiceStatus === 'solicitada' && canMark">
        <div class="mt-2 rounded-lg border border-sky-200 bg-white/70 p-2">
          <div class="text-mini text-gray-600">
            Cuando ya la hayas timbrado en tu sistema de facturación, márcala aquí: el cliente recibe un correo con el folio y el archivo (si lo subes).
          </div>
          <div class="mt-2 grid gap-2 sm:grid-cols-2">
            <ui-form-field label="Folio fiscal (opcional)" placeholder="UUID del CFDI"
              [name]="'folio-' + order.id" [ngModel]="folio" (ngModelChange)="folio = $event"
              inputClass="w-full rounded-lg border border-olive-30 bg-white/70 px-2 py-1 text-xs"></ui-form-field>
            <label class="block">
              <span class="text-xs text-gray-600">Archivo PDF o XML (opcional)</span>
              <input type="file" accept=".pdf,.xml,application/pdf,text/xml" class="mt-1 block w-full text-xs"
                [attr.aria-label]="'Archivo de la factura del pedido ' + order.id"
                (change)="onArchivo($event)">
            </label>
          </div>
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <ui-button variant="primary" size="sm" iconClass="fa-solid fa-file-circle-check"
              [disabled]="enviando" (pressed)="marcarEmitida()">
              {{ enviando ? 'Guardando...' : 'Marcar factura emitida' }}
            </ui-button>
            <span *ngIf="archivoNombre" class="text-mini text-gray-600">Adjunto: {{ archivoNombre }}</span>
          </div>
          <p *ngIf="mensaje" class="mt-2 text-xs" [ngClass]="tono === 'error' ? 'text-red-700' : 'text-emerald-700'">{{ mensaje }}</p>
        </div>
      </ng-container>
    </div>
  `
})
export class FacturaPedidoComponent {
  @Input({ required: true }) order!: AdminOrder;
  /** Quien no tiene `order_mark_paid` solo ve los datos. */
  @Input() canMark = false;
  @Output() emitida = new EventEmitter<FacturaEmitida>();

  folio = '';
  archivoNombre = '';
  private archivoBase64 = '';
  private archivoTipo = '';
  enviando = false;
  mensaje = '';
  tono: 'ok' | 'error' = 'ok';

  constructor(
    private readonly checkout: CheckoutService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  onArchivo(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      this.archivoNombre = '';
      this.archivoBase64 = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const resultado = String(reader.result || '');
      this.archivoBase64 = resultado.includes(',') ? resultado.split(',')[1] : resultado;
      this.archivoTipo = file.type || 'application/pdf';
      this.archivoNombre = file.name;
      this.cdr.markForCheck();
    };
    reader.readAsDataURL(file);
  }

  marcarEmitida(): void {
    if (this.enviando) {
      return;
    }
    this.enviando = true;
    this.mensaje = '';
    this.checkout
      .marcarFacturaEmitida(this.order.id, {
        folioFiscal: this.folio.trim() || undefined,
        name: this.archivoNombre || undefined,
        contentType: this.archivoTipo || undefined,
        contentBase64: this.archivoBase64 || undefined
      })
      .pipe(finalize(() => {
        this.enviando = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: (respuesta) => {
          this.tono = 'ok';
          this.mensaje = `Guardado: factura ${respuesta.invoiceStatus}` +
            (respuesta.invoiceFolio ? ` · folio ${respuesta.invoiceFolio}` : ' · sin folio') +
            (respuesta.invoiceFileUrl ? ' · archivo guardado' : ' · sin archivo') +
            '. Se avisó al cliente por correo.';
          this.emitida.emit(respuesta);
        },
        error: (error: { error?: { message?: string } }) => {
          this.tono = 'error';
          this.mensaje = error?.error?.message || 'No se pudo marcar la factura. Intenta de nuevo.';
        }
      });
  }
}
