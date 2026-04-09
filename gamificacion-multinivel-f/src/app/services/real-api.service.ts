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
  CustomerOrdersPage,
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
  DashboardProduct,
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

  resendEmailConfirmation(payload: ResendEmailConfirmationPayload): Observable<ResendEmailConfirmationResponse> {
    return this.http
      .post<ResendEmailConfirmationResponse & { Error?: string }>(`${this.baseUrl}/auth/resend-email-confirmation`, payload)
      .pipe(
        map((response) => {
          if (response.ok) {
            return response;
          }
          throw new Error(response.message ?? 'No se pudo reenviar el correo de confirmacion.');
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

  getAdminOrders(params: { status?: AdminOrder['status']; limit?: number; nextToken?: string } = {}): Observable<{ orders: AdminOrder[]; total: number; nextToken?: string; hasMore?: boolean }> {
    const q = new URLSearchParams();
    if (params.status) q.set('status', params.status);
    if (params.limit) q.set('limit', String(params.limit));
    if (params.nextToken) q.set('nextToken', params.nextToken);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return this.http
      .get<{ orders: unknown[]; total?: number; count?: number; nextToken?: string; hasMore?: boolean }>(`${this.baseUrl}/orders/find${qs}`, { headers: this.actorHeaders() })
      .pipe(
        map((response) => ({
          orders: this.normalizeOrders(response.orders),
          total: Number(response.total ?? response.count ?? (Array.isArray(response.orders) ? response.orders.length : 0)),
          nextToken: response.nextToken ?? undefined,
          hasMore: response.hasMore ?? false
        }))
      );
  }

  getAdminWarnings(): Observable<{ type: string; text: string; severity: string }[]> {
    return this.http.get<{ warnings: { type: string; text: string; severity: string }[] }>(`${this.baseUrl}/dashboard/admin/warnings`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.warnings ?? []));
  }

  private normalizeAdminCustomer(raw: Record<string, unknown>): AdminCustomer {
    return {
      id: Number(raw['customerId'] ?? raw['id'] ?? 0),
      name: String(raw['name'] ?? ''),
      email: String(raw['email'] ?? ''),
      isSuperUser: Boolean(raw['isSuperUser'] ?? false),
      leaderId: raw['leaderId'] != null ? Number(raw['leaderId']) : null,
      level: String(raw['level'] ?? ''),
      discount: String(raw['discount'] ?? '0%'),
      commissions: Number(raw['commissions'] ?? 0),
      commissionsPrevMonth: raw['commissionsPrevMonth'] != null ? Number(raw['commissionsPrevMonth']) : undefined,
      commissionsPrevMonthKey: raw['commissionsPrevMonthKey'] != null ? String(raw['commissionsPrevMonthKey']) : undefined,
      commissionsCurrentPending: raw['commissionsCurrentPending'] != null ? Number(raw['commissionsCurrentPending']) : undefined,
      commissionsCurrentConfirmed: raw['commissionsCurrentConfirmed'] != null ? Number(raw['commissionsCurrentConfirmed']) : undefined,
      commissionsPrevStatus: raw['commissionsPrevStatus'] as AdminCustomer['commissionsPrevStatus'],
      commissionsPrevReceiptUrl: raw['commissionsPrevReceiptUrl'] != null ? String(raw['commissionsPrevReceiptUrl']) : undefined,
      clabeInterbancaria: raw['clabeInterbancaria'] != null ? String(raw['clabeInterbancaria']) : undefined,
      bankInstitution: raw['bankInstitution'] != null ? String(raw['bankInstitution']) : undefined,
      documents: raw['documents'] as AdminCustomer['documents'],
    };
  }

  listCustomers(): Observable<AdminCustomer[]> {
    return this.http.get<{ customers: Record<string, unknown>[] }>(
      `${this.baseUrl}/customers/getall?limit=200`, { headers: this.actorHeaders() }
    ).pipe(map((r) => (r.customers ?? []).map((c) => this.normalizeAdminCustomer(c))));
  }

  listCustomersPaged(params: { limit?: number; nextToken?: string; search?: string } = {}): Observable<{ customers: AdminCustomer[]; nextToken?: string; hasMore?: boolean; total?: number }> {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.nextToken) q.set('nextToken', params.nextToken);
    if (params.search) q.set('search', params.search);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return this.http.get<{ customers: Record<string, unknown>[]; nextToken?: string; hasMore?: boolean; total?: number }>(
      `${this.baseUrl}/customers/getall${qs}`, { headers: this.actorHeaders() }
    ).pipe(map((r) => ({
      customers: (r.customers ?? []).map((c) => this.normalizeAdminCustomer(c)),
      nextToken: r.nextToken,
      hasMore: r.hasMore,
      total: r.total,
    })));
  }

  listProducts(): Observable<AdminProduct[]> {
    return this.http.get<{ products: AdminProduct[] }>(`${this.baseUrl}/catalog/catalog`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.products ?? []));
  }

  listCampaigns(): Observable<AdminCampaign[]> {
    return this.http.get<{ campaigns: AdminCampaign[] }>(`${this.baseUrl}/dashboard/campaigns`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.campaigns ?? []));
  }

  listAdminNotifications(): Observable<PortalNotification[]> {
    return this.http.get<{ notifications: PortalNotification[] }>(`${this.baseUrl}/dashboard/notifications`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.notifications ?? []));
  }

  getOrders(customerId: string, params: { limit?: number; nextToken?: string } = {}): Observable<CustomerOrdersPage> {
    const q = new URLSearchParams({ customerId });
    if (params.limit) q.set('limit', String(params.limit));
    if (params.nextToken) q.set('nextToken', params.nextToken);
    return this.http
      .get<{
        orders?: unknown[];
        pageSize?: number;
        count?: number;
        nextToken?: string | null;
        hasMore?: boolean;
        source?: string;
      }>(`${this.baseUrl}/orders/find?${q.toString()}`, { headers: this.actorHeaders() })
      .pipe(map((response) => this.normalizeCustomerOrdersPage(response, params.limit ?? 10)));
  }

  getCartData(): Observable<CartData> {
    return this.http.get<CartData>(`${this.baseUrl}/cart`);
  }

  getCatalogData(): Observable<CatalogData> {
    return this.http.get<{ products: Record<string, unknown>[]; productOfMonth?: Record<string, unknown> | null }>(
      `${this.baseUrl}/catalog/catalog`
    ).pipe(
      map((raw) => ({
        products: (raw.products ?? []).map((p) => this.normalizeDashboardProduct(p)),
        productOfMonth: raw.productOfMonth ? this.normalizeDashboardProduct(raw.productOfMonth) : null,
      } as CatalogData))
    );
  }

  private normalizeDashboardProduct(p: Record<string, unknown>): DashboardProduct {
    const images = Array.isArray(p['images']) ? (p['images'] as Array<{ section: string; url: string; assetId?: string }>) : [];
    const miniatura = images.find((im) => im.section === 'miniatura')?.url ?? '';
    const landing = images.find((im) => im.section === 'landing')?.url ?? '';
    const fallback = images[0]?.url ?? '';
    const tags = Array.isArray(p['tags']) ? (p['tags'] as string[]) : [];
    return {
      id: String(p['productId'] ?? p['id'] ?? ''),
      name: String(p['name'] ?? ''),
      price: Number(p['price'] ?? 0),
      badge: String(tags[0] ?? p['badge'] ?? ''),
      img: miniatura || landing || fallback,
      images,
      hook: String(p['hook'] ?? ''),
      description: p['description'] != null ? String(p['description']) : undefined,
      copyFacebook: p['copyFacebook'] != null ? String(p['copyFacebook']) : undefined,
      copyInstagram: p['copyInstagram'] != null ? String(p['copyInstagram']) : undefined,
      copyWhatsapp: p['copyWhatsapp'] != null ? String(p['copyWhatsapp']) : undefined,
      tags: tags.length ? tags : undefined,
      inOnlineStore: p['inOnlineStore'] != null ? Boolean(p['inOnlineStore']) : undefined,
      inPOS: p['inPOS'] != null ? Boolean(p['inPOS']) : undefined,
      commissionable: p['commissionable'] != null ? Boolean(p['commissionable']) : undefined,
    };
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
    return this.http.get<HonorBoard>(`${this.baseUrl}/dashboard/honor-board`, { headers: this.actorHeaders() });
  }

  requestCommissionPayout(payload: CommissionRequestPayload): Observable<{ request: unknown; summary?: unknown }> {
    return this.http.post<{ request: unknown; summary?: unknown }>(`${this.baseUrl}/commissions/request`, payload);
  }

  uploadCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.http.post<{ receipt: unknown; asset?: unknown }>(`${this.baseUrl}/commissions/receipt`, payload);
  }

  uploadAdminCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.http.post<{ receipt: unknown; asset?: unknown }>(`${this.baseUrl}/commissions/admin/receipt`, payload, {
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
      .pipe(map((response) => this.normalizeAdminOrder(response.order)));
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
      .pipe(map((response) => this.normalizeAdminOrder(response.order)));
  }

  getOrderStatus(orderOrPaymentId: string): Observable<OrderStatusLookup> {
    return this.http.get<OrderStatusLookup>(`${this.baseUrl}/orders/${encodeURIComponent(orderOrPaymentId)}/status`, {
      headers: this.actorHeaders()
    });
  }

  getAssociateMonth(associateId: string, monthKey: string): Observable<AssociateMonth> {
    return this.http
      .get<{ month: AssociateMonth }>(`${this.baseUrl}/commissions/associates/${encodeURIComponent(associateId)}/month/${encodeURIComponent(monthKey)}`)
      .pipe(map((response) => response.month));
  }


  getCustomer(customerId: string): Observable<CustomerProfile> {
    return this.http
      .get<{ customer: Record<string, unknown> }>(`${this.baseUrl}/customers/${encodeURIComponent(customerId)}`, { headers: this.actorHeaders() })
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
        `${this.baseUrl}/customers/documents`,
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
        map((response) => this.normalizeAdminOrder(this.requireBusinessValue(response, response.order, 'No se pudo actualizar el pedido.')))
      );
  }

  listStocks(): Observable<AdminStock[]> {
    return this.http
      .get<{ stocks: AdminStock[] }>(`${this.baseUrl}/inventory/stocks`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.stocks ?? []));
  }

  listPickupStocks(): Observable<Array<{ id: string; name: string; location: string }>> {
    return this.http
      .get<{ stocks: Array<{ id: string; name: string; location: string }> }>(`${this.baseUrl}/inventory/pickup-stocks`)
      .pipe(map((response) => response.stocks ?? []));
  }

  createStock(payload: { name: string; location: string; postalCode?: string; isMainWarehouse?: boolean; allowPickup?: boolean; linkedUserIds?: number[]; inventory?: Record<number, number> }): Observable<AdminStock> {
    return this.http
      .post<{ stock: AdminStock }>(`${this.baseUrl}/inventory/stocks`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.stock));
  }

  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory' | 'allowPickup'>>): Observable<AdminStock> {
    return this.http
      .patch<{ stock: AdminStock }>(`${this.baseUrl}/inventory/stocks/${encodeURIComponent(stockId)}`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.stock));
  }

  registerStockEntry(stockId: string, payload: { productId: number; qty: number; userId?: number | null; note?: string }): Observable<{ stock: AdminStock }> {
    return this.http
      .post<{ stock?: AdminStock; message?: string; Error?: string }>(
        `${this.baseUrl}/inventory/stocks/${encodeURIComponent(stockId)}/entries`,
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
        `${this.baseUrl}/inventory/stocks/${encodeURIComponent(stockId)}/damages`,
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
      .get<{ transfers: StockTransfer[] }>(`${this.baseUrl}/inventory/stocks/transfers${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.transfers ?? []));
  }

  createStockTransfer(payload: {
    sourceStockId: string;
    destinationStockId: string;
    lines: Array<{ productId: number; qty: number }>;
    createdByUserId?: number | null;
  }): Observable<{ transfer: StockTransfer }> {
    return this.http
      .post<{ transfer?: StockTransfer; message?: string; Error?: string }>(`${this.baseUrl}/inventory/stocks/transfers`, payload, {
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
        `${this.baseUrl}/inventory/stocks/transfers/${encodeURIComponent(transferId)}/receive`,
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
      .get<{ movements: InventoryMovement[] }>(`${this.baseUrl}/inventory/stocks/movements${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.movements ?? []));
  }

  listPosSales(stockId?: string): Observable<PosSale[]> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ sales: PosSale[] }>(`${this.baseUrl}/inventory/pos/sales${query}`, { headers: this.actorHeaders() })
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
      .post<{ sale?: PosSale; message?: string; Error?: string }>(`${this.baseUrl}/inventory/pos/sales`, payload, {
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
      .get<{ control: PosCashControl }>(`${this.baseUrl}/inventory/pos/cash-control${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.control));
  }

  createPosCashCut(payload: { stockId: string }): Observable<{ cut: PosCashCut; control: PosCashControl }> {
    return this.http.post<{ cut: PosCashCut; control: PosCashControl }>(`${this.baseUrl}/inventory/pos/cash-cut`, payload, {
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
      .get<{ employees: AdminEmployee[] }>(`${this.baseUrl}/auth/employees`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.employees ?? []));
  }

  createEmployee(payload: CreateEmployeePayload): Observable<AdminEmployee> {
    return this.http
      .post<{ employee: AdminEmployee }>(`${this.baseUrl}/auth/employees`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.employee));
  }

  updateEmployee(employeeId: number, payload: Partial<Pick<AdminEmployee, 'name' | 'phone' | 'active'>>): Observable<AdminEmployee> {
    return this.http
      .patch<{ employee: AdminEmployee }>(
        `${this.baseUrl}/auth/employees/${encodeURIComponent(String(employeeId))}`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(map((response) => response.employee));
  }

  updateEmployeePrivileges(employeeId: number, payload: UpdateEmployeePrivilegesPayload): Observable<AdminEmployee> {
    return this.http
      .patch<{ employee: AdminEmployee }>(
        `${this.baseUrl}/auth/employees/${encodeURIComponent(String(employeeId))}/privileges`,
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

  changePassword(_userId: string, payload: { currentPassword: string; newPassword: string }): Observable<void> {
    return this.http
      .post<void>(
        `${this.baseUrl}/auth/changepassword`,
        payload,
        { headers: this.actorHeaders() }
      );
  }

  updateProfile(_userId: string, payload: UpdateProfilePayload): Observable<CustomerProfile> {
    return this.http
      .patch<{ customer: CustomerProfile }>(
        `${this.baseUrl}/customers/profile`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(map((response) => response.customer));
  }

  saveCampaign(payload: SaveAdminCampaignPayload): Observable<AdminCampaign> {
    return this.http
      .post<{ campaign: AdminCampaign }>(`${this.baseUrl}/dashboard/campaigns`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.campaign));
  }

  listCategories(): Observable<ProductCategory[]> {
    return this.http
      .get<{ categories: ProductCategory[] }>(`${this.baseUrl}/catalog/categories`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.categories));
  }

  getSponsorContact(sponsorId: string): Observable<SponsorContact> {
    return this.http
      .get<{ sponsor: SponsorContact }>(`${this.baseUrl}/customers/sponsor/${encodeURIComponent(sponsorId)}`)
      .pipe(map((r) => r.sponsor));
  }

  saveCategory(payload: SaveProductCategoryPayload): Observable<ProductCategory> {
    return this.http
      .post<{ category: ProductCategory }>(`${this.baseUrl}/catalog/categories`, payload, { headers: this.actorHeaders() })
      .pipe(map((r) => r.category));
  }

  deleteCategory(id: string): Observable<{ ok: boolean }> {
    return this.http
      .delete<{ ok: boolean }>(`${this.baseUrl}/catalog/categories/${id}`, { headers: this.actorHeaders() });
  }

  saveNotification(payload: SaveAdminNotificationPayload): Observable<PortalNotification> {
    return this.http
      .post<{ notification: PortalNotification }>(`${this.baseUrl}/dashboard/notifications`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.notification));
  }

  markNotificationRead(notificationId: string, payload: { customerId?: number | string } = {}): Observable<NotificationReadResponse> {
    return this.http.post<NotificationReadResponse>(
      `${this.baseUrl}/dashboard/notifications/${encodeURIComponent(notificationId)}/read`,
      payload,
      { headers: this.actorHeaders() }
    );
  }

  getBusinessConfig(): Observable<AppBusinessConfig> {
    return this.http
      .get<{ config: AppBusinessConfig }>(`${this.baseUrl}/commissions/config/app`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.config));
  }

  getPublicBusinessConfig(): Observable<AppBusinessConfig> {
    return this.http
      .get<{ config: AppBusinessConfig }>(`${this.baseUrl}/catalog/config/public`)
      .pipe(map((response) => response.config));
  }

  saveBusinessConfig(payload: UpdateBusinessConfigPayload): Observable<AppBusinessConfig> {
    return this.http
      .put<{ config: AppBusinessConfig }>(`${this.baseUrl}/commissions/config/app`, payload, { headers: this.actorHeaders() })
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

  private normalizeCustomerOrdersPage(response: {
    orders?: unknown[];
    pageSize?: number;
    count?: number;
    nextToken?: string | null;
    hasMore?: boolean;
    source?: string;
  }, fallbackPageSize: number): CustomerOrdersPage {
    const orders = this.normalizeOrders(response.orders);
    const nextToken = typeof response.nextToken === 'string' && response.nextToken.trim().length > 0
      ? response.nextToken.trim()
      : null;

    return {
      orders,
      pageSize: Number(response.pageSize ?? fallbackPageSize) || fallbackPageSize,
      count: Number(response.count ?? orders.length) || 0,
      nextToken,
      hasMore: typeof response.hasMore === 'boolean' ? response.hasMore : Boolean(nextToken),
      source: response.source
    };
  }

  private normalizeOrders(rawOrders: unknown): AdminOrder[] {
    if (!Array.isArray(rawOrders)) {
      return [];
    }

    return rawOrders.map((order) => this.normalizeAdminOrder(order));
  }

  private normalizeAdminOrder(rawOrder: unknown): AdminOrder {
    const order = this.asRecord(rawOrder) ?? {};
    const total = this.readNumber(order, ['total', 'netTotal', 'grossSubtotal']);
    const status = this.normalizeOrderStatus(this.readString(order, ['status']));
    const rawItems = Array.isArray(order['items']) ? order['items'] : [];

    return {
      id: this.readString(order, ['id', 'orderId']) || '',
      createdAt: this.readString(order, ['createdAt', 'updatedAt']) || undefined,
      customer: this.readString(order, ['customer', 'customerName']) || 'Cliente',
      grossSubtotal: this.readNumber(order, ['grossSubtotal']) || 0,
      discountRate: this.readNumber(order, ['discountRate']) || 0,
      discountAmount: this.readNumber(order, ['discountAmount']) || 0,
      netTotal: this.readNumber(order, ['netTotal']) || total,
      total,
      status,
      shippingType: this.readString(order, ['shippingType']) as AdminOrder['shippingType'] | undefined,
      trackingNumber: this.readString(order, ['trackingNumber']) || undefined,
      deliveryPlace: this.readString(order, ['deliveryPlace']) || undefined,
      deliveryDate: this.readString(order, ['deliveryDate']) || undefined,
      recipientName: this.readString(order, ['recipientName']) || undefined,
      phone: this.readString(order, ['phone']) || undefined,
      street: this.readString(order, ['street']) || undefined,
      number: this.readString(order, ['number']) || undefined,
      address: this.readString(order, ['address']) || undefined,
      city: this.readString(order, ['city']) || undefined,
      postalCode: this.readString(order, ['postalCode']) || undefined,
      state: this.readString(order, ['state']) || undefined,
      country: this.readString(order, ['country']) || undefined,
      betweenStreets: this.readString(order, ['betweenStreets']) || undefined,
      references: this.readString(order, ['references']) || undefined,
      deliveryNotes: this.readString(order, ['deliveryNotes']) || undefined,
      items: rawItems.map((item) => this.normalizeAdminOrderItem(item)),
      stockId: this.readString(order, ['stockId']) || undefined,
      attendantUserId: this.readNullableNumber(order, ['attendantUserId']),
      paymentStatus: this.readString(order, ['paymentStatus']) || undefined,
      paymentTransactionId: this.readString(order, ['paymentTransactionId', 'paymentId']) || undefined,
      paymentRawStatus: this.readString(order, ['paymentRawStatus']) || undefined,
      paymentWebhookAt: this.readString(order, ['paymentWebhookAt']) || undefined,
      paymentProvider: this.readString(order, ['paymentProvider']) || undefined,
      paymentPreferenceId: this.readString(order, ['paymentPreferenceId']) || undefined,
      paymentInitPoint: this.readString(order, ['paymentInitPoint']) || undefined,
      paymentSandboxInitPoint: this.readString(order, ['paymentSandboxInitPoint']) || undefined,
      markedByWebhook: Boolean(order['markedByWebhook']),
      discountCutoffWindow: Boolean(order['discountCutoffWindow']),
      discountCutoffCountdown: this.readString(order, ['discountCutoffCountdown']) || undefined,
      discountCutoffMessage: this.readString(order, ['discountCutoffMessage']) || undefined,
      deliveryStatus: this.readString(order, ['deliveryStatus']) || undefined,
      shippingAddressId: this.readString(order, ['shippingAddressId']) || undefined,
      shippingAddressLabel: this.readString(order, ['shippingAddressLabel']) || undefined,
      deliveryType: this.readString(order, ['deliveryType']) as AdminOrder['deliveryType'] | undefined,
      pickupStockId: this.readString(order, ['pickupStockId']) || undefined,
      pickupPaymentMethod: this.readString(order, ['pickupPaymentMethod']) as AdminOrder['pickupPaymentMethod'] | undefined,
    };
  }

  private normalizeAdminOrderItem(rawItem: unknown): AdminOrderItem {
    const item = this.asRecord(rawItem) ?? {};
    return {
      productId: Number(item['productId'] ?? 0) || 0,
      name: this.readString(item, ['name']) || 'Producto',
      price: this.readNumber(item, ['price']) || 0,
      quantity: Math.max(1, Math.trunc(this.readNumber(item, ['quantity']) || 1))
    };
  }

  private normalizeOrderStatus(rawStatus: string): AdminOrder['status'] {
    const status = rawStatus.trim().toLowerCase();
    if (status === 'canceled') {
      return 'cancelled';
    }
    if (
      status === 'pending' ||
      status === 'paid' ||
      status === 'shipped' ||
      status === 'delivered' ||
      status === 'cancelled' ||
      status === 'en_devolucion' ||
      status === 'devuelto_validado' ||
      status === 'devolucion_rechazada'
    ) {
      return status;
    }
    return 'pending';
  }

  private readString(record: Record<string, unknown>, keys: string[]): string {
    for (const key of keys) {
      const value = record[key];
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
      if (typeof value === 'number' && Number.isFinite(value)) {
        return String(value);
      }
    }
    return '';
  }

  private readNumber(record: Record<string, unknown>, keys: string[]): number {
    for (const key of keys) {
      const value = Number(record[key]);
      if (Number.isFinite(value)) {
        return value;
      }
    }
    return 0;
  }

  private readNullableNumber(record: Record<string, unknown>, keys: string[]): number | null {
    for (const key of keys) {
      if (record[key] == null || record[key] === '') {
        continue;
      }
      const value = Number(record[key]);
      if (Number.isFinite(value)) {
        return value;
      }
    }
    return null;
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
      const docType = String(raw['docType'] ?? '').trim();
      const name = String(raw['name'] ?? '').trim();
      const type = String(raw['contentType'] ?? raw['type'] ?? '').trim();
      const url = String(raw['url'] ?? '').trim();
      if (!id || !name) {
        continue;
      }
      documents.push({
        id,
        ...(assetId ? { assetId } : {}),
        ...(docType ? { docType } : {}),
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
