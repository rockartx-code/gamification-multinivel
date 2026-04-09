import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { catchError, map, Observable, throwError } from 'rxjs';

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
  CustomerDocument,
  CustomerOwnDocumentPayload,
  CustomerShippingAddress,
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
  OrderCancelResponse,
  OrderReturnRequestPayload,
  OrderReturnRequestResponse
} from '../models/admin.model';
import { AdminEmployee, CreateEmployeePayload, UpdateEmployeePrivilegesPayload } from '../models/employee.model';
import { NotificationReadResponse, PortalNotification } from '../models/portal-notification.model';
import {
  CreateAccountPayload,
  CreateAccountResponse,
  LoginResponse,
  PasswordRecoveryRequestPayload,
  PasswordRecoveryRequestResponse,
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
  HonorBoard,
  SponsorContact,
  UserDashboardData
} from '../models/user-dashboard.model';
import type { AuthUser } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class RealApiService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient) {}

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
      .post<LoginResponse>(`${this.baseUrl}/auth/login`, {
        username,
        password
      })
      .pipe(
        map((response) => {
          if (response.user) {
            if (!response.token) {
              throw new Error('La respuesta de login no incluyo el JWT de sesion.');
            }
            const userId = response.user.userId != null ? String(response.user.userId) : undefined;
            return {
              ...response.user,
              userId,
              token: response.token
            };
          }
          if (response.name && response.role) {
            return {
              userId: response.id != null ? String(response.id) : undefined,
              name: response.name,
              role: response.role,
              token: response.token
            };
          }
          throw new Error(response.message ?? 'No se pudo iniciar sesion.');
        })
      );
  }

  createAccount(payload: CreateAccountPayload): Observable<CreateAccountResponse> {
    return this.http
      .post<{
        ok?: boolean;
        customerId?: CreateAccountResponse['customerId'];
        customer?: CreateAccountResponse['customer'];
        requiresEmailVerification?: boolean;
        message?: string;
        Error?: string;
      }>(
        `${this.baseUrl}/auth/crearcuenta`,
        payload
      )
      .pipe(
        map((response) => {
          if (response.ok && response.customerId != null) {
            return {
              ok: true,
              customerId: response.customerId,
              requiresEmailVerification: response.requiresEmailVerification ?? true,
              message: response.message
            };
          }
          if (response.customer) {
            return {
              ok: response.ok ?? true,
              customerId: response.customerId ?? response.customer.id,
              customer: response.customer,
              requiresEmailVerification: response.requiresEmailVerification ?? true,
              message: response.message
            };
          }
          throw new Error(response.message ?? response.Error ?? 'No se pudo crear la cuenta.');
        })
      );
  }

  verifyEmail(token: string): Observable<VerifyEmailResponse> {
    return this.http.post<VerifyEmailResponse>(`${this.baseUrl}/auth/verify-email`, { token }).pipe(
      catchError((error) => {
        const message = String(error?.error?.message ?? '');
        if (error?.status === 404 && /ruta.*no encontrada/i.test(message)) {
          return this.http.post<VerifyEmailResponse>(`${this.baseUrl}/verify-email`, { token });
        }

        return throwError(() => error);
      })
    );
  }

  requestPasswordRecovery(payload: PasswordRecoveryRequestPayload): Observable<PasswordRecoveryRequestResponse> {
    return this.http
      .post<PasswordRecoveryRequestResponse & { Error?: string }>(
        `${this.baseUrl}/auth/password/recovery`,
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
      .post<ResetPasswordResponse & { Error?: string }>(`${this.baseUrl}/auth/password/reset`, payload)
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

  getAdminOrders(params: { status?: AdminOrder['status']; limit?: number } = {}): Observable<{ orders: AdminOrder[]; total: number }> {
    const q = new URLSearchParams();
    if (params.status) q.set('status', params.status);
    if (params.limit) q.set('limit', String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : '';
    return this.http.get<{ orders: AdminOrder[]; total: number }>(`${this.baseUrl}/admin/orders${qs}`, { headers: this.actorHeaders() });
  }

  getAdminWarnings(): Observable<{ type: string; text: string; severity: string }[]> {
    return this.http.get<{ warnings: { type: string; text: string; severity: string }[] }>(`${this.baseUrl}/admin/warnings`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.warnings ?? []));
  }

  listCustomers(): Observable<AdminCustomer[]> {
    return this.http.get<{ customers: AdminCustomer[] }>(`${this.baseUrl}/customers`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.customers ?? []));
  }

  listProducts(): Observable<AdminProduct[]> {
    return this.http.get<{ products: AdminProduct[] }>(`${this.baseUrl}/products`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.products ?? []));
  }

  listCampaigns(): Observable<AdminCampaign[]> {
    return this.http.get<{ campaigns: AdminCampaign[] }>(`${this.baseUrl}/campaigns`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.campaigns ?? []));
  }

  listAdminNotifications(): Observable<PortalNotification[]> {
    return this.http.get<{ notifications: PortalNotification[] }>(`${this.baseUrl}/notifications`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.notifications ?? []));
  }

  getOrders(customerId: string, params: { limit?: number; page?: number } = {}): Observable<AdminOrder[]> {
    const q = new URLSearchParams({ customerId });
    if (params.limit) q.set('limit', String(params.limit));
    if (params.page) q.set('offset', String((params.page) * (params.limit ?? 10)));
    return this.http
      .get<{ orders: AdminOrder[]; total?: number }>(`${this.baseUrl}/orders?${q.toString()}`)
      .pipe(map((response) => response.orders));
  }

  getCartData(): Observable<CartData> {
    return this.http.get<CartData>(`${this.baseUrl}/cart`);
  }

  getCatalogData(): Observable<CatalogData> {
    return this.http.get<CatalogData>(`${this.baseUrl}/catalog/catalog`);
  }

  getDashboardData(): Observable<DashboardData> {
    return this.http.get<DashboardData>(`${this.baseUrl}/customers/dashboard`, { headers: this.actorHeaders() });
  }

  /** @deprecated Usar getCatalogData() + getDashboardData() en su lugar */
  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    const query = userId ? `?userId=${encodeURIComponent(userId)}` : '';
    return this.http.get<UserDashboardData>(`${this.baseUrl}/user-dashboard${query}`);
  }

  getHonorBoard(): Observable<HonorBoard> {
    return this.http.get<HonorBoard>(`${this.baseUrl}/honor-board`, { headers: this.actorHeaders() });
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
      .post<{ order: AdminOrder }>(`${this.baseUrl}/orders/create`, payload, { headers: this.actorHeaders() })
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
    }).pipe(map((response) => this.normalizeOrderCheckoutResponse(response, orderId)));
  }

  getOrder(orderId: string): Observable<AdminOrder> {
    return this.http
      .get<{ order: AdminOrder }>(`${this.baseUrl}/orders/${encodeURIComponent(orderId)}`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.order));
  }

  getOrderStatus(orderOrPaymentId: string): Observable<OrderStatusLookup> {
    return this.http.get<OrderStatusLookup>(`${this.baseUrl}/orders/${encodeURIComponent(orderOrPaymentId)}/status`, {
      headers: this.actorHeaders()
    });
  }

  getAssociateMonth(associateId: string, monthKey: string): Observable<AssociateMonth> {
    return this.http
      .get<{ month: AssociateMonth }>(`${this.baseUrl}/associates/${encodeURIComponent(associateId)}/month/${encodeURIComponent(monthKey)}`)
      .pipe(map((response) => response.month));
  }


  getCustomer(customerId: string): Observable<CustomerProfile> {
    return this.http
      .get<{ customer: Record<string, unknown> }>(`${this.baseUrl}/customers/${encodeURIComponent(customerId)}`)
      .pipe(map((response) => this.mapCustomerProfile(response.customer ?? {})));
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.http
      .post<{ customer: AdminCustomer }>(`${this.baseUrl}/customers`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.customer));
  }

  createAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    return this.http.post<AssetResponse>(`${this.baseUrl}/assets`, payload, { headers: this.actorHeaders() });
  }

  addCustomerDocument(customerId: string, payload: LinkCustomerDocumentPayload): Observable<CustomerProfile> {
    return this.http
      .post<{ customer?: Record<string, unknown>; message?: string; Error?: string }>(
        `${this.baseUrl}/customers/${encodeURIComponent(customerId)}/documents`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => this.requireBusinessValue(response, response.customer, 'No se pudo asociar el documento.')),
        map((customer) => this.mapCustomerProfile(customer))
      );
  }

  uploadCustomerOwnDocument(payload: CustomerOwnDocumentPayload): Observable<CustomerProfile> {
    return this.http
      .post<{ customer?: Record<string, unknown>; message?: string; Error?: string }>(
        `${this.baseUrl}/profile/documents`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => this.requireBusinessValue(response, response.customer, 'No se pudo subir el documento.')),
        map((customer) => this.mapCustomerProfile(customer))
      );
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

  listPickupStocks(): Observable<Array<{ id: string; name: string; location: string }>> {
    return this.http
      .get<{ stocks: Array<{ id: string; name: string; location: string }> }>(`${this.baseUrl}/inventory/pickup-stocks`)
      .pipe(map((response) => response.stocks ?? []));
  }

  createStock(payload: { name: string; location: string; postalCode?: string; isMainWarehouse?: boolean; allowPickup?: boolean; linkedUserIds?: number[]; inventory?: Record<number, number> }): Observable<AdminStock> {
    return this.http
      .post<{ stock: AdminStock }>(`${this.baseUrl}/stocks`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.stock));
  }

  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory' | 'allowPickup'>>): Observable<AdminStock> {
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

  listEmployees(): Observable<AdminEmployee[]> {
    return this.http
      .get<{ employees: AdminEmployee[] }>(`${this.baseUrl}/employees`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.employees ?? []));
  }

  createEmployee(payload: CreateEmployeePayload): Observable<AdminEmployee> {
    return this.http
      .post<{ employee: AdminEmployee }>(`${this.baseUrl}/employees`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.employee));
  }

  updateEmployee(employeeId: number, payload: Partial<Pick<AdminEmployee, 'name' | 'phone' | 'active'>>): Observable<AdminEmployee> {
    return this.http
      .patch<{ employee: AdminEmployee }>(
        `${this.baseUrl}/employees/${encodeURIComponent(String(employeeId))}`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(map((response) => response.employee));
  }

  updateEmployeePrivileges(employeeId: number, payload: UpdateEmployeePrivilegesPayload): Observable<AdminEmployee> {
    return this.http
      .patch<{ employee: AdminEmployee }>(
        `${this.baseUrl}/employees/${encodeURIComponent(String(employeeId))}/privileges`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(map((response) => response.employee));
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

  changePassword(userId: string, payload: { currentPassword: string; newPassword: string }): Observable<void> {
    return this.http
      .post<void>(
        `${this.baseUrl}/customers/${encodeURIComponent(userId)}/password`,
        payload,
        { headers: this.actorHeaders() }
      );
  }

  updateProfile(userId: string, payload: UpdateProfilePayload): Observable<CustomerProfile> {
    return this.http
      .patch<{ customer: CustomerProfile }>(
        `${this.baseUrl}/customers/${encodeURIComponent(userId)}/profile`,
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

  listCategories(): Observable<ProductCategory[]> {
    return this.http
      .get<{ categories: ProductCategory[] }>(`${this.baseUrl}/product-categories`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.categories));
  }

  getSponsorContact(sponsorId: string): Observable<SponsorContact> {
    return this.http
      .get<{ sponsor: SponsorContact }>(`${this.baseUrl}/customers/sponsor/${encodeURIComponent(sponsorId)}`)
      .pipe(map((r) => r.sponsor));
  }

  saveCategory(payload: SaveProductCategoryPayload): Observable<ProductCategory> {
    return this.http
      .post<{ category: ProductCategory }>(`${this.baseUrl}/product-categories`, payload, { headers: this.actorHeaders() })
      .pipe(map((r) => r.category));
  }

  deleteCategory(id: string): Observable<{ ok: boolean }> {
    return this.http
      .delete<{ ok: boolean }>(`${this.baseUrl}/product-categories/${id}`, { headers: this.actorHeaders() });
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
      .pipe(map((response) => response.config));
  }

  getPublicBusinessConfig(): Observable<AppBusinessConfig> {
    return this.http
      .get<{ config: AppBusinessConfig }>(`${this.baseUrl}/catalog/config/public`)
      .pipe(map((response) => response.config));
  }

  saveBusinessConfig(payload: UpdateBusinessConfigPayload): Observable<AppBusinessConfig> {
    return this.http
      .put<{ config: AppBusinessConfig }>(`${this.baseUrl}/config/app`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.config));
  }

  getShippingQuote(payload: ShippingQuoteRequest): Observable<ShippingRate[]> {
    const normalizedPayload = this.normalizeShippingQuotePayload(payload);
    return this.http
      .post<{ rates: ShippingRate[] }>(`${this.baseUrl}/shipping/quote`, normalizedPayload)
      .pipe(map((res) => res.rates ?? []));
  }

  cancelOrder(orderId: string, reason: string): Observable<OrderCancelResponse> {
    return this.http.post<OrderCancelResponse>(
      `${this.baseUrl}/orders/${encodeURIComponent(orderId)}/cancel`,
      { reason },
      { headers: this.actorHeaders() }
    );
  }

  requestReturn(orderId: string, payload: OrderReturnRequestPayload): Observable<OrderReturnRequestResponse> {
    return this.http.post<OrderReturnRequestResponse>(
      `${this.baseUrl}/orders/${encodeURIComponent(orderId)}/return`,
      payload,
      { headers: this.actorHeaders() }
    );
  }

  private actorHeaders(): HttpHeaders {
    let headers = new HttpHeaders();
    const raw = localStorage.getItem('auth-user');
    if (!raw) {
      return headers;
    }
    try {
      const user = JSON.parse(raw) as { userId?: string | number; id?: string | number; name?: string; role?: string; token?: string; accessToken?: string };
      const actorId = user.userId ?? user.id;
      const token = typeof user.token === 'string' && user.token.trim().length > 0
        ? user.token.trim()
        : typeof user.accessToken === 'string' && user.accessToken.trim().length > 0
          ? user.accessToken.trim()
          : '';
      if (actorId != null && String(actorId).trim()) {
        headers = headers.set('x-user-id', String(actorId));
      }
      if (user.name) {
        headers = headers.set('x-user-name', String(user.name));
      }
      if (user.role) {
        headers = headers.set('x-user-role', String(user.role));
      }
      if (token) {
        headers = headers.set('Authorization', `Bearer ${token}`);
      }
    } catch {
      return headers;
    }
    return headers;
  }

  private mapCustomerProfile(customer: Record<string, unknown>): CustomerProfile {
    const rawCustomerId = customer['customerId'] ?? customer['id'] ?? '';
    const numericCustomerId = Number(rawCustomerId);
    const addresses = Array.isArray(customer['addresses'])
      ? customer['addresses']
      : Array.isArray(customer['shippingAddresses'])
        ? customer['shippingAddresses']
        : [];
    const shippingAddresses: CustomerShippingAddress[] = [];
    for (const entry of addresses) {
      if (!entry || typeof entry !== 'object') {
        continue;
      }
      const raw = entry as Record<string, unknown>;
      const address = String(raw['address'] ?? '').trim();
      const postalCode = String(raw['postalCode'] ?? '').trim();
      const state = String(raw['state'] ?? '').trim();
      if (!address && !postalCode && !state) {
        continue;
      }
      shippingAddresses.push({
        id: String(raw['addressId'] ?? raw['id'] ?? ''),
        label: String(raw['label'] ?? ''),
        recipientName: raw['recipientName'] ? String(raw['recipientName']) : undefined,
        phone: raw['phone'] ? String(raw['phone']) : undefined,
        street: raw['street'] ? String(raw['street']) : undefined,
        number: raw['number'] ? String(raw['number']) : undefined,
        address,
        city: raw['city'] ? String(raw['city']) : undefined,
        postalCode,
        state,
        country: raw['country'] ? String(raw['country']) : undefined,
        betweenStreets: raw['betweenStreets'] ? String(raw['betweenStreets']) : undefined,
        references: raw['references'] ? String(raw['references']) : undefined,
        isDefault: Boolean(raw['isDefault'])
      });
    }
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
      rfc: customer['rfc'] ? String(customer['rfc']) : undefined,
      curp: customer['curp'] ? String(customer['curp']) : undefined,
      address: customer['address'] ? String(customer['address']) : undefined,
      city: customer['city'] ? String(customer['city']) : undefined,
      state: customer['state'] ? String(customer['state']) : undefined,
      postalCode: customer['postalCode'] ? String(customer['postalCode']) : undefined,
      clabeInterbancaria: customer['clabeInterbancaria'] ? String(customer['clabeInterbancaria']) : customer['clabe'] ? String(customer['clabe']) : undefined,
      clabeLast4: customer['clabeLast4'] ? String(customer['clabeLast4']) : undefined,
      bankInstitution: customer['bankInstitution'] ? String(customer['bankInstitution']) : undefined,
      documents: this.mapCustomerDocuments(customer['documents']),
      ownDocuments: this.mapCustomerDocuments(customer['ownDocuments']),
      addresses: shippingAddresses,
      defaultAddressId,
      shippingAddresses,
      defaultShippingAddressId: defaultAddressId
    };
  }

  private mapCustomerDocuments(rawDocuments: unknown): CustomerDocument[] {
    if (!Array.isArray(rawDocuments)) {
      return [];
    }
    const documents: CustomerDocument[] = [];
    for (const entry of rawDocuments) {
      if (!entry || typeof entry !== 'object') {
        continue;
      }
      const raw = entry as Record<string, unknown>;
      const id = String(raw['documentId'] ?? raw['id'] ?? '').trim();
      const assetId = String(raw['assetId'] ?? '').trim();
      const name = String(raw['name'] ?? '').trim();
      const type = String(raw['contentType'] ?? raw['type'] ?? '').trim();
      const url = String(raw['url'] ?? '').trim();
      if (!id || !name) {
        continue;
      }
      documents.push({
        id,
        ...(assetId ? { assetId } : {}),
        name,
        type,
        ...(url ? { url } : {}),
        ...(raw['uploadedAt'] ? { uploadedAt: String(raw['uploadedAt']) } : {})
      });
    }
    return documents;
  }

  private normalizeShippingQuotePayload(payload: ShippingQuoteRequest): ShippingQuoteRequest {
    const postalCode = String(payload.postalCode ?? payload.zipTo ?? '').trim();
    const name = String(payload.name ?? payload.recipientName ?? '').trim();
    const phone = String(payload.phone ?? '').trim();
    const street = String(payload.street ?? payload.address ?? '').trim();
    const number = String(payload.number ?? '').trim();
    const city = String(payload.city ?? '').trim();
    const state = String(payload.state ?? '').trim();
    const country = String(payload.country ?? '').trim().toUpperCase();
    const address = String(
      payload.address ?? [street, number, city].filter((part) => Boolean(String(part).trim())).join(', ')
    ).trim();

    return {
      ...payload,
      zipTo: String(payload.zipTo ?? postalCode).trim(),
      ...(postalCode ? { postalCode } : {}),
      ...(name ? { name, recipientName: payload.recipientName?.trim() || name } : {}),
      ...(phone ? { phone } : {}),
      ...(street ? { street } : {}),
      ...(number ? { number } : {}),
      ...(address ? { address } : {}),
      ...(city ? { city } : {}),
      ...(state ? { state } : {}),
      ...(country ? { country } : {})
    };
  }

  private normalizeOrderCheckoutResponse(
    response: unknown,
    fallbackOrderId: string
  ): {
    orderId: string;
    checkout?: {
      provider?: string;
      preferenceId?: string;
      initPoint?: string;
      sandboxInitPoint?: string;
      externalReference?: string;
    };
  } {
    const candidates = this.collectCheckoutResponseCandidates(response);
    const orderId = this.firstCheckoutString(candidates, ['orderId', 'order_id']) || fallbackOrderId;
    const provider = this.firstCheckoutString(candidates, ['provider']);
    const preferenceId = this.firstCheckoutString(candidates, ['preferenceId', 'preference_id', 'id']);
    const initPoint = this.firstCheckoutString(candidates, ['initPoint', 'init_point', 'checkoutUrl', 'checkout_url', 'url']);
    const sandboxInitPoint = this.firstCheckoutString(candidates, ['sandboxInitPoint', 'sandbox_init_point']);
    const externalReference =
      this.firstCheckoutString(candidates, ['externalReference', 'external_reference']) || orderId;

    if (!preferenceId && !initPoint && !sandboxInitPoint) {
      return { orderId };
    }

    return {
      orderId,
      checkout: {
        provider: provider || undefined,
        preferenceId: preferenceId || undefined,
        initPoint: initPoint || undefined,
        sandboxInitPoint: sandboxInitPoint || undefined,
        externalReference: externalReference || undefined
      }
    };
  }

  private collectCheckoutResponseCandidates(value: unknown, depth = 0, seen = new Set<object>()): Record<string, unknown>[] {
    if (depth > 4) {
      return [];
    }

    const record = this.asRecord(value);
    if (!record || seen.has(record)) {
      return [];
    }

    seen.add(record);
    const candidates: Record<string, unknown>[] = [record];

    for (const key of ['checkout', 'data', 'response', 'body']) {
      const nested = this.asRecord(record[key]);
      if (nested) {
        candidates.push(...this.collectCheckoutResponseCandidates(nested, depth + 1, seen));
      }
    }

    return candidates;
  }

  private firstCheckoutString(candidates: Record<string, unknown>[], keys: string[]): string {
    for (const candidate of candidates) {
      for (const key of keys) {
        const value = candidate[key];
        if (typeof value === 'string' && value.trim()) {
          return value.trim();
        }
      }
    }

    return '';
  }

  private asRecord(value: unknown): Record<string, unknown> | null {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }

    if (typeof value !== 'string') {
      return null;
    }

    const trimmed = value.trim();
    if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
      return null;
    }

    try {
      const parsed = JSON.parse(trimmed);
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : null;
    } catch {
      return null;
    }
  }
}
