import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

interface Order {
  id: string;
  customer: string;
  total: number;
  status: 'pending' | 'paid' | 'delivered';
}

interface Customer {
  id: number;
  name: string;
  email: string;
  level: string;
  discount: string;
  commissions: number;
}

interface Product {
  id: number;
  name: string;
  price: number;
  active: boolean;
}

interface Warning {
  type: string;
  text: string;
  severity: 'high' | 'medium' | 'low';
}

interface AssetSlot {
  label: string;
  hint: string;
}

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent {
  currentView: 'orders' | 'customers' | 'products' | 'stats' = 'orders';
  currentOrderStatus: Order['status'] = 'pending';
  isActionsModalOpen = false;
  isNewOrderModalOpen = false;
  isAddStructureModalOpen = false;

  readonly orders: Order[] = [
    { id: '#1001', customer: 'Ana López', total: 120, status: 'pending' },
    { id: '#1002', customer: 'Carlos Ruiz', total: 89, status: 'paid' },
    { id: '#1003', customer: 'María Pérez', total: 210, status: 'paid' },
    { id: '#1004', customer: 'Luis Gómez', total: 60, status: 'delivered' }
  ];

  readonly customers: Customer[] = [
    {
      id: 1,
      name: 'Ana López',
      email: 'ana@mail.com',
      level: 'Oro',
      discount: '15%',
      commissions: 320
    },
    {
      id: 2,
      name: 'Carlos Ruiz',
      email: 'carlos@mail.com',
      level: 'Plata',
      discount: '10%',
      commissions: 120
    },
    {
      id: 3,
      name: 'María Pérez',
      email: 'maria@mail.com',
      level: 'Bronce',
      discount: '5%',
      commissions: 0
    }
  ];

  readonly products: Product[] = [
    { id: 1, name: 'COLÁGENO', price: 35, active: true },
    { id: 2, name: 'OMEGA-3', price: 29, active: true },
    { id: 3, name: 'COMPLEJO B', price: 24, active: false }
  ];

  readonly warnings: Warning[] = [
    { type: 'commissions', text: '3 comisiones pendientes por depositar', severity: 'high' },
    { type: 'shipping', text: '2 pedidos pagados sin envío', severity: 'high' },
    { type: 'assets', text: 'Producto sin imagen para redes', severity: 'medium' }
  ];

  readonly assetSlots: AssetSlot[] = [
    { label: 'Miniatura (carrito)', hint: 'square 1:1' },
    { label: 'CTA / Banner', hint: 'landscape 16:9' },
    { label: 'Redes · Story', hint: '9:16' },
    { label: 'Redes · Feed', hint: '1:1' },
    { label: 'Producto del Mes', hint: 'landscape 16:9' },
    { label: 'Imagen extra', hint: 'opcional' }
  ];

  selectedCustomer = this.customers[0];
  assetPreviews = new Map<number, string>();

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

  get filteredOrders(): Order[] {
    return this.orders.filter((order) => order.status === this.currentOrderStatus);
  }

  get pendingCount(): number {
    return this.orders.filter((order) => order.status === 'pending').length;
  }

  get paidCount(): number {
    return this.orders.filter((order) => order.status === 'paid').length;
  }

  get shipCount(): number {
    return this.orders.filter((order) => order.status === 'paid').length;
  }

  get commissionsTotal(): number {
    return this.customers.reduce((acc, customer) => acc + customer.commissions, 0);
  }

  get customersCount(): number {
    return this.customers.length;
  }

  get productsCount(): number {
    return this.products.length;
  }

  formatMoney(value: number): string {
    return `$${value.toFixed(0)}`;
  }

  setView(view: 'orders' | 'customers' | 'products' | 'stats'): void {
    this.currentView = view;
  }

  setOrderStatus(status: Order['status']): void {
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

  advanceOrder(orderId: string): void {
    const order = this.orders.find((item) => item.id === orderId);
    if (!order) {
      return;
    }
    if (order.status === 'pending') {
      order.status = 'paid';
    } else if (order.status === 'paid') {
      order.status = 'delivered';
    }
  }

  selectCustomer(customerId: number): void {
    const found = this.customers.find((customer) => customer.id === customerId);
    if (found) {
      this.selectedCustomer = found;
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
