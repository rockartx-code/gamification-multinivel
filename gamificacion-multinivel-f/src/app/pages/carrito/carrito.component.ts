import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CartItem } from '../../models/cart.model';
import { CartControlService } from '../../services/cart-control.service';

@Component({
  selector: 'app-carrito',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './carrito.component.html',
  styleUrl: './carrito.component.css'
})
export class CarritoComponent implements OnInit, OnDestroy {
  constructor(private readonly cartControl: CartControlService) {}

  isToastVisible = false;
  toastMessage = 'Actualizado.';
  isSummaryOpen = false;
  private toastTimeout?: number;
  private countdownInterval?: number;

  ngOnInit(): void {
    this.cartControl.load().subscribe();
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

  get countdownLabel(): string {
    return this.cartControl.countdownLabel;
  }

  get cartItems(): CartItem[] {
    return this.cartControl.cartItems;
  }

  get payMethod(): 'card' | 'spei' | 'cash' {
    return this.cartControl.currentPayMethod;
  }

  get shipping(): number {
    return this.cartControl.shipping;
  }

  get discountPct(): number {
    return this.cartControl.discountPct;
  }

  get subtotal(): number {
    return this.cartControl.subtotal;
  }

  get discount(): number {
    return this.cartControl.discount;
  }

  get total(): number {
    return this.cartControl.total;
  }

  get itemsCount(): number {
    return this.cartControl.itemsCount;
  }

  get gapToGoal(): number {
    return this.cartControl.gapToGoal;
  }

  get benefitPercent(): number {
    return this.cartControl.benefitPercent;
  }

  formatMoney(value: number): string {
    return this.cartControl.formatMoney(value);
  }

  setQty(itemId: string, qty: number): void {
    const normalized = Math.max(0, Math.floor(qty));
    this.cartControl.setQty(itemId, normalized);
    if (normalized === 0) {
      this.showToast('Producto removido.');
      return;
    }
    this.showToast('Cantidad actualizada.');
  }

  removeItem(itemId: string): void {
    this.cartControl.removeItem(itemId);
    this.showToast('Producto removido.');
  }

  addSuggested(): void {
    this.cartControl.addSuggested();
    this.showToast('Agregado sugerido.');
  }

  selectPay(method: 'card' | 'spei' | 'cash'): void {
    this.cartControl.selectPay(method);
  }

  placeOrder(): void {
    if (!this.cartItems.length) {
      this.showToast('Agrega productos para continuar.');
      return;
    }
    this.showToast('Pedido creado (mock).');
  }

  showSummary(): void {
    if (window.matchMedia('(min-width: 1024px)').matches) {
      this.scrollToSection('resumen-carrito');
      return;
    }
    this.isSummaryOpen = true;
  }

  closeSummary(): void {
    this.isSummaryOpen = false;
  }

  showDetails(): void {
    this.isSummaryOpen = false;
    this.scrollToSection('detalle-carrito');
  }

  private updateCountdown(): void {
    const now = new Date();
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    lastDay.setHours(23, 59, 59, 999);
    const diff = Math.max(0, lastDay.getTime() - Date.now());
    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
    this.cartControl.updateCountdown(`${d}d ${h}h`);
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

  private scrollToSection(id: string): void {
    const section = document.getElementById(id);
    if (!section) {
      return;
    }
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}
