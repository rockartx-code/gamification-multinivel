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
  PosWithdrawal,
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
  CouponValidation,
  Coupon,
  SaveCouponPayload,
  AdminRefundPayload,
  AdminRefundResponse,
  AdminReturnInspectPayload,
  AdminReturnInspectResponse,
  OrderCancelResponse,
  OrderReturnRequestPayload,
  OrderReturnRequestResponse,
  MonthlyStatsResult
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
  DashboardCampaign,
  DashboardData,
  DashboardProduct,
  HonorBoard,
  SponsorContact,
  UserDashboardData
} from '../models/user-dashboard.model';
import type { AuthUser } from './auth.service';

function normalizeMovementType(raw: string | undefined): InventoryMovement['type'] {
  const t = (raw || 'entry').toLowerCase();
  if (t === 'damage' || t === 'damaged' || t === 'merma') return 'damaged';
  return t as InventoryMovement['type'];
}

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
    // Solo /auth/verify-email: el respaldo a /verify-email no tiene ruta en API Gateway.
    return this.http.post<VerifyEmailResponse>(`${this.baseUrl}/auth/verify-email`, { token });
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
          throw new Error(response.message ?? 'No se pudo actualizar la contraseña.');
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
      phone: raw['phone'] != null && String(raw['phone']).trim() ? String(raw['phone']).trim() : undefined,
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
      lastPurchaseAt: this.readString(raw, ['lastPurchaseAt']) || undefined,
      canAccessAdmin: Boolean(raw['canAccessAdmin']),
      privileges: (raw['privileges'] as AdminCustomer['privileges']) ?? {},
      doNotContact: Boolean(raw['doNotContact'] ?? false),
      contactNotes: Array.isArray(raw['contactNotes']) ? (raw['contactNotes'] as AdminCustomer['contactNotes']) : [],
      origin: raw['origin'] != null ? String(raw['origin']) : undefined,
      deletedAt: raw['deletedAt'] != null ? String(raw['deletedAt']) : undefined,
      mode: raw['mode'] === 'cliente' ? 'cliente' : 'socio', // paquete B
      modeActivatedAt: raw['modeActivatedAt'] != null ? String(raw['modeActivatedAt']) : undefined, // paquete B
    };
  }

  deleteCustomerData(customerId: number, reason: string): Observable<AdminCustomer> {
    return this.http
      .request<{ customer: Record<string, unknown> }>('DELETE', `${this.baseUrl}/customers/${encodeURIComponent(String(customerId))}`, {
        body: { reason },
        headers: this.actorHeaders()
      })
      .pipe(map((response) => this.normalizeAdminCustomer(response.customer)));
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

  listProducts(): Observable<{ products: AdminProduct[]; productOfMonthId: number | null }> {
    return this.http.get<{ products: Record<string, unknown>[]; productOfMonth?: Record<string, unknown> | null }>(
      `${this.baseUrl}/catalog/product`, { headers: this.actorHeaders() }
    ).pipe(map((r) => {
      const pomRaw = r.productOfMonth;
      const productOfMonthId = pomRaw != null
        ? (Number(pomRaw['productId'] ?? pomRaw['id'] ?? 0) || null)
        : null;
      return {
        products: (r.products ?? []).map((p) => this.normalizeAdminProduct(p)),
        productOfMonthId,
      };
    }));
  }

  private normalizeProductCategory(c: Record<string, unknown>): ProductCategory {
    return {
      id: String(c['categoryId'] ?? c['id'] ?? ''),
      name: String(c['name'] ?? ''),
      parentId: c['parentId'] != null ? String(c['parentId']) : null,
      position: c['position'] != null ? Number(c['position']) : 0,
      active: c['active'] !== false,
      createdAt: c['createdAt'] != null ? String(c['createdAt']) : undefined,
    };
  }

  private normalizeAdminProduct(p: Record<string, unknown>): AdminProduct {
    const tags = Array.isArray(p['tags']) ? (p['tags'] as string[]) : [];
    return {
      id: Number(p['productId'] ?? p['id'] ?? 0),
      name: String(p['name'] ?? ''),
      price: Number(p['price'] ?? 0),
      active: p['active'] !== false,
      inOnlineStore: p['inOnlineStore'] !== false,
      inPOS: p['inPOS'] !== false,
      commissionable: p['commissionable'] !== false,
      vpPoints: p['vpPoints'] != null ? Number(p['vpPoints']) : undefined,
      sku: p['sku'] != null ? String(p['sku']) : undefined,
      hook: p['hook'] != null ? String(p['hook']) : undefined,
      description: p['description'] != null ? String(p['description']) : undefined,
      copyFacebook: p['copyFacebook'] != null ? String(p['copyFacebook']) : undefined,
      copyInstagram: p['copyInstagram'] != null ? String(p['copyInstagram']) : undefined,
      copyWhatsapp: p['copyWhatsapp'] != null ? String(p['copyWhatsapp']) : undefined,
      tags: tags.length ? tags : undefined,
      images: Array.isArray(p['images']) ? (p['images'] as AdminProduct['images']) : undefined,
      variants: Array.isArray(p['variants']) ? (p['variants'] as AdminProduct['variants']) : undefined,
      categoryIds: Array.isArray(p['categoryIds']) ? (p['categoryIds'] as string[]) : undefined,
      weightKg: p['weightKg'] != null ? Number(p['weightKg']) : undefined,
      lengthCm: p['lengthCm'] != null ? Number(p['lengthCm']) : undefined,
      widthCm: p['widthCm'] != null ? Number(p['widthCm']) : undefined,
      heightCm: p['heightCm'] != null ? Number(p['heightCm']) : undefined,
    };
  }

  listCampaigns(): Observable<AdminCampaign[]> {
    return this.http.get<{ campaigns: Record<string, unknown>[] }>(`${this.baseUrl}/dashboard/campaigns`, { headers: this.actorHeaders() })
      .pipe(map((r) => (r.campaigns ?? []).map((c) => ({
        ...c,
        id: String(c['campaignId'] ?? c['id'] ?? ''),
        name: String(c['name'] ?? ''),
        active: c['active'] !== false,
        hook: String(c['hook'] ?? ''),
        story: String(c['story'] ?? ''),
        feed: String(c['feed'] ?? ''),
        banner: String(c['banner'] ?? ''),
      } as AdminCampaign))));
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
    return this.http.get<{
      products: Record<string, unknown>[];
      productOfMonth?: Record<string, unknown> | null;
      categories?: ProductCategory[];
      campaigns?: DashboardCampaign[];
    }>(
      `${this.baseUrl}/catalog/catalog`
    ).pipe(
      map((raw) => ({
        products: (raw.products ?? []).map((p) => this.normalizeDashboardProduct(p)),
        productOfMonth: raw.productOfMonth ? this.normalizeDashboardProduct(raw.productOfMonth) : null,
        categories: raw.categories ?? [],
        campaigns: raw.campaigns ?? [],
      } as CatalogData))
    );
  }

  private normalizeDashboardProduct(p: Record<string, unknown>): DashboardProduct {
    const images = Array.isArray(p['images']) ? (p['images'] as Array<{ section: string; url: string; assetId?: string }>) : [];
    const miniatura = images.find((im) => im.section === 'miniatura')?.url ?? '';
    const landing = images.find((im) => im.section === 'landing')?.url ?? '';
    const fallback = images[0]?.url ?? '';
    const tags = Array.isArray(p['tags']) ? (p['tags'] as string[]) : [];
    const variants = Array.isArray(p['variants'])
      ? (p['variants'] as Array<Record<string, unknown>>).map((v) => ({
          id: String(v['variantId'] ?? v['id'] ?? ''),
          name: String(v['name'] ?? '')
        }))
      : undefined;
    return {
      id: String(p['productId'] ?? p['id'] ?? ''),
      name: String(p['name'] ?? ''),
      price: Number(p['price'] ?? 0),
      badge: String(tags[0] ?? p['badge'] ?? ''),
      img: miniatura || landing || fallback,
      images,
      vpPoints: p['vpPoints'] != null ? Number(p['vpPoints']) : undefined,
      hook: String(p['hook'] ?? ''),
      description: p['description'] != null ? String(p['description']) : undefined,
      copyFacebook: p['copyFacebook'] != null ? String(p['copyFacebook']) : undefined,
      copyInstagram: p['copyInstagram'] != null ? String(p['copyInstagram']) : undefined,
      copyWhatsapp: p['copyWhatsapp'] != null ? String(p['copyWhatsapp']) : undefined,
      tags: tags.length ? tags : undefined,
      inOnlineStore: p['inOnlineStore'] != null ? Boolean(p['inOnlineStore']) : undefined,
      inPOS: p['inPOS'] != null ? Boolean(p['inPOS']) : undefined,
      commissionable: p['commissionable'] != null ? Boolean(p['commissionable']) : undefined,
      variants
    };
  }

  getDashboardData(): Observable<DashboardData> {
    return this.http.get<DashboardData>(`${this.baseUrl}/customers/dashboard`, { headers: this.actorHeaders() });
  }

  /**
   * @deprecated Endpoint obsoleto: usar `getCatalogData()` + `getDashboardData()`.
   *
   * El backend responde con cabeceras `Deprecation`/`Sunset` y registra cada
   * uso (`legacy_user_dashboard_hit`) para poder retirarlo con datos. Ningún
   * componente de la app lo llama ya; se conserva solo por si algún cliente
   * cacheado sigue vivo.
   */
  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    const query = userId ? `?userId=${encodeURIComponent(userId)}` : '';
    return this.http.get<UserDashboardData>(`${this.baseUrl}/user-dashboard${query}`);
  }

  getHonorBoard(month?: string): Observable<HonorBoard> {
    const qs = month ? `?month=${encodeURIComponent(month)}` : '';
    return this.http.get<HonorBoard>(`${this.baseUrl}/dashboard/honor-board${qs}`, { headers: this.actorHeaders() });
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

  revertCommissionPayment(customerId: number, monthKey: string, reason: string): Observable<{ ok: boolean; status: string }> {
    return this.http.post<{ ok: boolean; status: string }>(`${this.baseUrl}/commissions/admin/receipt/revert`, { customerId, monthKey, reason }, { headers: this.actorHeaders() });
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

  getCommissionsSummary(monthKey: string): Observable<Record<string, { customerId: string; monthKey: string; paidTotal: number; status: string; receiptUrl: string }>> {
    return this.http
      .get<{ summary: Record<string, unknown> }>(
        `${this.baseUrl}/commissions/summary?month=${encodeURIComponent(monthKey)}`,
        { headers: this.actorHeaders() }
      )
      .pipe(map((r) => (r.summary ?? {}) as Record<string, { customerId: string; monthKey: string; paidTotal: number; status: string; receiptUrl: string }>));
  }

  /** Mes contable del socio (ledger de comisiones) para el historial del panel. */
  getCommissionsLedgerMonth(associateId: string, monthKey: string): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(
      `${this.baseUrl}/commissions/associates/${encodeURIComponent(associateId)}/commissions?month=${encodeURIComponent(monthKey)}`,
      { headers: this.actorHeaders() }
    );
  }

  getAssociateMonth(associateId: string, monthKey: string): Observable<AssociateMonth> {
    return this.http
      .get<{ month: AssociateMonth }>(
        `${this.baseUrl}/commissions/associates/${encodeURIComponent(associateId)}/month/${encodeURIComponent(monthKey)}`,
        { headers: this.actorHeaders() }
      )
      .pipe(map((response) => response.month));
  }


  getCustomer(customerId: string): Observable<CustomerProfile> {
    return this.http
      .get<{ customer: Record<string, unknown> }>(`${this.baseUrl}/customers/${encodeURIComponent(customerId)}`, { headers: this.actorHeaders() })
      .pipe(map((response) => this.mapCustomerProfile(response.customer ?? {})));
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.http
      .post<{ customer: Record<string, unknown> }>(`${this.baseUrl}/customers/create`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => this.normalizeAdminCustomer(response.customer ?? {})));
  }

  createAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    return this.http.post<AssetResponse>(`${this.baseUrl}/assets`, payload, { headers: this.actorHeaders() });
  }

  createCampaignAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    return this.http.post<AssetResponse>(`${this.baseUrl}/dashboard/campaigns/assets`, payload, { headers: this.actorHeaders() });
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
    return this.http.post<ProductAssetUpload>(
      `${this.baseUrl}/catalog/product/${encodeURIComponent(String(payload.productId))}/assets`,
      payload,
      { headers: this.actorHeaders() }
    );
  }

  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse> {
    return this.http.post<ProductOfMonthResponse>(`${this.baseUrl}/catalog/product/product-of-month`, { productId }, { headers: this.actorHeaders() });
  }

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    return this.http
      .post<{ product: Record<string, unknown> }>(`${this.baseUrl}/catalog/product`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => this.normalizeAdminProduct(response.product ?? {})));
  }

  deleteProduct(productId: number): Observable<{ ok: boolean; productId: number }> {
    return this.http.post<{ ok: boolean; productId: number }>(
      `${this.baseUrl}/catalog/product/remove`,
      { productId },
      { headers: this.actorHeaders() }
    );
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
      .get<{ stocks: Record<string, unknown>[] }>(`${this.baseUrl}/inventory/stocks`, { headers: this.actorHeaders() })
      .pipe(map((response) => (response.stocks ?? []).map((s) => ({
        id: String(s['stockId'] ?? s['id'] ?? ''),
        name: String(s['name'] ?? ''),
        location: String(s['location'] ?? ''),
        postalCode: s['postalCode'] != null ? String(s['postalCode']) : undefined,
        isMainWarehouse: Boolean(s['isMainWarehouse']),
        allowPickup: Boolean(s['allowPickup']),
        linkedUserIds: Array.isArray(s['linkedUserIds']) ? (s['linkedUserIds'] as number[]) : [],
        inventory: (s['inventory'] as Record<number, number>) ?? {},
        createdAt: s['createdAt'] != null ? String(s['createdAt']) : undefined,
        updatedAt: s['updatedAt'] != null ? String(s['updatedAt']) : undefined,
      } as AdminStock))));
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

  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory' | 'allowPickup' | 'isMainWarehouse'>>): Observable<AdminStock> {
    return this.http
      .patch<{ stock: AdminStock }>(`${this.baseUrl}/inventory/stocks/${encodeURIComponent(stockId)}`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => response.stock));
  }

  registerStockEntry(stockId: string, payload: { productId: number; qty: number; userId?: number | null; note?: string }): Observable<{ ok: boolean; stock?: AdminStock }> {
    return this.http
      .post<{ ok?: boolean; stock?: AdminStock; message?: string; Error?: string }>(
        `${this.baseUrl}/inventory/stocks/${encodeURIComponent(stockId)}/entries`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => {
          if (response.Error) {
            throw new Error(response.message ?? 'No se pudo registrar la entrada de inventario.');
          }
          if (response.ok === true || response.stock) {
            return {
              ok: true,
              ...(response.stock ? { stock: response.stock } : {})
            };
          }
          throw new Error(response.message ?? 'No se pudo registrar la entrada de inventario.');
        })
      );
  }

  registerStockDamage(stockId: string, payload: { productId: number; qty: number; reason: string; userId?: number | null }): Observable<{ ok: boolean; stock?: AdminStock }> {
    return this.http
      .post<{ ok?: boolean; stock?: AdminStock; message?: string; Error?: string }>(
        `${this.baseUrl}/inventory/stocks/${encodeURIComponent(stockId)}/damages`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => {
          if (response.Error) {
            throw new Error(response.message ?? 'No se pudo registrar la merma de inventario.');
          }
          if (response.ok === true || response.stock) {
            return {
              ok: true,
              ...(response.stock ? { stock: response.stock } : {})
            };
          }
          throw new Error(response.message ?? 'No se pudo registrar la merma de inventario.');
        })
      );
  }

  listStockTransfers(stockId?: string): Observable<StockTransfer[]> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ transfers: Record<string, unknown>[] }>(`${this.baseUrl}/inventory/stocks/transfers${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => (response.transfers ?? []).map((t) => ({
        id: String(t['transferId'] ?? t['id'] ?? ''),
        sourceStockId: String(t['sourceStockId'] ?? ''),
        destinationStockId: String(t['destinationStockId'] ?? ''),
        lines: Array.isArray(t['lines']) ? (t['lines'] as Array<{ productId: number; qty: number }>) : [],
        status: (t['status'] as StockTransfer['status']) ?? 'pending',
        createdByUserId: (t['createdByUserId'] as number | null) ?? null,
        receivedByUserId: (t['receivedByUserId'] as number | null) ?? null,
        createdAt: t['createdAt'] != null ? String(t['createdAt']) : undefined,
        receivedAt: t['receivedAt'] != null ? String(t['receivedAt']) : undefined,
      } as StockTransfer))));
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

  receiveStockTransfer(transferId: string, payload: { receivedByUserId?: number | null; received?: Record<string, number> }): Observable<{ transfer: StockTransfer }> {
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
      .get<{ movements: Record<string, unknown>[] }>(`${this.baseUrl}/inventory/stocks/movements${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => (response.movements ?? []).map((m) => ({
        id: String(m['movementId'] ?? m['id'] ?? ''),
        // El backend registra las mermas como `damage`; el back office las lee como `damaged`.
        type: normalizeMovementType((m['type'] as string) ?? (m['movementType'] as string)),
        stockId: String(m['stockId'] ?? ''),
        productId: Number(m['productId'] ?? 0),
        qty: Number(m['qty'] ?? 0),
        userId: (m['userId'] as number | null) ?? null,
        userName: m['userName'] != null ? String(m['userName']) : undefined,
        paymentMethod: m['paymentMethod'] != null ? (String(m['paymentMethod']) as InventoryMovement['paymentMethod']) : undefined,
        reason: m['reason'] != null ? String(m['reason']) : undefined,
        referenceId: m['referenceId'] != null ? String(m['referenceId']) : undefined,
        createdAt: m['createdAt'] != null ? String(m['createdAt']) : undefined,
      } as InventoryMovement))));
  }

  settlePosSale(saleId: string, payload: { amount?: number; paymentMethod: 'cash' | 'card' | 'transfer' }): Observable<{ pendingAmount: number }> {
    return this.http
      .post<{ pendingAmount: number }>(`${this.baseUrl}/inventory/pos/sales/${encodeURIComponent(saleId)}/payments`, payload, { headers: this.actorHeaders() });
  }

  voidPosSale(saleId: string, reason: string): Observable<{ ok: boolean; saleId: string; orderId?: string }> {
    return this.http.post<{ ok: boolean; saleId: string; orderId?: string }>(
      `${this.baseUrl}/inventory/pos/sales/${encodeURIComponent(saleId)}/void`,
      { reason },
      { headers: this.actorHeaders() }
    );
  }

  listPosSales(stockId?: string): Observable<PosSale[]> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ sales: Record<string, unknown>[] }>(`${this.baseUrl}/inventory/pos/sales${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => (response.sales ?? []).map((s) => this.normalizePosSaleRecord(s))));
  }

  registerPosSale(payload: {
    stockId: string;
    customerId?: number | null;
    customerName?: string;
    paymentMethod?: 'cash' | 'card' | 'transfer';
    paymentStatus?: 'paid_branch';
    deliveryStatus?: 'delivered_branch';
    items: Array<Pick<AdminOrderItem, 'productId' | 'name' | 'price' | 'quantity'>>;
    cashierDiscountMode?: 'percent' | 'amount';
    cashierDiscountValue?: number;
    paymentType?: 'full' | 'partial' | 'credit';
    amountPaid?: number;
    authCode?: string;
    /** Descuento por escalón del socio, calculado igual que en la tienda en línea. */
    discountAmount?: number;
    discountRate?: number;
    /** Efectivo recibido en mostrador, solo para calcular el cambio. */
    cashReceived?: number;
  }): Observable<{ sale: PosSale }> {
    return this.http
      .post<{ sale?: Record<string, unknown>; saleId?: string; orderId?: string; message?: string; Error?: string }>(`${this.baseUrl}/inventory/pos/sales`, payload, {
        headers: this.actorHeaders()
      })
      .pipe(
        map((response) => ({ sale: this.normalizePosSaleResponse(response, payload) }))
      );
  }

  validatePosAuth(code: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(
      `${this.baseUrl}/inventory/pos/validate-auth`,
      { code },
      { headers: this.actorHeaders() }
    );
  }

  registerPosWithdrawal(payload: { stockId: string; amount: number; reason: string; authCode: string }): Observable<{ withdrawal: PosWithdrawal; control: PosCashControl }> {
    return this.http
      .post<{ withdrawal: Record<string, unknown>; control: Record<string, unknown> }>(
        `${this.baseUrl}/inventory/pos/withdrawal`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => ({
          withdrawal: this.normalizePosWithdrawal(response.withdrawal),
          control: this.normalizePosCashControl(response.control)
        }))
      );
  }

  savePosAuthCode(code: string): Observable<{ ok: boolean }> {
    return this.http.put<{ ok: boolean }>(
      `${this.baseUrl}/inventory/pos/auth-config`,
      { posAuthCode: code },
      { headers: this.actorHeaders() }
    );
  }

  listPosCashCuts(stockId?: string): Observable<PosCashCut[]> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ cuts: Record<string, unknown>[] }>(`${this.baseUrl}/inventory/pos/cash-cuts${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => (response.cuts ?? []).map((c) => this.normalizePosCashCut(c))));
  }

  getMonthlyStats(month: string): Observable<MonthlyStatsResult> {
    return this.http
      .get<MonthlyStatsResult>(`${this.baseUrl}/commissions/monthly-stats?month=${encodeURIComponent(month)}`, { headers: this.actorHeaders() });
  }

  getPosCashControl(stockId?: string): Observable<PosCashControl> {
    const query = stockId ? `?stockId=${encodeURIComponent(stockId)}` : '';
    return this.http
      .get<{ control: PosCashControl }>(`${this.baseUrl}/inventory/pos/cash-control${query}`, { headers: this.actorHeaders() })
      .pipe(map((response) => response.control));
  }

  createPosCashCut(payload: { stockId: string; cashToKeep?: number }): Observable<{ cut: PosCashCut; control: PosCashControl }> {
    return this.http
      .post<{ cut?: Record<string, unknown>; cashCut?: Record<string, unknown>; control?: Record<string, unknown> }>(
        `${this.baseUrl}/inventory/pos/cash-cut`,
        payload,
        { headers: this.actorHeaders() }
      )
      .pipe(
        map((response) => {
          const cutRaw = this.asRecord(response.cut) ?? this.asRecord(response.cashCut);
          const controlRaw = this.asRecord(response.control);
          if (!cutRaw) {
            throw new Error('No se pudo registrar el corte.');
          }
          return {
            cut: this.normalizePosCashCut(cutRaw),
            control: controlRaw
              ? this.normalizePosCashControl(controlRaw)
              : {
                  stockId: String(payload.stockId),
                  attendantUserId: null,
                  currentTotal: 0,
                  salesCount: 0,
                  cashToKeepSuggested: Number(payload.cashToKeep ?? 0),
                  lastCutAt: String(cutRaw['createdAt'] ?? ''),
                  lastCutTotal: Number(cutRaw['total'] ?? 0),
                  lastCutSalesCount: Number(cutRaw['salesCount'] ?? 0),
                  lastCutCashToKeep: Number(cutRaw['cashToKeep'] ?? 0),
                  lastCutWithdrawnAmount: Number(cutRaw['withdrawnAmount'] ?? 0),
                }
          };
        })
      );
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

  private normalizePosWithdrawal(raw: Record<string, unknown>): PosWithdrawal {
    return {
      id: String(raw['withdrawalId'] ?? raw['id'] ?? ''),
      stockId: String(raw['stockId'] ?? ''),
      attendantUserId: raw['attendantUserId'] != null ? Number(raw['attendantUserId']) : null,
      amount: Number(raw['amount'] ?? 0),
      reason: String(raw['reason'] ?? ''),
      createdAt: raw['createdAt'] != null ? String(raw['createdAt']) : undefined,
    };
  }

  private normalizePosSaleResponse(
    response: { sale?: Record<string, unknown>; saleId?: string; orderId?: string; message?: string; Error?: string },
    payload: {
      stockId: string;
      customerId?: number | null;
      customerName?: string;
      paymentMethod?: 'cash' | 'card' | 'transfer';
      paymentStatus?: 'paid_branch';
      deliveryStatus?: 'delivered_branch';
      items: Array<Pick<AdminOrderItem, 'productId' | 'name' | 'price' | 'quantity'>>;
      cashierDiscountMode?: 'percent' | 'amount';
      cashierDiscountValue?: number;
      paymentType?: 'full' | 'partial' | 'credit';
      amountPaid?: number;
      authCode?: string;
    }
  ): PosSale {
    const sale = this.asRecord(response.sale);
    if (sale) {
      return this.normalizePosSaleRecord(sale);
    }
    if (response.Error) {
      throw new Error(response.message ?? 'No se pudo registrar la venta.');
    }

    const grossSubtotal = payload.items.reduce((acc, item) => acc + Number(item.price) * Number(item.quantity), 0);
    return {
      id: String(response.saleId ?? ''),
      orderId: String(response.orderId ?? ''),
      stockId: payload.stockId,
      attendantUserId: null,
      customerId: payload.customerId ?? null,
      customerName: payload.customerName ?? 'Publico en General',
      paymentStatus: payload.paymentStatus ?? 'paid_branch',
      deliveryStatus: payload.deliveryStatus ?? 'delivered_branch',
      paymentMethod: payload.paymentMethod,
      grossSubtotal,
      discountRate: 0,
      discountAmount: 0,
      total: grossSubtotal,
      lines: payload.items.map((item) => ({ ...item })),
    };
  }

  private normalizePosSaleRecord(sale: Record<string, unknown>): PosSale {
    return {
      id: String(sale['saleId'] ?? sale['id'] ?? ''),
      orderId: String(sale['orderId'] ?? ''),
      stockId: String(sale['stockId'] ?? ''),
      attendantUserId: sale['attendantUserId'] != null ? Number(sale['attendantUserId']) : null,
      customerId: sale['customerId'] != null ? Number(sale['customerId']) : null,
      customerName: String(sale['customerName'] ?? 'Publico en General'),
      paymentStatus: (sale['paymentStatus'] as PosSale['paymentStatus']) ?? 'paid_branch',
      deliveryStatus: (sale['deliveryStatus'] as PosSale['deliveryStatus']) ?? 'delivered_branch',
      paymentMethod: sale['paymentMethod'] != null ? (String(sale['paymentMethod']) as PosSale['paymentMethod']) : undefined,
      grossSubtotal: sale['grossSubtotal'] != null ? Number(sale['grossSubtotal']) : undefined,
      discountRate: sale['discountRate'] != null ? Number(sale['discountRate']) : undefined,
      discountAmount: sale['discountAmount'] != null ? Number(sale['discountAmount']) : undefined,
      total: Number(sale['total'] ?? 0),
      lines: Array.isArray(sale['lines']) ? (sale['lines'] as AdminOrderItem[]) : [],
      createdAt: sale['createdAt'] != null ? String(sale['createdAt']) : undefined,
      cashCutId: sale['cashCutId'] != null ? String(sale['cashCutId']) : undefined,
      // Sin esto la caja seguía viendo como normales las ventas anuladas.
      status: sale['status'] != null ? String(sale['status']) : undefined,
      voidReason: sale['voidReason'] != null ? String(sale['voidReason']) : undefined,
      paymentType: sale['paymentType'] != null ? (String(sale['paymentType']) as PosSale['paymentType']) : undefined,
      amountPaid: sale['amountPaid'] != null ? Number(sale['amountPaid']) : undefined,
      pendingAmount: sale['pendingAmount'] != null ? Number(sale['pendingAmount']) : undefined,
      cashierDiscountMode: sale['cashierDiscountMode'] != null ? (String(sale['cashierDiscountMode']) as PosSale['cashierDiscountMode']) : undefined,
      cashierDiscountAmount: sale['cashierDiscountAmount'] != null ? Number(sale['cashierDiscountAmount']) : undefined,
    };
  }

  private normalizePosCashCut(cut: Record<string, unknown>): PosCashCut {
    return {
      id: String(cut['cashCutId'] ?? cut['cutId'] ?? cut['id'] ?? ''),
      stockId: String(cut['stockId'] ?? ''),
      attendantUserId: (cut['attendantUserId'] as number | null) ?? null,
      total: Number(cut['total'] ?? 0),
      salesCount: Number(cut['salesCount'] ?? 0),
      cashToKeep: cut['cashToKeep'] != null ? Number(cut['cashToKeep']) : undefined,
      withdrawnAmount: cut['withdrawnAmount'] != null ? Number(cut['withdrawnAmount']) : undefined,
      startedAt: cut['startedAt'] != null ? String(cut['startedAt']) : undefined,
      endedAt: cut['endedAt'] != null ? String(cut['endedAt']) : undefined,
      createdAt: cut['createdAt'] != null ? String(cut['createdAt']) : undefined,
      totalWithdrawals: cut['totalWithdrawals'] != null ? Number(cut['totalWithdrawals']) : undefined,
      sales: Array.isArray(cut['sales'])
        ? (cut['sales'] as Record<string, unknown>[]).map((s) => this.normalizePosSaleRecord(s))
        : undefined,
      withdrawals: Array.isArray(cut['withdrawals'])
        ? (cut['withdrawals'] as Record<string, unknown>[]).map((w) => this.normalizePosWithdrawal(w))
        : undefined,
    };
  }

  private normalizePosCashControl(control: Record<string, unknown>): PosCashControl {
    return {
      stockId: String(control['stockId'] ?? ''),
      attendantUserId: (control['attendantUserId'] as number | null) ?? null,
      currentTotal: Number(control['currentTotal'] ?? 0),
      salesCount: Number(control['salesCount'] ?? 0),
      cashToKeepSuggested: control['cashToKeepSuggested'] != null ? Number(control['cashToKeepSuggested']) : undefined,
      startedAt: control['startedAt'] != null ? String(control['startedAt']) : undefined,
      lastCutAt: control['lastCutAt'] != null ? String(control['lastCutAt']) : undefined,
      lastCutTotal: control['lastCutTotal'] != null ? Number(control['lastCutTotal']) : undefined,
      lastCutSalesCount: control['lastCutSalesCount'] != null ? Number(control['lastCutSalesCount']) : undefined,
      lastCutCashToKeep: control['lastCutCashToKeep'] != null ? Number(control['lastCutCashToKeep']) : undefined,
      lastCutWithdrawnAmount: control['lastCutWithdrawnAmount'] != null ? Number(control['lastCutWithdrawnAmount']) : undefined,
      lastSaleAt: control['lastSaleAt'] != null ? String(control['lastSaleAt']) : undefined,
    };
  }

  listEmployees(): Observable<AdminEmployee[]> {
    return this.http
      .get<{ employees: Record<string, unknown>[] }>(`${this.baseUrl}/auth/employees`, { headers: this.actorHeaders() })
      .pipe(map((response) => (response.employees ?? []).map((e) => ({
        id: Number(e['employeeId'] ?? e['id'] ?? 0),
        name: String(e['name'] ?? ''),
        email: String(e['email'] ?? ''),
        phone: e['phone'] != null ? String(e['phone']) : undefined,
        canAccessAdmin: Boolean(e['canAccessAdmin']),
        privileges: (e['privileges'] as AdminEmployee['privileges']) ?? {},
        active: e['active'] !== false,
        createdAt: e['createdAt'] != null ? String(e['createdAt']) : undefined,
      } as AdminEmployee))));
  }

  createEmployee(payload: CreateEmployeePayload): Observable<AdminEmployee> {
    return this.http
      .post<{ employee: AdminEmployee; tempPassword?: string }>(`${this.baseUrl}/auth/employees`, payload, { headers: this.actorHeaders() })
      .pipe(map((response) => ({ ...response.employee, tempPassword: response.tempPassword })));
  }

  generateEmployeePassword(employeeId: number): Observable<{ tempPassword: string }> {
    return this.http
      .post<{ tempPassword: string }>(
        `${this.baseUrl}/auth/employees/${encodeURIComponent(String(employeeId))}/reset-password`,
        {},
        { headers: this.actorHeaders() }
      );
  }

  updateEmployee(employeeId: number, payload: Partial<Pick<AdminEmployee, 'name' | 'phone' | 'active' | 'canAccessAdmin'>>): Observable<AdminEmployee> {
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
      .get<{ categories: Record<string, unknown>[] }>(`${this.baseUrl}/catalog/categories`, { headers: this.actorHeaders() })
      .pipe(map((r) => (r.categories ?? []).map((c) => this.normalizeProductCategory(c))));
  }

  getSponsorContact(sponsorId: string): Observable<SponsorContact> {
    return this.http
      .get<{ sponsor: SponsorContact }>(`${this.baseUrl}/customers/sponsor/${encodeURIComponent(sponsorId)}`)
      .pipe(map((r) => r.sponsor));
  }

  saveCategory(payload: SaveProductCategoryPayload): Observable<ProductCategory> {
    return this.http
      .post<{ category: Record<string, unknown> }>(`${this.baseUrl}/catalog/categories`, payload, { headers: this.actorHeaders() })
      .pipe(map((r) => this.normalizeProductCategory(r.category)));
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

  validateCoupon(code: string, subtotal: number, customerId?: string | number): Observable<CouponValidation> {
    return this.http.post<CouponValidation>(
      `${this.baseUrl}/orders/coupons/validate`,
      { code, subtotal, customerId },
      { headers: this.actorHeaders() }
    );
  }

  listCoupons(): Observable<Coupon[]> {
    return this.http
      .get<{ coupons: Coupon[] }>(`${this.baseUrl}/orders/coupons`, { headers: this.actorHeaders() })
      .pipe(map((r) => r.coupons ?? []));
  }

  saveCoupon(payload: SaveCouponPayload): Observable<Coupon> {
    return this.http
      .post<{ coupon: Coupon }>(`${this.baseUrl}/orders/coupons`, payload, { headers: this.actorHeaders() })
      .pipe(map((r) => r.coupon));
  }

  deleteCoupon(code: string): Observable<{ message: string; code: string }> {
    return this.http.delete<{ message: string; code: string }>(
      `${this.baseUrl}/orders/coupons/${encodeURIComponent(code)}`,
      { headers: this.actorHeaders() }
    );
  }

  getShippingQuote(payload: ShippingQuoteRequest): Observable<ShippingRate[]> {
    const normalizedPayload = this.normalizeShippingQuotePayload(payload);
    return this.http
      .post<{ rates: ShippingRate[] }>(`${this.baseUrl}/shipping/quote`, normalizedPayload)
      .pipe(map((res) => res.rates ?? []));
  }

  addOrderNote(orderId: string, text: string): Observable<AdminOrder> {
    return this.http
      .post<{ order: Record<string, unknown> }>(`${this.baseUrl}/orders/${encodeURIComponent(orderId)}/notes`, { text }, { headers: this.actorHeaders() })
      .pipe(map((r) => this.normalizeAdminOrder(r.order)));
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

  refundOrder(orderId: string, payload: AdminRefundPayload): Observable<AdminRefundResponse> {
    return this.http.post<AdminRefundResponse>(
      `${this.baseUrl}/orders/${encodeURIComponent(orderId)}/refund`,
      payload,
      { headers: this.actorHeaders() }
    );
  }

  inspectReturn(orderId: string, payload: AdminReturnInspectPayload): Observable<AdminReturnInspectResponse> {
    return this.http.post<AdminReturnInspectResponse>(
      `${this.baseUrl}/orders/${encodeURIComponent(orderId)}/return/inspect`,
      payload,
      { headers: this.actorHeaders() }
    );
  }

  public actorHeaders(): HttpHeaders {
    let headers = new HttpHeaders();
    // paquete C: sin "Recordarme" la sesión vive en sessionStorage.
    const raw = sessionStorage.getItem('auth-user') ?? localStorage.getItem('auth-user');
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
      // paquete B: ahorro como socia guardado en el pedido
      partnerMode: (this.readString(order, ['partnerMode']) || undefined) as AdminOrder['partnerMode'],
      partnerSavings: this.readNumber(order, ['partnerSavings']) || 0,
      partnerSavingsRate: this.readNumber(order, ['partnerSavingsRate']) || 0,
      partnerSavingsNextRate: this.readNumber(order, ['partnerSavingsNextRate']) || 0,
      partnerSavingsNextMissing: this.readNumber(order, ['partnerSavingsNextMissing']) || 0,
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
      paymentMethod: this.readString(order, ['paymentMethod']) as AdminOrder['paymentMethod'] | undefined,
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
      shippingCost: Number(order['shippingCost'] ?? 0) > 0 ? Number(order['shippingCost']) : undefined,
      shippingCarrier: this.readString(order, ['shippingCarrier']) || undefined,
      returnShippingCost: Number(order['returnShippingCost'] ?? 0) > 0 ? Number(order['returnShippingCost']) : undefined,
      refundAmount: order['refundAmount'] != null ? Number(order['refundAmount']) : undefined,
      refundReason: this.readString(order, ['refundReason']) || undefined,
      adminNotes: Array.isArray(order['adminNotes']) ? (order['adminNotes'] as AdminOrder['adminNotes']) : [],
      cancelReason: this.readString(order, ['cancelReason']) || undefined,
      cancelledAt: this.readString(order, ['cancelledAt']) || undefined,
      returnRequestId: this.readString(order, ['returnRequestId']) || undefined,
      returnInspection: (order['returnInspection'] as AdminOrder['returnInspection']) || undefined,
      rejectionReason: this.readString(order, ['rejectionReason']) || undefined,
      rejectedAt: this.readString(order, ['rejectedAt']) || undefined,
      refundReceiptUrl: this.readString(order, ['refundReceiptUrl']) || undefined,
      refundedAt: this.readString(order, ['refundedAt']) || undefined,
      // paquete C · factura
      invoiceRequested: Boolean(order['invoiceRequested']),
      invoiceStatus: (this.readString(order, ['invoiceStatus']) || undefined) as AdminOrder['invoiceStatus'],
      invoiceData: (order['invoiceData'] as AdminOrder['invoiceData']) || undefined,
      invoiceRequestedAt: this.readString(order, ['invoiceRequestedAt']) || undefined,
      invoiceIssuedAt: this.readString(order, ['invoiceIssuedAt']) || undefined,
      invoiceFolio: this.readString(order, ['invoiceFolio']) || undefined,
      invoiceFileUrl: this.readString(order, ['invoiceFileUrl']) || undefined,
      // ── Paquete C · ronda 26 ── desglose de IVA guardado en el pedido (§38)
      vatRate: order['vatRate'] != null ? Number(order['vatRate']) : undefined,
      taxBase: order['taxBase'] != null ? Number(order['taxBase']) : undefined,
      taxAmount: order['taxAmount'] != null ? Number(order['taxAmount']) : undefined,
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
      status === 'refunded' ||
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
