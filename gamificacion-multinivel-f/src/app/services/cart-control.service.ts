import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';

import { CartData, CartItem } from '../models/cart.model';

export type CartDeliveryState = {
  deliveryType: 'delivery' | 'pickup';
  selectedShippingAddressId: string;
  shippingAddressLabel: string;
  selectedShippingCarrier: string;
  selectedShippingRateId: string;
  deliveryName: string;
  deliveryPhone: string;
  deliveryStreet: string;
  deliveryNumber: string;
  deliveryCity: string;
  deliveryPostalCode: string;
  deliveryState: string;
  deliveryCountry: string;
  deliveryBetweenStreets: string;
  deliveryReferences: string;
  deliveryNotes: string;
};

@Injectable({
  providedIn: 'root'
})
export class CartControlService {
  private readonly dataSubject = new BehaviorSubject<CartData | null>(null);
  readonly data$ = this.dataSubject.asObservable();
  private payMethod: 'card' | 'spei' | 'cash' = 'card';
  private readonly localCartKey = 'cart-items';
  private deliveryState: CartDeliveryState = {
    deliveryType: 'delivery',
    selectedShippingAddressId: '',
    shippingAddressLabel: '',
    selectedShippingCarrier: '',
    selectedShippingRateId: '',
    deliveryName: '',
    deliveryPhone: '',
    deliveryStreet: '',
    deliveryNumber: '',
    deliveryCity: '',
    deliveryPostalCode: '',
    deliveryState: '',
    deliveryCountry: 'MX',
    deliveryBetweenStreets: '',
    deliveryReferences: '',
    deliveryNotes: ''
  };

  constructor() {}

  load(): Observable<CartData> {
    const localItems = this.readLocalCartItems();
    const next = this.buildLocalCartData(localItems);
    this.dataSubject.next(next);
    if (localItems.length) {
      this.persistLocalCartItems(localItems);
    }
    return of(next);
  }

  get data(): CartData | null {
    return this.dataSubject.value;
  }

  get cartItems(): CartItem[] {
    return this.data?.items ?? [];
  }

  getQty(itemId: string): number {
    return this.cartItems.find((item) => item.id === itemId)?.qty ?? 0;
  }

  get countdownLabel(): string {
    return this.data?.countdownLabel ?? '';
  }

  get shipping(): number {
    return this.data?.shipping ?? 0;
  }

  get discountPct(): number {
    return this.data?.discountPct ?? 0;
  }

  get user(): CartData['user'] | null {
    return this.data?.user ?? null;
  }

  get suggestedItem(): CartItem | null {
    return this.data?.suggestedItem ?? null;
  }

  get currentPayMethod(): 'card' | 'spei' | 'cash' {
    return this.payMethod;
  }

