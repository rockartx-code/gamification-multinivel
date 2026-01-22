import { CommonModule } from '@angular/common';
import { Component, OnInit, type Signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, forkJoin, from, map, of, switchMap } from 'rxjs';

import { AuthService, AuthUser } from '../../services/auth.service';
import {
  AdminAssetSlot,
  AdminCustomer,
  AdminData,
  AdminOrder,
  AdminOrderItem,
  AdminProduct,
  AdminWarning,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload
} from '../../models/admin.model';
import { AdminControlService } from '../../services/admin-control.service';

type StructureNode = {
  id: string;
  role: 'root' | 'L1' | 'L2';
  level: string;
  label: string;
  x: number;
  y: number;
};

type StructureLink = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {
  private readonly adminData: Signal<AdminData | null>;

  constructor(
    private readonly adminControl: AdminControlService,
    private readonly authService: AuthService,
    private readonly router: Router
  ) {
    this.adminData = toSignal(this.adminControl.data$, { initialValue: null });
  }

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
  productImagePreviews = new Map<CreateProductAssetPayload['section'], string>();
  productImageUploads = new Map<CreateProductAssetPayload['section'], boolean>();
  productImageFiles = new Map<CreateProductAssetPayload['section'], File>();
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
  newOrderCustomerId: number | null = null;
  newOrderStatus: AdminOrder['status'] = 'pending';
  newOrderItems = new Map<number, number>();
  isSavingOrder = false;
  isSavingStructure = false;
  isSavingProduct = false;
  private readonly updatingOrderIds = new Set<string>();

  ngOnInit(): void {
    this.adminControl.load().subscribe(() => {
      if (!this.selectedCustomer) {
        this.selectedCustomer = this.customers[0] ?? null;
      }
      if (!this.newOrderCustomerId) {
        this.newOrderCustomerId = this.customers[0]?.id ?? null;
      }
    });
  }

  get orders(): AdminOrder[] {
    return this.adminData()?.orders ?? [];
  }

  get customers(): AdminCustomer[] {
    return this.adminData()?.customers ?? [];
  }

  get products(): AdminProduct[] {
    return this.adminData()?.products ?? [];
  }

  get warnings(): AdminWarning[] {
    return this.adminData()?.warnings ?? [];
  }

  get assetSlots(): AdminAssetSlot[] {
    const slots = this.adminData()?.assetSlots ?? [];
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

  get structureRootLabel(): string {
    return this.structureNodeLabel(this.selectedCustomer?.name);
  }

  get structureGraph(): { nodes: StructureNode[]; links: StructureLink[] } {
    if (!this.selectedCustomer) {
      return { nodes: [], links: [] };
    }

    const referrals = this.buildReferralMap(this.customers);
    const directReferrals = referrals.get(this.selectedCustomer.id) ?? [];
    const indirectReferrals: Array<{ customer: AdminCustomer; parentId: number }> = [];

    directReferrals.forEach((member) => {
      const children = referrals.get(member.id) ?? [];
      children.forEach((child) => {
        indirectReferrals.push({ customer: child, parentId: member.id });
      });
    });

    const l1Positions = this.buildColumnPositions(directReferrals.length, 260);
    const l2Positions = this.buildColumnPositions(indirectReferrals.length, 420, 40, 180);
    const rootY =
      l1Positions.length > 0
        ? (l1Positions[0].y + l1Positions[l1Positions.length - 1].y) / 2
        : 110;

    const root: StructureNode = {
      id: `customer-${this.selectedCustomer.id}`,
      role: 'root',
      level: this.selectedCustomer.level,
      label: this.structureRootLabel,
      x: 120,
      y: rootY
    };

    const l1Customers = directReferrals.slice(0, l1Positions.length);
    const l1Nodes: StructureNode[] = l1Customers.map((customer, index) => ({
      id: `customer-${customer.id}`,
      role: 'L1',
      level: customer.level,
      label: this.structureNodeLabel(customer.name),
      x: l1Positions[index].x,
      y: l1Positions[index].y
    }));

    const l1NodeById = new Map(l1Customers.map((customer, index) => [customer.id, l1Nodes[index]]));
    const l2Entries = indirectReferrals
      .filter((entry) => l1NodeById.has(entry.parentId))
      .slice(0, l2Positions.length);
    const l2Nodes: StructureNode[] = l2Entries.map((entry, index) => ({
      id: `customer-${entry.customer.id}`,
      role: 'L2',
      level: entry.customer.level,
      label: this.structureNodeLabel(entry.customer.name),
      x: l2Positions[index].x,
      y: l2Positions[index].y
    }));

    const links: StructureLink[] = l1Nodes.map((node) => ({
      x1: root.x,
      y1: root.y,
      x2: node.x,
      y2: node.y
    }));

    l2Nodes.forEach((node, index) => {
      const entry = l2Entries[index];
      const parent = entry ? l1NodeById.get(entry.parentId) : undefined;
      if (!parent) {
        return;
      }
      links.push({
        x1: parent.x,
        y1: parent.y,
        x2: node.x,
        y2: node.y
      });
    });

    return { nodes: [root, ...l1Nodes, ...l2Nodes], links };
  }

  get isStructureFormValid(): boolean {
    return Boolean(this.structureForm.name.trim() && this.structureForm.email.trim());
  }

  get isProductFormValid(): boolean {
    return Boolean(this.productForm.name.trim() && Number(this.productForm.price));
  }

  structureNodeFill(level: string): string {
    const normalized = this.normalizeLevel(level);
    if (normalized === 'oro') {
      return 'rgba(245,185,66,.92)';
    }
    if (normalized === 'plata') {
      return 'rgba(59,130,246,.92)';
    }
    if (normalized === 'bronce') {
      return 'rgba(139,92,246,.92)';
    }
    return 'rgba(148,163,184,.85)';
  }

  structureNodeRadius(role: StructureNode['role']): number {
    if (role === 'root') {
      return 26;
    }
    if (role === 'L1') {
      return 16;
    }
    return 12;
  }

  structureNodeFont(role: StructureNode['role']): number {
    if (role === 'root') {
      return 12;
    }
    if (role === 'L1') {
      return 10;
    }
    return 9;
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
    console.log('[Admin] closeModals()', {
      isActionsModalOpen: this.isActionsModalOpen,
      isNewOrderModalOpen: this.isNewOrderModalOpen,
      isAddStructureModalOpen: this.isAddStructureModalOpen
    });
    this.isActionsModalOpen = false;
    this.isNewOrderModalOpen = false;
    this.isAddStructureModalOpen = false;
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  advanceOrder(order: AdminOrder): void {
    if (this.updatingOrderIds.has(order.id)) {
      return;
    }
    const nextStatus =
      order.status === 'pending' ? 'paid' : order.status === 'paid' ? 'delivered' : order.status;
    if (nextStatus === order.status) {
      return;
    }
    this.updatingOrderIds.add(order.id);
    this.adminControl
      .updateOrderStatus(order.id, nextStatus)
      .pipe(
        finalize(() => {
          this.updatingOrderIds.delete(order.id);
        })
      )
      .subscribe();
  }

  isUpdatingOrder(orderId: string): boolean {
    return this.updatingOrderIds.has(orderId);
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
    console.log('[Admin] saveNewOrder() start', {
      newOrderCustomerId: this.newOrderCustomerId,
      items: this.newOrderItems.size,
      isSavingOrder: this.isSavingOrder
    });
    if (!this.newOrderCustomerId || this.newOrderItems.size === 0 || this.isSavingOrder) {
      console.log('[Admin] saveNewOrder() aborted');
      return;
    }
    const customer = this.customers.find((entry) => entry.id === this.newOrderCustomerId);
    if (!customer) {
      console.log('[Admin] saveNewOrder() aborted: customer not found');
      return;
    }
    const payload: CreateAdminOrderPayload = {
      customerId: customer.id,
      customerName: customer.name,
      status: this.newOrderStatus,
      items: this.getNewOrderItems()
    };
    this.isSavingOrder = true;
    console.log('[Admin] saveNewOrder() call createOrder', payload);
    this.adminControl
      .createOrder(payload)
      .pipe(
        switchMap(() => {
          console.log('[Admin] saveNewOrder() createOrder next -> load()');
          return this.adminControl.load();
        }),
        finalize(() => {
          console.log('[Admin] saveNewOrder() finalize');
          this.isSavingOrder = false;
        })
      )
      .subscribe({
        next: () => {
          console.log('[Admin] saveNewOrder() load next -> closeModals()');
          this.closeModals();
        },
        error: () => {
          console.log('[Admin] saveNewOrder() error -> closeModals()');
          this.closeModals();
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
    //if (this.isStructureLevelBronze || this.isSavingStructure || !this.isStructureFormValid) {
    //  return;
    //}
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
        this.adminControl.load().subscribe();
        this.closeModals();
      },
      error: () => {
        this.isSavingStructure = false;
      }
    });
  }

  selectCustomer(customerId: number): void {
    const selected = this.customers.find((customer) => customer.id === customerId) ?? null;
    this.selectedCustomer = selected;
  }

  editProduct(product: AdminProduct): void {
    this.productForm = {
      id: product.id,
      name: product.name,
      price: String(product.price),
      sku: '',
      hook: ''
    };
    this.resetProductAssets();
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
      active: true,
      sku: this.productForm.sku.trim() || undefined,
      hook: this.productForm.hook.trim() || undefined
    };
    this.adminControl
      .saveProduct(payload)
      .pipe(
        switchMap((product) =>
          this.uploadProductImages(product.id).pipe(
            map((uploads) => ({
              product,
              uploads
            }))
          )
        ),
        finalize(() => {
          this.isSavingProduct = false;
        })
      )
      .subscribe({
        next: ({ product, uploads }) => {
          const hasFailures = uploads.some((upload) => !upload.success);
          if (hasFailures) {
            this.announceProductMessage(
              `Producto guardado: ${product.name}. Algunas imágenes no se pudieron subir.`
            );
          } else {
            this.announceProductMessage(
              this.productForm.id ? `Producto actualizado: ${product.name}.` : `Producto creado: ${product.name}.`
            );
          }
          this.adminControl.load().subscribe();
          this.resetProductForm();
        },
        error: () => {
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
    this.resetProductAssets();
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
    this.productImageFiles.set(section, file);
    this.productImageUploads.set(section, false);
  }

  private setProductImagePreview(section: CreateProductAssetPayload['section'], file: File): void {
    const previewUrl = URL.createObjectURL(file);
    const currentUrl = this.productImagePreviews.get(section);
    if (currentUrl) {
      URL.revokeObjectURL(currentUrl);
    }
    this.productImagePreviews.set(section, previewUrl);
  }

  private resetProductAssets(): void {
    this.productImageFiles.clear();
    this.productImageUploads.clear();
    this.productImagePreviews.forEach((value) => {
      URL.revokeObjectURL(value);
    });
    this.productImagePreviews.clear();
  }

  private uploadProductImages(
    productId: number
  ): Observable<Array<{ section: CreateProductAssetPayload['section']; success: boolean }>> {
    const entries = Array.from(this.productImageFiles.entries());
    if (entries.length === 0) {
      return of([]);
    }
    entries.forEach(([section]) => {
      this.productImageUploads.set(section, true);
    });
    const uploads = entries.map(([section, file]) => {
      const payload: CreateProductAssetPayload = {
        productId: String(productId),
        section,
        filename: file.name,
        contentType: file.type || 'application/octet-stream'
      };
      return this.adminControl.createProductAsset(payload).pipe(
        switchMap((response) => {
          if (!response.uploadUrl) {
            return of({ section, success: true });
          }
          return from(
            fetch(response.uploadUrl, {
              method: 'PUT',
              headers: {
                'Content-Type': payload.contentType ?? 'application/octet-stream'
              },
              body: file
            })
          ).pipe(
            map((uploadResponse) => ({
              section,
              success: uploadResponse.ok
            }))
          );
        }),
        catchError(() => of({ section, success: false })),
        finalize(() => {
          this.productImageUploads.set(section, false);
        })
      );
    });
    return forkJoin(uploads);
  }

  private normalizeLevel(level?: string): string {
    return (level ?? '').trim().toLowerCase();
  }

  private structureNodeLabel(name?: string): string {
    const value = (name ?? '').trim();
    if (!value) {
      return 'Cliente';
    }
    const first = value.split(' ')[0] ?? value;
    return first.slice(0, 6);
  }

  private buildReferralMap(customers: AdminCustomer[]): Map<number, AdminCustomer[]> {
    const map = new Map<number, AdminCustomer[]>();
    customers.forEach((customer) => {
      if (customer.leaderId == null) {
        return;
      }
      const entries = map.get(customer.leaderId) ?? [];
      entries.push(customer);
      map.set(customer.leaderId, entries);
    });
    return map;
  }

  private buildColumnPositions(count: number, x: number, top = 50, bottom = 170): { x: number; y: number }[] {
    if (count <= 0) {
      return [];
    }
    if (count === 1) {
      return [{ x, y: (top + bottom) / 2 }];
    }
    const spacing = (bottom - top) / (count - 1);
    return Array.from({ length: count }, (_, index) => ({
      x,
      y: top + spacing * index
    }));
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
