import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { tap } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { CartControlService } from '../../services/cart-control.service';
import { UserDashboardData, DashboardCampaign, DashboardProduct } from '../../models/user-dashboard.model';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { FeatureBadgeComponent } from '../../components/feature-badge/feature-badge.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';

@Component({
  selector: 'app-tienda',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiFormFieldComponent, UiButtonComponent, FeatureBadgeComponent, UiHeaderComponent, UiFooterComponent],
  templateUrl: './tienda.component.html'
})
export class TiendaComponent implements OnInit {
  readonly currentYear = new Date().getFullYear();

  readonly defaultHero = {
    name: 'COLÁGENO',
    badge: 'Bienestar avanzado · Uso diario · Resultados medibles',
    title: 'Cuida tu cuerpo.',
    accent: 'Potencia tu energía.',
    tail: 'Empieza hoy.',
    description: 'Productos de bienestar de alta calidad con resultados medibles.',
    ctaPrimaryText: 'Agregar al carrito',
    ctaSecondaryText: 'Ver beneficios',
    img: 'images/Colageno-Clean.png',
    tags: ['Energía diaria', 'Recuperación', 'Salud integral'],
    price: 0
  };

  referralToken = '';
  productId = '';
  isLoading = true;

  featuredProduct: {
    id: string;
    name: string;
    badge?: string;
    title?: string;
    accent?: string;
    tail?: string;
    description?: string;
    ctaPrimaryText?: string;
    ctaSecondaryText?: string;
    img: string;
    tags: string[];
    price?: number;
    copyWhatsapp?: string;
    copyInstagram?: string;
    copyFacebook?: string;
  } | null = null;

  allProducts: DashboardProduct[] = [];

