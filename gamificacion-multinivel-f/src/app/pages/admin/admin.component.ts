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
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload
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
  structureForm = {
    name: '',
    phone: '',
    email: '',
    address: '',
    city: ''
  };
  structureLeader: AdminCustomer | null = null;
  structureLevel: 'Oro' | 'Plata' | 'Bronce' = 'Oro';
  assetPreviews = new Map<number, string>();
  productImagePreviews = new Map<string, string>();
  productImageUploads = new Map<string, boolean>();
  productMessage = '';
  private productMessageTimeout?: number;
  productForm = {
    id: null as number | null,
    name: '',
    price: '',
    sku: '',
    hook: ''
  };
  productImageSlots = [
    { key: 'redes', label: 'Redes', hint: 'Story / Feed' },
    { key: 'landing', label: 'Landing', hint: 'Hero 16:9' },
    { key: 'miniatura', label: 'Miniatura', hint: '1:1' }
  ] as const;
  defaultAssetSlots: AdminAssetSlot[] = [
    { label: 'Miniatura (carrito)', hint: 'square 1:1' },
    { label: 'CTA / Banner', hint: 'landscape 16:9' },
    { label: 'Redes · Story', hint: '9:16' },
    { label: 'Redes · Feed', hint: '1:1' },
    { label: 'Producto del Mes', hint: 'landscape 16:9' },
    { label: 'Imagen extra', hint: 'opcional' }
  ];
  draftProductId = this.createDraftProductId();
  newOrderCustomerId: number | null = null;
  newOrderStatus: AdminOrder['status'] = 'pending';
  newOrderItems = new Map<number, number>();
  isSavingOrder = false;
  isSavingStructure = false;
  isSavingProduct = false;

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
    const slots = this.adminControl.data?.assetSlots ?? [];
    return slots.length ? slots : this.defaultAssetSlots;
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

  get isSelectedCustomerBronze(): boolean {
    return this.normalizeLevel(this.selectedCustomer?.level) === 'bronce';
  }

  get isStructureLevelBronze(): boolean {
    return this.normalizeLevel(this.structureLevel) === 'bronce';
  }

  get structureLeaderLabel(): string {
    if (!this.structureLeader) {
      return 'Sin líder asignado';
    }
    return `${this.structureLeader.name} · ${this.structureLeader.level}`;
  }

  get isStructureFormValid(): boolean {
    return Boolean(this.structureForm.name.trim() && this.structureForm.email.trim());
  }

  get isProductFormValid(): boolean {
    return Boolean(this.productForm.name.trim() && Number(this.productForm.price));
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
    this.resetStructureForm();
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

  resetStructureForm(): void {
    this.structureForm = {
      name: '',
      phone: '',
      email: '',
      address: '',
      city: ''
    };
    this.isSavingStructure = false;
    if (this.selectedCustomer) {
      this.structureLeader = this.selectedCustomer;
      this.structureLevel = this.getLowerStructureLevel(this.selectedCustomer.level);
      return;
    }
    this.structureLeader = null;
    this.structureLevel = 'Oro';
  }

  updateStructureField(
    field: 'name' | 'phone' | 'email' | 'address' | 'city',
    value: string
  ): void {
    this.structureForm = {
      ...this.structureForm,
      [field]: value
    };
  }

  saveStructureCustomer(): void {
    if (this.isStructureLevelBronze || this.isSavingStructure || !this.isStructureFormValid) {
      return;
    }
    const payload: CreateStructureCustomerPayload = {
      name: this.structureForm.name.trim(),
      email: this.structureForm.email.trim(),
      phone: this.structureForm.phone?.trim() || undefined,
      address: this.structureForm.address?.trim() || undefined,
      city: this.structureForm.city?.trim() || undefined,
      leaderId: this.structureLeader?.id ?? null,
      level: this.structureLevel
    };
    this.isSavingStructure = true;
    this.adminControl.createStructureCustomer(payload).subscribe({
      next: () => {
        this.isSavingStructure = false;
        this.closeModals();
      },
      error: () => {
        this.isSavingStructure = false;
      }
    });
  }

  selectCustomer(customerId: number): void {
    const selected = this.adminControl.selectCustomer(customerId);
    if (selected) {
      this.selectedCustomer = selected;
    }
  }

  editProduct(product: AdminProduct): void {
    this.productForm = {
      id: product.id,
      name: product.name,
      price: String(product.price),
      sku: '',
      hook: ''
    };
    this.announceProductMessage(`Editando ${product.name}.`);
  }

  updateProductField(field: 'name' | 'price' | 'sku' | 'hook', value: string): void {
    this.productForm = {
      ...this.productForm,
      [field]: value
    };
  }

  saveProduct(): void {
    if (this.isSavingProduct || !this.isProductFormValid) {
      return;
    }
    this.isSavingProduct = true;
    const payload = {
      id: this.productForm.id,
      name: this.productForm.name.trim(),
      price: Number(this.productForm.price),
      active: true
    };
    this.adminControl.saveProduct(payload).subscribe({
      next: (product) => {
        this.isSavingProduct = false;
        this.announceProductMessage(
          this.productForm.id ? `Producto actualizado: ${product.name}.` : `Producto creado: ${product.name}.`
        );
        this.resetProductForm();
      },
      error: () => {
        this.isSavingProduct = false;
        this.announceProductMessage('No se pudo guardar el producto.');
      }
    });
  }

  private resetProductForm(): void {
    this.productForm = {
      id: null,
      name: '',
      price: '',
      sku: '',
      hook: ''
    };
  }

  private announceProductMessage(message: string): void {
    this.productMessage = message;
    if (this.productMessageTimeout) {
      window.clearTimeout(this.productMessageTimeout);
    }
    this.productMessageTimeout = window.setTimeout(() => {
      this.productMessage = '';
    }, 2800);
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

  uploadProductImage(event: Event, section: CreateProductAssetPayload['section']): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) {
      return;
    }
    this.setProductImagePreview(section, file);
    this.productImageUploads.set(section, true);
    const payload: CreateProductAssetPayload = {
      productId: this.draftProductId,
      section,
      filename: file.name,
      contentType: file.type || 'application/octet-stream'
    };
    this.adminControl.createProductAsset(payload).subscribe({
      next: (response) => {
        if (response.uploadUrl) {
          void fetch(response.uploadUrl, {
            method: 'PUT',
            headers: {
              'Content-Type': payload.contentType ?? 'application/octet-stream'
            },
            body: file
          })
            .then(() => {
              this.productImageUploads.set(section, false);
            })
            .catch(() => {
              this.productImageUploads.set(section, false);
            });
          return;
        }
        this.productImageUploads.set(section, false);
      },
      error: () => {
        this.productImageUploads.set(section, false);
      }
    });
  }

  private setProductImagePreview(section: string, file: File): void {
    const previewUrl = URL.createObjectURL(file);
    const currentUrl = this.productImagePreviews.get(section);
    if (currentUrl) {
      URL.revokeObjectURL(currentUrl);
    }
    this.productImagePreviews.set(section, previewUrl);
  }

  private createDraftProductId(): string {
    const cryptoObj = globalThis.crypto;
    if (cryptoObj?.randomUUID) {
      return cryptoObj.randomUUID();
    }
    return `draft-${Date.now()}`;
  }

  private normalizeLevel(level?: string): string {
    return (level ?? '').trim().toLowerCase();
  }

  private getLowerStructureLevel(level: string): 'Oro' | 'Plata' | 'Bronce' {
    const normalized = this.normalizeLevel(level);
    if (normalized === 'oro') {
      return 'Plata';
    }
    if (normalized === 'plata') {
      return 'Bronce';
    }
    return 'Bronce';
  }
}
