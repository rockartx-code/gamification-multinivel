import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import {
  AdminOrder,
  OrderReturnEvidenceFile,
  OrderReturnMotivo,
  OrderReturnRequestResponse
} from '../../models/admin.model';
import { ApiService } from '../../services/api.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';

type Step = 1 | 2 | 3;

@Component({
  selector: 'app-order-devolucion',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent],
  templateUrl: './order-devolucion.component.html'
})
export class OrderDevolucionComponent implements OnInit {
  orderId = '';
  order: AdminOrder | null = null;
  isLoading = true;
  isSubmitting = false;
  error = '';
  step: Step = 1;
  result: OrderReturnRequestResponse | null = null;

  // Step 1
  motivo: OrderReturnMotivo | '' = '';
  descripcion = '';

  // Step 2 — evidence files
  fotosProducto: OrderReturnEvidenceFile[] = [];
  fotosEmpaque: OrderReturnEvidenceFile[] = [];
  fotosGuia: OrderReturnEvidenceFile[] = [];

  // Preview names
  fotosProductoNames: string[] = [];
  fotosEmpaqueNames: string[] = [];
  fotosGuiaNames: string[] = [];

  readonly motivos: Array<{ value: OrderReturnMotivo; label: string; hint: string }> = [
    { value: 'DANADO_DEFECTUOSO', label: 'Producto dañado o defectuoso', hint: 'El producto llegó roto, dañado o no funciona.' },
    { value: 'ERROR_ENVIO', label: 'Error en el envío', hint: 'Recibiste un producto diferente al pedido.' },
    { value: 'DESISTIMIENTO', label: 'Desistimiento (arrepentimiento)', hint: 'Decidiste no quedarte con el producto.' }
  ];

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.orderId = this.route.snapshot.paramMap.get('idOrden') ?? '';
    if (!this.orderId) { void this.router.navigate(['/dashboard']); return; }

    this.api.getOrder(this.orderId)
      .pipe(finalize(() => { this.isLoading = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: (order) => {
          this.order = order;
          if ((order?.status ?? '') !== 'delivered') {
            this.error = 'Solo puedes solicitar devoluciones de pedidos entregados.';
          }
        },
        error: () => { this.error = 'No se pudo cargar la orden.'; }
      });
  }

  get orderIsDelivered(): boolean { return this.order?.status === 'delivered'; }
  get canProceedStep1(): boolean { return this.motivo !== ''; }
  get canProceedStep2(): boolean {
    return this.fotosProducto.length > 0 &&
           this.fotosEmpaque.length > 0 &&
           this.fotosGuia.length > 0;
  }
  get shippingResponsibility(): 'empresa' | 'cliente' {
    return this.motivo === 'DESISTIMIENTO' ? 'cliente' : 'empresa';
  }
  get motivoLabel(): string {
    return this.motivos.find(m => m.value === this.motivo)?.label ?? '';
  }

  nextStep(): void {
    if (this.step === 1 && this.canProceedStep1) this.step = 2;
    else if (this.step === 2 && this.canProceedStep2) this.step = 3;
    this.cdr.markForCheck();
  }
  prevStep(): void {
    if (this.step > 1) { this.step = (this.step - 1) as Step; this.cdr.markForCheck(); }
  }

  onFilesChange(category: 'producto' | 'empaque' | 'guia', event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!files.length) return;

    const results: OrderReturnEvidenceFile[] = [];
    const names: string[] = [];
    let pending = files.length;

    files.forEach(file => {
      names.push(file.name);
      const reader = new FileReader();
      reader.onload = () => {
        const raw = reader.result as string;
        const [meta, contentBase64] = raw.split(',');
        const contentType = (meta?.match(/:(.*?);/) ?? [])[1] ?? 'image/jpeg';
        results.push({ contentBase64: contentBase64 ?? '', contentType, fileName: file.name });
        if (--pending === 0) {
          if (category === 'producto') { this.fotosProducto = results; this.fotosProductoNames = names; }
          else if (category === 'empaque') { this.fotosEmpaque = results; this.fotosEmpaqueNames = names; }
          else { this.fotosGuia = results; this.fotosGuiaNames = names; }
          this.cdr.markForCheck();
        }
      };
      reader.readAsDataURL(file);
    });
  }

  submit(): void {
    if (!this.canProceedStep2 || !this.motivo || this.isSubmitting) return;
    this.isSubmitting = true;
    this.error = '';

    this.api.requestReturn(this.orderId, {
      motivo: this.motivo,
      descripcion: this.descripcion.trim() || undefined,
      evidence: {
        fotos_producto: this.fotosProducto,
        fotos_empaque: this.fotosEmpaque,
        fotos_guia_envio: this.fotosGuia
      }
    }).pipe(finalize(() => { this.isSubmitting = false; this.cdr.markForCheck(); }))
      .subscribe({
        next: (res) => { this.result = res; },
        error: (err: any) => {
          this.error = err?.error?.message || 'No se pudo enviar la solicitud.';
        }
      });
  }

  formatMoney(v?: number | null): string {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(v ?? 0);
  }
}
