import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { tap } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { CartControlService } from '../../services/cart-control.service';
import { CatalogData, DashboardCampaign, DashboardProduct } from '../../models/user-dashboard.model';
import { ProductCategory } from '../../models/admin.model';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { FeatureBadgeComponent } from '../../components/feature-badge/feature-badge.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { RevealOnScrollDirective } from '../../directives/reveal-on-scroll.directive';
import { UiAhorroSocioComponent } from '../../components/ui-ahorro-socio/ui-ahorro-socio.component';
import { ModoVisible, PlanSocioService } from '../../services/plan-socio.service';

@Component({
  selector: 'app-tienda',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiFormFieldComponent, UiButtonComponent, FeatureBadgeComponent, UiHeaderComponent, UiFooterComponent, RevealOnScrollDirective, UiAhorroSocioComponent],
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
    vpPoints?: number;
    copyWhatsapp?: string;
    copyInstagram?: string;
    copyFacebook?: string;
  } | null = null;

  allProducts: DashboardProduct[] = [];
  categories: ProductCategory[] = [];
  selectedCategoryId = '';

  // ── Paquete C · ronda 26 · propuesta 22 ──
  /** Lo que la persona escribe en el buscador de la tienda. */
  searchTerm = '';
  /** Se muestra un momento tras copiar el enlace del producto. */
  enlaceCopiado = false;
  private enlaceCopiadoTimeout?: number;

  form = {
    firstName: '',
    apellidoPaterno: '',
    apellidoMaterno: '',
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
    private readonly cartControl: CartControlService,
    private readonly planSocio: PlanSocioService
  ) {}

  /** Neto ya comprado este mes (solo con sesión en modo cliente); sirve para "como socia habrías ahorrado". */
  monthNetSocio = 0;

  get modoVisible(): ModoVisible {
    return this.planSocio.modoActual;
  }

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('refToken') ?? '';
    // `#/tienda/producto/:id` es una ruta distinta de `#/tienda/:refToken` (tres segmentos contra
    // dos): entrar por el enlace de un producto no toca la atribución de la patrocinadora.
    const porRuta = this.route.snapshot.paramMap.get('id') ?? '';
    const product = porRuta || this.route.snapshot.queryParamMap.get('p') || this.getHashQueryParam('p');
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
    // Paquete B: con sesión se confirma el modo y el neto del mes para el ahorro como socia.
    if (this.authService.hasSession) {
      this.planSocio.modo().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (respuesta) => {
          this.monthNetSocio = respuesta.indicators?.monthSpend ?? 0;
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck()
      });
    }
    this.planSocio.modo$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.cdr.markForCheck());
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
  get heroImage(): string {
    if (this.selectedVariantId) {
      const variant = this.featuredVariants.find((v) => v.id === this.selectedVariantId);
      if (variant?.img) return variant.img;
    }
    return this.featuredProduct?.img || this.defaultHero.img;
  }
  get heroTags(): string[] {
    const tags = (this.featuredProduct?.tags ?? []).map((t) => (t || '').trim()).filter(Boolean);
    return tags.length ? tags : this.defaultHero.tags;
  }
  get heroPrice(): number { return this.activeVariantPrice; }
  get heroName(): string { return this.featuredProduct?.name || this.defaultHero.name; }

  get availableCategories(): ProductCategory[] {
    const usedIds = new Set(this.allProducts.flatMap((p) => p.categoryIds ?? []));
    return this.categories.filter((c) => usedIds.has(c.id) && c.active !== false);
  }

  get filteredProducts(): DashboardProduct[] {
    const porCategoria = this.selectedCategoryId
      ? this.allProducts.filter((p) => (p.categoryIds ?? []).includes(this.selectedCategoryId))
      : this.allProducts;
    const busqueda = this.normalizarTexto(this.searchTerm);
    if (!busqueda) {
      return porCategoria;
    }
    // Ernesto leyó los trece nombres uno por uno con la vista cansada, y "omega 3" ya vive en las
    // etiquetas del producto: se busca en nombre, etiquetas y descripción, sin acentos ni mayúsculas.
    const palabras = busqueda.split(/\s+/).filter(Boolean);
    return porCategoria.filter((producto) => {
      const texto = this.textoBuscableDe(producto);
      return palabras.every((palabra) => texto.includes(palabra));
    });
  }

  /** Minúsculas y sin acentos: "colageno" encuentra "Colágeno" y al revés. */
  private normalizarTexto(valor: string): string {
    return String(valor ?? '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  private textoBuscableDe(producto: DashboardProduct): string {
    const partes = [producto.name, producto.description, producto.badge, ...(producto.tags ?? [])];
    return this.normalizarTexto(partes.filter(Boolean).join(' '));
  }

  get hasSearch(): boolean {
    return Boolean(this.normalizarTexto(this.searchTerm));
  }

  clearSearch(): void {
    this.searchTerm = '';
  }

  /** "3 de 13 productos" / "Ningún producto coincide con …": la lista dice siempre qué está mostrando. */
  get resultadoBusquedaTexto(): string {
    const total = this.allProducts.length;
    const mostrados = this.filteredProducts.length;
    if (!this.hasSearch && !this.selectedCategoryId) {
      return `${total} producto${total === 1 ? '' : 's'}`;
    }
    return `${mostrados} de ${total} producto${total === 1 ? '' : 's'}`;
  }

  selectCategory(id: string): void {
    this.selectedCategoryId = this.selectedCategoryId === id ? '' : id;
  }

  selectProduct(product: DashboardProduct): void {
    this.featuredProduct = this.mapProduct(product);
    this.selectedVariantId = '';
    this.productId = product.id;
    // La dirección de la barra cambia con el producto que se está viendo, para poder mandarlo.
    void this.router.navigate(['/tienda/producto', product.id], { replaceUrl: true });
    document.getElementById('hero')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /** Enlace directo al producto que se está viendo (Julio no tenía qué mandarle a un cliente). */
  get enlaceDelProducto(): string {
    const id = this.featuredProduct?.id ?? '';
    if (!id || typeof window === 'undefined') {
      return '';
    }
    const { origin, pathname } = window.location;
    return `${origin}${pathname}#/tienda/producto/${encodeURIComponent(id)}`;
  }

  copiarEnlaceDelProducto(): void {
    const enlace = this.enlaceDelProducto;
    if (!enlace) {
      return;
    }
    void navigator.clipboard?.writeText(enlace);
    this.enlaceCopiado = true;
    this.cdr.markForCheck();
    if (this.enlaceCopiadoTimeout) {
      window.clearTimeout(this.enlaceCopiadoTimeout);
    }
    this.enlaceCopiadoTimeout = window.setTimeout(() => {
      this.enlaceCopiado = false;
      this.cdr.markForCheck();
    }, 2500);
  }

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
    if (!this.form.firstName.trim() || !this.form.apellidoPaterno.trim() || !this.form.email || !this.form.password) {
      this.setFeedback('Completa los campos obligatorios.', 'error');
      return;
    }
    if (this.form.password !== this.form.confirmPassword) {
      this.setFeedback('Las contraseñas no coinciden.', 'error');
      return;
    }
    const fullName = `${this.form.firstName.trim()} ${this.form.apellidoPaterno.trim()} ${this.form.apellidoMaterno.trim()}`.trim();
    const payload = {
      name: fullName,
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
        if (response?.requiresEmailVerification) {
          this.form = { firstName: '', apellidoPaterno: '', apellidoMaterno: '', email: '', phone: '', password: '', confirmPassword: '' };
          this.setFeedback('Solo falta un paso, confirma tu cuenta desde tu correo electrónico.', 'success');
          this.cdr.detectChanges();
          return;
        }
        if (response?.customer) {
          this.authService.setUserFromCreateAccount(response.customer);
        }
        this.form = { firstName: '', apellidoPaterno: '', apellidoMaterno: '', email: '', phone: '', password: '', confirmPassword: '' };
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
    // La tienda solo necesita catálogo. Antes usaba el `/user-dashboard`
    // monolítico, que además cargaba la red completa del sistema (1 GetItem
    // por cliente) en la pantalla más visitada de la app.
    this.api.getCatalogData().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => {
        this.isLoading = false;
        this.allProducts = (data.products ?? []).filter((p) => p.inOnlineStore !== false);
        this.categories = data.categories ?? [];
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

  private pickFromQuery(data: CatalogData, queryId: string): TiendaComponent['featuredProduct'] | null {
    if (queryId.startsWith('campaign:')) {
      const campaignId = queryId.slice('campaign:'.length);
      const campaign = (data.campaigns ?? []).find((c) => c.id === campaignId);
      if (campaign) return this.mapCampaign(campaign);
    }
    const productMatch = data.products?.find((p) => p.id === queryId);
    if (productMatch) return this.mapProduct(productMatch);
    return null;
  }

  private pickDefaultProduct(data: CatalogData): TiendaComponent['featuredProduct'] | null {
    if (data.productOfMonth) {
      const p = data.productOfMonth;
      return { id: p.id, name: p.name, badge: p.badge, title: 'Cuida tu cuerpo.', accent: p.name, tail: 'Empieza hoy.', description: p.description || this.defaultHero.description, ctaPrimaryText: 'Agregar al carrito', ctaSecondaryText: 'Ver beneficios', img: p.img, tags: p.tags?.length ? p.tags : [], price: p.price };
    }
    if (data.products?.length) return this.mapProduct(data.products[0]);
    return null;
  }

  mapProduct(p: DashboardProduct): TiendaComponent['featuredProduct'] {
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