  form = {
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  };
  isSubmitting = false;
  feedbackMessage = '';
  feedbackType: 'error' | 'success' | '' = '';
  selectedVariantId = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef,
    private readonly destroyRef: DestroyRef,
    private readonly router: Router,
    private readonly authService: AuthService,
    private readonly cartControl: CartControlService
  ) {}

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('refToken') ?? '';
    const product = this.route.snapshot.queryParamMap.get('p') ?? this.getHashQueryParam('p');
    this.referralToken = token.trim();
    this.productId = product.trim();
    if (this.referralToken) {
      localStorage.setItem('leaderId', this.referralToken);
    }
    // Ensure cart is loaded and keep UI in sync reactively
    this.cartControl.load();
    this.cartControl.data$.pipe(
      tap(() => this.cdr.detectChanges()),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe();
    this.loadData();
  }

  get cartCount(): number { return this.cartControl.itemsCount; }
  get cartSubtotal(): number { return this.cartControl.subtotal; }
  get cartGapToGoal(): number { return this.cartControl.gapToGoal; }
  get cartBenefitPercent(): number { return this.cartControl.benefitPercent; }
  get cartHasGoal(): boolean { return (this.cartControl.user?.activeSpendTarget ?? 0) > 0; }
  formatMoney(n: number): string { return this.cartControl.formatMoney(n); }

  get heroTitle(): string { return this.featuredProduct?.title || this.defaultHero.title; }
  get heroAccent(): string { return this.featuredProduct?.accent || this.defaultHero.accent; }
  get heroTail(): string { return this.featuredProduct?.tail || this.defaultHero.tail; }
  get heroDescription(): string { return this.featuredProduct?.description || this.defaultHero.description; }
  get heroBadge(): string { return this.featuredProduct?.badge || this.defaultHero.badge; }
  get heroPrimaryCta(): string { return this.featuredProduct?.ctaPrimaryText || this.defaultHero.ctaPrimaryText; }
  get heroSecondaryCta(): string { return this.featuredProduct?.ctaSecondaryText || this.defaultHero.ctaSecondaryText; }
  get heroImage(): string { return this.featuredProduct?.img || this.defaultHero.img; }
  get heroTags(): string[] { const t = this.featuredProduct?.tags ?? []; return t.length ? t : this.defaultHero.tags; }
  get heroPrice(): number { return this.activeVariantPrice; }
  get heroName(): string { return this.featuredProduct?.name || this.defaultHero.name; }

  get featuredVariants() {
    const product = this.allProducts.find((p) => p.id === this.featuredProduct?.id);
    return product?.variants?.filter((v) => v.active !== false) ?? [];
  }

  get activeVariantPrice(): number {
    const base = this.featuredProduct?.price ?? 0;
    if (!this.selectedVariantId) return base;
    const variant = this.featuredVariants.find((v) => v.id === this.selectedVariantId);
    return variant?.price ?? base;
  }

  getTagClass(index: number): string {
    return index % 2 === 0
      ? 'inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-500/15 px-3 py-1 text-xs text-sand-200'
      : 'inline-flex items-center gap-2 rounded-full border border-yellow-400/20 bg-yellow-400/15 px-3 py-1 text-xs text-sand-200';
  }

  getTagIcon(index: number): string {
    return index % 2 === 0 ? 'fa-solid fa-bolt' : 'fa-solid fa-seedling';
  }

  scrollTo(sectionId: string, event?: Event): void {
    event?.preventDefault();
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  addToCart(): void {
    const product = this.allProducts.find((p) => p.id === this.featuredProduct?.id);
    if (!product) return;
    const variant = this.featuredVariants.find((v) => v.id === this.selectedVariantId);
    const price = variant?.price ?? product.price;
    const name = variant ? `${product.name} – ${variant.name}` : product.name;
    this.cartControl.addItem(
      { id: product.id, name, price, qty: 1, note: this.selectedVariantId, img: product.img },
      1
    );
  }

  goToCart(): void {
    void this.router.navigate(['/carrito']);
  }

  createAccount(): void {
    if (this.isSubmitting) return;
    if (!this.form.name || !this.form.email || !this.form.password) {
      this.setFeedback('Completa los campos obligatorios.', 'error');
      return;
    }
    if (this.form.password !== this.form.confirmPassword) {
      this.setFeedback('Las contraseñas no coinciden.', 'error');
      return;
    }
    const payload = {
      name: this.form.name.trim(),
      email: this.form.email.trim(),
      phone: this.form.phone.trim() || undefined,
      password: this.form.password,
      confirmPassword: this.form.confirmPassword,
      referralToken: this.referralToken || undefined,
      productId: this.productId || undefined
    };
    this.isSubmitting = true;
    this.api.createAccount(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (response) => {
        this.isSubmitting = false;
        if (response?.customer) {
          this.authService.setUserFromCreateAccount(response.customer);
        }
        this.form = { name: '', email: '', phone: '', password: '', confirmPassword: '' };
        this.setFeedback('', 'success');
        this.cdr.detectChanges();
        this.router.navigate(['/dashboard']);
      },
      error: (error: any) => {
        this.isSubmitting = false;
        const msg = error?.error?.message || error?.error?.Error || error?.message || 'No se pudo crear la cuenta.';
        this.setFeedback(msg, 'error');
        this.cdr.detectChanges();
      }
    });
  }

  private setFeedback(message: string, type: 'error' | 'success'): void {
    this.feedbackMessage = message;
    this.feedbackType = type;
  }

  private loadData(): void {
    this.api.getUserDashboardData().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => {
        this.isLoading = false;
        this.allProducts = data.products ?? [];
        const queryId = this.productId.trim();
        const fromQuery = queryId ? this.pickFromQuery(data, queryId) : null;
        const defaultProduct = this.pickDefaultProduct(data);
        this.featuredProduct = fromQuery ?? defaultProduct;
        this.selectedVariantId = '';
        if (fromQuery?.id) { this.productId = fromQuery.id; }
        else if (defaultProduct?.id) { this.productId = defaultProduct.id; }
        this.cdr.detectChanges();
      },
      error: () => { this.isLoading = false; this.cdr.detectChanges(); }
    });
  }

  private pickFromQuery(data: UserDashboardData, queryId: string): TiendaComponent['featuredProduct'] | null {
    if (queryId.startsWith('campaign:')) {
      const campaignId = queryId.slice('campaign:'.length);
      const campaign = (data.campaigns ?? []).find((c) => c.id === campaignId);
      if (campaign) return this.mapCampaign(campaign);
    }
    const productMatch = data.products?.find((p) => p.id === queryId);
    if (productMatch) return this.mapProduct(productMatch);
    return null;
  }

  private pickDefaultProduct(data: UserDashboardData): TiendaComponent['featuredProduct'] | null {
    if (data.productOfMonth) {
      const p = data.productOfMonth;
      return { id: p.id, name: p.name, badge: p.badge, title: 'Cuida tu cuerpo.', accent: p.name, tail: 'Empieza hoy.', description: p.description || this.defaultHero.description, ctaPrimaryText: 'Agregar al carrito', ctaSecondaryText: 'Ver beneficios', img: p.img, tags: p.tags?.length ? p.tags : [], price: p.price };
    }
    if (data.products?.length) return this.mapProduct(data.products[0]);
    return null;
  }

  private mapProduct(p: DashboardProduct): TiendaComponent['featuredProduct'] {
    return {
      id: p.id,
      name: p.name,
      badge: p.badge,
      title: 'Cuida tu cuerpo.',
      accent: p.name,
      tail: 'Empieza hoy.',
      description: p.description || this.defaultHero.description,
      ctaPrimaryText: 'Agregar al carrito',
      ctaSecondaryText: 'Ver beneficios',
      img: p.img,
      tags: p.tags?.length ? p.tags : p.badge ? [p.badge] : [],
      price: p.price,
      copyWhatsapp: p.copyWhatsapp,
      copyInstagram: p.copyInstagram,
      copyFacebook: p.copyFacebook
    };
  }

  private mapCampaign(c: DashboardCampaign): TiendaComponent['featuredProduct'] {
    return {
      id: `campaign:${c.id}`,
      name: c.name,
      badge: c.heroBadge || '',
      title: c.heroTitle || this.defaultHero.title,
      accent: c.heroAccent || this.defaultHero.accent,
      tail: c.heroTail || this.defaultHero.tail,
      description: c.heroDescription || c.description || this.defaultHero.description,
      ctaPrimaryText: c.ctaPrimaryText || 'Agregar al carrito',
      ctaSecondaryText: c.ctaSecondaryText || 'Ver beneficios',
      img: c.heroImage || c.banner || c.feed || c.story || this.defaultHero.img,
      tags: c.benefits?.length ? c.benefits : []
    };
  }

  private getHashQueryParam(param: string): string {
    if (typeof window === 'undefined') return '';
    try {
      const hash = window.location.hash ?? '';
      const qi = hash.indexOf('?');
      if (qi === -1) return '';
      return new URLSearchParams(hash.slice(qi + 1)).get(param) ?? '';
    } catch { return ''; }
  }
}
