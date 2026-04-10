import { Injectable } from '@angular/core';
import { finalize, map, Observable, of, shareReplay, tap } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AdminCustomer,
  AdminData,
  AdminCampaign,
  AppBusinessConfig,
  AdminOrder,
  CustomerOrdersPage,
  AdminOrderItem,
  AdminProduct,
  AdminStock,
  AssetResponse,
  CreateAssetPayload,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  CustomerOwnDocumentPayload,
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
  OrderStatusLookup,
  AssociateMonth,
  UpdateBusinessConfigPayload,
  UpdateCustomerPayload,
  UpdateCustomerPrivilegesPayload,
  UpdateProfilePayload,
  ProductCategory,
  SaveProductCategoryPayload,
  ShippingRate,
  ShippingQuoteRequest,
  AdminRefundPayload,
  AdminRefundResponse,
  AdminReturnInspectPayload,
  AdminReturnInspectResponse,
  OrderCancelResponse,
  OrderReturnRequestPayload,
  OrderReturnRequestResponse
} from '../models/admin.model';
import { AdminEmployee, CreateEmployeePayload, UpdateEmployeePrivilegesPayload } from '../models/employee.model';
import { NotificationReadResponse, PortalNotification } from '../models/portal-notification.model';
import {
  CreateAccountPayload,
  CreateAccountResponse,
  PasswordRecoveryRequestPayload,
  PasswordRecoveryRequestResponse,
  ResendEmailConfirmationPayload,
  ResendEmailConfirmationResponse,
  ResetPasswordPayload,
  ResetPasswordResponse,
  VerifyEmailResponse
} from '../models/auth.model';
import { CartData } from '../models/cart.model';
import {
  CatalogData,
  CommissionReceiptPayload,
  CommissionRequestPayload,
  CustomerClabePayload,
  DashboardData,
  SponsorContact,
  UserDashboardData
} from '../models/user-dashboard.model';
import type { AuthUser } from './auth.service';
import { MockApiService } from './mock-api.service';
import { RealApiService } from './real-api.service';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly pickupStocksCacheKey = 'pickup-stocks-cache-v1';
  private readonly pickupStocksTtlMs = 24 * 60 * 60 * 1000;
  private pickupStocksRequest?: Observable<Array<{ id: string; name: string; location: string }>>;

  constructor(
    private readonly mockApi: MockApiService,
    private readonly realApi: RealApiService
  ) {}

  login(username: string, password: string): Observable<AuthUser> {
    return this.resolveApi().login(username, password);
  }

  createAccount(payload: CreateAccountPayload): Observable<CreateAccountResponse> {
    return this.resolveApi().createAccount(payload);
  }

  verifyEmail(token: string): Observable<VerifyEmailResponse> {
    return this.resolveApi().verifyEmail(token);
  }

  resendEmailConfirmation(payload: ResendEmailConfirmationPayload): Observable<ResendEmailConfirmationResponse> {
    return this.resolveApi().resendEmailConfirmation(payload);
  }

  requestPasswordRecovery(payload: PasswordRecoveryRequestPayload): Observable<PasswordRecoveryRequestResponse> {
    return this.resolveApi().requestPasswordRecovery(payload);
  }

  resetPassword(payload: ResetPasswordPayload): Observable<ResetPasswordResponse> {
    return this.resolveApi().resetPassword(payload);
  }

  getAdminData(): Observable<AdminData> {
    return this.resolveApi().getAdminData();
  }

  getAdminOrders(params: { status?: AdminOrder['status']; limit?: number } = {}): Observable<{ orders: AdminOrder[]; total: number }> {
    return this.resolveApi().getAdminOrders(params);
  }

  getAdminWarnings(): Observable<{ type: string; text: string; severity: string }[]> {
    return this.resolveApi().getAdminWarnings();
  }

  listCustomers(): Observable<AdminCustomer[]> {
    return this.resolveApi().listCustomers();
  }

  listCustomersPaged(params: { limit?: number; nextToken?: string; search?: string } = {}): Observable<{ customers: AdminCustomer[]; nextToken?: string; hasMore?: boolean; total?: number }> {
    return this.realApi.listCustomersPaged(params);
  }

  listProducts(): Observable<{ products: AdminProduct[]; productOfMonthId: number | null }> {
    return this.resolveApi().listProducts();
  }

  listCampaigns(): Observable<AdminCampaign[]> {
    return this.resolveApi().listCampaigns();
  }

  listAdminNotifications(): Observable<PortalNotification[]> {
    return this.resolveApi().listAdminNotifications();
  }

  getCartData(): Observable<CartData> {
    return this.resolveApi().getCartData();
  }

  getCatalogData(): Observable<CatalogData> {
    return this.resolveApi().getCatalogData();
  }

  getDashboardData(): Observable<DashboardData> {
    return this.resolveApi().getDashboardData();
  }

  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    return this.resolveApi().getUserDashboardData(userId);
  }

  getHonorBoard(): Observable<import('../models/user-dashboard.model').HonorBoard> {
    return this.resolveApi().getHonorBoard();
  }

  requestCommissionPayout(payload: CommissionRequestPayload): Observable<{ request: unknown; summary?: unknown }> {
    return this.resolveApi().requestCommissionPayout(payload);
  }

  uploadCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.resolveApi().uploadCommissionReceipt(payload);
  }

  uploadAdminCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.resolveApi().uploadAdminCommissionReceipt(payload);
  }

  saveCustomerClabe(payload: CustomerClabePayload): Observable<{ ok: boolean; clabeLast4?: string }> {
    return this.resolveApi().saveCustomerClabe(payload);
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    return this.resolveApi().createOrder(payload);
  }

  createOrderCheckout(
    orderId: string,
    payload: {
      successUrl?: string;
      failureUrl?: string;
      pendingUrl?: string;
      notificationUrl?: string;
      currencyId?: string;
    } = {}
  ): Observable<{
    orderId: string;
    checkout?: {
      provider?: string;
      preferenceId?: string;
      initPoint?: string;
      sandboxInitPoint?: string;
      externalReference?: string;
    };
  }> {
    return this.resolveApi().createOrderCheckout(orderId, payload);
  }

  getOrder(orderId: string): Observable<AdminOrder> {
    return this.resolveApi().getOrder(orderId);
  }

  getOrderStatus(orderOrPaymentId: string): Observable<OrderStatusLookup> {
    return this.resolveApi().getOrderStatus(orderOrPaymentId);
  }

  getAssociateMonth(associateId: string, monthKey: string): Observable<AssociateMonth> {
    return this.resolveApi().getAssociateMonth(associateId, monthKey);
  }

  getOrders(customerId: string, params: { limit?: number; nextToken?: string } = {}): Observable<CustomerOrdersPage> {
    return this.resolveApi().getOrders(customerId, params);
  }

  getCustomer(customerId: string): Observable<CustomerProfile> {
    return this.resolveApi().getCustomer(customerId);
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.resolveApi().createStructureCustomer(payload);
  }

  createAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    return this.resolveApi().createAsset(payload);
  }

  addCustomerDocument(customerId: string, payload: LinkCustomerDocumentPayload): Observable<CustomerProfile> {
    return this.resolveApi().addCustomerDocument(customerId, payload);
  }

  uploadCustomerOwnDocument(payload: CustomerOwnDocumentPayload): Observable<CustomerProfile> {
    return this.resolveApi().uploadCustomerOwnDocument(payload);
  }

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    return this.resolveApi().createProductAsset(payload);
  }

  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse> {
    return this.resolveApi().setProductOfMonth(productId);
  }

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    return this.resolveApi().saveProduct(payload);
  }

  deleteProduct(productId: number): Observable<{ ok: boolean; productId: number }> {
    return this.resolveApi().deleteProduct(productId);
  }

  listCategories(): Observable<ProductCategory[]> {
    return this.resolveApi().listCategories();
  }

  getSponsorContact(sponsorId: string): Observable<SponsorContact> {
    return this.resolveApi().getSponsorContact(sponsorId);
  }

  saveCategory(payload: SaveProductCategoryPayload): Observable<ProductCategory> {
    return this.resolveApi().saveCategory(payload);
  }

  deleteCategory(id: string): Observable<{ ok: boolean }> {
    return this.resolveApi().deleteCategory(id);
  }

  updateOrderStatus(orderId: string, payload: UpdateOrderStatusPayload): Observable<AdminOrder> {
    return this.resolveApi().updateOrderStatus(orderId, payload);
  }

  listStocks(): Observable<AdminStock[]> {
    return this.resolveApi().listStocks();
  }

  listPickupStocks(): Observable<Array<{ id: string; name: string; location: string }>> {
    const cached = this.readPickupStocksCache();
    if (cached) {
      return of(cached);
    }

    if (this.pickupStocksRequest) {
      return this.pickupStocksRequest;
    }

    const request = this.resolveApi()
      .listPickupStocks()
      .pipe(
        map((stocks) => this.normalizePickupStocks(stocks)),
        tap((stocks) => this.writePickupStocksCache(stocks)),
        finalize(() => {
          this.pickupStocksRequest = undefined;
        }),
        shareReplay(1)
      );

    this.pickupStocksRequest = request;
    return request;
  }

  createStock(payload: { name: string; location: string; postalCode?: string; isMainWarehouse?: boolean; allowPickup?: boolean; linkedUserIds?: number[]; inventory?: Record<number, number> }): Observable<AdminStock> {
    return this.resolveApi().createStock(payload);
  }

  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory' | 'allowPickup'>>): Observable<AdminStock> {
    return this.resolveApi().updateStock(stockId, payload);
  }

  registerStockEntry(stockId: string, payload: { productId: number; qty: number; userId?: number | null; note?: string }): Observable<{ ok: boolean; stock?: AdminStock }> {
    return this.resolveApi().registerStockEntry(stockId, payload);
  }

  registerStockDamage(stockId: string, payload: { productId: number; qty: number; reason: string; userId?: number | null }): Observable<{ ok: boolean; stock?: AdminStock }> {
    return this.resolveApi().registerStockDamage(stockId, payload);
  }

  listStockTransfers(stockId?: string): Observable<StockTransfer[]> {
    return this.resolveApi().listStockTransfers(stockId);
  }

  createStockTransfer(payload: {
    sourceStockId: string;
    destinationStockId: string;
    lines: Array<{ productId: number; qty: number }>;
    createdByUserId?: number | null;
  }): Observable<{ transfer: StockTransfer }> {
    return this.resolveApi().createStockTransfer(payload);
  }

  receiveStockTransfer(transferId: string, payload: { receivedByUserId?: number | null }): Observable<{ transfer: StockTransfer }> {
    return this.resolveApi().receiveStockTransfer(transferId, payload);
  }

  listInventoryMovements(stockId?: string): Observable<InventoryMovement[]> {
    return this.resolveApi().listInventoryMovements(stockId);
  }

  listPosSales(stockId?: string): Observable<PosSale[]> {
    return this.resolveApi().listPosSales(stockId);
  }

  registerPosSale(payload: {
    stockId: string;
    customerId?: number | null;
    customerName?: string;
    paymentMethod?: 'cash' | 'card' | 'transfer';
    paymentStatus?: 'paid_branch';
    deliveryStatus?: 'delivered_branch';
    items: Array<Pick<AdminOrderItem, 'productId' | 'name' | 'price' | 'quantity'>>;
  }): Observable<{ sale: PosSale }> {
    return this.resolveApi().registerPosSale(payload);
  }

  getPosCashControl(stockId?: string): Observable<PosCashControl> {
    return this.resolveApi().getPosCashControl(stockId);
  }

  createPosCashCut(payload: { stockId: string; cashToKeep?: number }): Observable<{ cut: PosCashCut; control: PosCashControl }> {
    return this.resolveApi().createPosCashCut(payload);
  }

  updateCustomerPrivileges(customerId: number, payload: UpdateCustomerPrivilegesPayload): Observable<AdminCustomer> {
    return this.resolveApi().updateCustomerPrivileges(customerId, payload);
  }

  updateCustomer(customerId: number, payload: UpdateCustomerPayload): Observable<AdminCustomer> {
    return this.resolveApi().updateCustomer(customerId, payload);
  }

  changePassword(userId: string, payload: { currentPassword: string; newPassword: string }): Observable<void> {
    return this.resolveApi().changePassword(userId, payload);
  }

  updateProfile(userId: string, payload: UpdateProfilePayload): Observable<CustomerProfile> {
    return this.resolveApi().updateProfile(userId, payload);
  }

  saveCampaign(payload: SaveAdminCampaignPayload): Observable<AdminCampaign> {
    return this.resolveApi().saveCampaign(payload);
  }

  saveNotification(payload: SaveAdminNotificationPayload): Observable<PortalNotification> {
    return this.resolveApi().saveNotification(payload);
  }

  markNotificationRead(notificationId: string, payload: { customerId?: number | string } = {}): Observable<NotificationReadResponse> {
    return this.resolveApi().markNotificationRead(notificationId, payload);
  }

  getBusinessConfig(): Observable<AppBusinessConfig> {
    return this.resolveApi().getBusinessConfig();
  }

  getPublicBusinessConfig(): Observable<AppBusinessConfig> {
    return this.resolveApi().getPublicBusinessConfig();
  }

  saveBusinessConfig(payload: UpdateBusinessConfigPayload): Observable<AppBusinessConfig> {
    return this.resolveApi().saveBusinessConfig(payload);
  }

  listEmployees(): Observable<AdminEmployee[]> {
    return this.resolveApi().listEmployees();
  }

  createEmployee(payload: CreateEmployeePayload): Observable<AdminEmployee> {
    return this.resolveApi().createEmployee(payload);
  }

  updateEmployee(employeeId: number, payload: Partial<Pick<AdminEmployee, 'name' | 'phone' | 'active'>>): Observable<AdminEmployee> {
    return this.resolveApi().updateEmployee(employeeId, payload);
  }

  updateEmployeePrivileges(employeeId: number, payload: UpdateEmployeePrivilegesPayload): Observable<AdminEmployee> {
    return this.resolveApi().updateEmployeePrivileges(employeeId, payload);
  }

  getShippingQuote(payload: ShippingQuoteRequest): Observable<ShippingRate[]> {
    return this.resolveApi().getShippingQuote(payload);
  }

  cancelOrder(orderId: string, reason: string): Observable<OrderCancelResponse> {
    return this.resolveApi().cancelOrder(orderId, reason);
  }

  requestReturn(orderId: string, payload: OrderReturnRequestPayload): Observable<OrderReturnRequestResponse> {
    return this.resolveApi().requestReturn(orderId, payload);
  }

  refundOrder(orderId: string, payload: AdminRefundPayload): Observable<AdminRefundResponse> {
    return this.resolveApi().refundOrder(orderId, payload);
  }

  inspectReturn(orderId: string, payload: AdminReturnInspectPayload): Observable<AdminReturnInspectResponse> {
    return this.resolveApi().inspectReturn(orderId, payload);
  }

  private resolveApi(): MockApiService | RealApiService {
    return environment.useMockApi ? this.mockApi : this.realApi;
  }

  private readPickupStocksCache(): Array<{ id: string; name: string; location: string }> | null {
    try {
      const raw = localStorage.getItem(this.pickupStocksCacheKey);
      if (!raw) {
        return null;
      }

      const parsed = JSON.parse(raw) as {
        expiresAt?: number;
        stocks?: Array<{ id: string; name: string; location: string }>;
      };

      if (!parsed.expiresAt || parsed.expiresAt <= Date.now() || !Array.isArray(parsed.stocks)) {
        localStorage.removeItem(this.pickupStocksCacheKey);
        return null;
      }

      const stocks = this.normalizePickupStocks(parsed.stocks);

      if (stocks.length === 0) {
        localStorage.removeItem(this.pickupStocksCacheKey);
        return null;
      }

      return stocks;
    } catch {
      return null;
    }
  }

  private writePickupStocksCache(stocks: Array<{ id: string; name: string; location: string }>): void {
    try {
      localStorage.setItem(
        this.pickupStocksCacheKey,
        JSON.stringify({
          expiresAt: Date.now() + this.pickupStocksTtlMs,
          stocks
        })
      );
    } catch {
      // ignore storage errors
    }
  }

  private normalizePickupStocks(stocks: unknown): Array<{ id: string; name: string; location: string }> {
    if (!Array.isArray(stocks)) {
      return [];
    }

    return stocks.reduce<Array<{ id: string; name: string; location: string }>>((acc, entry) => {
      if (!entry || typeof entry !== 'object') {
        return acc;
      }

      const row = entry as { id?: unknown; stockId?: unknown; name?: unknown; location?: unknown };
      const id = this.normalizePickupStockId(row.id ?? row.stockId);
      const name = typeof row.name === 'string' ? row.name.trim() : '';
      const location = typeof row.location === 'string' ? row.location.trim() : '';

      if (!id || !name || !location) {
        return acc;
      }

      acc.push({ id, name, location });
      return acc;
    }, []);
  }

  private normalizePickupStockId(value: unknown): string {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return String(value);
    }

    if (typeof value !== 'string') {
      return '';
    }

    return value.trim();
  }
}
