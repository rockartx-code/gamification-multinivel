import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

interface Goal {
  key: string;
  title: string;
  subtitle: string;
  target: number;
  base: number;
  cart: number;
  ctaText: string;
  ctaFragment: string;
  isCountGoal?: boolean;
}

interface Product {
  id: string;
  name: string;
  price: number;
  badge: string;
  img: string;
}

interface NetworkMember {
  name: string;
  level: string;
  spend: number;
  status: 'Activa' | 'En progreso' | 'Inactiva';
}

interface FeaturedItem {
  id: string;
  label: string;
  hook: string;
  story: string;
  feed: string;
  banner: string;
}

@Component({
  selector: 'app-user-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './user-dashboard.component.html',
  styleUrl: './user-dashboard.component.css'
})
export class UserDashboardComponent implements OnInit, OnDestroy {
  readonly countdownLabel = signal('3d 12h 20m 10s');
  readonly cutoffDay = 25;
  readonly cutoffHour = 23;
  readonly cutoffMinute = 59;
  readonly userCode = 'ABC123';
  readonly networkGoal = 300;
  activeFeaturedId = 'colageno';
  socialFormat: 'story' | 'feed' | 'banner' = 'story';
  goalsCollapsed = false;
  toastMessage = 'Actualizado.';
  isToastVisible = false;
  captionText = '';
  heroQty = 0;

  goals: Goal[] = [
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
  ];

  products: Product[] = [
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
  ];

  readonly buyAgainIds = new Set(['omega3', 'complejoB', 'antioxidante']);

  readonly networkMembers: NetworkMember[] = [
    { name: 'María G.', level: 'L1', spend: 80, status: 'Activa' },
    { name: 'Luis R.', level: 'L1', spend: 25, status: 'En progreso' },
    { name: 'Ana P.', level: 'L1', spend: 0, status: 'Inactiva' },
    { name: 'Carlos V.', level: 'L2', spend: 40, status: 'Activa' },
    { name: 'Sofía M.', level: 'L2', spend: 15, status: 'En progreso' },
    { name: 'Diego S.', level: 'L2', spend: 0, status: 'Inactiva' }
  ];

  readonly featured: FeaturedItem[] = [
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
  ];

  private cart: Record<string, number> = {};
  private countdownInterval?: number;
  private toastTimeout?: number;

  get buyAgainProducts(): Product[] {
    return this.products.filter((product) => this.buyAgainIds.has(product.id));
  }

  get otherProducts(): Product[] {
    return this.products.filter((product) => !this.buyAgainIds.has(product.id));
  }

  get productsCount(): string {
    return `${this.products.length} productos`;
  }

  get activeFeatured(): FeaturedItem {
    return this.featured.find((item) => item.id === this.activeFeaturedId) ?? this.featured[0];
  }

  get referralLink(): string {
    return `https://tu-dominio.com/r/${this.userCode}?p=${this.activeFeatured.id}`;
  }

  get networkProgress(): number {
    return this.networkMembers.reduce((acc, member) => acc + member.spend, 0);
  }

  get networkPercent(): number {
    return Math.min(100, (this.networkProgress / this.networkGoal) * 100);
  }

  get levelOneCount(): number {
    return this.networkMembers.filter((member) => member.level === 'L1').length;
  }

  get levelTwoCount(): number {
    return this.networkMembers.filter((member) => member.level === 'L2').length;
  }

  get activeCount(): number {
    return this.networkMembers.filter((member) => member.status === 'Activa').length;
  }

  get cartTotal(): number {
    return this.products.reduce((total, product) => {
      const qty = this.cart[product.id] ?? 0;
      return total + product.price * qty;
    }, 0);
  }

  get socialFormatLabel(): string {
    if (this.socialFormat === 'feed') {
      return 'Feed (1:1)';
    }
    if (this.socialFormat === 'banner') {
      return 'Banner (16:9)';
    }
    return 'Story (9:16)';
  }

  get socialAspectRatio(): string {
    if (this.socialFormat === 'feed') {
      return '1/1';
    }
    if (this.socialFormat === 'banner') {
      return '16/9';
    }
    return '9/16';
  }

  get activeSocialAsset(): string {
    if (this.socialFormat === 'feed') {
      return this.activeFeatured.feed;
    }
    if (this.socialFormat === 'banner') {
      return this.activeFeatured.banner;
    }
    return this.activeFeatured.story;
  }

  ngOnInit(): void {
    this.updateCountdown();
    this.countdownInterval = window.setInterval(() => this.updateCountdown(), 1000);
  }

  ngOnDestroy(): void {
    if (this.countdownInterval) {
      window.clearInterval(this.countdownInterval);
    }
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
  }

  formatMoney(value: number): string {
    return `$${value.toFixed(0)}`;
  }