  formatMoney(value: number): string {
    const amount = Number.isFinite(value) ? value : 0;
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      maximumFractionDigits: 0
    }).format(amount);
  }

  get subtotal(): number {
    return this.cartItems.reduce((acc, item) => acc + item.price * item.qty, 0);
  }

  get discount(): number {
    return Math.round(this.subtotal * this.discountPct);
  }

  get total(): number {
    return Math.max(0, this.subtotal + this.shipping - this.discount);
  }

  get itemsCount(): number {
    return this.cartItems.reduce((acc, item) => acc + item.qty, 0);
  }

  get gapToGoal(): number {
    if (!this.user) {
      return 0;
    }
    const needed = Math.max(0, this.user.activeSpendTarget - this.user.monthSpendActual);
    return Math.max(0, needed - this.subtotal);
  }

  get benefitPercent(): number {
    if (!this.user) {
      return 0;
    }
    const needed = Math.max(0, this.user.activeSpendTarget - this.user.monthSpendActual);
    if (needed === 0) {
      return 100;
    }
    return Math.min(100, (this.subtotal / needed) * 100);
  }

  setQty(itemId: string, qty: number): void {
    const current = this.ensureData();
    const normalized = Math.max(0, Math.floor(qty));
    const updatedItems = current.items.reduce<CartItem[]>((acc, item) => {
      if (item.id !== itemId) {
        acc.push(item);
        return acc;
      }
      if (normalized === 0) {
        return acc;
      }
      acc.push({ ...item, qty: normalized });
      return acc;
    }, []);
    this.dataSubject.next({ ...current, items: updatedItems });
    this.persistLocalCartItems(updatedItems);
  }

  upsertItem(item: CartItem, qty: number): void {
    const current = this.ensureData();
    const normalized = Math.max(0, Math.floor(qty));
    const existing = current.items.find((it) => it.id === item.id);
    let updatedItems: CartItem[];
    if (normalized === 0) {
      updatedItems = current.items.filter((it) => it.id !== item.id);
    } else if (existing) {
      updatedItems = current.items.map((it) => (it.id === item.id ? { ...it, qty: normalized } : it));
    } else {
      updatedItems = [...current.items, { ...item, qty: normalized }];
    }
    this.dataSubject.next({ ...current, items: updatedItems });
    this.persistLocalCartItems(updatedItems);
  }

  removeItem(itemId: string): void {
    const current = this.dataSubject.value;
    if (!current) {
      return;
    }
    const updatedItems = current.items.filter((item) => item.id !== itemId);
    this.dataSubject.next({ ...current, items: updatedItems });
    this.persistLocalCartItems(updatedItems);
  }

  addSuggested(): void {
    const current = this.ensureData();
    const suggested = current.suggestedItem;
    const updatedItems = current.items.map((item) =>
      item.id === suggested.id ? { ...item, qty: item.qty + 1 } : item
    );
    if (!updatedItems.some((item) => item.id === suggested.id)) {
      updatedItems.push({ ...suggested });
    }
    this.dataSubject.next({ ...current, items: updatedItems });
    this.persistLocalCartItems(updatedItems);
  }

  addItem(item: CartItem, addQty: number): void {
    const current = this.ensureData();
    const normalized = Math.max(1, Math.floor(addQty));
    const existing = current.items.find((it) => it.id === item.id);
    let updatedItems: CartItem[];
    if (existing) {
      updatedItems = current.items.map((it) =>
        it.id === item.id ? { ...it, qty: it.qty + normalized } : it
      );
    } else {
      updatedItems = [...current.items, { ...item, qty: normalized }];
    }
    this.dataSubject.next({ ...current, items: updatedItems });
    this.persistLocalCartItems(updatedItems);
  }

  clearCart(): void {
    const current = this.ensureData();
    this.dataSubject.next({ ...current, items: [] });
    try {
      localStorage.removeItem(this.localCartKey);
    } catch {
      // ignore storage errors
    }
  }

  selectPay(method: 'card' | 'spei' | 'cash'): void {
    this.payMethod = method;
  }

  getDeliveryState(): CartDeliveryState {
    return { ...this.deliveryState };
  }

  saveDeliveryState(state: Partial<CartDeliveryState>): void {
    this.deliveryState = { ...this.deliveryState, ...state };
  }

  updateCountdown(label: string): void {
    const current = this.dataSubject.value;
    if (!current) {
      return;
    }
    this.dataSubject.next({ ...current, countdownLabel: label });
  }

  private ensureData(): CartData {
    const current = this.dataSubject.value;
    if (current) {
      return current;
    }
    const init = this.buildLocalCartData([]);
    this.dataSubject.next(init);
    return init;
  }

  private readLocalCartItems(): CartItem[] {
    try {
      const raw = localStorage.getItem(this.localCartKey);
      if (!raw) {
        return [];
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed.filter((item) => item && typeof item.id === 'string' && typeof item.qty === 'number');
    } catch {
      return [];
    }
  }

  private buildLocalCartData(items: CartItem[]): CartData {
    return {
      countdownLabel: '',
      shipping: 0,
      discountPct: 0,
      user: { monthSpendActual: 0, activeSpendTarget: 0 },
      items,
      suggestedItem: {
        id: '',
        name: '',
        price: 0,
        qty: 0,
        note: '',
        img: ''
      }
    };
  }

  private persistLocalCartItems(items: CartItem[]): void {
    try {
      localStorage.setItem(this.localCartKey, JSON.stringify(items));
    } catch {
      // ignore storage errors
    }
  }
}
