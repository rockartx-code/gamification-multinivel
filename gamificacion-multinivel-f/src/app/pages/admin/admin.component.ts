import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService, AuthUser } from '../../services/auth.service';
import {
  AdminAssetSlot,
  AdminCustomer,
  AdminOrder,
  AdminOrderItem,
  AdminProduct,
  AdminWarning,
  CreateAdminOrderPayload
} from '../../models/admin.model';
import { AdminControlService } from '../../services/admin-control.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {
  constructor(
    private readonly adminControl: AdminControlService,
    private readonly authService: AuthService,
    private readonly router: Router
  ) {}

  currentView: 'orders' | 'customers' | 'products' | 'stats' = 'orders';
  currentOrderStatus: AdminOrder['status'] = 'pending';
  isActionsModalOpen = false;
  isNewOrderModalOpen = false;
  isAddStructureModalOpen = false;

  selectedCustomer: AdminCustomer | null = null;
  assetPreviews = new Map<number, string>();
  newOrderCustomerId: number | null = null;
  newOrderStatus: AdminOrder['status'] = 'pending';
  newOrderItems = new Map<number, number>();
  isSavingOrder = false;

  ngOnInit(): void {
    this.adminControl.load().subscribe(() => {
      if (!this.selectedCustomer) {
        this.selectedCustomer = this.adminControl.customers[0] ?? null;
      }
      if (!this.newOrderCustomerId) {
        this.newOrderCustomerId = this.adminControl.customers[0]?.id ?? null;
      }
    });
  }

  get orders(): AdminOrder[] {
    return this.adminControl.orders;
  }

  get customers(): AdminCustomer[] {
    return this.adminControl.customers;
  }

  get products(): AdminProduct[] {
    return this.adminControl.data?.products ?? [];
  }

  get warnings(): AdminWarning[] {
    return this.adminControl.data?.warnings ?? [];
  }

  get assetSlots(): AdminAssetSlot[] {
    return this.adminControl.data?.assetSlots ?? [];
  }

  get viewTitle(): string {
    if (this.currentView === 'customers') {
      return 'Clientes';
    }
    if (this.currentView === 'products') {
      return 'Productos';
    }
    if (this.currentView === 'stats') {
      return 'Estadísticas';
    }
    return 'Pedidos';
  }

  get viewSubtitle(): string {
    if (this.currentView === 'customers') {
      return 'Niveles, estructura y comisiones.';
    }
    if (this.currentView === 'products') {
      return 'Altas, imágenes y CTA.';
    }
    if (this.currentView === 'stats') {
      return 'Ventas, funnel y alertas.';
    }
    return 'Cambia estado: pendiente, pagado, entregado.';
  }

  get filteredOrders(): AdminOrder[] {
    return this.adminControl.getFilteredOrders(this.currentOrderStatus);
  }

  get pendingCount(): number {
    return this.adminControl.pendingCount;
  }

  get paidCount(): number {
    return this.adminControl.paidCount;
  }

  get shipCount(): number {
    return this.adminControl.shipCount;
  }

  get commissionsTotal(): number {
    return this.adminControl.commissionsTotal;
  }

  get customersCount(): number {
    return this.adminControl.customersCount;
  }

  get productsCount(): number {
    return this.adminControl.productsCount;
  }

  get currentUser(): AuthUser | null {
    return this.authService.currentUser;
  }

  formatMoney(value: number): string {
    return this.adminControl.formatMoney(value);
  }

  setView(view: 'orders' | 'customers' | 'products' | 'stats'): void {
    this.currentView = view;
  }

  setOrderStatus(status: AdminOrder['status']): void {
    this.currentOrderStatus = status;
  }

  showActions(): void {
    this.currentView = 'stats';
    this.isActionsModalOpen = true;
    setTimeout(() => {
      const actionsPanel = document.getElementById('admin-actions');
      actionsPanel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 0);
  }

  openNewOrderModal(): void {
    this.resetNewOrderForm();
    this.isNewOrderModalOpen = true;
  }

  openAddStructureModal(): void {
    this.isAddStructureModalOpen = true;
  }

  closeModals(): void {
    this.isActionsModalOpen = false;
    this.isNewOrderModalOpen = false;
    this.isAddStructureModalOpen = false;
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  advanceOrder(orderId: string): void {
    this.adminControl.advanceOrder(orderId);
  }

  updateNewOrderCustomer(customerId: number): void {
    this.newOrderCustomerId = customerId;
  }

  updateNewOrderStatus(status: AdminOrder['status']): void {
    this.newOrderStatus = status;
  }

  toggleProductSelection(productId: number, selected: boolean): void {
    if (selected) {
      this.newOrderItems.set(productId, this.newOrderItems.get(productId) ?? 1);
      return;
    }
    this.newOrderItems.delete(productId);
  }

  updateProductQty(productId: number, quantityValue: string): void {
    const quantity = Math.max(1, Number(quantityValue) || 1);
    if (this.newOrderItems.has(productId)) {
      this.newOrderItems.set(productId, quantity);
    }
  }

  getNewOrderItems(): AdminOrderItem[] {
    return this.products
      .filter((product) => this.newOrderItems.has(product.id))
      .map((product) => ({
        productId: product.id,
        name: product.name,
        price: product.price,
        quantity: this.newOrderItems.get(product.id) ?? 1
      }));
  }

  getNewOrderTotal(): number {
    return this.getNewOrderItems().reduce((acc, item) => acc + item.price * item.quantity, 0);
  }

  saveNewOrder(): void {
    if (!this.newOrderCustomerId || this.newOrderItems.size === 0 || this.isSavingOrder) {
      return;
    }
    const customer = this.customers.find((entry) => entry.id === this.newOrderCustomerId);
    if (!customer) {
      return;
    }
    const payload: CreateAdminOrderPayload = {
      customerId: customer.id,
      customerName: customer.name,
      status: this.newOrderStatus,
      items: this.getNewOrderItems()
    };
    this.isSavingOrder = true;
    this.adminControl.createOrder(payload).subscribe({
      next: () => {
        this.isSavingOrder = false;
        this.closeModals();
      },
      error: () => {
        this.isSavingOrder = false;
      }
    });
  }

  resetNewOrderForm(): void {
    this.newOrderCustomerId = this.customers[0]?.id ?? null;
    this.newOrderStatus = 'pending';
    this.newOrderItems.clear();
    this.isSavingOrder = false;
  }

  selectCustomer(customerId: number): void {
    const selected = this.adminControl.selectCustomer(customerId);
    if (selected) {
      this.selectedCustomer = selected;
    }
  }

  previewAsset(event: Event, slotIndex: number): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) {
      return;
    }
    const previewUrl = URL.createObjectURL(file);
    const currentUrl = this.assetPreviews.get(slotIndex);
    if (currentUrl) {
      URL.revokeObjectURL(currentUrl);
    }
    this.assetPreviews.set(slotIndex, previewUrl);
  }
}