  goalBasePercent(goal: Goal): number {
    return Math.min(100, (goal.base / goal.target) * 100);
  }

  goalCartPercent(goal: Goal): number {
    if (goal.isCountGoal) {
      return 0;
    }
    const basePercent = this.goalBasePercent(goal);
    const cartPercent = (goal.cart / goal.target) * 100;
    return Math.min(100 - basePercent, Math.max(0, cartPercent));
  }

  goalProgressLabel(goal: Goal): string {
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

  toggleGoals(): void {
    this.goalsCollapsed = !this.goalsCollapsed;
  }

  setFeatured(id: string): void {
    this.activeFeaturedId = id;
  }

  setSocialFormat(format: 'story' | 'feed' | 'banner'): void {
    this.socialFormat = format;
  }

  copyLink(): void {
    this.copyToClipboard(this.referralLink, 'Link copiado.');
  }

  copyAssetPath(): void {
    this.copyToClipboard(this.activeSocialAsset, 'Ruta copiada.');
  }

  generateTemplate(): void {
    const template = `✨ ${this.activeFeatured.label}\n${this.activeFeatured.hook}\n\nConsíguelo aquí 👉 ${this.referralLink}`;
    this.captionText = template;
    this.showToast('Template generado.');
  }

  copyCaption(): void {
    const text = this.captionText.trim();
    if (!text) {
      this.showToast('Escribe un copy primero.');
      return;
    }
    this.copyToClipboard(text, 'Copy copiado.');
  }

  updateCart(productId: string, qty: number): void {
    const normalized = Math.max(0, Math.floor(qty));
    if (normalized === 0) {
      delete this.cart[productId];
    } else {
      this.cart[productId] = normalized;
    }
    if (productId === 'colageno') {
      this.heroQty = normalized;
    }
    this.syncGoalCartTotals();
    if (this.cartTotal > 0) {
      this.showToast(`En carrito: ${this.formatMoney(this.cartTotal)} (pendiente de pago)`);
    }
  }

  addQuick(productId: string, addQty: number): void {
    const current = this.cart[productId] ?? 0;
    this.updateCart(productId, current + addQty);
  }

  setHeroQty(value: number): void {
    this.heroQty = Math.max(0, Math.floor(value));
    this.updateCart('colageno', this.heroQty);
  }

  addHeroToCart(): void {
    if (this.heroQty <= 0) {
      this.heroQty = 1;
    }
    this.addQuick('colageno', 1);
    this.heroQty = this.cart['colageno'] ?? 0;
  }

  getCartQty(productId: string): number {
    return this.cart[productId] ?? 0;
  }

  showCartToast(): void {
    this.showToast(`Carrito: ${this.formatMoney(this.cartTotal)}`);
  }

  scrollToGoal(goalId: string): void {
    const node = document.getElementById(goalId);
    if (!node) {
      return;
    }
    node.scrollIntoView({ behavior: 'smooth', block: 'center' });
    node.classList.add('ring-2', 'ring-yellow-400/60');
    window.setTimeout(() => node.classList.remove('ring-2', 'ring-yellow-400/60'), 1200);
  }

  scrollToSection(sectionId: string): void {
    const node = document.getElementById(sectionId);
    if (!node) {
      return;
    }
    node.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  notifyAction(message: string): void {
    this.showToast(message);
  }

  simulateInvite(): void {
    this.showToast('Invitación enviada (mock).');
  }

  private syncGoalCartTotals(): void {
    this.goals = this.goals.map((goal) => {
      if (goal.key === 'active' || goal.key === 'discount') {
        return { ...goal, cart: this.cartTotal };
      }
      return goal;
    });
  }

  private updateCountdown(): void {
    const diff = Math.max(0, this.getNextCutoffDate().getTime() - Date.now());
    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
    const m = Math.floor((diff / (1000 * 60)) % 60);
    const s = Math.floor((diff / 1000) % 60);
    this.countdownLabel.set(`${d}d ${h}h ${m}m ${s}s`);
  }

  private getNextCutoffDate(): Date {
    const now = new Date();
    let cutoff = new Date(
      now.getFullYear(),
      now.getMonth(),
      this.cutoffDay,
      this.cutoffHour,
      this.cutoffMinute,
      59,
      999
    );
    if (cutoff.getTime() <= now.getTime()) {
      cutoff = new Date(
        now.getFullYear(),
        now.getMonth() + 1,
        this.cutoffDay,
        this.cutoffHour,
        this.cutoffMinute,
        59,
        999
      );
    }
    return cutoff;
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

  private copyToClipboard(text: string, toastMessage: string): void {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(() => this.showToast(toastMessage))
        .catch(() => this.showToast('No se pudo copiar.'));
      return;
    }
    this.showToast('No se pudo copiar.');
  }
}
