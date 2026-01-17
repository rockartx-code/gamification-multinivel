import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

interface Goal {
  key: string;
  title: string;
  subtitle: string;
  target: number;
  base: number;
  cart: number;
  ctaText: string;
  ctaHref: string;
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
  imports: [CommonModule],
  templateUrl: './user-dashboard.component.html',
  styleUrl: './user-dashboard.component.css'
})
export class UserDashboardComponent {
  readonly countdownLabel = '3d 12h 20m 10s';
  readonly userCode = 'ABC123';
  readonly networkGoal = 300;
  readonly cartTotal = 0;
  readonly activeFeaturedId = 'colageno';
  readonly socialFormatLabel = 'Story (9:16)';
  readonly socialAspectRatio = '9/16';

  readonly goals: Goal[] = [
    {
      key: 'active',
      title: 'Siguiente reto: Usuario activo',
      subtitle: 'Completa tu consumo mínimo del mes',
      target: 60,
      base: 45,
      cart: 0,
      ctaText: 'Ir a tienda',
      ctaHref: '#merchant'
    },
    {
      key: 'discount',
      title: 'Siguiente nivel de descuento',
      subtitle: 'Alcanza el umbral para mejorar tu beneficio',
      target: 120,
      base: 45,
      cart: 0,
      ctaText: 'Completar consumo',
      ctaHref: '#merchant'
    },
    {
      key: 'invite',
      title: 'Crecer tu red',
      subtitle: 'Agrega 1 usuario nuevo este mes',
      target: 1,
      base: 0,
      cart: 0,
      ctaText: 'Invitar ahora',
      ctaHref: '#links',
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
      ctaHref: '#links'
    }
  ];

  readonly products: Product[] = [
    {
      id: 'colageno',
      name: 'COLÁGENO',
      price: 35,
      badge: 'Regeneración',
      img: 'assets/images/product-colageno.svg'
    },
    {
      id: 'omega3',
      name: 'OMEGA-3',
      price: 29,
      badge: 'Cuerpo & mente',
      img: 'assets/images/product-omega3.svg'
    },
    {
      id: 'creatina',
      name: 'CREATINA',
      price: 27,
      badge: 'Fuerza',
      img: 'assets/images/product-creatina.svg'
    },
    {
      id: 'complejoB',
      name: 'COMPLEJO B',
      price: 24,
      badge: 'Energía',
      img: 'assets/images/product-complejo-b.svg'
    },
    {
      id: 'antioxidante',
      name: 'ANTIOXIDANTE',
      price: 31,
      badge: 'Longevidad',
      img: 'assets/images/product-antioxidante.svg'
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
      story: 'assets/images/social-story.svg',
      feed: 'assets/images/social-feed.svg',
      banner: 'assets/images/social-banner.svg'
    },
    {
      id: 'omega3',
      label: 'OMEGA-3',
      hook: 'Cuerpo y mente, todos los días.',
      story: 'assets/images/social-story.svg',
      feed: 'assets/images/social-feed.svg',
      banner: 'assets/images/social-banner.svg'
    },
    {
      id: 'creatina',
      label: 'CREATINA',
      hook: 'Potencia y rendimiento.',
      story: 'assets/images/social-story.svg',
      feed: 'assets/images/social-feed.svg',
      banner: 'assets/images/social-banner.svg'
    },
    {
      id: 'antioxidante',
      label: 'ANTIOXIDANTE',
      hook: 'Brilla hoy. Longevidad mañana.',
      story: 'assets/images/social-story.svg',
      feed: 'assets/images/social-feed.svg',
      banner: 'assets/images/social-banner.svg'
    }
  ];

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

  formatMoney(value: number): string {
    return `$${value.toFixed(0)}`;
  }

  goalBasePercent(goal: Goal): number {
    return Math.min(100, (goal.base / goal.target) * 100);
  }

  goalCartPercent(goal: Goal): number {
    if (goal.isCountGoal) {
      return this.goalBasePercent(goal);
    }
    return Math.min(100, ((goal.base + goal.cart) / goal.target) * 100);
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
}
