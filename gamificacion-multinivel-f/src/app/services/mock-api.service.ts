import { Injectable } from '@angular/core';
import { delay, Observable, of, throwError } from 'rxjs';

import {
  AdminCustomer,
  AdminData,
  AdminOrder,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  ProductAssetUpload
} from '../models/admin.model';
import { CartData } from '../models/cart.model';
import { UserDashboardData } from '../models/user-dashboard.model';
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
        name: 'Admin Rivera',
        role: 'admin' as const
      }
    },
    {
      username: 'cliente',
      password: 'cliente123',
      profile: {
        name: 'Valeria Torres',
        role: 'cliente' as const,
        discountPercent: 15,
        discountActive: true,
        level: 'Oro'
      }
    }
  ];

  login(username: string, password: string): Observable<AuthUser> {
    const match = this.loginUsers.find((user) => user.username === username && user.password === password);
    if (!match) {
      return throwError(() => new Error('Credenciales inválidas'));
    }
    return of(match.profile).pipe(delay(120));
  }

  getAdminData(): Observable<AdminData> {
    const payload: AdminData = {
      orders: [
        { id: '#1001', customer: 'Ana López', total: 120, status: 'pending' },
        { id: '#1002', customer: 'Carlos Ruiz', total: 89, status: 'paid' },
        { id: '#1003', customer: 'María Pérez', total: 210, status: 'paid' },
        { id: '#1004', customer: 'Luis Gómez', total: 60, status: 'delivered' }
      ],
      customers: [
        {
          id: 1,
          name: 'Ana López',
          email: 'ana@mail.com',
          level: 'Oro',
          discount: '15%',
          commissions: 320
        },
        {
          id: 2,
          name: 'Carlos Ruiz',
          email: 'carlos@mail.com',
          level: 'Plata',
          discount: '10%',
          commissions: 120
        },
        {
          id: 3,
          name: 'María Pérez',
          email: 'maria@mail.com',
          level: 'Bronce',
          discount: '5%',
          commissions: 0
        }
      ],
      products: [
        { id: 1, name: 'COLÁGENO', price: 35, active: true },
        { id: 2, name: 'OMEGA-3', price: 29, active: true },
        { id: 3, name: 'COMPLEJO B', price: 24, active: false }
      ],
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

  getUserDashboardData(): Observable<UserDashboardData> {
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
      buyAgainIds: ['omega3', 'complejoB', 'antioxidante']
    };

    return of(payload).pipe(delay(120));
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    const total = payload.items.reduce((acc, item) => acc + item.price * item.quantity, 0);
    const order: AdminOrder = {
      id: `#${Math.floor(1000 + Math.random() * 9000)}`,
      customer: payload.customerName,
      total,
      status: payload.status
    };
    return of(order).pipe(delay(120));
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
      level: payload.level,
      discount: discountByLevel[payload.level],
      commissions: 0
    };
    return of(customer).pipe(delay(120));
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
}
