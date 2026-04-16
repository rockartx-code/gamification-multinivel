import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { CatalogData, FeaturedItem, DashboardCampaign, SponsorContact } from '../../models/user-dashboard.model';
import { AppBusinessConfig, BonusRule, RankThreshold } from '../../models/admin.model';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { FeatureBadgeComponent } from '../../components/feature-badge/feature-badge.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiFormFieldComponent, UiButtonComponent, FeatureBadgeComponent, UiHeaderComponent, UiFooterComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css'
})
export class LandingComponent implements OnInit {
  readonly currentYear = new Date().getFullYear();
  readonly defaultHero = {
    id: '',
    name: 'COLAGENO',
    badge: 'Bienestar avanzado · Uso diario · Resultados medibles',
    title: 'Cuida tu cuerpo.',
    accent: 'Potencia tu energia.',
    tail: 'Compartelo.',
    description: 'Un sistema de bienestar con recompensas: mejoras tu y ayudas a otros a mejorar.',
    ctaPrimaryText: 'Obtenerlo ahora',
    ctaSecondaryText: 'Ver recompensas',
    img: 'images/Colageno-Clean.png',
    tags: ['Energia diaria', 'Recuperación', 'Salud integral', 'Recompensas']
  };

  form = {
    firstName: '',
    apellidoPaterno: '',
    apellidoMaterno: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  };

