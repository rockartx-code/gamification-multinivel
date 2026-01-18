import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService, AuthUser } from '../../services/auth.service';
import {
  AdminAssetSlot,
  AdminCustomer,
  AdminOrder,
  AdminProduct,
  AdminWarning
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

  ngOnInit(): void {
    this.adminControl.load().subscribe(() => {
      if (!this.selectedCustomer) {
        this.selectedCustomer = this.adminControl.customers[0] ?? null;
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
