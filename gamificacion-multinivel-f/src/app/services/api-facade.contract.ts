import { Observable } from 'rxjs';

import {
  AdminCampaign,
  AdminCustomer,
  AdminData,
  AdminOrder,
  AdminOrderItem,
  AdminProduct,
  AdminStock,
  AppBusinessConfig,
  AssetResponse,
  AssociateMonth,
  CreateAdminOrderPayload,
  CreateAssetPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  CustomerProfile,
  InventoryMovement,
  OrderStatusLookup,
  PosCashControl,
  PosCashCut,
  PosSale,
  ProductAssetUpload,
  ProductOfMonthResponse,
  SaveAdminCampaignPayload,
  SaveAdminNotificationPayload,
  SaveAdminProductPayload,
  StockTransfer,
  UpdateBusinessConfigPayload,
  UpdateCustomerPayload,
  UpdateCustomerPrivilegesPayload,
  UpdateOrderStatusPayload
} from '../models/admin.model';
import {
  CreateAccountPayload,
  CreateAccountResponse,
  PasswordRecoveryRequestPayload,
  PasswordRecoveryRequestResponse,
  ResetPasswordPayload,
  ResetPasswordResponse
} from '../models/auth.model';
import { CartData } from '../models/cart.model';
import { NotificationReadResponse, PortalNotification } from '../models/portal-notification.model';
import {
  CommissionReceiptPayload,
  CommissionRequestPayload,
  CustomerClabePayload,
  UserDashboardData
} from '../models/user-dashboard.model';
import type { AuthUser } from './auth.service';

export interface ApiFacade {
  login(username: string, password: string): Observable<AuthUser>;
  createAccount(payload: CreateAccountPayload): Observable<CreateAccountResponse>;
  requestPasswordRecovery(payload: PasswordRecoveryRequestPayload): Observable<PasswordRecoveryRequestResponse>;
  resetPassword(payload: ResetPasswordPayload): Observable<ResetPasswordResponse>;
  getAdminData(): Observable<AdminData>;
  getCartData(): Observable<CartData>;
  getUserDashboardData(userId?: string): Observable<UserDashboardData>;
  requestCommissionPayout(payload: CommissionRequestPayload): Observable<{ request: unknown; summary?: unknown }>;
  uploadCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }>;
  uploadAdminCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }>;
  saveCustomerClabe(payload: CustomerClabePayload): Observable<{ ok: boolean; clabeLast4?: string }>;
  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder>;
  createOrderCheckout(
    orderId: string,
    payload?: {
      successUrl?: string;
      failureUrl?: string;
      pendingUrl?: string;
      notificationUrl?: string;
      currencyId?: string;
    }
  ): Observable<{
    orderId: string;
    checkout?: {
      provider?: string;
      preferenceId?: string;
      initPoint?: string;
      sandboxInitPoint?: string;
      externalReference?: string;
    };
  }>;
  getOrder(orderId: string): Observable<AdminOrder>;
  getOrderStatus(orderOrPaymentId: string): Observable<OrderStatusLookup>;
  getAssociateMonth(associateId: string, monthKey: string): Observable<AssociateMonth>;
  getOrders(customerId: string): Observable<AdminOrder[]>;
  getCustomer(customerId: string): Observable<CustomerProfile>;
  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer>;
  createAsset(payload: CreateAssetPayload): Observable<AssetResponse>;
  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload>;
  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse>;
  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct>;
  updateOrderStatus(orderId: string, payload: UpdateOrderStatusPayload): Observable<AdminOrder>;
  listStocks(): Observable<AdminStock[]>;
  createStock(payload: { name: string; location: string; linkedUserIds?: number[]; inventory?: Record<number, number> }): Observable<AdminStock>;
  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory'>>): Observable<AdminStock>;
  registerStockEntry(stockId: string, payload: { productId: number; qty: number; userId?: number | null; note?: string }): Observable<{ stock: AdminStock }>;
  registerStockDamage(stockId: string, payload: { productId: number; qty: number; reason: string; userId?: number | null }): Observable<{ stock: AdminStock }>;
  listStockTransfers(stockId?: string): Observable<StockTransfer[]>;
  createStockTransfer(payload: {
    sourceStockId: string;
    destinationStockId: string;
    lines: Array<{ productId: number; qty: number }>;
    createdByUserId?: number | null;
  }): Observable<{ transfer: StockTransfer }>;
  receiveStockTransfer(transferId: string, payload: { receivedByUserId?: number | null }): Observable<{ transfer: StockTransfer }>;
  listInventoryMovements(stockId?: string): Observable<InventoryMovement[]>;
  listPosSales(stockId?: string): Observable<PosSale[]>;
  registerPosSale(payload: {
    stockId: string;
    customerId?: number | null;
    customerName?: string;
    paymentStatus?: 'paid_branch';
    deliveryStatus?: 'delivered_branch';
    items: Array<Pick<AdminOrderItem, 'productId' | 'name' | 'price' | 'quantity'>>;
  }): Observable<{ sale: PosSale }>;
  getPosCashControl(stockId?: string): Observable<PosCashControl>;
  createPosCashCut(payload: { stockId: string }): Observable<{ cut: PosCashCut; control: PosCashControl }>;
  updateCustomerPrivileges(customerId: number, payload: UpdateCustomerPrivilegesPayload): Observable<AdminCustomer>;
  updateCustomer(customerId: number, payload: UpdateCustomerPayload): Observable<AdminCustomer>;
  saveCampaign(payload: SaveAdminCampaignPayload): Observable<AdminCampaign>;
  saveNotification(payload: SaveAdminNotificationPayload): Observable<PortalNotification>;
  markNotificationRead(notificationId: string, payload?: { customerId?: number | string }): Observable<NotificationReadResponse>;
  getBusinessConfig(): Observable<AppBusinessConfig>;
  saveBusinessConfig(payload: UpdateBusinessConfigPayload): Observable<AppBusinessConfig>;
}
