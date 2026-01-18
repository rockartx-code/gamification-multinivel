import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import { CartData, CartItem } from '../models/cart.model';
import { MockApiService } from './mock-api.service';

@Injectable({
  providedIn: 'root'
})
export class CartControlService {
  private readonly dataSubject = new BehaviorSubject<CartData | null>(null);
  private payMethod: 'card' | 'spei' | 'cash' = 'card';

  constructor(private readonly api: MockApiService) {}

  load(): Observable<CartData> {
    return this.api.getCartData().pipe(
      tap((data) => {
        this.dataSubject.next(structuredClone(data));
      })
    );
  }

  get data(): CartData | null {
    return this.dataSubject.value;
  }

  get cartItems(): CartItem[] {
    return this.data?.items ?? [];
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
    return `$${value.toFixed(0)}`;
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
    const current = this.dataSubject.value;
    if (!current) {
      return;
    }
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
  }

  removeItem(itemId: string): void {
    const current = this.dataSubject.value;
    if (!current) {
      return;
    }
    const updatedItems = current.items.filter((item) => item.id !== itemId);
    this.dataSubject.next({ ...current, items: updatedItems });
  }

  addSuggested(): void {
    const current = this.dataSubject.value;
    if (!current) {
      return;
    }
    const suggested = current.suggestedItem;
    const updatedItems = current.items.map((item) =>
      item.id === suggested.id ? { ...item, qty: item.qty + 1 } : item
    );
    if (!updatedItems.some((item) => item.id === suggested.id)) {
      updatedItems.push({ ...suggested });
    }
    this.dataSubject.next({ ...current, items: updatedItems });
  }

  selectPay(method: 'card' | 'spei' | 'cash'): void {
    this.payMethod = method;
  }

  updateCountdown(label: string): void {
    const current = this.dataSubject.value;
    if (!current) {
      return;
    }
    this.dataSubject.next({ ...current, countdownLabel: label });
  }
}
