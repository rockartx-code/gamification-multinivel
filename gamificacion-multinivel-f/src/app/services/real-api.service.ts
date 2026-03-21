import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { map, Observable } from 'rxjs';

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
  CustomerShippingAddress,
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
import { ApiFacade } from './api-facade.contract';
import type { AuthUser } from './auth.service';
import { BrowserStorageService } from './browser/browser-storage.service';
import { BusinessConfigService } from './business-config.service';

@Injectable({
  providedIn: 'root'
})
export class RealApiService implements ApiFacade {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(
    private readonly http: HttpClient,
    private readonly storage: BrowserStorageService,
    private readonly businessConfigService: BusinessConfigService
  ) {}

  private requireBusinessValue<T>(
    response: { message?: string; Error?: string },
    value: T | null | undefined,
    fallbackMessage: string
  ): T {
    if (response.Error || value == null) {
      throw new Error(response.message ?? fallbackMessage);
    }
    return value;
  }

  login(username: string, password: string): Observable<AuthUser> {
    return this.http
      .post<{ user?: AuthUser; message?: string; Error?: string }>(`${this.baseUrl}/login`, {
        username,
        password
      })
      .pipe(
        map((response) => {
          if (response.user) {
            return response.user;
          }
          throw new Error(response.message ?? 'No se pudo iniciar sesion.');
        })
      );
  }

  createAccount(payload: CreateAccountPayload): Observable<CreateAccountResponse> {
    return this.http
      .post<{ customer?: CreateAccountResponse['customer']; message?: string; Error?: string }>(
        `${this.baseUrl}/crearcuenta`,
        payload
      )
      .pipe(
        map((response) => {
          if (response.customer) {
            return { customer: response.customer };
          }
          throw new Error(response.message ?? 'No se pudo crear la cuenta.');
        })
      );
  }

  requestPasswordRecovery(payload: PasswordRecoveryRequestPayload): Observable<PasswordRecoveryRequestResponse> {
    return this.http
      .post<PasswordRecoveryRequestResponse & { Error?: string }>(
        `${this.baseUrl}/password/recovery`,
        payload
      )
      .pipe(
        map((response) => {
          if (response.ok) {
            return response;
          }
          throw new Error(response.message ?? 'No se pudo enviar el codigo OTP.');
        })
      );
  }

  resetPassword(payload: ResetPasswordPayload): Observable<ResetPasswordResponse> {
    return this.http
      .post<ResetPasswordResponse & { Error?: string }>(`${this.baseUrl}/password/reset`, payload)
      .pipe(
        map((response) => {
          if (response.ok) {
            return response;
          }
          throw new Error(response.message ?? 'No se pudo actualizar la contrasena.');
        })
      );
  }

  getAdminData(): Observable<AdminData> {
    return this.http.get<AdminData>(`${this.baseUrl}/admin/dashboard`);
  }

