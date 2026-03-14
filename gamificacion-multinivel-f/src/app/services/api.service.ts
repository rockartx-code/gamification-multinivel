import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AdminCustomer,
  AdminData,
  AdminCampaign,
  AppBusinessConfig,
  AdminOrder,
  AdminOrderItem,
  AdminProduct,
  AdminStock,
  AssetResponse,
  CreateAssetPayload,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  CustomerProfile,
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
  UpdateCustomerPrivilegesPayload
} from '../models/admin.model';
import { NotificationReadResponse, PortalNotification } from '../models/portal-notification.model';
import {
  CreateAccountPayload,
  CreateAccountResponse,
  PasswordRecoveryRequestPayload,
  PasswordRecoveryRequestResponse,
  ResetPasswordPayload,
  ResetPasswordResponse
} from '../models/auth.model';
import { CartData } from '../models/cart.model';
import {
  CommissionReceiptPayload,
  CommissionRequestPayload,
  CustomerClabePayload,
  UserDashboardData
} from '../models/user-dashboard.model';
import type { AuthUser } from './auth.service';
import { MockApiService } from './mock-api.service';
import { RealApiService } from './real-api.service';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
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

  requestPasswordRecovery(payload: PasswordRecoveryRequestPayload): Observable<PasswordRecoveryRequestResponse> {
    return this.resolveApi().requestPasswordRecovery(payload);
  }

  resetPassword(payload: ResetPasswordPayload): Observable<ResetPasswordResponse> {
    return this.resolveApi().resetPassword(payload);
  }

  getAdminData(): Observable<AdminData> {
    return this.resolveApi().getAdminData();
  }

  getCartData(): Observable<CartData> {
    return this.resolveApi().getCartData();
  }

  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    return this.resolveApi().getUserDashboardData(userId);
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

  getOrders(customerId: string): Observable<AdminOrder[]> {
    return this.resolveApi().getOrders(customerId);
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

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    return this.resolveApi().createProductAsset(payload);
  }

  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse> {
    return this.resolveApi().setProductOfMonth(productId);
  }

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    return this.resolveApi().saveProduct(payload);
  }

  updateOrderStatus(orderId: string, payload: UpdateOrderStatusPayload): Observable<AdminOrder> {
    return this.resolveApi().updateOrderStatus(orderId, payload);
  }

  listStocks(): Observable<AdminStock[]> {
    return this.resolveApi().listStocks();
  }

  createStock(payload: { name: string; location: string; linkedUserIds?: number[]; inventory?: Record<number, number> }): Observable<AdminStock> {
    return this.resolveApi().createStock(payload);
  }

  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory'>>): Observable<AdminStock> {
    return this.resolveApi().updateStock(stockId, payload);
  }

  registerStockEntry(stockId: string, payload: { productId: number; qty: number; userId?: number | null; note?: string }): Observable<{ stock: AdminStock }> {
    return this.resolveApi().registerStockEntry(stockId, payload);
  }

  registerStockDamage(stockId: string, payload: { productId: number; qty: number; reason: string; userId?: number | null }): Observable<{ stock: AdminStock }> {
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
    paymentStatus?: 'paid_branch';
    deliveryStatus?: 'delivered_branch';
    items: Array<Pick<AdminOrderItem, 'productId' | 'name' | 'price' | 'quantity'>>;
  }): Observable<{ sale: PosSale }> {
    return this.resolveApi().registerPosSale(payload);
  }

  getPosCashControl(stockId?: string): Observable<PosCashControl> {
    return this.resolveApi().getPosCashControl(stockId);
  }

  createPosCashCut(payload: { stockId: string }): Observable<{ cut: PosCashCut; control: PosCashControl }> {
    return this.resolveApi().createPosCashCut(payload);
  }

  updateCustomerPrivileges(customerId: number, payload: UpdateCustomerPrivilegesPayload): Observable<AdminCustomer> {
    return this.resolveApi().updateCustomerPrivileges(customerId, payload);
  }

  updateCustomer(customerId: number, payload: UpdateCustomerPayload): Observable<AdminCustomer> {
    return this.resolveApi().updateCustomer(customerId, payload);
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

  saveBusinessConfig(payload: UpdateBusinessConfigPayload): Observable<AppBusinessConfig> {
    return this.resolveApi().saveBusinessConfig(payload);
  }

  private resolveApi(): MockApiService | RealApiService {
    return environment.useMockApi ? this.mockApi : this.realApi;
  }
}
