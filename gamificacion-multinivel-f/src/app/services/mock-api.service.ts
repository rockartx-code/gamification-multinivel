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
import { CommissionReceiptPayload, CommissionRequestPayload, UserDashboardData } from '../models/user-dashboard.model';
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
    { id: 1, name: 'COL?GENO', price: 35, active: true, sku: 'COL-001', hook: 'Regeneraci?n diaria', tags: ['bienestar'] },
    { id: 2, name: 'OMEGA-3', price: 29, active: true, sku: 'OMG-003', hook: 'Cuerpo & mente', tags: ['salud', 'mente'] },
    { id: 3, name: 'COMPLEJO B', price: 24, active: false, sku: 'CMP-010', hook: 'Energ?a', tags: ['energia'] }
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
          commissions: 320
        },
        {
          id: 2,
          name: 'Carlos Ruiz',
          email: 'carlos@mail.com',
          leaderId: 1,
          level: 'Plata',
          discount: '10%',
          commissions: 120
        },
        {
          id: 3,
          name: 'María Pérez',
          email: 'maria@mail.com',
          leaderId: 2,
          level: 'Bronce',
          discount: '5%',
          commissions: 0
        }
      ],
      products: [...this.products],
      warnings: [
        { type: 'commissions', text: '3 comisiones pendientes por depositar', severity: 'high' },
        { type: 'shipping', text: '2 pedidos pagados sin envío', severity: 'high' },
        { type: 'assets', text: 'Producto sin imagen para redes', severity: 'medium' }
      ],
      commissionsPaidSummary: {
        monthKey: '2026-02',
        count: 2,
        total: 180,
        rows: [
          { beneficiaryId: 1, beneficiaryName: 'Ana L??pez', orderId: '#1000', amount: 120, createdAt: '2026-02-01T08:10:00Z' },
          { beneficiaryId: 2, beneficiaryName: 'Carlos Ruiz', orderId: '#1005', amount: 60, createdAt: '2026-02-01T09:20:00Z' }
        ]
      },
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
          img: 'images/L-Colageno.png'
        },
        {
          id: 'omega3',
          name: 'OMEGA-3',
          price: 29,
          qty: 2,
          note: 'Cuerpo & mente',
          img: 'images/L-Omega3.png'
        }
      ],
      suggestedItem: {
        id: 'complejoB',
        name: 'COMPLEJO B',
        price: 24,
        qty: 1,
        note: 'Energía',
        img: 'images/L-ComplejoB.png'
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
          img: 'images/L-Creatina.png'
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
          img: 'images/L-Antioxidante.png'
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
        { name: 'María G.', level: 'L1', spend: 80, status: 'Activa' },
        { name: 'Luis R.', level: 'L1', spend: 25, status: 'En progreso' },
        { name: 'Ana P.', level: 'L1', spend: 0, status: 'Inactiva' },
        { name: 'Carlos V.', level: 'L2', spend: 40, status: 'Activa' },
        { name: 'Sofía M.', level: 'L2', spend: 15, status: 'En progreso' },
        { name: 'Diego S.', level: 'L2', spend: 0, status: 'Inactiva' }
      ],
      buyAgainIds: ['omega3', 'complejoB', 'antioxidante'],
      commissions: {
        monthKey: '2026-02',
        pendingTotal: 150,
        paidTotal: 80,
        hasPending: true,
        clabeOnFile: true,
        clabeLast4: '1234',
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
