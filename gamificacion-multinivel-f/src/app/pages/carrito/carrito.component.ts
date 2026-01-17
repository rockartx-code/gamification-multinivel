import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';

interface CartItem {
  id: string;
  name: string;
  price: number;
  qty: number;
  note: string;
  img: string;
}

@Component({
  selector: 'app-carrito',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './carrito.component.html',
  styleUrl: './carrito.component.css'
})
export class CarritoComponent implements OnInit, OnDestroy {
  countdownLabel = '3d 8h';
  readonly shipping = 0;
  readonly discountPct = 0.05;
  readonly user = {
    monthSpendActual: 45,
    activeSpendTarget: 60
  };

  cartItems: CartItem[] = [
    {
      id: 'colageno',
      name: 'COLÁGENO',
      price: 35,
      qty: 1,
      note: 'Regeneración',
      img: 'assets/images/product-colageno.svg'
    },
    {
      id: 'omega3',
      name: 'OMEGA-3',
      price: 29,
      qty: 2,
      note: 'Cuerpo & mente',
      img: 'assets/images/product-omega3.svg'
    }
  ];

  payMethod: 'card' | 'spei' | 'cash' = 'card';
  isToastVisible = false;
  toastMessage = 'Actualizado.';
  private toastTimeout?: number;
  private countdownInterval?: number;

  ngOnInit(): void {
    this.updateCountdown();
    this.countdownInterval = window.setInterval(() => this.updateCountdown(), 60000);
  }

  ngOnDestroy(): void {
    if (this.countdownInterval) {
      window.clearInterval(this.countdownInterval);
    }
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
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
    const needed = Math.max(0, this.user.activeSpendTarget - this.user.monthSpendActual);
    return Math.max(0, needed - this.subtotal);
  }

  get benefitPercent(): number {
    const needed = Math.max(0, this.user.activeSpendTarget - this.user.monthSpendActual);
    if (needed === 0) {
      return 100;
    }
    return Math.min(100, (this.subtotal / needed) * 100);
  }

  formatMoney(value: number): string {
    return `$${value.toFixed(0)}`;
  }

  setQty(itemId: string, qty: number): void {
    const normalized = Math.max(0, Math.floor(qty));
    const itemIndex = this.cartItems.findIndex((item) => item.id === itemId);
    if (itemIndex < 0) {
      return;
    }
    if (normalized === 0) {
      this.cartItems.splice(itemIndex, 1);
      this.showToast('Producto removido.');
      return;
    }
    this.cartItems[itemIndex] = { ...this.cartItems[itemIndex], qty: normalized };
    this.showToast('Cantidad actualizada.');
  }

  removeItem(itemId: string): void {
    const itemIndex = this.cartItems.findIndex((item) => item.id === itemId);
    if (itemIndex >= 0) {
      this.cartItems.splice(itemIndex, 1);
      this.showToast('Producto removido.');
    }
  }

  addSuggested(): void {
    const suggested: CartItem = {
      id: 'complejoB',
      name: 'COMPLEJO B',
      price: 24,
      qty: 1,
      note: 'Energía',
      img: 'assets/images/product-complejo-b.svg'
    };
    const existing = this.cartItems.find((item) => item.id === suggested.id);
    if (existing) {
      existing.qty += 1;
    } else {
      this.cartItems.push(suggested);
    }
    this.showToast('Agregado sugerido.');
  }

  selectPay(method: 'card' | 'spei' | 'cash'): void {
    this.payMethod = method;
  }

  placeOrder(): void {
    if (!this.cartItems.length) {
      this.showToast('Agrega productos para continuar.');
      return;
    }
    this.showToast('Pedido creado (mock).');
  }

  private updateCountdown(): void {
    const now = new Date();
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    lastDay.setHours(23, 59, 59, 999);
    const diff = Math.max(0, lastDay.getTime() - Date.now());
    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
    this.countdownLabel = `${d}d ${h}h`;
  }

  private showToast(message: string): void {
    this.toastMessage = message;
    this.isToastVisible = true;
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
    this.toastTimeout = window.setTimeout(() => {
      this.isToastVisible = false;
    }, 2200);
  }
}
