import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

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
export class CarritoComponent {
  readonly countdownLabel = '3d 8h';
  readonly shipping = 0;
  readonly discountPct = 0.05;
  readonly user = {
    monthSpendActual: 45,
    activeSpendTarget: 60
  };

  readonly cartItems: CartItem[] = [
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
}
