import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, map, Observable, of, tap } from 'rxjs';

import {
  AdminCustomer,
  AdminData,
  AdminCampaign,
  AppBusinessConfig,
  AdminOrder,
  ProductCategory,
  AdminOrderItem,
  AssociateMonth,
  AdminProduct,
  AdminStock,
  AssetResponse,
  CreateAssetPayload,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  CustomerProfile,
  LinkCustomerDocumentPayload,
  InventoryMovement,
  PosCashControl,
  PosCashCut,
  PosSale,
  StockTransfer,
  UpdateOrderStatusPayload,
  ProductAssetUpload,
  ProductOfMonthResponse,
  SaveAdminProductPayload,
  SaveAdminCampaignPayload,
  SaveAdminNotificationPayload,
  UpdateBusinessConfigPayload,
  UpdateCustomerPayload,
  UpdateCustomerPrivilegesPayload
} from '../models/admin.model';
import { AdminEmployee, CreateEmployeePayload, UpdateEmployeePrivilegesPayload } from '../models/employee.model';
import { PortalNotification } from '../models/portal-notification.model';
import { CommissionReceiptPayload } from '../models/user-dashboard.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class AdminControlService {
  private readonly dataSubject = new BehaviorSubject<AdminData | null>(null);
  readonly data$ = this.dataSubject.asObservable();

  // Rastrear qué secciones ya fueron cargadas en esta sesión
  private readonly loadedSections = new Set<string>();

  // Estado de carga por sección
  readonly loadingState = new BehaviorSubject<Record<string, boolean>>({});

  constructor(private readonly api: ApiService) {}

  private setLoading(section: string, value: boolean): void {
    this.loadingState.next({ ...this.loadingState.value, [section]: value });
  }

  private patchData(patch: Partial<AdminData>): void {
    const current = this.dataSubject.value ?? ({} as AdminData);
    this.dataSubject.next({ ...current, ...patch });
  }

  /** Carga inicial mínima: solo warnings */
  load(): Observable<AdminData> {
    return this.api.getAdminWarnings().pipe(
      tap((warnings) => {
        this.patchData({ warnings: warnings as AdminData['warnings'] });
        this.loadedSections.add('warnings');
      }),
      map(() => this.dataSubject.value as AdminData)
    );
  }

  /** Órdenes filtradas por status desde el backend */
  loadOrders(status: AdminOrder['status'], limit = 100): Observable<AdminOrder[]> {
    this.setLoading('orders', true);
    return this.api.getAdminOrders({ status, limit }).pipe(
      tap(({ orders }) => {
        const current = this.dataSubject.value;
        // Fusionar: reemplazar las del status dado, conservar el resto
        const existing = (current?.orders ?? []).filter((o) => o.status !== status);
        this.patchData({ orders: [...orders, ...existing] });
        this.loadedSections.add(`orders:${status}`);
        this.setLoading('orders', false);
      }),
      map(({ orders }) => orders)
    );
  }

  hasLoadedOrders(status: AdminOrder['status']): boolean {
    return this.loadedSections.has(`orders:${status}`);
  }

  /** Clientes — carga única */
  loadCustomers(): Observable<AdminCustomer[]> {
    if (this.loadedSections.has('customers')) return of(this.customers);
    this.setLoading('customers', true);
    return this.api.listCustomers().pipe(
      tap((customers) => {
        this.patchData({ customers });
        this.loadedSections.add('customers');
        this.setLoading('customers', false);
      })
    );
  }

  /** Productos — carga única */
  loadProducts(): Observable<AdminProduct[]> {
    if (this.loadedSections.has('products')) return of(this.products);
    this.setLoading('products', true);
    return this.api.listProducts().pipe(
      tap((products) => {
        this.patchData({ products });
        this.loadedSections.add('products');
        this.setLoading('products', false);
      })
    );
  }

  /** Empleados — carga única */
  loadEmployees(): Observable<AdminEmployee[]> {
    if (this.loadedSections.has('employees')) return of(this.employees);
    this.setLoading('employees', true);
    return this.api.listEmployees().pipe(
      tap((employees) => {
        this.patchData({ employees });
        this.loadedSections.add('employees');
        this.setLoading('employees', false);
      })
    );
  }

  /** Campañas — carga única */
  loadCampaigns(): Observable<AdminCampaign[]> {
    if (this.loadedSections.has('campaigns')) return of(this.campaigns);
    this.setLoading('campaigns', true);
    return this.api.listCampaigns().pipe(
      tap((campaigns) => {
        this.patchData({ campaigns });
        this.loadedSections.add('campaigns');
        this.setLoading('campaigns', false);
      })
    );
  }

  /** Notificaciones — carga única */
  loadNotifications(): Observable<PortalNotification[]> {
    if (this.loadedSections.has('notifications')) return of(this.notifications);
    this.setLoading('notifications', true);
    return this.api.listAdminNotifications().pipe(
      tap((notifications) => {
        this.patchData({ notifications });
        this.loadedSections.add('notifications');
        this.setLoading('notifications', false);
      })
    );
  }

  get employees(): AdminEmployee[] {
    return (this.data as (AdminData & { employees?: AdminEmployee[] }) | null)?.employees ?? [];
  }

  get campaigns(): AdminCampaign[] {
    return this.data?.campaigns ?? [];
  }

  get notifications(): PortalNotification[] {
    return this.data?.notifications ?? [];
  }

  get products(): AdminProduct[] {
    return this.data?.products ?? [];
  }

  isLoading(section: string): boolean {
    return this.loadingState.value[section] ?? false;
  }

  get data(): AdminData | null {
    return this.dataSubject.value;
  }

  updateCategories(categories: ProductCategory[]): void {
    const current = this.dataSubject.value;
    if (!current) return;
    this.dataSubject.next({ ...current, categories });
  }

  get orders(): AdminOrder[] {
    return this.data?.orders ?? [];
  }

  get customers(): AdminCustomer[] {
    return this.data?.customers ?? [];
  }

  get productsCount(): number {
    return this.data?.products?.length ?? 0;
  }

  get customersCount(): number {
    return this.customers.length;
  }

  get pendingCount(): number {
    return this.orders.filter((order) => order.status === 'pending').length;
  }

  get paidCount(): number {
    return this.orders.filter((order) => order.status === 'paid').length;
  }

  get shipCount(): number {
    return this.orders.filter((order) => order.status === 'shipped').length;
  }

  get commissionsTotal(): number {
    return this.customers.reduce((acc, customer) => acc + customer.commissions, 0);
  }

  formatMoney(value: number): string {
    const amount = Number.isFinite(value) ? value : 0;
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      maximumFractionDigits: 0
    }).format(amount);
  }

  getFilteredOrders(status: AdminOrder['status']): AdminOrder[] {
    return this.orders.filter((order) => order.status === status);
  }

  updateOrderStatus(orderId: string, payload: UpdateOrderStatusPayload): Observable<AdminOrder> {
    return this.api.updateOrderStatus(orderId, payload).pipe(
      tap((order) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const nextStatus = order.status ?? payload.status;
        const updatedOrders = current.orders.map((entry) =>
          entry.id === orderId
            ? {
                ...entry,
                status: nextStatus,
                shippingType: order.shippingType ?? payload.shippingType ?? entry.shippingType,
                trackingNumber: order.trackingNumber ?? payload.trackingNumber ?? entry.trackingNumber,
                deliveryPlace: order.deliveryPlace ?? payload.deliveryPlace ?? entry.deliveryPlace,
                deliveryDate: order.deliveryDate ?? payload.deliveryDate ?? entry.deliveryDate,
                stockId: order.stockId ?? payload.stockId ?? entry.stockId,
                paymentStatus: order.paymentStatus ?? entry.paymentStatus,
                deliveryStatus: order.deliveryStatus ?? entry.deliveryStatus,
                attendantUserId: order.attendantUserId ?? entry.attendantUserId,
                items: order.items ?? entry.items
              }
            : entry
        );
        this.dataSubject.next({ ...current, orders: updatedOrders });
      })
    );
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    return this.api.createOrder(payload).pipe(
      tap((order) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        this.dataSubject.next({ ...current, orders: [order, ...current.orders] });
      })
    );
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.api.createStructureCustomer(payload).pipe(
      tap((customer) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        this.dataSubject.next({ ...current, customers: [customer, ...current.customers] });
      })
    );
  }

  createAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    return this.api.createAsset(payload);
  }

  getCustomer(customerId: string): Observable<CustomerProfile> {
    return this.api.getCustomer(customerId);
  }

  addCustomerDocument(customerId: string, payload: LinkCustomerDocumentPayload): Observable<CustomerProfile> {
    return this.api.addCustomerDocument(customerId, payload);
  }

  uploadAdminCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.api.uploadAdminCommissionReceipt(payload);
  }

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    return this.api.createProductAsset(payload);
  }

  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse> {
    return this.api.setProductOfMonth(productId);
  }

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    return this.api.saveProduct(payload).pipe(
      tap((product) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const existingIndex = current.products.findIndex((entry) => entry.id === payload.id);
        const updatedProducts =
          existingIndex >= 0
            ? current.products.map((entry, index) => (index === existingIndex ? product : entry))
            : [product, ...current.products];
        this.dataSubject.next({ ...current, products: updatedProducts });
      })
    );
  }

  selectCustomer(customerId: number): AdminCustomer | null {
    return this.customers.find((customer) => customer.id === customerId) ?? null;
  }

  saveCampaign(payload: SaveAdminCampaignPayload): Observable<AdminCampaign> {
    return this.api.saveCampaign(payload).pipe(
      tap((campaign) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const existingIndex = (current.campaigns ?? []).findIndex((entry) => entry.id === campaign.id);
        const nextCampaigns =
          existingIndex >= 0
            ? (current.campaigns ?? []).map((entry, index) => (index === existingIndex ? campaign : entry))
            : [campaign, ...(current.campaigns ?? [])];
        this.dataSubject.next({ ...current, campaigns: nextCampaigns });
      })
    );
  }

  saveNotification(payload: SaveAdminNotificationPayload): Observable<PortalNotification> {
    return this.api.saveNotification(payload).pipe(
      tap((notification) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const nextNotifications = [...(current.notifications ?? [])];
        const existingIndex = nextNotifications.findIndex((entry) => entry.id === notification.id);
        if (existingIndex >= 0) {
          nextNotifications[existingIndex] = notification;
        } else {
          nextNotifications.unshift(notification);
        }
        nextNotifications.sort((a, b) => String(b.startAt ?? '').localeCompare(String(a.startAt ?? '')));
        this.dataSubject.next({ ...current, notifications: nextNotifications });
      })
    );
  }

  getBusinessConfig(): Observable<AppBusinessConfig> {
    return this.api.getBusinessConfig();
  }

  saveBusinessConfig(payload: UpdateBusinessConfigPayload): Observable<AppBusinessConfig> {
    return this.api.saveBusinessConfig(payload).pipe(
      tap((config) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        this.dataSubject.next({ ...current, businessConfig: config });
      })
    );
  }

  listStocks(): Observable<AdminStock[]> {
    return this.api.listStocks();
  }

  createStock(payload: { name: string; location: string; postalCode?: string; isMainWarehouse?: boolean; allowPickup?: boolean; linkedUserIds?: number[]; inventory?: Record<number, number> }): Observable<AdminStock> {
    return this.api.createStock(payload);
  }

  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory' | 'allowPickup'>>): Observable<AdminStock> {
    return this.api.updateStock(stockId, payload);
  }

  registerStockEntry(stockId: string, payload: { productId: number; qty: number; userId?: number | null; note?: string }): Observable<{ stock: AdminStock }> {
    return this.api.registerStockEntry(stockId, payload);
  }

  registerStockDamage(stockId: string, payload: { productId: number; qty: number; reason: string; userId?: number | null }): Observable<{ stock: AdminStock }> {
    return this.api.registerStockDamage(stockId, payload);
  }

  listStockTransfers(stockId?: string): Observable<StockTransfer[]> {
    return this.api.listStockTransfers(stockId);
  }

  createStockTransfer(payload: {
    sourceStockId: string;
    destinationStockId: string;
    lines: Array<{ productId: number; qty: number }>;
    createdByUserId?: number | null;
  }): Observable<{ transfer: StockTransfer }> {
    return this.api.createStockTransfer(payload);
  }

  receiveStockTransfer(transferId: string, payload: { receivedByUserId?: number | null }): Observable<{ transfer: StockTransfer }> {
    return this.api.receiveStockTransfer(transferId, payload);
  }

  listInventoryMovements(stockId?: string): Observable<InventoryMovement[]> {
    return this.api.listInventoryMovements(stockId);
  }

  listPosSales(stockId?: string): Observable<PosSale[]> {
    return this.api.listPosSales(stockId);
  }

  registerPosSale(payload: {
    stockId: string;
    customerId?: number | null;
    customerName?: string;
    paymentStatus?: 'paid_branch';
    deliveryStatus?: 'delivered_branch';
    items: Array<Pick<AdminOrderItem, 'productId' | 'name' | 'price' | 'quantity'>>;
  }): Observable<{ sale: PosSale }> {
    return this.api.registerPosSale(payload);
  }

  getAssociateMonth(associateId: string, monthKey: string): Observable<AssociateMonth> {
    return this.api.getAssociateMonth(associateId, monthKey);
  }

  getPosCashControl(stockId?: string): Observable<PosCashControl> {
    return this.api.getPosCashControl(stockId);
  }

  createPosCashCut(payload: { stockId: string }): Observable<{ cut: PosCashCut; control: PosCashControl }> {
    return this.api.createPosCashCut(payload);
  }

  updateCustomerPrivileges(customerId: number, payload: UpdateCustomerPrivilegesPayload): Observable<AdminCustomer> {
    return this.api.updateCustomerPrivileges(customerId, payload).pipe(
      tap((customer) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const customers = current.customers.map((entry) => (entry.id === customerId ? { ...entry, ...customer } : entry));
        this.dataSubject.next({ ...current, customers });
      })
    );
  }

  updateCustomer(customerId: number, payload: UpdateCustomerPayload): Observable<AdminCustomer> {
    return this.api.updateCustomer(customerId, payload).pipe(
      tap((customer) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const customers = current.customers.map((entry) => (entry.id === customerId ? { ...entry, ...customer } : entry));
        this.dataSubject.next({ ...current, customers });
      })
    );
  }

  createEmployee(payload: CreateEmployeePayload): Observable<AdminEmployee> {
    return this.api.createEmployee(payload).pipe(
      tap((emp) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        this.dataSubject.next({ ...current, employees: [emp, ...(current.employees ?? [])] });
      })
    );
  }

  updateEmployee(employeeId: number, payload: Partial<Pick<AdminEmployee, 'name' | 'phone' | 'active'>>): Observable<AdminEmployee> {
    return this.api.updateEmployee(employeeId, payload).pipe(
      tap((emp) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const employees = (current.employees ?? []).map((e) => (e.id === employeeId ? { ...e, ...emp } : e));
        this.dataSubject.next({ ...current, employees });
      })
    );
  }

  updateEmployeePrivileges(employeeId: number, payload: UpdateEmployeePrivilegesPayload): Observable<AdminEmployee> {
    return this.api.updateEmployeePrivileges(employeeId, payload).pipe(
      tap((emp) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const employees = (current.employees ?? []).map((e) => (e.id === employeeId ? { ...e, ...emp } : e));
        this.dataSubject.next({ ...current, employees });
      })
    );
  }

  loadStocksAndPosState(): Observable<{
    stocks: AdminStock[];
    transfers: StockTransfer[];
    movements: InventoryMovement[];
    posSales: PosSale[];
  }> {
    return forkJoin({
      stocks: this.api.listStocks(),
      transfers: this.api.listStockTransfers(),
      movements: this.api.listInventoryMovements(),
      posSales: this.api.listPosSales()
    }).pipe(
      map((response) => ({
        stocks: response.stocks ?? [],
        transfers: response.transfers ?? [],
        movements: response.movements ?? [],
        posSales: response.posSales ?? []
      }))
    );
  }
}
