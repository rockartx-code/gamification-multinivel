import { Injectable } from '@angular/core';
import { delay, Observable, of, throwError } from 'rxjs';

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
  ProductVariant,
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
  PasswordRecoveryRequestPayload,
  PasswordRecoveryRequestResponse,
  ResetPasswordPayload,
  ResetPasswordResponse
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
import { ESTADOS_MX_CODES } from '../constants/states-mx';
import type { AuthUser } from './auth.service';
import { ALL_PRIVILEGES, normalizePrivileges } from '../models/privileges.model';

@Injectable({
  providedIn: 'root'
})
export class MockApiService {
  private businessConfig: AppBusinessConfig = {
    version: 'app-v1',
    rewards: {
      version: 'v1',
      activationNetMin: 2500,
      discountTiers: [
        { min: 3600, max: 8000, rate: 0.3 },
        { min: 8001, max: 12000, rate: 0.4 },
        { min: 12001, max: null, rate: 0.5 }
      ],
      commissionLevels: [
        { rate: 0.1, minActiveUsers: 0, minIndividualPurchase: 0, minGroupPurchase: 0 },
        { rate: 0.05, minActiveUsers: 0, minIndividualPurchase: 0, minGroupPurchase: 0 },
        { rate: 0.03, minActiveUsers: 0, minIndividualPurchase: 0, minGroupPurchase: 0 }
      ],
      payoutDay: 10,
      cutRule: 'hard_cut_no_pass'
    },
    orders: {
      requireStockOnShipped: true,
      requireDispatchLinesOnShipped: true
    },
    pos: {
      defaultCustomerName: 'Publico en General',
      defaultPaymentStatus: 'paid_branch',
      defaultDeliveryStatus: 'delivered_branch',
      orderStatusByDeliveryStatus: {
        delivered_branch: 'delivered',
        paid_branch: 'paid'
      }
    },
    stocks: {
      requireLinkedUserForTransferReceive: true
    },
    adminWarnings: {
      showCommissions: true,
      showShipping: true,
      showPendingPayments: true,
      showPendingTransfers: true,
      showPosSalesToday: true
    },
    shipping: {
      enabled: true,
      markup: 0,
      carriers: ['dhl', 'fedex']
    }
  };
  private stocks: AdminStock[] = [];
  private stockTransfers: StockTransfer[] = [];
  private inventoryMovements: InventoryMovement[] = [];
  private posSales: PosSale[] = [];
  private posCashCuts: PosCashCut[] = [];
  private associateMonths: Record<string, AssociateMonth> = {};
  private campaigns: AdminCampaign[] = [
    {
      id: 'CMP-PROGRAMA-FAMILIA',
      name: 'Programa Familia',
      active: true,
      type: 'multinivel',
      hook: 'Cuida a tu familia con bienestar que se comparte.',
      description: 'Campana de reclutamiento para el programa familiar de bienestar.',
      story: 'images/L-Programa3.png',
      feed: 'images/L-Programa3.png',
      banner: 'images/L-Programa3.png',
      heroImage: 'images/L-Programa3.png',
      heroBadge: 'Programa familiar',
      heroTitle: 'Cuida tu cuerpo.',
      heroAccent: 'Potencia tu energia.',
      heroTail: 'Compartelo.',
      heroDescription: 'Un sistema de bienestar con recompensas: mejoras tu y ayudas a otros a mejorar.',
      ctaPrimaryText: 'Obtenerlo ahora',
      ctaSecondaryText: 'Ver recompensas',
      benefits: ['Bienestar familiar', 'Descuentos por compra', 'Red activa', 'Bonos mensuales'],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    },
    {
      id: 'CMP-PROGRAMA-ENTRENADOR',
      name: 'Programa Entrenador',
      active: true,
      type: 'multinivel',
      hook: 'Potencia tu entrenamiento y comparte los resultados.',
      description: 'Campana de reclutamiento para entrenadores y deportistas.',
      story: 'images/L-Programa2.png',
      feed: 'images/L-Programa2.png',
      banner: 'images/L-Programa2.png',
      heroImage: 'images/L-Programa2.png',
      heroBadge: 'Programa entrenador',
      heroTitle: 'Cuida tu cuerpo.',
      heroAccent: 'Potencia tu energia.',
      heroTail: 'Compartelo.',
      heroDescription: 'Un sistema de bienestar con recompensas: mejoras tu y ayudas a otros a mejorar.',
      ctaPrimaryText: 'Obtenerlo ahora',
      ctaSecondaryText: 'Ver recompensas',
      benefits: ['Recuperacion activa', 'Energia sostenida', 'Red deportiva', 'Bonos mensuales'],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    },
    {
      id: 'CMP-LANZAMIENTO-ENERGIA',
      name: 'Lanzamiento Energia',
      active: true,
      type: 'producto',
      hook: 'Campana especial de energia diaria.',
      description: 'Push de conversion para nuevos registros con foco en energia.',
      story: 'images/L-Programa3.png',
      feed: 'images/L-Programa3.png',
      banner: 'images/L-Programa3.png',
      heroImage: 'images/L-Programa3.png',
      heroBadge: 'Campana del mes',
      heroTitle: 'Activa tu',
      heroAccent: 'energia',
      heroTail: 'desde hoy',
      heroDescription: 'Un empuje inicial para compartir bienestar y activar recompensas.',
      ctaPrimaryText: 'Quiero activar la campana',
      ctaSecondaryText: 'Ver recompensas',
      benefits: ['Energia diaria', 'Recuperacion', 'Red activa', 'Bonos'],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
  ];
  private categories: ProductCategory[] = [
    { id: 'suplementos', name: 'Suplementos', parentId: null, position: 0, active: true },
    { id: 'proteinas', name: 'Proteínas', parentId: 'suplementos', position: 0, active: true },
    { id: 'vitaminas', name: 'Vitaminas', parentId: 'suplementos', position: 1, active: true },
    { id: 'bienestar', name: 'Bienestar', parentId: null, position: 1, active: true },
    { id: 'articulaciones', name: 'Articulaciones', parentId: 'bienestar', position: 0, active: true },
    { id: 'energia', name: 'Energía', parentId: null, position: 2, active: true }
  ];
  private notifications: PortalNotification[] = [
    {
      id: 'NTF-BIENVENIDA',
      title: 'Capacitacion de bienvenida',
      description: 'Recuerda conectarte a la capacitacion de onboarding este martes a las 7:00 pm para revisar producto, pedidos y recompensas.',
      linkUrl: 'https://www.findingu.com.mx/#/dashboard',
      linkText: 'Ver',
      startAt: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
      endAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 5).toISOString(),
      active: true,
      status: 'active',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    },
    {
      id: 'NTF-PROXIMA-CAMPANA',
      title: 'Nueva campana programada',
      description: 'La siguiente campana de contenidos iniciara la proxima semana. Deja lista tu red para compartir los nuevos materiales.',
      startAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 2).toISOString(),
      endAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 10).toISOString(),
      active: true,
      status: 'scheduled',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
  ];
  private notificationReads: Record<string, Record<string, string>> = {
    '1': {}
  };
  private customers: AdminCustomer[] = [
    {
      id: 1,
      name: 'Ana López',
      email: 'ana@mail.com',
      leaderId: null,
      level: 'L1',
      discount: '15%',
      commissions: 320,
      commissionsPrevMonth: 180,
      commissionsPrevMonthKey: '2026-01',
      commissionsCurrentPending: 60,
      commissionsCurrentConfirmed: 120,
      commissionsPrevStatus: 'pending',
      commissionsPrevReceiptUrl: '',
      clabeInterbancaria: '012345678901234567'
    },
    {
      id: 2,
      name: 'Carlos Ruiz',
      email: 'carlos@mail.com',
      leaderId: 1,
      level: 'L2',
      discount: '10%',
      commissions: 120,
      commissionsPrevMonth: 0,
      commissionsPrevMonthKey: '2026-01',
      commissionsCurrentPending: 0,
      commissionsCurrentConfirmed: 40,
      commissionsPrevStatus: 'no_moves',
      commissionsPrevReceiptUrl: '',
      clabeInterbancaria: ''
    },
    {
      id: 3,
      name: 'María Pérez',
      email: 'maria@mail.com',
      leaderId: 2,
      level: 'L3',
      discount: '5%',
      commissions: 0,
      commissionsPrevMonth: 90,
      commissionsPrevMonthKey: '2026-01',
      commissionsCurrentPending: 0,
      commissionsCurrentConfirmed: 0,
      commissionsPrevStatus: 'paid',
      commissionsPrevReceiptUrl: 'https://example.com/recibo.pdf',
      clabeInterbancaria: '987654321098765432'
    }
  ];
  private employees: AdminEmployee[] = [
    {
      id: 10001,
      name: 'Admin Demo',
      email: 'admin@mail.com',
      canAccessAdmin: true,
      privileges: Object.fromEntries(ALL_PRIVILEGES.map((p) => [p, true])) as AdminEmployee['privileges'],
      active: true
    }
  ];
  private customerProfiles: Record<string, CustomerProfile> = {
    '1': {
      id: 1,
      name: 'Valeria Torres',
      email: 'valeria@mail.com',
      phone: '+52 555-0101',
      address: 'Av. Insurgentes 123',
      city: 'CDMX',
      state: 'CDMX',
      postalCode: '03100',
      defaultAddressId: 'addr-home',
      defaultShippingAddressId: 'addr-home',
      addresses: [
        {
          id: 'addr-home',
          label: 'Casa',
          recipientName: 'Valeria Torres',
          phone: '+52 555-0101',
          address: 'Av. Insurgentes 123',
          postalCode: '03100',
          state: 'CDMX',
          isDefault: true
        },
        {
          id: 'addr-office',
          label: 'Oficina',
          recipientName: 'Valeria Torres',
          phone: '+52 555-0101',
          address: 'Reforma 250, Piso 8',
          postalCode: '06600',
          state: 'CDMX',
          isDefault: false
        }
      ],
      shippingAddresses: [
        {
          id: 'addr-home',
          label: 'Casa',
          recipientName: 'Valeria Torres',
          phone: '+52 555-0101',
          address: 'Av. Insurgentes 123',
          postalCode: '03100',
          state: 'CDMX',
          isDefault: true
        },
        {
          id: 'addr-office',
          label: 'Oficina',
          recipientName: 'Valeria Torres',
          phone: '+52 555-0101',
          address: 'Reforma 250, Piso 8',
          postalCode: '06600',
          state: 'CDMX',
          isDefault: false
        }
      ]
    }
  };

  private readonly loginUsers = [
    {
      username: 'admin',
      password: 'admin123',
      profile: {
        userId: 'admin-001',
        name: 'Admin Rivera',
        role: 'admin' as const,
        canAccessAdmin: true,
        isSuperUser: true,
        privileges: Object.fromEntries(ALL_PRIVILEGES.map((privilege) => [privilege, true]))
      }
    },
    {
      username: 'cliente',
      password: 'cliente123',
      profile: {
        userId: '1',
        name: 'Ana López',
        role: 'cliente' as const,
        canAccessAdmin: true,
        privileges: Object.fromEntries(
          [
            'access_screen_orders',
            'access_screen_customers',
            'order_mark_paid',
            'order_mark_shipped',
            'order_mark_delivered'
          ].map((privilege) => [privilege, true])
        ),
        discountPercent: 15,
        discountActive: true
      }
    }
  ];
  private products: AdminProduct[] = [
    {
      id: 1,
      name: 'COL?GENO',
      price: 35,
      active: true,
      sku: 'COL-001',
      hook: 'Regeneraci?n diaria',
      description: 'Apoya piel, articulaciones y recuperaci?n diaria.',
      copyWhatsapp: 'Col?geno diario para piel y articulaciones. ?Te comparto el link?',
      copyInstagram: 'Col?geno diario ? Piel y articulaciones fuertes. #bienestar',
      copyFacebook: 'Col?geno diario para piel y articulaciones. Escr?beme y te paso el link.',
      tags: ['bienestar'],
      variants: [{ id: 'natural', name: 'Natural', price: 35 }, { id: 'coco', name: 'Sabor Coco', price: 38 }, { id: 'vainilla', name: 'Sabor Vainilla', price: 38 }],
      categoryIds: ['suplementos', 'articulaciones']
    },
    {
      id: 2,
      name: 'OMEGA-3',
      price: 29,
      active: true,
      sku: 'OMG-003',
      hook: 'Cuerpo & mente',
      description: 'Ayuda a coraz?n y concentraci?n con Omega-3 puro.',
      copyWhatsapp: 'Omega-3 para mente y coraz?n. ?Quieres el link?',
      copyInstagram: 'Omega-3 para mente y coraz?n. #salud',
      copyFacebook: 'Omega-3 para mente y coraz?n. Escr?beme y te paso el link.',
      tags: ['salud', 'mente'],
      variants: [{ id: 'estandar', name: 'Estándar', price: 29 }, { id: 'triple', name: 'Triple Fuerza', price: 45 }],
      categoryIds: ['suplementos', 'bienestar']
    },
    {
      id: 3,
      name: 'COMPLEJO B',
      price: 24,
      active: false,
      sku: 'CMP-010',
      hook: 'Energ?a',
      description: 'Refuerza energ?a y metabolismo diario.',
      copyWhatsapp: 'Complejo B para energ?a diaria. ?Te paso el link?',
      copyInstagram: 'Complejo B para energ?a diaria. #energia',
      copyFacebook: 'Complejo B para energ?a diaria. Escr?beme y te paso el link.',
      tags: ['energia'],
      variants: [{ id: 'normal', name: 'Normal', price: 24 }, { id: 'extra', name: 'Extra Potencia', price: 32 }],
      categoryIds: ['energia']
    }
  ];
  private productOfMonthId = 1;

  login(username: string, password: string): Observable<AuthUser> {
    const match = this.loginUsers.find((user) => user.username === username && user.password === password);
    if (!match) {
      return throwError(() => new Error('Credenciales inválidas'));
    }
    return of(match.profile).pipe(delay(120));
  }

  createAccount(payload: CreateAccountPayload): Observable<CreateAccountResponse> {
    if (!payload.name || !payload.email || !payload.password) {
      return throwError(() => new Error('Datos incompletos'));
    }
    const emailExists = this.customers.some(
      (customer) => customer.email.trim().toLowerCase() === payload.email.trim().toLowerCase()
    );
    if (emailExists) {
      return throwError(() => new Error('El correo ya está registrado. Intenta usar "recuperar contraseña".'));
    }
    if (payload.password !== payload.confirmPassword) {
      return throwError(() => new Error('Las contrase?as no coinciden'));
    }
    const customer = {
      id: Math.floor(100000 + Math.random() * 900000),
      name: payload.name,
      email: payload.email,
      leaderId: payload.referralToken ? payload.referralToken : null,
      isAssociate: true,
      discount: '0%',
      activeBuyer: false,
      discountRate: 0,
      commissions: 0
    };
    return of({ ok: true, customerId: customer.id, customer, requiresEmailVerification: true }).pipe(delay(160));
  }

  verifyEmail(_token: string): Observable<{ ok: boolean; message?: string }> {
    return of({ ok: true, message: 'Correo verificado correctamente.' }).pipe(delay(300));
  }

  requestPasswordRecovery(payload: PasswordRecoveryRequestPayload): Observable<PasswordRecoveryRequestResponse> {
    if (!payload.email?.trim()) {
      return throwError(() => new Error('Ingresa tu correo electronico.'));
    }
    return of({
      ok: true,
      message: 'Si el correo existe, te enviamos un codigo OTP para recuperar tu contrasena.'
    }).pipe(delay(140));
  }

  resetPassword(payload: ResetPasswordPayload): Observable<ResetPasswordResponse> {
    if (!payload.email?.trim() || !payload.otp?.trim() || !payload.password) {
      return throwError(() => new Error('Completa correo, OTP y nueva contrasena.'));
    }
    if (payload.password !== payload.confirmPassword) {
      return throwError(() => new Error('Las contrasenas no coinciden.'));
    }
    return of({
      ok: true,
      message: 'Contrasena actualizada correctamente.'
    }).pipe(delay(160));
  }

  getAdminData(): Observable<AdminData> {
    const payload: AdminData = {
      productOfMonthId: this.productOfMonthId,
      orders: [
        {
          id: '#1001',
          createdAt: '2026-01-16T09:35:00.000Z',
          customer: 'Ana Lopez',
          total: 120,
          status: 'pending',
          recipientName: 'Ana Lopez',
          phone: '5512345678',
          address: 'Av. Insurgentes Sur 1234, Col. Del Valle',
          postalCode: '03100',
          state: 'CDMX',
          betweenStreets: 'Entre Mier y Pesado y Gabriel Mancera',
          references: 'Edificio azul, departamento 302',
          items: [
            { productId: 1, name: 'Producto Alpha', price: 80, quantity: 1 },
            { productId: 2, name: 'Producto Beta', price: 40, quantity: 1 }
          ]
        },
        {
          id: '#1002',
          createdAt: '2026-01-16T11:20:00.000Z',
          customer: 'Carlos Ruiz',
          total: 89,
          status: 'paid',
          recipientName: 'Carlos Ruiz',
          address: 'Calle Morelos 45, Col. Centro',
          postalCode: '06010',
          state: 'CDMX',
          items: [
            { productId: 3, name: 'Producto Gamma', price: 89, quantity: 1 }
          ]
        },
        {
          id: '#1003',
          createdAt: '2026-01-15T17:05:00.000Z',
          customer: 'Maria Perez',
          total: 210,
          status: 'paid',
          recipientName: 'Maria Perez',
          address: 'Blvd. Adolfo Lopez Mateos 800, Col. San Pedro',
          postalCode: '72150',
          state: 'Puebla',
          betweenStreets: 'Entre Calle 5 de Mayo y Calle 16 de Septiembre',
          items: [
            { productId: 1, name: 'Producto Alpha', price: 80, quantity: 2 },
            { productId: 4, name: 'Producto Delta', price: 50, quantity: 1 }
          ]
        },
        {
          id: '#1004',
          createdAt: '2026-01-14T14:50:00.000Z',
          customer: 'Luis Gomez',
          total: 60,
          status: 'delivered',
          items: [
            { productId: 2, name: 'Producto Beta', price: 60, quantity: 1 }
          ]
        }
      ],
      customers: [...this.customers],
      employees: [...this.employees],
      products: [...this.products],
      campaigns: [...this.campaigns],
      categories: [...this.categories],
      notifications: this.notifications.map((notification) => this.normalizeNotification(notification)),
      businessConfig: structuredClone(this.businessConfig),
      warnings: [
        { type: 'commissions', text: '3 comisiones pendientes por depositar', severity: 'high' },
        { type: 'shipping', text: '2 pedidos pagados sin envío', severity: 'high' },
        { type: 'assets', text: 'Producto sin imagen para redes', severity: 'medium' }
      ],
      assetSlots: [
        { label: 'Miniatura (carrito)', hint: 'square 1:1' },
        { label: 'CTA / Banner', hint: 'landscape 16:9' },
        { label: 'Redes · Story', hint: '9:16' },
        { label: 'Redes · Feed', hint: '1:1' },
        { label: 'Producto del Mes', hint: 'landscape 16:9' },
        { label: 'Imagen extra', hint: 'opcional' }
      ]
    };

    return of(payload).pipe(delay(120));
  }

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    const nextId = this.products.reduce((max, product) => Math.max(max, product.id), 0) + 1;
    const existing = payload.id != null ? this.products.find((p) => p.id === payload.id) : undefined;
    const product: AdminProduct = {
      id: payload.id ?? nextId,
      name: payload.name,
      price: payload.price,
      active: payload.active,
      sku: payload.sku,
      hook: payload.hook,
      description: payload.description,
      copyFacebook: payload.copyFacebook,
      copyInstagram: payload.copyInstagram,
      copyWhatsapp: payload.copyWhatsapp,
      tags: payload.tags,
      images: payload.images,
      variants: payload.variants ?? existing?.variants ?? [],
      categoryIds: payload.categoryIds ?? existing?.categoryIds ?? []
    };
    const existingIndex = this.products.findIndex((entry) => entry.id === payload.id);
    if (existingIndex >= 0) {
      this.products[existingIndex] = product;
    } else {
      this.products = [product, ...this.products];
    }
    return of(product).pipe(delay(120));
  }

  updateOrderStatus(orderId: string, payload: UpdateOrderStatusPayload): Observable<AdminOrder> {
    const order: AdminOrder = {
      id: orderId,
      customer: 'Actualizado',
      total: 0,
      status: payload.status,
      shippingType: payload.shippingType,
      trackingNumber: payload.trackingNumber,
      deliveryPlace: payload.deliveryPlace,
      deliveryDate: payload.deliveryDate
    };
    return of(order).pipe(delay(120));
  }

  getCatalogData(): Observable<CatalogData> {
    const full = this.getMockDashboardPayload('1');
    const catalog: CatalogData = {
      products: full.products,
      featured: full.featured,
      productOfMonth: full.productOfMonth ?? null,
      campaigns: full.campaigns ?? [],
      categories: full.categories ?? [],
      config: {
        vpConfig: { mxnPerVp: 50, maxNetworkLevels: 5 },
        rankThresholds: [
          { rank: 'ORO', vg: 700 },
          { rank: 'PLATINO', vg: 2000 },
          { rank: 'DIAMANTE', vg: 5000 },
        ],
        discountTiers: [
          { min: 0, max: 999, rate: 0 },
          { min: 1000, max: 2999, rate: 0.05 },
          { min: 3000, rate: 0.10 },
        ],
      },
    };
    return of(catalog).pipe(delay(100));
  }

  getDashboardData(): Observable<DashboardData> {
    const customerKey = '1';
    const full = this.getMockDashboardPayload(customerKey);
    const customer = this.ensureCustomerProfile(customerKey);
    const dashboard: DashboardData = {
      isGuest: full.isGuest,
      settings: full.settings,
      customer: {
        id: String(customer.id),
        name: customer.name,
        phone: customer.phone,
        address: customer.address,
        city: customer.city,
        state: customer.state,
        postalCode: customer.postalCode,
        addresses: [...(customer.addresses ?? customer.shippingAddresses ?? [])],
        defaultAddressId: customer.defaultAddressId,
        shippingAddresses: [...(customer.addresses ?? customer.shippingAddresses ?? [])],
        defaultShippingAddressId: customer.defaultShippingAddressId
      },
      user: full.user,
      sponsor: full.sponsor,
      goals: full.goals,
      featured: full.featured,
      campaigns: full.campaigns,
      networkMembers: full.networkMembers,
      buyAgainIds: full.buyAgainIds,
      commissions: full.commissions,
      notifications: full.notifications ?? [],
      vp: full.vp,
      vg: full.vg,
      rank: full.rank,
      bonuses: full.bonuses ?? [],
    };
    return of(dashboard).pipe(delay(120));
  }

  getCartData(): Observable<CartData> {
    const payload: CartData = {
      countdownLabel: '3d 8h',
      shipping: 0,
      discountPct: 0.05,
      user: {
        monthSpendActual: 45,
        activeSpendTarget: 60
      },
      items: [
        {
          id: 'colageno',
          name: 'COLÁGENO',
          price: 35,
          qty: 1,
          note: 'Regeneración',
          img: 'images/L-Colageno.png',
        },
        {
          id: 'omega3',
          name: 'OMEGA-3',
          price: 29,
          qty: 2,
          note: 'Cuerpo & mente',
          img: 'images/L-Omega3.png',
        }
      ],
      suggestedItem: {
        id: 'complejoB',
        name: 'COMPLEJO B',
        price: 24,
        qty: 1,
        note: 'Energía',
        img: 'images/L-ComplejoB.png',
      }
    };

    return of(payload).pipe(delay(120));
  }

  private getMockDashboardPayload(customerKey: string): UserDashboardData {
    return {
      settings: {
        cutoffDay: 25,
        cutoffHour: 23,
        cutoffMinute: 59,
        userCode: 'ABC123',
        networkGoal: 300
      },
      user: {
        discountPercent: 15,
        discountActive: true
      },
      sponsor: {
        name: 'FindingU',
        email: 'coach@findingu.com.mx',
        phone: '+52 1 55 1498 2351',
        isDefault: true
      },
      goals: [
        {
          key: 'active',
          title: 'VP personal mínimo (usuario activo)',
          subtitle: 'Meta mensual: 50 VP',
          target: 50,
          base: 52,
          cart: 0,
          ctaText: 'Ir a tienda',
          ctaFragment: 'merchant',
          unit: 'vp' as const,
          achieved: true
        },
        {
          key: 'invite',
          title: 'Crecer tu red',
          subtitle: 'Agrega 1 usuario nuevo este mes',
          target: 1,
          base: 0,
          cart: 0,
          ctaText: 'Invitar ahora',
          ctaFragment: 'links',
          isCountGoal: true,
          unit: 'count' as const
        },
        {
          key: 'rank_oro',
          title: 'Alcanzar rango ORO',
          subtitle: 'VG mínimo para ORO: 700 VP',
          target: 700,
          base: 730,
          cart: 0,
          ctaText: 'Ver bonos ORO',
          ctaFragment: 'volumen',
          unit: 'vp' as const,
          rank: 'ORO',
          achieved: true
        },
        {
          key: 'rank_platino',
          title: 'Alcanzar rango PLATINO',
          subtitle: 'VG mínimo para PLATINO: 2,000 VP',
          target: 2000,
          base: 730,
          cart: 0,
          ctaText: 'Impulsar tu red',
          ctaFragment: 'red',
          unit: 'vp' as const,
          rank: 'PLATINO'
        },
        {
          key: 'bonus_inicio_rapido',
          title: 'Bono de Inicio Rápido',
          subtitle: 'VG de referidos directos ≥ 600 VP en primeros 30 días',
          target: 600,
          base: 160,
          cart: 0,
          ctaText: 'Invitar ahora',
          ctaFragment: 'links',
          unit: 'vp' as const,
          bonusRuleId: 'inicio_rapido'
        }
      ],
      products: [
        {
          id: 'colageno',
          name: 'COLÁGENO',
          price: 35,
          badge: 'Regeneración',
          img: 'images/L-Colageno.png',
          tags: ['bienestar'],
          variants: this.products.find((p) => p.id === 1)?.variants,
          categoryIds: this.products.find((p) => p.id === 1)?.categoryIds
        },
        {
          id: 'omega3',
          name: 'OMEGA-3',
          price: 29,
          badge: 'Cuerpo & mente',
          img: 'images/L-Omega3.png',
          tags: ['salud', 'mente'],
          variants: this.products.find((p) => p.id === 2)?.variants,
          categoryIds: this.products.find((p) => p.id === 2)?.categoryIds
        },
        {
          id: 'creatina',
          name: 'CREATINA',
          price: 27,
          badge: 'Fuerza',
          img: 'images/L-Creatina.png',
          tags: ['fuerza'],
          description: 'Potencia rendimiento y fuerza en entrenamientos diarios.',
          copyWhatsapp: 'Creatina para rendimiento diario. ¿Te paso el link?',
          copyInstagram: 'Creatina para rendimiento diario. #fuerza',
          copyFacebook: 'Creatina para rendimiento diario. Escríbeme y te paso el link.'
        },
        {
          id: 'complejoB',
          name: 'COMPLEJO B',
          price: 24,
          badge: 'Energía',
          img: 'images/L-ComplejoB.png',
          tags: ['energia'],
          variants: this.products.find((p) => p.id === 3)?.variants,
          categoryIds: this.products.find((p) => p.id === 3)?.categoryIds
        },
        {
          id: 'antioxidante',
          name: 'ANTIOXIDANTE',
          price: 31,
          badge: 'Longevidad',
          img: 'images/L-Antioxidante.png',
          tags: ['longevidad'],
          description: 'Protección antioxidante para bienestar continuo.',
          copyWhatsapp: 'Antioxidante para bienestar continuo.¿Te paso el link?',
          copyInstagram: 'Antioxidante para bienestar continuo. #longevidad',
          copyFacebook: 'Antioxidante para bienestar continuo. Escríbeme y te paso el link.'
        }
      ],
      featured: [
        {
          id: 'colageno',
          label: 'COLÁGENO',
          hook: 'Regenera. Fortalece. Perdura.',
          story: 'images/L-Colageno.png',
          feed: 'images/L-Colageno.png',
          banner: 'images/L-Colageno.png'
        },
        {
          id: 'omega3',
          label: 'OMEGA-3',
          hook: 'Cuerpo y mente, todos los días.',
          story: 'images/L-Omega3.png',
          feed: 'images/L-Omega3.png',
          banner: 'images/L-Omega3.png'
        },
        {
          id: 'creatina',
          label: 'CREATINA',
          hook: 'Potencia y rendimiento.',
          story: 'images/L-Creatina.png',
          feed: 'images/L-Creatina.png',
          banner: 'images/L-Creatina.png'
        },
        {
          id: 'antioxidante',
          label: 'ANTIOXIDANTE',
          hook: 'Brilla hoy. Longevidad mañana.',
          story: 'images/L-Antioxidante.png',
          feed: 'images/L-Antioxidante.png',
          banner: 'images/L-Antioxidante.png'
        }
      ],
      campaigns: this.campaigns
        .filter((campaign) => campaign.active)
        .map((campaign) => ({
          id: campaign.id,
          name: campaign.name,
          type: campaign.type,
          hook: campaign.hook,
          description: campaign.description,
          story: campaign.story,
          feed: campaign.feed,
          banner: campaign.banner,
          heroImage: campaign.heroImage,
          heroBadge: campaign.heroBadge,
          heroTitle: campaign.heroTitle,
          heroAccent: campaign.heroAccent,
          heroTail: campaign.heroTail,
          heroDescription: campaign.heroDescription,
          ctaPrimaryText: campaign.ctaPrimaryText,
          ctaSecondaryText: campaign.ctaSecondaryText,
          benefits: campaign.benefits ?? []
        })),
      notifications: this.buildActiveNotifications(customerKey),
      networkMembers: [
        { id: 'c-1', name: 'Mar?a G.', level: 'L1', spend: 80, status: 'Activa', leaderId: 'client-001' },
        { id: 'c-2', name: 'Luis R.', level: 'L1', spend: 25, status: 'En progreso', leaderId: 'client-001' },
        { id: 'c-3', name: 'Ana P.', level: 'L1', spend: 0, status: 'Inactiva', leaderId: 'client-001' },
        { id: 'c-4', name: 'Carlos V.', level: 'L2', spend: 40, status: 'Activa', leaderId: 'c-1' },
        { id: 'c-5', name: 'Sof?a M.', level: 'L2', spend: 15, status: 'En progreso', leaderId: 'c-2' },
        { id: 'c-6', name: 'Diego S.', level: 'L2', spend: 0, status: 'Inactiva', leaderId: 'c-2' }
      ],
      buyAgainIds: ['omega3', 'complejoB', 'antioxidante'],
      categories: this.categories.filter((c) => c.active !== false),
      honorBoard: this.getMockHonorBoard(),
      vp: 52,
      vg: 730,
      rank: 'ORO',
      bonuses: [
        {
          id: 'mock-award-1',
          ruleId: 'oro_smart_tv',
          ruleName: 'Bono ORO — Smart TV',
          customerId: 1,
          monthKey: '2026-02',
          rewardType: 'item',
          rewardItemLabel: 'Smart TV',
          status: 'pending',
          createdAt: '2026-02-28T00:00:00Z'
        }
      ],
      commissions: {
        monthKey: '2026-02',
        pendingTotal: 150,
        paidTotal: 80,
        hasPending: true,
        clabeOnFile: true,
        clabeLast4: '1234',
        prevStatus: 'paid',
        prevReceiptUrl: 'https://example.com/recibo.pdf',
        payoutDay: 10
      }
    };
  }

  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    const customerKey = this.normalizeCustomerKey(userId || '1') || '1';
    return of(this.getMockDashboardPayload(customerKey)).pipe(delay(120));
  }

  requestCommissionPayout(payload: CommissionRequestPayload): Observable<{ request: unknown; summary?: unknown }> {
    const request = {
      requestId: `req-${Math.random().toString(16).slice(2)}`,
      customerId: payload.customerId,
      monthKey: payload.monthKey ?? '2026-02',
      amount: 150,
      status: 'requested',
      clabeLast4: payload.clabe.slice(-4),
      createdAt: new Date().toISOString()
    };
    const summary = { monthKey: request.monthKey, pendingTotal: 150, paidTotal: 0, hasPending: true };
    return of({ request, summary }).pipe(delay(120));
  }

  uploadCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    const receipt = {
      receiptId: `rcpt-${Math.random().toString(16).slice(2)}`,
      customerId: payload.customerId,
      monthKey: payload.monthKey ?? '2026-02',
      assetUrl: 'images/receipt-mock.png',
      status: 'uploaded',
      createdAt: new Date().toISOString()
    };
    return of({ receipt }).pipe(delay(120));
  }

  uploadAdminCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    const receipt = {
      receiptId: `rcpt-${Math.random().toString(16).slice(2)}`,
      customerId: payload.customerId,
      monthKey: payload.monthKey ?? '2026-01',
      assetUrl: 'images/receipt-mock.png',
      status: 'paid',
      createdAt: new Date().toISOString()
    };
    return of({ receipt }).pipe(delay(120));
  }

  saveCustomerClabe(payload: CustomerClabePayload): Observable<{ ok: boolean; clabeLast4?: string }> {
    const key = this.normalizeCustomerKey(String(payload.customerId));
    if (key) {
      const profile = this.ensureCustomerProfile(key);
      profile.clabeInterbancaria = payload.clabe;
      if (payload.bankInstitution !== undefined) {
        profile.bankInstitution = payload.bankInstitution;
      }
      this.customerProfiles[key] = profile;
    }
    return of({ ok: true, clabeLast4: payload.clabe.slice(-4) }).pipe(delay(120));
  }

  uploadCustomerOwnDocument(payload: CustomerOwnDocumentPayload): Observable<CustomerProfile> {
    const key = this.normalizeCustomerKey(payload.userId) || '1';
    const profile = this.ensureCustomerProfile(key);
    const assetId = `mock-asset-${Math.random().toString(16).slice(2)}`;
    const newDoc = {
      id: `mock-own-doc-${Math.random().toString(16).slice(2)}`,
      assetId,
      name: payload.docLabel,
      type: payload.contentType,
      url: `s3://mock-bucket/${assetId}`,
      uploadedAt: new Date().toISOString(),
      docType: payload.docType
    };
    const updated: CustomerProfile = {
      ...profile,
      ownDocuments: [
        ...(profile.ownDocuments ?? []).filter((d) => (d as { docType?: string }).docType !== payload.docType),
        newDoc
      ]
    };
    this.customerProfiles[key] = updated;
    return of(updated).pipe(delay(200));
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    const total = payload.items.reduce((acc, item) => acc + item.price * item.quantity, 0);
    const customerKey = this.normalizeCustomerKey(payload.customerId);
    const trimmedAddress = payload.address?.trim() ?? '';
    const trimmedPostalCode = payload.postalCode?.trim() ?? '';
    const trimmedState = payload.state?.trim() ?? '';
    const trimmedStreet = payload.street?.trim() ?? '';
    const trimmedNumber = payload.number?.trim() ?? '';
    const trimmedCity = payload.city?.trim() ?? '';
    const trimmedCountry = payload.country?.trim() ?? '';
    const trimmedPhone = payload.phone?.trim() ?? '';
    const trimmedRecipientName = payload.recipientName?.trim() ?? payload.customerName?.trim() ?? '';
    const trimmedLabel = payload.shippingAddressLabel?.trim() ?? '';
    const shippingAddressId = payload.shippingAddressId?.trim() ?? '';

    if (customerKey && payload.saveShippingAddress && (trimmedAddress || trimmedPostalCode || trimmedState)) {
      const profile = this.ensureCustomerProfile(customerKey, payload.customerName);
      const nextAddresses = [...(profile.addresses ?? profile.shippingAddresses ?? [])];
      const existingIndex = shippingAddressId ? nextAddresses.findIndex((entry) => entry.id === shippingAddressId) : -1;
      const savedAddress: CustomerShippingAddress = {
        id: shippingAddressId || `addr-${Math.random().toString(16).slice(2, 10)}`,
        label: trimmedLabel || `Direccion ${nextAddresses.length + (existingIndex >= 0 ? 0 : 1)}`,
        recipientName: trimmedRecipientName || undefined,
        phone: trimmedPhone || undefined,
        street: trimmedStreet || undefined,
        number: trimmedNumber || undefined,
        address: trimmedAddress,
        city: trimmedCity || undefined,
        postalCode: trimmedPostalCode,
        state: trimmedState,
        country: trimmedCountry || undefined,
        isDefault: true
      };
      if (existingIndex >= 0) {
        nextAddresses[existingIndex] = savedAddress;
      } else {
        nextAddresses.unshift(savedAddress);
      }
      const normalizedAddresses = nextAddresses.map((entry) => ({
        ...entry,
        isDefault: entry.id === savedAddress.id
      }));
      profile.addresses = normalizedAddresses;
      profile.shippingAddresses = normalizedAddresses;
      profile.defaultAddressId = savedAddress.id;
      profile.defaultShippingAddressId = savedAddress.id;
      profile.phone = savedAddress.phone || profile.phone;
      profile.address = savedAddress.address || profile.address;
      profile.city = savedAddress.city || profile.city;
      profile.state = savedAddress.state || profile.state;
      profile.postalCode = savedAddress.postalCode || profile.postalCode;
      this.customerProfiles[customerKey] = profile;
    }

    const order: AdminOrder = {
      id: `#${Math.floor(1000 + Math.random() * 9000)}`,
      createdAt: new Date().toISOString(),
      customer: payload.customerName,
      grossSubtotal: total,
      discountRate: 0,
      discountAmount: 0,
      netTotal: total,
      total,
      status: payload.status,
      recipientName: payload.recipientName,
      phone: payload.phone,
      street: payload.street,
      number: payload.number,
      address: payload.address,
      city: payload.city,
      postalCode: payload.postalCode,
      state: payload.state,
      country: payload.country,
      betweenStreets: payload.betweenStreets,
      references: payload.references,
      deliveryNotes: payload.deliveryNotes,
      shippingAddressId: payload.shippingAddressId,
      shippingAddressLabel: payload.shippingAddressLabel,
      items: payload.items
    };
    return of(order).pipe(delay(120));
  }

  getOrder(orderId: string): Observable<AdminOrder> {
    const order: AdminOrder = {
      id: orderId,
      createdAt: new Date().toISOString(),
      customer: 'Cliente',
      grossSubtotal: 0,
      discountRate: 0,
      discountAmount: 0,
      netTotal: 0,
      total: 0,
      status: 'pending'
    };
    return of(order).pipe(delay(120));
  }

  createOrderCheckout(
    orderId: string,
    _payload: {
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
    const preferenceId = `MOCK-PREF-${Math.random().toString(16).slice(2, 10).toUpperCase()}`;
    return of({
      orderId,
      checkout: {
        provider: 'mercadolibre',
        preferenceId,
        initPoint: `https://www.mercadopago.com.mx/checkout/v1/redirect?pref_id=${preferenceId}`,
        sandboxInitPoint: `https://sandbox.mercadopago.com.mx/checkout/v1/redirect?pref_id=${preferenceId}`,
        externalReference: orderId
      }
    }).pipe(delay(120));
  }

  getOrderStatus(orderOrPaymentId: string): Observable<OrderStatusLookup> {
    const payload: OrderStatusLookup = {
      orderId: orderOrPaymentId,
      status: 'pending',
      paymentStatus: 'mercadolibre_pending',
      paymentTransactionId: orderOrPaymentId,
      paymentRawStatus: 'pending',
      markedByWebhook: false
    };
    return of(payload).pipe(delay(120));
  }

  getAssociateMonth(associateId: string, monthKey: string): Observable<AssociateMonth> {
    return of(
      structuredClone(
        this.associateMonths[this.monthStateKey(associateId, monthKey)] ?? {
          associateId,
          monthKey,
          netVolume: 0,
          isActive: false
        }
      )
    ).pipe(delay(120));
  }

  getAdminOrders(params: { status?: AdminOrder['status']; limit?: number } = {}): Observable<{ orders: AdminOrder[]; total: number }> {
    return of({ orders: [], total: 0 }).pipe(delay(80));
  }

  getAdminWarnings(): Observable<{ type: string; text: string; severity: string }[]> {
    return of([]).pipe(delay(80));
  }

  listCustomers(): Observable<AdminCustomer[]> {
    return of(this.customers ?? []).pipe(delay(120));
  }

  listProducts(): Observable<AdminProduct[]> {
    return of(this.products ?? []).pipe(delay(120));
  }

  listCampaigns(): Observable<AdminCampaign[]> {
    return of(this.campaigns ?? []).pipe(delay(120));
  }

  listAdminNotifications(): Observable<PortalNotification[]> {
    return of(this.notifications ?? []).pipe(delay(120));
  }

  getOrders(customerId: string, params: { limit?: number; nextToken?: string } = {}): Observable<CustomerOrdersPage> {
    const pageSize = Math.max(1, Number(params.limit) || 10);
    const page = Math.max(0, Number(params.nextToken ?? 0) || 0);
    const orders: AdminOrder[] = [
      {
        id: `#${Math.floor(1000 + Math.random() * 9000)}`,
        createdAt: new Date().toISOString(),
        customer: `Cliente ${customerId}`,
        grossSubtotal: 0,
        discountRate: 0,
        discountAmount: 0,
        netTotal: 0,
        total: 0,
        status: 'pending'
      }
    ];
    return of({
      orders,
      pageSize,
      count: orders.length,
      nextToken: page < 2 ? String(page + 1) : null,
      hasMore: page < 2
    }).pipe(delay(120));
  }

  getCustomer(customerId: string): Observable<CustomerProfile> {
    const customer = this.ensureCustomerProfile(this.normalizeCustomerKey(customerId) || '1');
    return of(customer).pipe(delay(120));
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    const customer: AdminCustomer = {
      id: Math.floor(100000 + Math.random() * 900000),
      name: payload.name,
      email: payload.email,
      leaderId: payload.leaderId ?? null,
      level: 'L1',
      discount: '0%',
      commissions: 0
    };
    this.customers = [customer, ...this.customers];
    return of(customer).pipe(delay(120));
  }

  createAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    const now = new Date().toISOString();
    const assetId = `mock-asset-${Math.random().toString(16).slice(2)}`;
    const response: AssetResponse = {
      asset: {
        assetId,
        name: payload.name,
        contentType: payload.contentType ?? 'application/octet-stream',
        url: `s3://mock-bucket/${assetId}`,
        createdAt: now,
        updatedAt: now
      }
    };
    return of(response).pipe(delay(120));
  }

  addCustomerDocument(customerId: string, payload: LinkCustomerDocumentPayload): Observable<CustomerProfile> {
    const profile = this.ensureCustomerProfile(this.normalizeCustomerKey(customerId) || '1');
    const assetId = String(payload.assetId ?? '').trim();
    if (!assetId) {
      return throwError(() => new Error('Asset invalido.'));
    }

    const name = String(payload.name ?? '').trim() || `Documento ${(profile.documents?.length ?? 0) + 1}`;
    const now = new Date().toISOString();
    const nextDocument = {
      id: `mock-doc-${Math.random().toString(16).slice(2)}`,
      assetId,
      name,
      type: 'application/pdf',
      url: `s3://mock-bucket/${assetId}`,
      uploadedAt: now
    };
    const updated: CustomerProfile = {
      ...profile,
      documents: [...(profile.documents ?? []), nextDocument],
      addresses: [...(profile.addresses ?? profile.shippingAddresses ?? [])],
      shippingAddresses: [...(profile.addresses ?? profile.shippingAddresses ?? [])]
    };
    this.customerProfiles[this.normalizeCustomerKey(customerId) || '1'] = updated;
    return of(updated).pipe(delay(120));
  }

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    const now = new Date().toISOString();
    const assetId = `mock-${Math.random().toString(16).slice(2)}`;
    const response: ProductAssetUpload = {
      asset: {
        assetId,
        bucket: 'mock-bucket',
        key: `products/${payload.productId}/${payload.section}/${assetId}/${payload.filename}`,
        ownerType: 'product',
        ownerId: payload.productId,
        section: payload.section,
        contentType: payload.contentType ?? 'application/octet-stream',
        createdAt: now,
        updatedAt: now
      }
    };
    return of(response).pipe(delay(120));
  }
 
  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse> {
    this.productOfMonthId = productId;
    return of({
      productOfMonth: {
        productId
      }
    }).pipe(delay(120));
  }

  listStocks(): Observable<AdminStock[]> {
    return of([...this.stocks]).pipe(delay(120));
  }

  listPickupStocks(): Observable<Array<{ id: string; name: string; location: string }>> {
    const rows = this.stocks
      .filter((stock) => stock.allowPickup)
      .map((stock) => ({ id: stock.id, name: stock.name, location: stock.location }));
    return of(rows).pipe(delay(120));
  }

  createStock(payload: { name: string; location: string; postalCode?: string; isMainWarehouse?: boolean; allowPickup?: boolean; linkedUserIds?: number[]; inventory?: Record<number, number> }): Observable<AdminStock> {
    const stock: AdminStock = {
      id: `STK-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
      name: payload.name,
      location: payload.location,
      linkedUserIds: payload.linkedUserIds ?? [],
      inventory: payload.inventory ?? {},
      allowPickup: payload.allowPickup ?? false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    this.stocks = [stock, ...this.stocks];
    return of(stock).pipe(delay(120));
  }

  updateStock(stockId: string, payload: Partial<Pick<AdminStock, 'name' | 'location' | 'linkedUserIds' | 'inventory' | 'allowPickup'>>): Observable<AdminStock> {
    const current = this.stocks.find((stock) => stock.id === stockId);
    if (!current) {
      throw new Error('Stock no encontrado');
    }
    const updated: AdminStock = {
      ...current,
      ...payload,
      updatedAt: new Date().toISOString()
    };
    this.stocks = this.stocks.map((stock) => (stock.id === stockId ? updated : stock));
    return of(updated).pipe(delay(120));
  }

  registerStockEntry(stockId: string, payload: { productId: number; qty: number; userId?: number | null; note?: string }): Observable<{ stock: AdminStock }> {
    const stock = this.stocks.find((entry) => entry.id === stockId);
    if (!stock) {
      throw new Error('Stock no encontrado');
    }
    const nextInventory = { ...(stock.inventory as Record<number, number>) };
    nextInventory[payload.productId] = (nextInventory[payload.productId] ?? 0) + payload.qty;
    const updated = { ...stock, inventory: nextInventory, updatedAt: new Date().toISOString() };
    this.stocks = this.stocks.map((entry) => (entry.id === stockId ? updated : entry));
    this.inventoryMovements = [
      {
        id: `MOV-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
        type: 'entry',
        stockId,
        productId: payload.productId,
        qty: payload.qty,
        userId: payload.userId ?? null,
        reason: payload.note,
        createdAt: new Date().toISOString()
      },
      ...this.inventoryMovements
    ];
    return of({ stock: updated }).pipe(delay(120));
  }

  registerStockDamage(stockId: string, payload: { productId: number; qty: number; reason: string; userId?: number | null }): Observable<{ stock: AdminStock }> {
    const stock = this.stocks.find((entry) => entry.id === stockId);
    if (!stock) {
      throw new Error('Stock no encontrado');
    }
    const nextInventory = { ...(stock.inventory as Record<number, number>) };
    nextInventory[payload.productId] = Math.max(0, (nextInventory[payload.productId] ?? 0) - payload.qty);
    const updated = { ...stock, inventory: nextInventory, updatedAt: new Date().toISOString() };
    this.stocks = this.stocks.map((entry) => (entry.id === stockId ? updated : entry));
    this.inventoryMovements = [
      {
        id: `MOV-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
        type: 'damaged',
        stockId,
        productId: payload.productId,
        qty: payload.qty,
        userId: payload.userId ?? null,
        reason: payload.reason,
        createdAt: new Date().toISOString()
      },
      ...this.inventoryMovements
    ];
    return of({ stock: updated }).pipe(delay(120));
  }

  listStockTransfers(stockId?: string): Observable<StockTransfer[]> {
    const rows = stockId
      ? this.stockTransfers.filter((transfer) => transfer.sourceStockId === stockId || transfer.destinationStockId === stockId)
      : this.stockTransfers;
    return of([...rows]).pipe(delay(120));
  }

  createStockTransfer(payload: {
    sourceStockId: string;
    destinationStockId: string;
    lines: Array<{ productId: number; qty: number }>;
    createdByUserId?: number | null;
  }): Observable<{ transfer: StockTransfer }> {
    const transfer: StockTransfer = {
      id: `TRF-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
      sourceStockId: payload.sourceStockId,
      destinationStockId: payload.destinationStockId,
      lines: payload.lines,
      status: 'pending',
      createdByUserId: payload.createdByUserId ?? null,
      createdAt: new Date().toISOString()
    };
    this.stockTransfers = [transfer, ...this.stockTransfers];
    return of({ transfer }).pipe(delay(120));
  }

  receiveStockTransfer(transferId: string, payload: { receivedByUserId?: number | null }): Observable<{ transfer: StockTransfer }> {
    const transfer = this.stockTransfers.find((item) => item.id === transferId);
    if (!transfer) {
      throw new Error('Transferencia no encontrada');
    }
    const updated: StockTransfer = {
      ...transfer,
      status: 'received',
      receivedByUserId: payload.receivedByUserId ?? null,
      receivedAt: new Date().toISOString()
    };
    this.stockTransfers = this.stockTransfers.map((item) => (item.id === transferId ? updated : item));
    return of({ transfer: updated }).pipe(delay(120));
  }

  listInventoryMovements(stockId?: string): Observable<InventoryMovement[]> {
    const rows = stockId ? this.inventoryMovements.filter((movement) => movement.stockId === stockId) : this.inventoryMovements;
    return of([...rows]).pipe(delay(120));
  }

  listPosSales(stockId?: string): Observable<PosSale[]> {
    const rows = stockId ? this.posSales.filter((sale) => sale.stockId === stockId) : this.posSales;
    return of([...rows]).pipe(delay(120));
  }

  registerPosSale(payload: {
    stockId: string;
    customerId?: number | null;
    customerName?: string;
    paymentStatus?: 'paid_branch';
    deliveryStatus?: 'delivered_branch';
    items: Array<Pick<AdminOrderItem, 'productId' | 'name' | 'price' | 'quantity'>>;
  }): Observable<{ sale: PosSale }> {
    const actorId = this.currentActorId();
    if (!actorId) {
      return throwError(() => new Error('Se requiere un usuario logeado para operar POS'));
    }
    const stock = this.stocks.find((entry) => entry.id === payload.stockId && entry.linkedUserIds.includes(actorId));
    if (!stock) {
      return throwError(() => new Error('El stock no esta vinculado al usuario logeado'));
    }

    const customer = payload.customerId != null ? this.customers.find((entry) => entry.id === payload.customerId) ?? null : null;
    if (payload.customerId != null && !customer) {
      return throwError(() => new Error('Cliente no encontrado'));
    }

    const grossSubtotal = payload.items.reduce((acc, item) => acc + item.price * item.quantity, 0);
    const monthKey = this.monthKeyNow();
    const monthState =
      customer != null
        ? this.associateMonths[this.monthStateKey(customer.id, monthKey)] ?? {
            associateId: String(customer.id),
            monthKey,
            netVolume: 0,
            isActive: false
          }
        : null;
    const projectedRate = customer ? this.calculateDiscountRate((monthState?.netVolume ?? 0) + grossSubtotal) : 0;
    const discountRate = customer ? Math.max(this.parseDiscountRate(customer.discount), projectedRate) : 0;
    const discountAmount = grossSubtotal * discountRate;
    const total = grossSubtotal - discountAmount;

    const nextInventory = { ...(stock.inventory as Record<number, number>) };
    for (const item of payload.items) {
      const currentQty = Number(nextInventory[item.productId] ?? 0);
      if (currentQty < item.quantity) {
        return throwError(() => new Error(`Stock insuficiente para ${item.name}`));
      }
      nextInventory[item.productId] = currentQty - item.quantity;
    }
    this.stocks = this.stocks.map((entry) =>
      entry.id === stock.id
        ? {
            ...entry,
            inventory: nextInventory,
            updatedAt: new Date().toISOString()
          }
        : entry
    );

    const sale: PosSale = {
      id: `SALE-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
      orderId: `POS-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
      stockId: payload.stockId,
      attendantUserId: actorId,
      customerId: customer?.id ?? null,
      customerName: customer?.name || payload.customerName || 'Publico en General',
      paymentStatus: payload.paymentStatus ?? 'paid_branch',
      deliveryStatus: payload.deliveryStatus ?? 'delivered_branch',
      grossSubtotal,
      discountRate,
      discountAmount,
      total,
      lines: payload.items.map((item) => ({ ...item })),
      createdAt: new Date().toISOString()
    };
    this.inventoryMovements = [
      ...payload.items.map((item) => ({
        id: `MOV-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
        type: 'pos_sale' as const,
        stockId: payload.stockId,
        productId: item.productId,
        qty: item.quantity,
        userId: actorId,
        referenceId: sale.orderId,
        createdAt: sale.createdAt
      })),
      ...this.inventoryMovements
    ];
    this.posSales = [sale, ...this.posSales];
    if (customer && monthState) {
      const netVolume = monthState.netVolume + grossSubtotal;
      this.associateMonths[this.monthStateKey(customer.id, monthKey)] = {
        associateId: String(customer.id),
        monthKey,
        netVolume,
        isActive: netVolume >= this.businessConfig.rewards.activationNetMin
      };
      this.customers = this.customers.map((entry) =>
        entry.id === customer.id
          ? {
              ...entry,
              discount: `${Math.round(discountRate * 100)}%`
            }
          : entry
      );
    }
    return of({ sale }).pipe(delay(120));
  }

  getPosCashControl(stockId?: string): Observable<PosCashControl> {
    const actorId = this.currentActorId();
    if (!actorId) {
      return throwError(() => new Error('Se requiere un usuario logeado para operar POS'));
    }
    const control = this.buildPosCashControl(stockId, actorId);
    if (!control) {
      return throwError(() => new Error('El usuario logeado no tiene un stock vinculado'));
    }
    return of(control).pipe(delay(120));
  }

  createPosCashCut(payload: { stockId: string }): Observable<{ cut: PosCashCut; control: PosCashControl }> {
    const actorId = this.currentActorId();
    if (!actorId) {
      return throwError(() => new Error('Se requiere un usuario logeado para operar POS'));
    }
    const control = this.buildPosCashControl(payload.stockId, actorId);
    if (!control) {
      return throwError(() => new Error('El usuario logeado no tiene un stock vinculado'));
    }
    if (control.salesCount <= 0 || control.currentTotal <= 0) {
      return throwError(() => new Error('No hay ventas pendientes para corte'));
    }
    const now = new Date().toISOString();
    const cut: PosCashCut = {
      id: `CUT-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
      stockId: control.stockId,
      attendantUserId: actorId,
      total: control.currentTotal,
      salesCount: control.salesCount,
      startedAt: control.startedAt,
      endedAt: now,
      createdAt: now
    };
    this.posCashCuts = [cut, ...this.posCashCuts];
    return of({
      cut,
      control: this.buildPosCashControl(payload.stockId, actorId) ?? {
        stockId: payload.stockId,
        attendantUserId: actorId,
        currentTotal: 0,
        salesCount: 0
      }
    }).pipe(delay(120));
  }

  updateCustomerPrivileges(customerId: number, payload: UpdateCustomerPrivilegesPayload): Observable<AdminCustomer> {
    const customer = this.customers.find((entry) => entry.id === customerId);
    if (!customer) {
      return throwError(() => new Error('Cliente no encontrado'));
    }
    return of({ ...customer }).pipe(delay(120));
  }

  listEmployees(): Observable<AdminEmployee[]> {
    return of([...this.employees]).pipe(delay(100));
  }

  createEmployee(payload: CreateEmployeePayload): Observable<AdminEmployee> {
    const emp: AdminEmployee = {
      id: Math.floor(100000 + Math.random() * 900000),
      name: payload.name,
      email: payload.email,
      phone: payload.phone,
      canAccessAdmin: payload.canAccessAdmin ?? true,
      privileges: normalizePrivileges(payload.privileges),
      active: true,
      tempPassword: 'TempPass123'
    };
    this.employees = [emp, ...this.employees];
    return of({ ...emp }).pipe(delay(120));
  }

  updateEmployee(employeeId: number, payload: Partial<Pick<AdminEmployee, 'name' | 'phone' | 'active'>>): Observable<AdminEmployee> {
    const emp = this.employees.find((e) => e.id === employeeId);
    if (!emp) {
      return throwError(() => new Error('Empleado no encontrado'));
    }
    const updated: AdminEmployee = { ...emp, ...payload };
    this.employees = this.employees.map((e) => (e.id === employeeId ? updated : e));
    return of(updated).pipe(delay(120));
  }

  updateEmployeePrivileges(employeeId: number, payload: UpdateEmployeePrivilegesPayload): Observable<AdminEmployee> {
    const emp = this.employees.find((e) => e.id === employeeId);
    if (!emp) {
      return throwError(() => new Error('Empleado no encontrado'));
    }
    const updated: AdminEmployee = {
      ...emp,
      canAccessAdmin: payload.canAccessAdmin ?? emp.canAccessAdmin,
      privileges: normalizePrivileges(payload.privileges ?? emp.privileges)
    };
    this.employees = this.employees.map((e) => (e.id === employeeId ? updated : e));
    return of(updated).pipe(delay(120));
  }

  changePassword(_userId: string, payload: { currentPassword: string; newPassword: string }): Observable<void> {
    if (!payload.currentPassword) {
      return throwError(() => ({ error: { message: 'La contraseña actual es requerida.' } }));
    }
    if (!payload.newPassword || payload.newPassword.length < 8) {
      return throwError(() => ({ error: { message: 'La nueva contraseña debe tener al menos 8 caracteres.' } }));
    }
    return of(undefined as void).pipe(delay(300));
  }

  updateProfile(userId: string, payload: UpdateProfilePayload): Observable<CustomerProfile> {
    const key = this.normalizeCustomerKey(userId) || '1';
    const profile = this.ensureCustomerProfile(key);
    const updated: CustomerProfile = {
      ...profile,
      name: payload.name ?? profile.name,
      phone: payload.phone ?? profile.phone,
      rfc: payload.rfc ?? profile.rfc,
      curp: payload.curp ?? profile.curp
    };
    this.customerProfiles[key] = updated;
    return of({ ...updated }).pipe(delay(120));
  }

  updateCustomer(customerId: number, payload: UpdateCustomerPayload): Observable<AdminCustomer> {
    const customer = this.customers.find((entry) => entry.id === customerId);
    if (!customer) {
      return throwError(() => new Error('Cliente no encontrado'));
    }
    const updated: AdminCustomer = {
      ...customer,
      leaderId: payload.leaderId !== undefined ? payload.leaderId : customer.leaderId,
      level: payload.level !== undefined ? payload.level : customer.level
    };
    this.customers = this.customers.map((entry) => (entry.id === customerId ? updated : entry));
    return of(updated).pipe(delay(120));
  }

  private ensureCustomerProfile(customerId: number | string, customerName = 'Valeria Torres'): CustomerProfile {
    const key = this.normalizeCustomerKey(customerId) || '1';
    const existing = this.customerProfiles[key];
    if (existing) {
      return {
        ...existing,
        addresses: [...(existing.addresses ?? existing.shippingAddresses ?? [])],
        shippingAddresses: [...(existing.addresses ?? existing.shippingAddresses ?? [])]
      };
    }
    const numericCustomerId = Number(key);
    const profile: CustomerProfile = {
      id: Number.isFinite(numericCustomerId) ? numericCustomerId : key,
      name: customerName,
      email: `${key}@mail.com`,
      phone: '',
      rfc: '',
      curp: '',
      clabeInterbancaria: '',
      documents: [],
      addresses: [],
      shippingAddresses: []
    };
    this.customerProfiles[key] = profile;
    return { ...profile, addresses: [], shippingAddresses: [] };
  }

  private normalizeCustomerKey(customerId: number | string | null | undefined): string {
    const raw = String(customerId ?? '').trim();
    if (!raw || raw === '0' || raw.toLowerCase() === 'nan') {
      return '';
    }
    return raw;
  }

  private currentActorId(): number | null {
    const raw = localStorage.getItem('auth-user');
    if (!raw) {
      return null;
    }
    try {
      const user = JSON.parse(raw) as { userId?: string | number };
      const parsed = Number(user.userId);
      return Number.isFinite(parsed) ? parsed : null;
    } catch {
      return null;
    }
  }

  private monthKeyNow(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }

  private monthStateKey(associateId: number | string, monthKey: string): string {
    return `${associateId}#${monthKey}`;
  }

  private calculateDiscountRate(volume: number): number {
    for (const tier of this.businessConfig.rewards.discountTiers) {
      const min = Number(tier.min ?? 0);
      const max = tier.max == null ? null : Number(tier.max);
      const rate = Number(tier.rate ?? 0);
      if (volume >= min && (max == null || volume <= max)) {
        return Number.isFinite(rate) ? rate : 0;
      }
    }
    return 0;
  }

  private parseDiscountRate(label: string | undefined): number {
    const match = String(label ?? '').match(/(\d+(?:\.\d+)?)\s*%/);
    if (!match) {
      return 0;
    }
    const value = Number(match[1]);
    return Number.isFinite(value) ? value / 100 : 0;
  }

  private buildPosCashControl(stockId: string | undefined, actorId: number): PosCashControl | null {
    const linkedStocks = this.stocks.filter((entry) => entry.linkedUserIds.includes(actorId));
    const selectedStock = linkedStocks.find((entry) => entry.id === stockId) ?? linkedStocks[0];
    if (!selectedStock) {
      return null;
    }
    const lastCut = this.posCashCuts.find((entry) => entry.stockId === selectedStock.id && entry.attendantUserId === actorId);
    const relevantSales = this.posSales
      .filter(
        (entry) =>
          entry.stockId === selectedStock.id &&
          entry.attendantUserId === actorId &&
          (!lastCut?.createdAt || String(entry.createdAt ?? '') > String(lastCut.createdAt))
      )
      .sort((a, b) => String(a.createdAt ?? '').localeCompare(String(b.createdAt ?? '')));
    return {
      stockId: selectedStock.id,
      attendantUserId: actorId,
      currentTotal: relevantSales.reduce((acc, entry) => acc + entry.total, 0),
      salesCount: relevantSales.length,
      startedAt: relevantSales[0]?.createdAt ?? lastCut?.createdAt,
      lastCutAt: lastCut?.createdAt,
      lastCutTotal: lastCut?.total ?? 0,
      lastCutSalesCount: lastCut?.salesCount ?? 0,
      lastSaleAt: relevantSales.at(-1)?.createdAt
    };
  }

  private buildActiveNotifications(customerKey: string): PortalNotification[] {
    const reads = this.notificationReads[customerKey] ?? {};
    return this.notifications
      .map((notification) => this.normalizeNotification(notification))
      .filter((notification) => notification.status === 'active')
      .map((notification) => ({
        ...notification,
        isRead: Boolean(reads[notification.id]),
        readAt: reads[notification.id] ?? ''
      }));
  }

  private normalizeNotification(notification: PortalNotification): PortalNotification {
    return {
      ...notification,
      linkText: notification.linkUrl ? notification.linkText || 'Ver' : '',
      status: this.resolveNotificationStatus(notification)
    };
  }

  private resolveNotificationStatus(notification: PortalNotification): PortalNotification['status'] {
    if (!notification.active) {
      return 'inactive';
    }
    const now = Date.now();
    const start = notification.startAt ? new Date(notification.startAt).getTime() : 0;
    const end = notification.endAt ? new Date(notification.endAt).getTime() : 0;
    if (start && start > now) {
      return 'scheduled';
    }
    if (end && end < now) {
      return 'expired';
    }
    return 'active';
  }

  saveCampaign(payload: SaveAdminCampaignPayload): Observable<AdminCampaign> {
    const now = new Date().toISOString();
    const existing = payload.id ? this.campaigns.find((entry) => entry.id === payload.id) : null;
    const campaign: AdminCampaign = {
      id: payload.id || `CMP-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
      name: payload.name,
      active: payload.active,
      type: payload.type ?? 'multinivel',
      hook: payload.hook,
      description: payload.description,
      story: payload.story,
      feed: payload.feed,
      banner: payload.banner,
      heroImage: payload.heroImage,
      heroBadge: payload.heroBadge,
      heroTitle: payload.heroTitle,
      heroAccent: payload.heroAccent,
      heroTail: payload.heroTail,
      heroDescription: payload.heroDescription,
      ctaPrimaryText: payload.ctaPrimaryText,
      ctaSecondaryText: payload.ctaSecondaryText,
      benefits: payload.benefits ?? [],
      createdAt: existing?.createdAt ?? now,
      updatedAt: now
    };
    this.campaigns = existing
      ? this.campaigns.map((entry) => (entry.id === campaign.id ? campaign : entry))
      : [campaign, ...this.campaigns];
    return of(campaign).pipe(delay(120));
  }

  saveNotification(payload: SaveAdminNotificationPayload): Observable<PortalNotification> {
    const now = new Date().toISOString();
    const existing = payload.id ? this.notifications.find((entry) => entry.id === payload.id) : null;
    const notification: PortalNotification = this.normalizeNotification({
      id: payload.id || `NTF-${Math.random().toString(16).slice(2, 10).toUpperCase()}`,
      title: payload.title,
      description: payload.description.slice(0, 300),
      linkUrl: payload.linkUrl?.trim() || '',
      linkText: payload.linkUrl?.trim() ? payload.linkText?.trim() || 'Ver' : '',
      startAt: payload.startAt,
      endAt: payload.endAt,
      active: payload.active,
      createdAt: existing?.createdAt ?? now,
      updatedAt: now
    });
    this.notifications = existing
      ? this.notifications.map((entry) => (entry.id === notification.id ? notification : entry))
      : [notification, ...this.notifications];
    this.notifications.sort((a, b) => String(b.startAt ?? '').localeCompare(String(a.startAt ?? '')));
    return of(notification).pipe(delay(120));
  }

  markNotificationRead(notificationId: string, payload: { customerId?: number | string } = {}): Observable<NotificationReadResponse> {
    const customerKey = this.normalizeCustomerKey(payload.customerId || '1') || '1';
    const readAt = new Date().toISOString();
    const reads = this.notificationReads[customerKey] ?? {};
    reads[notificationId] = reads[notificationId] || readAt;
    this.notificationReads[customerKey] = reads;
    return of({
      ok: true,
      notificationId,
      customerId: customerKey,
      readAt: reads[notificationId]
    }).pipe(delay(120));
  }

  getBusinessConfig(): Observable<AppBusinessConfig> {
    return of(structuredClone(this.businessConfig)).pipe(delay(120));
  }

  getPublicBusinessConfig(): Observable<AppBusinessConfig> {
    // Returns same structure but only the rewards/bonuses slice (matches /catalog/config/public backend shape)
    const cfg = structuredClone(this.businessConfig);
    const publicCfg: AppBusinessConfig = {
      ...cfg,
      bonuses: cfg.bonuses ? {
        ...cfg.bonuses,
        rules: cfg.bonuses.rules.filter((r: import('../models/admin.model').BonusRule) => r.active)
      } : undefined
    };
    return of(publicCfg).pipe(delay(120));
  }

  saveBusinessConfig(payload: UpdateBusinessConfigPayload): Observable<AppBusinessConfig> {
    this.businessConfig = structuredClone(payload.config);
    return of(structuredClone(this.businessConfig)).pipe(delay(120));
  }

  listCategories(): Observable<ProductCategory[]> {
    return of([...this.categories]).pipe(delay(80));
  }

  getSponsorContact(_sponsorId: string): Observable<SponsorContact> {
    return of({
      name: 'Ana Promotora',
      email: 'ana@ejemplo.com',
      phone: '+525512345678',
      isDefault: false
    }).pipe(delay(80));
  }

  saveCategory(payload: SaveProductCategoryPayload): Observable<ProductCategory> {
    const now = new Date().toISOString();
    const existing = payload.id ? this.categories.find((c) => c.id === payload.id) : null;
    const category: ProductCategory = {
      id: payload.id || `cat-${Math.random().toString(36).slice(2, 9)}`,
      name: payload.name,
      parentId: payload.parentId ?? null,
      position: payload.position ?? 0,
      active: payload.active ?? true,
      createdAt: existing?.createdAt ?? now
    };
    this.categories = existing
      ? this.categories.map((c) => (c.id === category.id ? category : c))
      : [...this.categories, category];
    return of(category).pipe(delay(100));
  }

  deleteCategory(id: string): Observable<{ ok: boolean }> {
    this.categories = this.categories.filter((c) => c.id !== id && c.parentId !== id);
    return of({ ok: true }).pipe(delay(80));
  }

  getShippingQuote(payload: ShippingQuoteRequest): Observable<ShippingRate[]> {
    const postalCode = String(payload.postalCode ?? payload.zipTo ?? '').trim();
    const name = String(payload.name ?? payload.recipientName ?? '').trim();
    const phone = String(payload.phone ?? '').trim();
    const street = String(payload.street ?? payload.address ?? '').trim();
    const number = String(payload.number ?? '').trim();
    const city = String(payload.city ?? '').trim();
    const state = String(payload.state ?? '').trim();
    const country = String(payload.country ?? '').trim().toUpperCase();

    if (
      !name ||
      !phone ||
      !street ||
      !number ||
      !city ||
      !/^\d{5}$/.test(postalCode) ||
      !ESTADOS_MX_CODES.has(state) ||
      !country
    ) {
      return throwError(() => new Error('Datos de cotizacion incompletos o invalidos.'));
    }

    const mockRates: ShippingRate[] = [
      { carrier: 'FedEx', service: 'FedEx Express', price: 145, displayPrice: this.applyShippingMarkup(145), currency: 'MXN', transitDays: 1, deliveryEstimate: 'Día siguiente' },
      { carrier: 'DHL', service: 'DHL Express', price: 132, displayPrice: this.applyShippingMarkup(132), currency: 'MXN', transitDays: 2, deliveryEstimate: '2-3 días' },
      { carrier: 'Estafeta', service: 'Estafeta Dia Siguiente', price: 98, displayPrice: this.applyShippingMarkup(98), currency: 'MXN', transitDays: 2, deliveryEstimate: '2-3 días' },
      { carrier: 'Redpack', service: 'Redpack Express', price: 87, displayPrice: this.applyShippingMarkup(87), currency: 'MXN', transitDays: 3, deliveryEstimate: '3-5 días' },
    ];
    return of(mockRates);
  }

  private applyShippingMarkup(price: number): number {
    return Math.ceil((price * 1.15) / 50) * 50;
  }

  cancelOrder(orderId: string, reason: string): Observable<OrderCancelResponse> {
    return of({ ok: true, orderId, status: 'cancelled', pendingRefund: true }).pipe(delay(200));
  }

  requestReturn(orderId: string, payload: OrderReturnRequestPayload): Observable<OrderReturnRequestResponse> {
    const requestId = `RET-MOCK-${Math.random().toString(16).slice(2, 10).toUpperCase()}`;
    const shipping: 'empresa' | 'cliente' = payload.motivo === 'DESISTIMIENTO' ? 'cliente' : 'empresa';
    return of({
      ok: true,
      requestId,
      status: 'PENDIENTE' as const,
      shippingResponsibility: shipping,
      message: 'Solicitud registrada correctamente.'
    }).pipe(delay(300));
  }

  getHonorBoard(): Observable<HonorBoard> {
    return of(this.getMockHonorBoard()).pipe(delay(120));
  }

  private getMockHonorBoard(): HonorBoard {
    const monthKey = '2026-04';
    const byVg = [
      { customerId: 'c-other-1', name: 'Roberto A.', vp: 180, vg: 4100, rank: 'PLATINO', position: 1 },
      { customerId: 'c-other-2', name: 'Sandra M.', vp: 145, vg: 3250, rank: 'PLATINO', position: 2 },
      { customerId: 'client-001', name: 'Valeria Torres', vp: 52, vg: 730, rank: 'ORO', position: 3, prevPosition: 5 },
      { customerId: 'c-other-3', name: 'Andrés V.', vp: 120, vg: 620, rank: 'ORO', position: 4 },
      { customerId: 'c-other-4', name: 'Lucía H.', vp: 98, vg: 510, rank: 'ORO', position: 5 },
      { customerId: 'c-other-5', name: 'Carlos P.', vp: 90, vg: 490, rank: 'ORO', position: 6 },
      { customerId: 'c-other-6', name: 'Diana R.', vp: 82, vg: 410, rank: 'ORO', position: 7 },
      { customerId: 'c-other-7', name: 'Marcos T.', vp: 75, vg: 380, rank: 'ORO', position: 8 },
      { customerId: 'c-other-8', name: 'Elena S.', vp: 70, vg: 320, rank: '', position: 9 },
      { customerId: 'c-other-9', name: 'Javier C.', vp: 65, vg: 290, rank: '', position: 10 }
    ];
    const byVp = [
      { customerId: 'c-other-1', name: 'Roberto A.', vp: 180, vg: 4100, rank: 'PLATINO', position: 1 },
      { customerId: 'c-other-2', name: 'Sandra M.', vp: 145, vg: 3250, rank: 'PLATINO', position: 2 },
      { customerId: 'c-other-3', name: 'Andrés V.', vp: 120, vg: 620, rank: 'ORO', position: 3 },
      { customerId: 'c-other-4', name: 'Lucía H.', vp: 98, vg: 510, rank: 'ORO', position: 4 },
      { customerId: 'c-other-5', name: 'Carlos P.', vp: 90, vg: 490, rank: 'ORO', position: 5 },
      { customerId: 'client-001', name: 'Valeria Torres', vp: 52, vg: 730, rank: 'ORO', position: 6, prevPosition: 4 },
      { customerId: 'c-other-6', name: 'Diana R.', vp: 82, vg: 410, rank: 'ORO', position: 7 },
      { customerId: 'c-other-7', name: 'Marcos T.', vp: 75, vg: 380, rank: 'ORO', position: 8 },
      { customerId: 'c-other-8', name: 'Elena S.', vp: 70, vg: 320, rank: '', position: 9 },
      { customerId: 'c-other-9', name: 'Javier C.', vp: 65, vg: 290, rank: '', position: 10 }
    ];
    return { monthKey, byVg, byVp };
  }
}
