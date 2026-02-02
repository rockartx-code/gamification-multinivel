import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, Subscription } from 'rxjs';
import { Router, RouterLink } from '@angular/router';

import { CartItem } from '../../models/cart.model';
import { DashboardGoal } from '../../models/user-dashboard.model';
import { AdminOrderItem } from '../../models/admin.model';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { CartControlService } from '../../services/cart-control.service';
import { GoalControlService } from '../../services/goal-control.service';

@Component({
  selector: 'app-carrito',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './carrito.component.html',
  styleUrl: './carrito.component.css'
})
export class CarritoComponent implements OnInit, OnDestroy {
  constructor(
    private readonly cartControl: CartControlService,
    private readonly cdr: ChangeDetectorRef,
    private readonly goalControl: GoalControlService,
    private readonly api: ApiService,
    private readonly authService: AuthService,
    private readonly router: Router
  ) {}

  isToastVisible = false;
  toastMessage = 'Actualizado.';
  isSummaryOpen = false;
  isPlacingOrder = false;
  deliveryName = '';
  deliveryPhone = '';
  deliveryAddress = '';
  deliveryPostalCode = '';
  deliveryState = '';
  private toastTimeout?: number;
  private countdownInterval?: number;
  private dataSub?: Subscription;
  private goalsSub?: Subscription;
  private customerSub?: Subscription;

  ngOnInit(): void {
    this.cartControl.load().subscribe();
    this.dataSub = this.cartControl.data$.subscribe(() => this.cdr.markForCheck());
    this.goalControl.load().subscribe();
    this.goalsSub = this.goalControl.goals$.subscribe(() => this.cdr.markForCheck());
    this.updateCountdown();
    this.countdownInterval = window.setInterval(() => this.updateCountdown(), 60000);
    this.prefillCustomerAddress();
  }

  ngOnDestroy(): void {
    this.dataSub?.unsubscribe();
    this.goalsSub?.unsubscribe();
    if (this.countdownInterval) {
      window.clearInterval(this.countdownInterval);
    }
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
    this.customerSub?.unsubscribe();
  }

  get countdownLabel(): string {
    return this.cartControl.countdownLabel;
  }

  get cartItems(): CartItem[] {
    return this.cartControl.cartItems;
  }

  get shipping(): number {
    return this.cartControl.shipping;
  }

  get discountPct(): number {
    return this.cartControl.discountPct;
  }

  private get discountPercentValue(): number {
    const raw = this.authService.currentUser?.discountPercent;
    const value = typeof raw === 'string' ? Number(raw) : Number(raw ?? 0);
    return Number.isFinite(value) ? value : 0;
  }

  private get discountActiveValue(): boolean {
    return Boolean(this.authService.currentUser?.discountActive);
  }

  get discountLevelLabel(): string {
    if (!this.discountActiveValue) {
      return 'Inactivo';
    }
    const pct = this.discountPercentValue;
    if (!pct) {
      return 'Sin descuento';
    }
    if (pct >= 40) {
      return 'Nivel 3';
    }
    if (pct >= 35) {
      return 'Nivel 2';
    }
    if (pct >= 30) {
      return 'Nivel 1';
    }
    return 'Nivel base';
  }

  get hasDiscount(): boolean {
    return this.discountActiveValue && this.discountPercentValue > 0;
  }

  get discountPercent(): number {
    return this.hasDiscount ? this.discountPercentValue : 0;
  }

  get discountLabel(): string {
    if (!this.discountActiveValue) {
      return 'Sin descuento';
    }
    const pct = this.discountPercentValue;
    if (!pct) {
      return 'Sin descuento';
    }
    return `Dto ${pct}%`;
  }

  discountedPrice(value: number): number {
    if (!this.hasDiscount) {
      return value;
    }
    const pct = this.discountPercentValue / 100;
    return Math.max(0, Math.round(value * (1 - pct)));
  }

  get subtotal(): number {
    return this.cartControl.subtotal;
  }

  get discount(): number {
    if (!this.hasDiscount) {
      return 0;
    }
    return Math.round(this.subtotal * (this.discountPercentValue / 100));
  }

  get total(): number {
    return Math.max(0, this.subtotal + this.shipping - this.discount);
  }

  get itemsCount(): number {
    return this.cartControl.itemsCount;
  }

  get totalDiscount(): number {
    return this.discount;
  }

  get gapToGoal(): number {
    const goal = this.activeGoal;
    if (!goal) {
      return this.cartControl.gapToGoal;
    }
    const target = Number(goal.target ?? 0);
    const base = Number(goal.base ?? 0);
    const remaining = Math.max(0, target - base);
    return Math.max(0, remaining - this.subtotal);
  }

