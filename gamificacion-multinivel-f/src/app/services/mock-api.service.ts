import { Injectable } from '@angular/core';
import { delay, Observable, of, throwError } from 'rxjs';

import {
  AdminCustomer,
  AdminData,
  AdminOrder,
  AdminProduct,
  AssetResponse,
  CreateAssetPayload,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  CustomerProfile,
  UpdateOrderStatusPayload,
  ProductAssetUpload,
  ProductOfMonthResponse,
  SaveAdminProductPayload
} from '../models/admin.model';
import { CreateAccountPayload, CreateAccountResponse } from '../models/auth.model';
import { CartData } from '../models/cart.model';
import {
  CommissionReceiptPayload,
  CommissionRequestPayload,
  CustomerClabePayload,
  UserDashboardData
} from '../models/user-dashboard.model';
import type { AuthUser } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class MockApiService {
  private readonly loginUsers = [
    {
      username: 'admin',
      password: 'admin123',
      profile: {
        userId: 'admin-001',
        name: 'Admin Rivera',
        role: 'admin' as const
      }
    },
    {
      username: 'cliente',
      password: 'cliente123',
      profile: {
        userId: 'client-001',
        name: 'Valeria Torres',
        role: 'cliente' as const,
        discountPercent: 15,
        discountActive: true,
        level: 'Oro'
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
      tags: ['bienestar']
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
      tags: ['salud', 'mente']
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
      tags: ['energia']
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
    if (payload.password !== payload.confirmPassword) {
      return throwError(() => new Error('Las contrase?as no coinciden'));
    }
    const customer = {
      id: Math.floor(100000 + Math.random() * 900000),
      name: payload.name,
      email: payload.email,
      leaderId: payload.referralToken ? payload.referralToken : null,
      level: 'Oro',
      isAssociate: true,
      discount: '0%',
      activeBuyer: false,
      discountRate: 0,
      commissions: 0
    };
    return of({ customer }).pipe(delay(160));
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
          status: 'pending'
        },
        {
          id: '#1002',
          createdAt: '2026-01-16T11:20:00.000Z',
          customer: 'Carlos Ruiz',
          total: 89,
          status: 'paid'
        },
        {
          id: '#1003',
          createdAt: '2026-01-15T17:05:00.000Z',
          customer: 'Maria Perez',
          total: 210,
          status: 'paid'
        },
        {
          id: '#1004',
          createdAt: '2026-01-14T14:50:00.000Z',
          customer: 'Luis Gomez',
          total: 60,
          status: 'delivered'
        }
      ],
      customers: [
        {
          id: 1,
          name: 'Ana López',
          email: 'ana@mail.com',
          leaderId: null,
          level: 'Oro',
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
          level: 'Plata',
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
          level: 'Bronce',
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
      ],
      products: [...this.products],
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
      images: payload.images
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

  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    const payload: UserDashboardData = {
      settings: {
        cutoffDay: 25,
        cutoffHour: 23,
        cutoffMinute: 59,
        userCode: 'ABC123',
        networkGoal: 300
      },
      goals: [
        {
          key: 'active',
          title: 'Siguiente reto: Usuario activo',
          subtitle: 'Completa tu consumo mínimo del mes',
          target: 60,
          base: 45,
          cart: 0,
          ctaText: 'Ir a tienda',
          ctaFragment: 'merchant'
        },
        {
          key: 'discount',
          title: 'Siguiente nivel de descuento',
          subtitle: 'Alcanza el umbral para mejorar tu beneficio',
          target: 120,
          base: 45,
          cart: 0,
          ctaText: 'Completar consumo',
          ctaFragment: 'merchant'
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
          isCountGoal: true
        },
        {
          key: 'network',
          title: 'Red logra sus metas',
          subtitle: 'Impulsa el consumo de tu red este mes',
          target: 300,
          base: 160,
          cart: 0,
          ctaText: 'Compartir enlace',
          ctaFragment: 'links'
        }
      ],
      products: [
        {
          id: 'colageno',
          name: 'COLÁGENO',
          price: 35,
          badge: 'Regeneración',
          img: 'images/L-Colageno.png'
        },
        {
          id: 'omega3',
          name: 'OMEGA-3',
          price: 29,
          badge: 'Cuerpo & mente',
          img: 'images/L-Omega3.png'
        },
        {
          id: 'creatina',
          name: 'CREATINA',
          price: 27,
          badge: 'Fuerza',
          img: 'images/L-Creatina.png',
          description: 'Potencia rendimiento y fuerza en entrenamientos diarios.',
          copyWhatsapp: 'Creatina para rendimiento diario. ??Te paso el link?',
          copyInstagram: 'Creatina para rendimiento diario. #fuerza',
          copyFacebook: 'Creatina para rendimiento diario. Escr??beme y te paso el link.'
        },
        {
          id: 'complejoB',
          name: 'COMPLEJO B',
          price: 24,
          badge: 'Energía',
          img: 'images/L-ComplejoB.png'
        },
        {
          id: 'antioxidante',
          name: 'ANTIOXIDANTE',
          price: 31,
          badge: 'Longevidad',
          img: 'images/L-Antioxidante.png',
          description: 'Protecci??n antioxidante para bienestar continuo.',
          copyWhatsapp: 'Antioxidante para bienestar continuo. ??Te paso el link?',
          copyInstagram: 'Antioxidante para bienestar continuo. #longevidad',
          copyFacebook: 'Antioxidante para bienestar continuo. Escr??beme y te paso el link.'
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
      networkMembers: [
        { id: 'c-1', name: 'Mar?a G.', level: 'L1', spend: 80, status: 'Activa', leaderId: 'client-001' },
        { id: 'c-2', name: 'Luis R.', level: 'L1', spend: 25, status: 'En progreso', leaderId: 'client-001' },
        { id: 'c-3', name: 'Ana P.', level: 'L1', spend: 0, status: 'Inactiva', leaderId: 'client-001' },
        { id: 'c-4', name: 'Carlos V.', level: 'L2', spend: 40, status: 'Activa', leaderId: 'c-1' },
        { id: 'c-5', name: 'Sof?a M.', level: 'L2', spend: 15, status: 'En progreso', leaderId: 'c-2' },
        { id: 'c-6', name: 'Diego S.', level: 'L2', spend: 0, status: 'Inactiva', leaderId: 'c-2' }
      ],
      buyAgainIds: ['omega3', 'complejoB', 'antioxidante'],
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

    return of(payload).pipe(delay(120));
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
    return of({ ok: true, clabeLast4: payload.clabe.slice(-4) }).pipe(delay(120));
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    const total = payload.items.reduce((acc, item) => acc + item.price * item.quantity, 0);
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
      address: payload.address,
      postalCode: payload.postalCode,
      state: payload.state
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

  getOrders(customerId: string): Observable<AdminOrder[]> {
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
    return of(orders).pipe(delay(120));
  }

  getCustomer(customerId: string): Observable<CustomerProfile> {
    const customer: CustomerProfile = {
      id: Number(customerId) || 1001,
      name: 'Valeria Torres',
      email: 'valeria@mail.com',
      phone: '+52 555-0101',
      address: 'Av. Insurgentes 123',
      city: 'CDMX',
      state: 'CDMX',
      postalCode: '03100'
    };
    return of(customer).pipe(delay(120));
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    const discountByLevel: Record<CreateStructureCustomerPayload['level'], string> = {
      Oro: '15%',
      Plata: '10%',
      Bronce: '5%'
    };
    const customer: AdminCustomer = {
      id: Math.floor(100000 + Math.random() * 900000),
      name: payload.name,
      email: payload.email,
      leaderId: payload.leaderId ?? null,
      level: payload.level,
      discount: discountByLevel[payload.level],
      commissions: 0
    };
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
}
