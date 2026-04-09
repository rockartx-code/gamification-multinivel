import { Injectable } from '@angular/core';
import { BehaviorSubject, finalize, forkJoin, Observable, of, shareReplay, tap } from 'rxjs';
import { map } from 'rxjs/operators';

import {
  DashboardData,
  DashboardCustomerProfile,
  DashboardGoal,
  DashboardProduct,
  FeaturedItem,
  DashboardCampaign,
  NetworkMember,
  UserDashboardData
} from '../models/user-dashboard.model';
import { CustomerShippingAddress } from '../models/admin.model';
import { NotificationReadResponse, PortalNotification } from '../models/portal-notification.model';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class UserDashboardControlService {
  private readonly dataSubject = new BehaviorSubject<UserDashboardData | null>(null);
  readonly data$ = this.dataSubject.asObservable();
  private readonly emptyGoals: DashboardGoal[] = [];
  private readonly emptyProducts: DashboardProduct[] = [];
  private readonly emptyFeatured: FeaturedItem[] = [];
  private readonly emptyCampaigns: DashboardCampaign[] = [];
  private readonly emptyNetworkMembers: NetworkMember[] = [];
  private readonly emptyNotifications: PortalNotification[] = [];
  private cart: Record<string, number> = {};
  private heroQty = 0;
  private heroProductId = '';
  private networkMembersCache: NetworkMember[] = [];
  private buyAgainIdsCache = new Set<string>();
  private loadRequest?: Observable<UserDashboardData>;

  constructor(
    private readonly api: ApiService,
    private readonly authService: AuthService
  ) {}

  load(options: { force?: boolean } = {}): Observable<UserDashboardData> {
    if (!options.force && this.dataSubject.value) {
      return of(this.cloneDashboardData(this.dataSubject.value));
    }

    if (!options.force && this.loadRequest) {
      return this.loadRequest;
    }

    const dashboardRequest = this.authService.hasSession
      ? this.api.getDashboardData()
      : of<DashboardData>({
          isGuest: true,
          settings: {
            cutoffDay: 25,
            cutoffHour: 23,
            cutoffMinute: 59,
            userCode: '',
            networkGoal: 300
          },
          goals: [],
          featured: [],
          campaigns: [],
          networkMembers: [],
          buyAgainIds: [],
          commissions: null,
          notifications: [],
          customer: null
        });

    const request = forkJoin([
      this.api.getCatalogData(),
      dashboardRequest
    ]).pipe(
      map(([catalog, dashboard]) => ({
        // Datos de catálogo (GET /catalog)
        products: catalog.products ?? [],
        productOfMonth: catalog.productOfMonth ?? null,
        categories: [],
        // Datos de dashboard autenticado (GET /customer/dashboard)
        featured: dashboard.featured ?? [],
        campaigns: dashboard.campaigns ?? [],
        settings: dashboard.settings,
        goals: dashboard.goals ?? [],
        networkMembers: dashboard.networkMembers ?? [],
        buyAgainIds: dashboard.buyAgainIds ?? [],
        commissions: dashboard.commissions ?? null,
        notifications: dashboard.notifications ?? [],
        customer: this.normalizeDashboardCustomer(dashboard.customer),
        user: dashboard.user,
        sponsor: dashboard.sponsor,
        isGuest: dashboard.isGuest,
        vp: dashboard.vp,
        vg: dashboard.vg,
        rank: dashboard.rank,
        bonuses: dashboard.bonuses ?? [],
      } satisfies UserDashboardData)),
      tap((data) => {
        const safeNetworkMembers = Array.isArray(data.networkMembers) ? data.networkMembers : [];
        const safeBuyAgainIds = (Array.isArray(data.buyAgainIds) ? data.buyAgainIds : [])
          .filter((item): item is string => typeof item === 'string');
        const rawCommissions = data.commissions;
        const normalizedCommissions = rawCommissions
          ? {
              ...rawCommissions,
              pendingTotal:
                (rawCommissions as any).pendingTotal ?? (rawCommissions as any).totalPending ?? 0,
              monthTotal:
                (rawCommissions as any).monthTotal ?? (rawCommissions as any).totalConfirmed ?? 0,
              paidTotal: (rawCommissions as any).paidTotal ?? 0,
              blockedTotal:
                (rawCommissions as any).blockedTotal ?? (rawCommissions as any).totalBlocked ?? 0,
              ledger: Array.isArray((rawCommissions as any).ledger) ? (rawCommissions as any).ledger : [],
              hasPending:
                typeof (rawCommissions as any).hasPending === 'boolean'
                  ? (rawCommissions as any).hasPending
                  : Boolean(((rawCommissions as any).pendingTotal ?? (rawCommissions as any).totalPending ?? 0) > 0),
              hasConfirmed:
                typeof (rawCommissions as any).hasConfirmed === 'boolean'
                  ? (rawCommissions as any).hasConfirmed
                  : Boolean(((rawCommissions as any).monthTotal ?? (rawCommissions as any).totalConfirmed ?? 0) > 0)
            }
          : null;
        const mappedData: UserDashboardData = {
          ...data,
          networkMembers: safeNetworkMembers,
          buyAgainIds: safeBuyAgainIds,
          notifications: Array.isArray(data.notifications) ? data.notifications : [],
          commissions: normalizedCommissions
        };
        this.networkMembersCache = safeNetworkMembers;
        this.buyAgainIdsCache = new Set(safeBuyAgainIds);
        const clonedData = this.cloneDashboardData(mappedData);
        this.dataSubject.next(clonedData);
        this.heroProductId =
          mappedData.productOfMonth?.id ?? mappedData.products?.[0]?.id ?? this.heroProductId;
        if (this.heroProductId) {
          this.heroQty = this.cart[this.heroProductId] ?? 0;
        }
      }),
      finalize(() => {
        this.loadRequest = undefined;
      }),
      shareReplay(1)
    );

    this.loadRequest = request;
    return request;
  }

  get data(): UserDashboardData | null {
    return this.dataSubject.value;
  }

  get goals(): DashboardGoal[] {
    return this.data?.goals ?? this.emptyGoals;
  }

  get products(): DashboardProduct[] {
    return this.data?.products ?? this.emptyProducts;
  }

  get featured(): FeaturedItem[] {
    return this.data?.featured ?? this.emptyFeatured;
  }

  get campaigns(): DashboardCampaign[] {
    return this.data?.campaigns ?? this.emptyCampaigns;
  }

  get networkMembers(): NetworkMember[] {
    if (this.networkMembersCache.length) {
      return this.networkMembersCache;
    }
    return this.data?.networkMembers ?? this.emptyNetworkMembers;
  }

  get notifications(): PortalNotification[] {
    return this.data?.notifications ?? this.emptyNotifications;
  }

  get customer(): DashboardCustomerProfile | null {
    return this.data?.customer ?? null;
  }

  get shippingAddresses(): CustomerShippingAddress[] {
    const customer = this.customer;
    if (!customer) {
      return [];
    }
    return customer.addresses?.length ? customer.addresses : customer.shippingAddresses ?? [];
  }

  get defaultShippingAddressId(): string {
    const customer = this.customer;
    if (!customer) {
      return '';
    }
    return customer.defaultAddressId ?? customer.defaultShippingAddressId ?? '';
  }

  get buyAgainIds(): Set<string> {
    return this.buyAgainIdsCache.size ? new Set(this.buyAgainIdsCache) : new Set(this.data?.buyAgainIds ?? []);
  }

  getProjectedDiscountPercent(cartSubtotal: number): number {
    if (!Number.isFinite(cartSubtotal) || cartSubtotal <= 0) {
      return 0;
    }

    const discountGoals = (this.data?.goals ?? [])
      .filter((goal) => goal?.key?.startsWith('discount_'))
      .map((goal) => {
        const target = Number(goal.target ?? 0);
        const base = Number(goal.base ?? 0);
        const percent = this.extractDiscountPercent(goal);
        return {
          target,
          base,
          percent
        };
      })
      .filter((goal) => goal.percent > 0 && goal.target > 0 && Number.isFinite(goal.base))
      .sort((a, b) => a.percent - b.percent);

    if (!discountGoals.length) {
      return 0;
    }

    const projectedNet = discountGoals[0].base + cartSubtotal;
    let projectedPercent = 0;
    for (const goal of discountGoals) {
      if (projectedNet >= goal.target) {
        projectedPercent = goal.percent;
      }
    }
    return projectedPercent;
  }

  get heroQuantity(): number {
    return this.heroQty;
  }

  get heroProduct(): string {
    return this.heroProductId;
  }

  get cartTotal(): number {
    return this.products.reduce((total, product) => {
      const qty = this.cart[product.id] ?? 0;
      return total + product.price * qty;
    }, 0);
  }

  getCartQty(productId: string): number {
    return this.cart[productId] ?? 0;
  }

  formatMoney(value: number): string {
    const amount = Number.isFinite(value) ? value : 0;
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      maximumFractionDigits: 0
    }).format(amount);
  }

  goalBasePercent(goal: DashboardGoal): number {
    return Math.min(100, (goal.base / goal.target) * 100);
  }

  goalCartPercent(goal: DashboardGoal): number {
    if (goal.isCountGoal || goal.unit === 'vp') {
      return 0;
    }
    const basePercent = this.goalBasePercent(goal);
    const cartPercent = (goal.cart / goal.target) * 100;
    return Math.min(100 - basePercent, Math.max(0, cartPercent));
  }

  goalProgressLabel(goal: DashboardGoal): string {
    if (goal.isCountGoal || goal.unit === 'count') {
      return `${goal.base} / ${goal.target}`;
    }
    if (goal.unit === 'vp') {
      return `${goal.base.toFixed(1)} / ${goal.target.toFixed(0)} VP`;
    }
    return `${this.formatMoney(goal.base)} / ${this.formatMoney(goal.target)}`;
  }

  statusBadgeClass(status: NetworkMember['status']): string {
    if (status === 'Activa') {
      return 'bg-emerald-500/10 border-emerald-400/30 text-main';
    }
    if (status === 'En progreso') {
      return 'bg-gold-12 border-gold-35 text-on-gold';
    }
    return 'bg-ivory-80 border-olive-30 text-muted';
  }

  updateCart(productId: string, qty: number): void {
    const normalized = Math.max(0, Math.floor(qty));
    if (normalized === 0) {
      delete this.cart[productId];
    } else {
      this.cart[productId] = normalized;
    }
    if (productId === this.heroProductId) {
      this.heroQty = normalized;
    }
    this.syncGoalCartTotals();
  }

  addQuick(productId: string, addQty: number): void {
    const current = this.cart[productId] ?? 0;
    this.updateCart(productId, current + addQty);
  }

  setHeroQty(value: number): void {
    if (!this.heroProductId) {
      return;
    }
    this.heroQty = Math.max(0, Math.floor(value));
    this.updateCart(this.heroProductId, this.heroQty);
  }

  addHeroToCart(): void {
    if (!this.heroProductId) {
      return;
    }
    if (this.heroQty <= 0) {
      this.heroQty = 1;
    }
    this.addQuick(this.heroProductId, 1);
    this.heroQty = this.cart[this.heroProductId] ?? 0;
  }

  getCountdownLabel(): string {
    const settings = this.data?.settings;
    if (!settings) {
      return '';
    }
    const diff = Math.max(0, this.getNextCutoffDate(settings).getTime() - Date.now());
    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
    const m = Math.floor((diff / (1000 * 60)) % 60);
    const s = Math.floor((diff / 1000) % 60);
    return `${d}d ${h}h ${m}m ${s}s`;
  }

  markNotificationRead(notificationId: string): Observable<NotificationReadResponse> {
    const customerId = this.authService.currentUser?.userId;
    return this.api.markNotificationRead(notificationId, customerId ? { customerId } : {}).pipe(
      tap((response) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const notifications = (current.notifications ?? []).map((notification) =>
          notification.id === notificationId
            ? {
                ...notification,
                isRead: true,
                readAt: response.readAt ?? notification.readAt ?? ''
              }
            : notification
        );
        this.dataSubject.next({
          ...current,
          notifications
        });
      })
    );
  }

  private syncGoalCartTotals(): void {
    const current = this.dataSubject.value;
    if (!current) {
      return;
    }
    const updatedGoals = current.goals.map((goal) => {
      const isConsumptionGoal =
        goal.key === 'active' ||
        goal.key === 'discount' ||
        goal.key.startsWith('discount_');
      if (isConsumptionGoal && !goal.isCountGoal && goal.unit !== 'vp') {
        return { ...goal, cart: this.cartTotal };
      }
      return goal;
    });
    this.dataSubject.next({ ...current, goals: updatedGoals });
  }

  private getNextCutoffDate(settings: UserDashboardData['settings']): Date {
    const now = new Date();
    let cutoff = new Date(
      now.getFullYear(),
      now.getMonth(),
      settings.cutoffDay,
      settings.cutoffHour,
      settings.cutoffMinute,
      59,
      999
    );
    if (cutoff.getTime() <= now.getTime()) {
      cutoff = new Date(
        now.getFullYear(),
        now.getMonth() + 1,
        settings.cutoffDay,
        settings.cutoffHour,
        settings.cutoffMinute,
        59,
        999
      );
    }
    return cutoff;
  }

  private normalizeDashboardCustomer(customer: DashboardData['customer']): DashboardCustomerProfile | null {
    if (!customer) {
      return null;
    }

    const sourceAddresses = Array.isArray(customer.addresses)
      ? customer.addresses
      : Array.isArray(customer.shippingAddresses)
        ? customer.shippingAddresses
        : [];

    const addresses = sourceAddresses
      .filter((entry): entry is CustomerShippingAddress => Boolean(entry?.id))
      .map((entry) => ({ ...entry }));

    const defaultAddressId = customer.defaultAddressId ?? customer.defaultShippingAddressId ?? '';
    const normalizedAddresses = addresses.map((entry) => ({
      ...entry,
      isDefault: Boolean(entry.isDefault) || Boolean(defaultAddressId && entry.id === defaultAddressId)
    }));

    return {
      ...customer,
      addresses: normalizedAddresses,
      shippingAddresses: normalizedAddresses,
      defaultAddressId,
      defaultShippingAddressId: defaultAddressId
    };
  }

  private extractDiscountPercent(goal: DashboardGoal): number {
    const match = String(goal.title ?? '').match(/(\d+(?:\.\d+)?)\s*%/);
    if (!match) {
      return 0;
    }
    const value = Number(match[1]);
    return Number.isFinite(value) ? Math.round(value) : 0;
  }

  private cloneDashboardData(data: UserDashboardData): UserDashboardData {
    return typeof structuredClone === 'function'
      ? structuredClone(data)
      : (JSON.parse(JSON.stringify(data)) as UserDashboardData);
  }
}