  referralToken = '';
  referralCodeInput = '';
  productId = '';
  sponsor: SponsorContact | null = null;
  businessConfig: AppBusinessConfig | null = null;
  isSubmitting = false;
  feedbackMessage = '';
  feedbackType: 'error' | 'success' | '' = '';
  registrationState: 'form' | 'pending' = 'form';
  registeredEmail = '';
  fieldErrors: { firstName: string; apellidoPaterno: string; apellidoMaterno: string; email: string; password: string; confirmPassword: string } = {
    firstName: '',
    apellidoPaterno: '',
    apellidoMaterno: '',
    email: '',
    password: '',
    confirmPassword: ''
  };
  featuredProduct: {
    id: string;
    name: string;
    hook: string;
    badge?: string;
    title?: string;
    accent?: string;
    tail?: string;
    description?: string;
    ctaPrimaryText?: string;
    ctaSecondaryText?: string;
    img: string;
    tags: string[];
  } | null = null;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef,
    private readonly destroyRef: DestroyRef,
    private readonly router: Router,
    private readonly authService: AuthService
  ) {}

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('idSponsor') ?? '';
    const product = this.route.snapshot.queryParamMap.get('p') ?? this.getHashQueryParam('p');
    this.referralToken = token.trim();
    this.productId = product.trim();
    if (this.referralToken) {
      localStorage.setItem('leaderId', this.referralToken);
      this.loadSponsorContact(this.referralToken);
    }
    this.loadFeaturedProduct(this.productId);
    this.loadBusinessConfig();
  }

  // ─── Business config derived getters ────────────────────────────────────────

  get discountTiers(): Array<{ min: number; max: number | null; rate: number }> {
    return this.businessConfig?.rewards?.discountTiers ?? [];
  }

  get commissionLevels(): AppBusinessConfig['rewards']['commissionLevels'] {
    return this.businessConfig?.rewards?.commissionLevels ?? [];
  }

  get mxnPerVp(): number {
    return this.businessConfig?.bonuses?.vpConfig?.mxnPerVp ?? 50;
  }

  get rankThresholds(): RankThreshold[] {
    return this.businessConfig?.bonuses?.rankThresholds ?? [
      { rank: 'ORO', vgMin: 700 },
      { rank: 'PLATINO', vgMin: 2000 },
      { rank: 'DIAMANTE', vgMin: 6000 }
    ];
  }

  get activeBonus_inicioRapido(): BonusRule | null {
    return this.businessConfig?.bonuses?.rules?.find(r => r.id === 'inicio_rapido' && r.active) ?? null;
  }

  /** Reglas de bono agrupadas por rango */
  get rulesByRank(): Array<{ rank: RankThreshold; rules: BonusRule[] }> {
    const rules = this.businessConfig?.bonuses?.rules ?? [];
    return this.rankThresholds.map(rt => ({
      rank: rt,
      rules: rules.filter(r => r.active && r.rank === rt.rank)
    }));
  }

  rankIcon(rank: string): string {
    switch (rank.toUpperCase()) {
      case 'ORO':      return '🥇';
      case 'PLATINO':  return '🥈';
      case 'DIAMANTE': return '💎';
      default:         return '⭐';
    }
  }

  rewardLabel(rule: BonusRule): string {
    return rule.rewards.map(r => {
      if (r.type === 'cash_mxn' && r.amount) return `$${r.amount.toLocaleString('es-MX')} MXN`;
      if (r.type === 'monthly_cash' && r.amount) return `$${r.amount.toLocaleString('es-MX')} MXN/mes`;
      if (r.type === 'item' && r.itemLabel) return r.itemLabel;
      if (r.type === 'annual_fund_pct' && r.pct) return `${r.pct}% fondo anual`;
      return '';
    }).filter(Boolean).join(' · ');
  }

  discountRateLabel(rate: number): string {
    return `${Math.round(rate * 100)}% OFF`;
  }

  discountRangeLabel(tier: { min: number; max: number | null }): string {
    const min = `$${tier.min.toLocaleString('es-MX')}`;
    if (!tier.max) return `${min} o más`;
    return `De ${min} a $${tier.max.toLocaleString('es-MX')}`;
  }

  get heroTitle(): string {
    return this.featuredProduct?.title || this.defaultHero.title;
  }

  get heroAccent(): string {
    return this.featuredProduct?.accent || this.defaultHero.accent;
  }

  get heroTail(): string {
    return this.featuredProduct?.tail || this.defaultHero.tail;
  }

  get heroDescription(): string {
    return this.featuredProduct?.description || this.defaultHero.description;
  }

  get heroBadge(): string {
    return this.featuredProduct?.badge || this.defaultHero.badge;
  }

  get heroPrimaryCta(): string {
    return this.featuredProduct?.ctaPrimaryText || this.defaultHero.ctaPrimaryText;
  }

  get heroSecondaryCta(): string {
    return this.featuredProduct?.ctaSecondaryText || this.defaultHero.ctaSecondaryText;
  }

  get heroImage(): string {
    return this.featuredProduct?.img || this.defaultHero.img;
  }

  get sponsorName(): string {
    return this.sponsor?.name || 'tu promotor';
  }

  get sponsorFirstName(): string {
    return this.sponsorName.split(' ')[0];
  }

  get whatsappHref(): string {
    const raw = (this.sponsor?.phone ?? '').replace(/\D/g, '');
    if (!raw) return 'https://wa.me/';
    return `https://wa.me/${raw}?text=${encodeURIComponent('Hola, me llegó tu invitación y me interesa saber más.')}`;
  }

  get hasRealSponsor(): boolean {
    return !!this.sponsor && !this.sponsor.isDefault;
  }

  scrollTo(sectionId: string, event?: Event): void {
    event?.preventDefault();
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  get referralCodeDisplay(): string {
    return this.buildReferralCode(this.form.firstName, this.form.apellidoPaterno, this.form.apellidoMaterno);
  }

  createAccount(): void {
    if (this.isSubmitting) {
      return;
    }
    this.fieldErrors = {
      firstName: this.form.firstName.trim() ? '' : 'El nombre es obligatorio.',
      apellidoPaterno: this.form.apellidoPaterno.trim() ? '' : 'El apellido paterno es obligatorio.',
      apellidoMaterno: this.form.apellidoMaterno.trim() ? '' : 'El apellido materno es obligatorio.',
      email: this.form.email.trim() ? '' : 'El correo electrónico es obligatorio.',
      password: this.form.password ? '' : 'La contraseña es obligatoria.',
      confirmPassword: ''
    };
    if (this.fieldErrors.firstName || this.fieldErrors.apellidoPaterno || this.fieldErrors.apellidoMaterno || this.fieldErrors.email || this.fieldErrors.password) {
      return;
    }
    if (this.form.password !== this.form.confirmPassword) {
      this.fieldErrors.confirmPassword = 'Las contraseñas no coinciden.';
      return;
    }

    const fullName = `${this.form.firstName.trim()} ${this.form.apellidoPaterno.trim()} ${this.form.apellidoMaterno.trim()}`.trim();
    const effectiveToken = this.referralToken || this.referralCodeInput.trim() || undefined;

    const payload = {
      name: fullName,
      email: this.form.email.trim(),
      phone: this.form.phone.trim() || undefined,
      password: this.form.password,
      confirmPassword: this.form.confirmPassword,
      referralToken: effectiveToken,
      productId: this.productId || undefined
    };

    this.isSubmitting = true;
    this.api
      .createAccount(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.isSubmitting = false;
          if (response?.requiresEmailVerification) {
            this.setFeedback('', 'success');
            this.registeredEmail = this.form.email.trim();
            this.form = { firstName: '', apellidoPaterno: '', apellidoMaterno: '', email: '', phone: '', password: '', confirmPassword: '' };
            this.fieldErrors = { firstName: '', apellidoPaterno: '', apellidoMaterno: '', email: '', password: '', confirmPassword: '' };
            this.registrationState = 'pending';
            this.cdr.detectChanges();
            return;
          }
          if (response?.customer) {
            this.authService.setUserFromCreateAccount(response.customer);
          }
          this.form = { firstName: '', apellidoPaterno: '', apellidoMaterno: '', email: '', phone: '', password: '', confirmPassword: '' };
          this.fieldErrors = { firstName: '', apellidoPaterno: '', apellidoMaterno: '', email: '', password: '', confirmPassword: '' };
          this.setFeedback('', 'success');
          this.cdr.detectChanges();
          this.router.navigate(['/dashboard']);
        },
        error: (error: any) => {
          this.isSubmitting = false;
          const apiMessage =
            error?.error?.message || error?.error?.Error || error?.message || 'No se pudo crear la cuenta.';
          this.setFeedback(apiMessage, 'error');
          this.cdr.detectChanges();
        }
      });
  }

  private buildReferralCode(firstName: string, apellidoPaterno: string, apellidoMaterno: string): string {
    const all = `${firstName} ${apellidoPaterno} ${apellidoMaterno}`.trim();
    const words = all.split(/\s+/).filter(w => w.length > 0);
    if (words.length === 0) return '';
    const initials = words.map(w => w[0].toUpperCase()).join('');
    return `${words[0]}-${initials}`;
  }

  private setFeedback(message: string, type: 'error' | 'success'): void {
    this.feedbackMessage = message;
    this.feedbackType = type;
  }

  private loadBusinessConfig(): void {
    this.api
      .getPublicBusinessConfig()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (config) => {
          this.businessConfig = config;
          this.cdr.detectChanges();
        },
        error: () => { this.businessConfig = null; }
      });
  }

  private loadSponsorContact(sponsorId: string): void {
    this.api
      .getSponsorContact(sponsorId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (contact) => {
          this.sponsor = contact ?? null;
          this.cdr.detectChanges();
        },
        error: () => { this.sponsor = null; }
      });
  }

  private loadFeaturedProduct(queryProductId: string): void {
    this.api
      .getCatalogData()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          const queryId = (queryProductId ?? '').trim();
          const fromQuery = queryId ? this.pickFromQuery(data, queryId) : null;
          const defaultProduct = this.pickDefaultProduct(data);
          this.featuredProduct = fromQuery ?? defaultProduct;
          if (fromQuery?.id) {
            this.productId = fromQuery.id;
          } else if (defaultProduct?.id) {
            this.productId = defaultProduct.id;
          }
          this.cdr.detectChanges();
        },
        error: () => {
          this.featuredProduct = null;
          this.cdr.detectChanges();
        }
      });
  }

  private getHashQueryParam(param: string): string {
    if (typeof window === 'undefined') {
      return '';
    }
    try {
      const hash = window.location.hash ?? '';
      const queryIndex = hash.indexOf('?');
      if (queryIndex === -1) {
        return '';
      }
      const query = hash.slice(queryIndex + 1);
      return new URLSearchParams(query).get(param) ?? '';
    } catch {
      return '';
    }
  }

  private pickFromQuery(data: CatalogData, queryId: string): LandingComponent['featuredProduct'] | null {
    if (queryId.startsWith('campaign:')) {
      const campaignId = queryId.slice('campaign:'.length);
      const campaign = (data.campaigns ?? []).find((entry) => entry.id === campaignId);
      if (campaign) {
        return this.mapCampaign(campaign);
      }
    }
    const featuredMatch = data.featured?.find((item) => item.id === queryId);
    if (featuredMatch) {
      return this.mapFeaturedItem(featuredMatch);
    }
    const productMatch = data.products?.find((item) => item.id === queryId);
    if (productMatch) {
      return {
        id: productMatch.id,
        name: productMatch.name,
        hook: productMatch.badge || '',
        title: 'Cuida tu cuerpo.',
        accent: 'Potencia tu energia.',
        tail: productMatch.name || 'Compartelo.',
        description: productMatch.description || this.defaultHero.description,
        badge: this.defaultHero.badge,
        ctaPrimaryText: this.defaultHero.ctaPrimaryText,
        ctaSecondaryText: this.defaultHero.ctaSecondaryText,
        img: productMatch.img,
        tags: productMatch.badge ? [productMatch.badge] : []
      };
    }
    return null;
  }

  private pickDefaultProduct(data: CatalogData): LandingComponent['featuredProduct'] | null {
    const pom = data.productOfMonth;
    if (pom) {
      return {
        id: pom.id,
        name: pom.name,
        hook: pom.hook || pom.badge || '',
        title: 'Cuida tu cuerpo.',
        accent: pom.name || 'Potencia tu energia.',
        tail: 'Compartelo.',
        description: pom.description || this.defaultHero.description,
        badge: this.defaultHero.badge,
        ctaPrimaryText: this.defaultHero.ctaPrimaryText,
        ctaSecondaryText: this.defaultHero.ctaSecondaryText,
        img: pom.img || '',
        tags: pom.tags?.length ? pom.tags : pom.badge ? [pom.badge] : []
      };
    }
    if (data.featured?.length) {
      return this.mapFeaturedItem(data.featured[0]);
    }
    if (data.products?.length) {
      const first = data.products[0];
      return {
        id: first.id,
        name: first.name,
        hook: first.badge || '',
        img: first.img,
        tags: first.badge ? [first.badge] : []
      };
    }
    return null;
  }

  private mapFeaturedItem(item: FeaturedItem): LandingComponent['featuredProduct'] {
    return {
      id: item.id,
      name: item.label,
      hook: item.hook,
      title: 'Cuida tu cuerpo.',
      accent: item.label || 'Potencia tu energia.',
      tail: 'Compartelo.',
      description: item.hook || this.defaultHero.description,
      badge: this.defaultHero.badge,
      ctaPrimaryText: this.defaultHero.ctaPrimaryText,
      ctaSecondaryText: this.defaultHero.ctaSecondaryText,
      img: item.banner || item.feed || item.story,
      tags: []
    };
  }

  private mapCampaign(campaign: DashboardCampaign): LandingComponent['featuredProduct'] {
    return {
      id: `campaign:${campaign.id}`,
      name: campaign.name,
      hook: campaign.hook || '',
      badge: campaign.heroBadge || this.defaultHero.badge,
      title: campaign.heroTitle || this.defaultHero.title,
      accent: campaign.heroAccent || this.defaultHero.accent,
      tail: campaign.heroTail || this.defaultHero.tail,
      description: campaign.heroDescription || campaign.description || this.defaultHero.description,
      ctaPrimaryText: campaign.ctaPrimaryText || this.defaultHero.ctaPrimaryText,
      ctaSecondaryText: campaign.ctaSecondaryText || this.defaultHero.ctaSecondaryText,
      img: campaign.heroImage || campaign.banner || campaign.feed || campaign.story || this.defaultHero.img,
      tags: Array.isArray(campaign.benefits) && campaign.benefits.length ? campaign.benefits : this.defaultHero.tags
    };
  }
}