  getCartData(): Observable<CartData> {
    return this.http.get<CartData>(`${this.baseUrl}/cart`);
  }

  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    const query = userId ? `?userId=${encodeURIComponent(userId)}` : '';
    return this.http.get<UserDashboardData>(`${this.baseUrl}/user-dashboard${query}`);
  }

  requestCommissionPayout(payload: CommissionRequestPayload): Observable<{ request: unknown; summary?: unknown }> {
    return this.http.post<{ request: unknown; summary?: unknown }>(`${this.baseUrl}/commissions/request`, payload);
  }

  uploadCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.http.post<{ receipt: unknown; asset?: unknown }>(`${this.baseUrl}/commissions/receipt`, payload);
  }

  uploadAdminCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.http.post<{ receipt: unknown; asset?: unknown }>(`${this.baseUrl}/admin/commissions/receipt`, payload, {
      headers: this.actorHeaders()
    });
  }

  saveCustomerClabe(payload: CustomerClabePayload): Observable<{ ok: boolean; clabeLast4?: string }> {
    return this.http.post<{ ok: boolean; clabeLast4?: string }>(`${this.baseUrl}/customers/clabe`, payload, {
      headers: this.actorHeaders()
    });
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    return this.http
      .post<{ order: AdminOrder }>(`${this.baseUrl}/orders`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.order));
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
    return this.http.post<{
      orderId: string;
      checkout?: {
        provider?: string;
        preferenceId?: string;
        initPoint?: string;
        sandboxInitPoint?: string;
        externalReference?: string;
      };
    }>(`${this.baseUrl}/orders/${encodeURIComponent(orderId)}/checkout`, payload, {
      headers: this.actorHeaders()
    });
  }

  getOrder(orderId: string): Observable<AdminOrder> {
    return this.http
      .get<{ order: AdminOrder }>(`${this.baseUrl}/orders/${orderId}`)
      .pipe(map((response) => response.order));
  }

  getOrderStatus(orderOrPaymentId: string): Observable<OrderStatusLookup> {
    return this.http.get<OrderStatusLookup>(`${this.baseUrl}/orders/${encodeURIComponent(orderOrPaymentId)}/status`);
  }

  getAssociateMonth(associateId: string, monthKey: string): Observable<AssociateMonth> {
    return this.http
      .get<{ month: AssociateMonth }>(`${this.baseUrl}/associates/${encodeURIComponent(associateId)}/month/${encodeURIComponent(monthKey)}`)
      .pipe(map((response) => response.month));
  }

  getOrders(customerId: string): Observable<AdminOrder[]> {
    return this.http
      .get<{ orders: AdminOrder[] }>(`${this.baseUrl}/orders?customerId=${encodeURIComponent(customerId)}`)
      .pipe(map((response) => response.orders));
  }

  getCustomer(customerId: string): Observable<CustomerProfile> {
    return this.http
      .get<{ customer: Record<string, unknown> }>(`${this.baseUrl}/customers/${encodeURIComponent(customerId)}`)
      .pipe(
        map((response) => {
          const customer = response.customer ?? {};
          const rawCustomerId = customer['customerId'] ?? customer['id'] ?? '';
          const numericCustomerId = Number(rawCustomerId);
          const addresses = Array.isArray(customer['addresses'])
            ? customer['addresses']
            : Array.isArray(customer['shippingAddresses'])
              ? customer['shippingAddresses']
              : [];
          const shippingAddresses = addresses
                .map((entry): CustomerShippingAddress | null => {
                  if (!entry || typeof entry !== 'object') {
                    return null;
                  }
                  const raw = entry as Record<string, unknown>;
                  const address = String(raw['address'] ?? '').trim();
                  const postalCode = String(raw['postalCode'] ?? '').trim();
                  const state = String(raw['state'] ?? '').trim();
                  if (!address && !postalCode && !state) {
                    return null;
                  }
                  return {
                    id: String(raw['addressId'] ?? raw['id'] ?? ''),
                    label: String(raw['label'] ?? ''),
                    recipientName: raw['recipientName'] ? String(raw['recipientName']) : undefined,
                    phone: raw['phone'] ? String(raw['phone']) : undefined,
                    address,
                    postalCode,
                    state,
                    isDefault: Boolean(raw['isDefault'])
                  };
                })
                .filter((entry): entry is CustomerShippingAddress => Boolean(entry));
          const defaultAddressId = customer['defaultAddressId']
            ? String(customer['defaultAddressId'])
            : customer['defaultShippingAddressId']
              ? String(customer['defaultShippingAddressId'])
              : shippingAddresses.find((entry) => entry.isDefault)?.id;

          return {
            id: Number.isFinite(numericCustomerId) && String(rawCustomerId).trim() !== ''
              ? numericCustomerId
              : String(rawCustomerId ?? ''),
            name: String(customer['name'] ?? ''),
            email: String(customer['email'] ?? ''),
            phone: customer['phone'] ? String(customer['phone']) : undefined,
            address: customer['address'] ? String(customer['address']) : undefined,
            city: customer['city'] ? String(customer['city']) : undefined,
            state: customer['state'] ? String(customer['state']) : undefined,
            postalCode: customer['postalCode'] ? String(customer['postalCode']) : undefined,
            addresses: shippingAddresses,
            defaultAddressId,
            shippingAddresses,
            defaultShippingAddressId: defaultAddressId
          };
        })
      );
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.http
      .post<{ customer: AdminCustomer }>(`${this.baseUrl}/customers`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.customer));
  }

  createAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    return this.http.post<AssetResponse>(`${this.baseUrl}/assets`, payload, { headers: this.actorHeaders() });
  }

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    return this.http.post<ProductAssetUpload>(`${this.baseUrl}/products/assets`, payload, { headers: this.actorHeaders() });
  }

  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse> {
    return this.http.post<ProductOfMonthResponse>(`${this.baseUrl}/products/product-of-month`, { productId }, { headers: this.actorHeaders() });
  }

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    return this.http
      .post<{ product: AdminProduct }>(`${this.baseUrl}/products`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.product));
  }

  updateOrderStatus(orderId: string, payload: UpdateOrderStatusPayload): Observable<AdminOrder> {
    return this.http
      .patch<{ order?: AdminOrder; message?: string; Error?: string }>(`${this.baseUrl}/orders/${orderId}`, payload, {
        headers: this.actorHeaders()
      })
      .pipe(
        map((response) => this.requireBusinessValue(response, response.order, 'No se pudo actualizar el pedido.'))
      );
  }

  listStocks(): Observable<AdminStock[]> {
    return this.http
      .get<{ stocks: AdminStock[] }>(`${this.baseUrl}/stocks`)
      .pipe(map((response) => response.stocks ?? []));
  }

  createStock(payload: { name: string; location: string; linkedUserIds?: number[]; inventory?: Record<number, number> }): Observable<AdminStock> {
    return this.http
      .post<{ stock: AdminStock }>(`${this.baseUrl}/stocks`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.stock));
  }

  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory'>>): Observable<AdminStock> {
    return this.http
      .patch<{ stock: AdminStock }>(`${this.baseUrl}/stocks/${encodeURIComponent(stockId)}`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.stock));
  }

  registerStockEntry(stockId: string, payload: { productId: number; qty: number; userId?: number | null; note?: string }): Observable<{ stock: AdminStock }> {
    return this.http
      .post<{ stock?: AdminStock; message?: string; Error?: string }>(
        `${this.baseUrl}/stocks/${encodeURIComponent(stockId)}/entries`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => ({
          stock: this.requireBusinessValue(response, response.stock, 'No se pudo registrar la entrada de inventario.')
        }))
      );
  }

  registerStockDamage(stockId: string, payload: { productId: number; qty: number; reason: string; userId?: number | null }): Observable<{ stock: AdminStock }> {
    return this.http
      .post<{ stock?: AdminStock; message?: string; Error?: string }>(
        `${this.baseUrl}/stocks/${encodeURIComponent(stockId)}/damages`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => ({
          stock: this.requireBusinessValue(response, response.stock, 'No se pudo registrar la merma de inventario.')
        }))
      );
  }

  listStockTransfers(stockId?: string): Observable<StockTransfer[]> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ transfers: StockTransfer[] }>(`${this.baseUrl}/stocks/transfers${query}`)
      .pipe(map((response) => response.transfers ?? []));
  }

  createStockTransfer(payload: {
    sourceStockId: string;
    destinationStockId: string;
    lines: Array<{ productId: number; qty: number }>;
    createdByUserId?: number | null;
  }): Observable<{ transfer: StockTransfer }> {
    return this.http
      .post<{ transfer?: StockTransfer; message?: string; Error?: string }>(`${this.baseUrl}/stocks/transfers`, payload, {
        headers: this.actorHeaders()
      })
      .pipe(
        map((response) => ({
          transfer: this.requireBusinessValue(response, response.transfer, 'No se pudo crear la transferencia.')
        }))
      );
  }

  receiveStockTransfer(transferId: string, payload: { receivedByUserId?: number | null }): Observable<{ transfer: StockTransfer }> {
    return this.http
      .post<{ transfer?: StockTransfer; message?: string; Error?: string }>(
        `${this.baseUrl}/stocks/transfers/${encodeURIComponent(transferId)}/receive`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => ({
          transfer: this.requireBusinessValue(response, response.transfer, 'No se pudo recibir la transferencia.')
        }))
      );
  }

  listInventoryMovements(stockId?: string): Observable<InventoryMovement[]> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ movements: InventoryMovement[] }>(`${this.baseUrl}/stocks/movements${query}`)
      .pipe(map((response) => response.movements ?? []));
  }

  listPosSales(stockId?: string): Observable<PosSale[]> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ sales: PosSale[] }>(`${this.baseUrl}/pos/sales${query}`)
      .pipe(map((response) => response.sales ?? []));
  }

  registerPosSale(payload: {
    stockId: string;
    customerId?: number | null;
    customerName?: string;
    paymentStatus?: 'paid_branch';
    deliveryStatus?: 'delivered_branch';
    items: Array<Pick<AdminOrderItem, 'productId' | 'name' | 'price' | 'quantity'>>;
  }): Observable<{ sale: PosSale }> {
    return this.http
      .post<{ sale?: PosSale; message?: string; Error?: string }>(`${this.baseUrl}/pos/sales`, payload, {
        headers: this.actorHeaders()
      })
      .pipe(
        map((response) => ({
          sale: this.requireBusinessValue(response, response.sale, 'No se pudo registrar la venta.')
        }))
      );
  }

  getPosCashControl(stockId?: string): Observable<PosCashControl> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ control: PosCashControl }>(`${this.baseUrl}/pos/cash-control${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.control));
  }

  createPosCashCut(payload: { stockId: string }): Observable<{ cut: PosCashCut; control: PosCashControl }> {
    return this.http.post<{ cut: PosCashCut; control: PosCashControl }>(`${this.baseUrl}/pos/cash-cut`, payload, {
      headers: this.actorHeaders()
    });
  }

  updateCustomerPrivileges(customerId: number, payload: UpdateCustomerPrivilegesPayload): Observable<AdminCustomer> {
    return this.http
      .patch<{ customer: AdminCustomer }>(
        `${this.baseUrl}/customers/${encodeURIComponent(String(customerId))}/privileges`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(map((response) => response.customer));
  }

  updateCustomer(customerId: number, payload: UpdateCustomerPayload): Observable<AdminCustomer> {
    return this.http
      .patch<{ customer: AdminCustomer }>(
        `${this.baseUrl}/customers/${encodeURIComponent(String(customerId))}`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(map((response) => response.customer));
  }

  saveCampaign(payload: SaveAdminCampaignPayload): Observable<AdminCampaign> {
    return this.http
      .post<{ campaign: AdminCampaign }>(`${this.baseUrl}/campaigns`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.campaign));
  }

  saveNotification(payload: SaveAdminNotificationPayload): Observable<PortalNotification> {
    return this.http
      .post<{ notification: PortalNotification }>(`${this.baseUrl}/notifications`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.notification));
  }

  markNotificationRead(notificationId: string, payload: { customerId?: number | string } = {}): Observable<NotificationReadResponse> {
    return this.http.post<NotificationReadResponse>(
      `${this.baseUrl}/notifications/${encodeURIComponent(notificationId)}/read`,
      payload,
      { headers: this.actorHeaders() }
    );
  }

  getBusinessConfig(): Observable<AppBusinessConfig> {
    return this.http
      .get<{ config: AppBusinessConfig }>(`${this.baseUrl}/config/app`, { headers: this.actorHeaders() })
      .pipe(map((response) => this.businessConfigService.normalizeForDraft(response.config)));
  }

  saveBusinessConfig(payload: UpdateBusinessConfigPayload): Observable<AppBusinessConfig> {
    return this.http
      .put<{ config: AppBusinessConfig }>(
        `${this.baseUrl}/config/app`,
        { config: this.businessConfigService.normalizeForSave(payload.config) },
        { headers: this.actorHeaders() }
      )
      .pipe(map((response) => this.businessConfigService.normalizeForDraft(response.config)));
  }

  private actorHeaders(): HttpHeaders {
    let headers = new HttpHeaders();
    const user = this.storage.getJson<{ userId?: string; name?: string; role?: string }>('auth-user');
    if (!user) {
      return headers;
    }
    if (user.userId) {
      headers = headers.set('x-user-id', String(user.userId));
    }
    if (user.name) {
      headers = headers.set('x-user-name', String(user.name));
    }
    if (user.role) {
      headers = headers.set('x-user-role', String(user.role));
    }
    return headers;
  }
}