  get benefitPercent(): number {
    const goal = this.activeGoal;
    if (!goal) {
      return this.cartControl.benefitPercent;
    }
    const target = Number(goal.target ?? 0);
    const base = Number(goal.base ?? 0);
    const remaining = Math.max(0, target - base);
    if (remaining === 0) {
      return 100;
    }
    return Math.min(100, (this.subtotal / remaining) * 100);
  }

  private get activeGoal(): DashboardGoal | null {
    return this.goalControl.goals.find((goal) => goal.key === 'active') ?? null;
  }

  formatMoney(value: number): string {
    return this.cartControl.formatMoney(value);
  }

  setQty(itemId: string, qty: number): void {
    const normalized = Math.max(0, Math.floor(qty));
    this.cartControl.setQty(itemId, normalized);
    this.cdr.markForCheck();
    if (normalized === 0) {
      this.showToast('Producto removido.');
      return;
    }
    this.showToast('Cantidad actualizada.');
  }

  removeItem(itemId: string): void {
    this.cartControl.removeItem(itemId);
    this.cdr.markForCheck();
    this.showToast('Producto removido.');
  }

  addSuggested(): void {
    this.cartControl.addSuggested();
    this.cdr.markForCheck();
    this.showToast('Agregado sugerido.');
  }

  placeOrder(): void {
    if (!this.cartItems.length) {
      this.showToast('Agrega productos para continuar.');
      return;
    }
    if (this.isPlacingOrder) {
      return;
    }
    const address = this.deliveryAddress.trim();
    const postalCode = this.deliveryPostalCode.trim();
    const state = this.deliveryState.trim();
    if (!address || !postalCode || !state) {
      this.showToast('Completa dirección, CP y estado para continuar.');
      this.scrollToSection('detalle-carrito');
      return;
    }
    const user = this.authService.currentUser;
    const items: AdminOrderItem[] = this.cartItems.map((item) => ({
      productId: Number(item.id),
      name: item.name,
      price: item.price,
      quantity: item.qty
    }));
    const payload = {
      customerId: user?.userId ? Number(user.userId) : 0,
      customerName: user?.name || this.deliveryName.trim() || 'Cliente',
      status: 'pending' as const,
      items,
      recipientName: this.deliveryName.trim() || user?.name,
      phone: this.deliveryPhone.trim() || undefined,
      address,
      postalCode,
      state
    };
    this.isPlacingOrder = true;
    this.api
      .createOrder(payload)
      .pipe(
        finalize(() => {
          this.isPlacingOrder = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (order) => {
          const resolvedId = (order as { id?: string | number; orderId?: string | number } | null)?.id ??
            (order as { orderId?: string | number } | null)?.orderId ??
            '';
          if (!resolvedId) {
            this.showToast('Orden creada, pero no se recibió el ID.');
            return;
          }
          const orderId = String(resolvedId);
          this.showToast('Orden creada. Redirigiendo...');
          this.router.navigate(['/orden', orderId]);
        },
        error: () => {
          this.showToast('No se pudo crear la orden.');
        }
      });
  }

  showSummary(): void {
    if (window.matchMedia('(min-width: 1024px)').matches) {
      this.scrollToSection('resumen-carrito');
      return;
    }
    this.isSummaryOpen = true;
  }

  closeSummary(): void {
    this.isSummaryOpen = false;
  }

  showDetails(): void {
    this.isSummaryOpen = false;
    this.scrollToSection('detalle-carrito');
  }

  private updateCountdown(): void {
    const now = new Date();
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    lastDay.setHours(23, 59, 59, 999);
    const diff = Math.max(0, lastDay.getTime() - Date.now());
    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
    this.cartControl.updateCountdown(`${d}d ${h}h`);
  }

  private showToast(message: string): void {
    this.toastMessage = message;
    this.isToastVisible = true;
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
    this.toastTimeout = window.setTimeout(() => {
      this.isToastVisible = false;
    }, 2200);
  }

  private scrollToSection(id: string): void {
    const section = document.getElementById(id);
    if (!section) {
      return;
    }
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  private prefillCustomerAddress(): void {
    const user = this.authService.currentUser;
    if (!user?.userId || user.role !== 'cliente') {
      return;
    }
    this.customerSub = this.api.getCustomer(String(user.userId)).subscribe({
      next: (customer) => {
        this.deliveryName = this.deliveryName || customer.name || '';
        this.deliveryPhone = this.deliveryPhone || customer.phone || '';
        this.deliveryAddress = this.deliveryAddress || customer.address || '';
        const resolvedState = customer.state || customer.city || '';
        this.deliveryState = this.deliveryState || resolvedState;
        this.deliveryPostalCode = this.deliveryPostalCode || customer.postalCode || '';
        this.cdr.markForCheck();
      },
      error: () => {
        // No-op: fallback to manual entry.
      }
    });
  }
}
