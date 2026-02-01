import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import {
  DashboardGoal,
  DashboardProduct,
  FeaturedItem,
  NetworkMember,
  UserDashboardData
} from '../models/user-dashboard.model';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class UserDashboardControlService {
  private readonly dataSubject = new BehaviorSubject<UserDashboardData | null>(null);
  readonly data$ = this.dataSubject.asObservable();
  private cart: Record<string, number> = {};
  private heroQty = 0;
  private heroProductId = '';
  private networkMembersCache: NetworkMember[] = [];
  private buyAgainIdsCache = new Set<string>();

  constructor(
    private readonly api: ApiService,
    private readonly authService: AuthService
  ) {}

  load(): Observable<UserDashboardData> {
    const userId = this.authService.currentUser?.userId;
    return this.api.getUserDashboardData(userId).pipe(
      tap((data) => {
        const safeNetworkMembers = Array.isArray(data.networkMembers) ? data.networkMembers : [];
        const rawBuyAgainIds = data.buyAgainIds;
        const safeBuyAgainIds = Array.isArray(rawBuyAgainIds)
          ? rawBuyAgainIds.filter((item): item is string => typeof item === 'string')
          : [];
        const mappedData = {
          ...data,
          networkMembers: safeNetworkMembers,
          buyAgainIds: safeBuyAgainIds
        };
        this.networkMembersCache = safeNetworkMembers;
        this.buyAgainIdsCache = new Set(safeBuyAgainIds);
        console.log('dashboard payload networkMembers:', data.networkMembers);
        console.log('dashboard mapped networkMembers:', mappedData.networkMembers);
        const clonedData =
          typeof structuredClone === 'function'
            ? structuredClone(mappedData)
            : (JSON.parse(JSON.stringify(mappedData)) as UserDashboardData);
        this.dataSubject.next(clonedData);
        this.heroProductId =
          mappedData.productOfMonth?.id ?? mappedData.products?.[0]?.id ?? this.heroProductId;
        if (this.heroProductId) {
          this.heroQty = this.cart[this.heroProductId] ?? 0;
        }
      })
    );
  }

  get data(): UserDashboardData | null {
    return this.dataSubject.value;
  }

  get goals(): DashboardGoal[] {
    return this.data?.goals ?? [];
  }

  get products(): DashboardProduct[] {
    return this.data?.products ?? [];
  }

  get featured(): FeaturedItem[] {
    return this.data?.featured ?? [];
  }

  get networkMembers(): NetworkMember[] {
    return this.networkMembersCache.length ? this.networkMembersCache : this.data?.networkMembers ?? [];
  }

  get buyAgainIds(): Set<string> {
    return this.buyAgainIdsCache.size ? new Set(this.buyAgainIdsCache) : new Set(this.data?.buyAgainIds ?? []);
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
    return `$${value.toFixed(0)}`;
  }

  goalBasePercent(goal: DashboardGoal): number {
    return Math.min(100, (goal.base / goal.target) * 100);
  }

  goalCartPercent(goal: DashboardGoal): number {
    if (goal.isCountGoal) {
      return 0;
    }
    const basePercent = this.goalBasePercent(goal);
    const cartPercent = (goal.cart / goal.target) * 100;
    return Math.min(100 - basePercent, Math.max(0, cartPercent));
  }

  goalProgressLabel(goal: DashboardGoal): string {
    if (goal.isCountGoal) {
      return `${goal.base} / ${goal.target}`;
    }
    return `${this.formatMoney(goal.base)} / ${this.formatMoney(goal.target)}`;
  }

  statusBadgeClass(status: NetworkMember['status']): string {
    if (status === 'Activa') {
      return 'bg-blue-500/15 border-blue-400/20 text-blue-200';
    }
    if (status === 'En progreso') {
      return 'bg-yellow-400/15 border-yellow-400/20 text-yellow-200';
    }
    return 'bg-white/5 border-white/10 text-zinc-300';
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
      if (isConsumptionGoal && !goal.isCountGoal) {
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
}
