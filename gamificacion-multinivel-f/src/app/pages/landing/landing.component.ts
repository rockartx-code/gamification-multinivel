import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { UserDashboardData, FeaturedItem } from '../../models/user-dashboard.model';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiFormFieldComponent, UiButtonComponent, UiHeaderComponent, UiFooterComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css'
})
export class LandingComponent implements OnInit {
  readonly currentYear = new Date().getFullYear();
  readonly defaultHero = {
    id: '',
    name: 'COLAGENO',
    hook: 'Regeneracion, soporte articular y recuperacion diaria.',
    img: 'images/Colageno-Clean.png',
    tags: ['10g por porcion', 'Alta biodisponibilidad']
  };

  form = {
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  };

  referralToken = '';
  productId = '';
  isSubmitting = false;
  feedbackMessage = '';
  feedbackType: 'error' | 'success' | '' = '';
  featuredProduct: {
    id: string;
    name: string;
    hook: string;
    img: string;
    tags: string[];
  } | null = null;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef,
    private readonly router: Router,
    private readonly authService: AuthService
  ) {}

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('refToken') ?? '';
    const product = this.route.snapshot.queryParamMap.get('p') ?? this.getHashQueryParam('p');
    this.referralToken = token.trim();
    this.productId = product.trim();
    if (this.referralToken) {
      localStorage.setItem('leaderId', this.referralToken);
    }
    this.loadFeaturedProduct(this.productId);
  }

  get heroTitle(): string {
    return this.featuredProduct?.name || this.defaultHero.name;
  }

  get heroHook(): string {
    return this.featuredProduct?.hook || this.defaultHero.hook;
  }

  get heroImage(): string {
    return this.featuredProduct?.img || this.defaultHero.img;
  }

  get heroTags(): string[] {
    const tags = this.featuredProduct?.tags ?? [];
    return tags.length ? tags : this.defaultHero.tags;
  }

  getTagClass(index: number): string {
    if (index % 2 === 0) {
      return 'inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-500/15 px-3 py-1 text-xs text-blue-200';
    }
    return 'inline-flex items-center gap-2 rounded-full border border-yellow-400/20 bg-yellow-400/15 px-3 py-1 text-xs text-yellow-200';
  }

  getTagIcon(index: number): string {
    return index % 2 === 0 ? 'fa-weight-hanging' : 'fa-seedling';
  }

  scrollTo(sectionId: string, event?: Event): void {
    event?.preventDefault();
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  createAccount(): void {
    if (this.isSubmitting) {
      return;
    }
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
    this.api
      .createAccount(payload)
      .pipe(
        finalize(() => {
          this.isSubmitting = false;
        })
      )
      .subscribe({
        next: (response) => {
          if (response?.customer) {
            this.authService.setUserFromCreateAccount(response.customer);
          }
          this.form = { name: '', email: '', phone: '', password: '', confirmPassword: '' };
          this.setFeedback('', 'success');
          this.router.navigate(['/dashboard']);
        },
        error: (error: any) => {
          const apiMessage =
            error?.error?.message || error?.error?.Error || error?.message || 'No se pudo crear la cuenta.';
          this.setFeedback(apiMessage, 'error');
        }
      });
  }

  private setFeedback(message: string, type: 'error' | 'success'): void {
    this.feedbackMessage = message;
    this.feedbackType = type;
  }

  private loadFeaturedProduct(queryProductId: string): void {
    this.api.getUserDashboardData().subscribe({
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
        this.cdr.markForCheck();
      },
      error: () => {
        this.featuredProduct = null;
        this.cdr.markForCheck();
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

  private pickFromQuery(data: UserDashboardData, queryId: string): LandingComponent['featuredProduct'] | null {
    if (queryId === 'fixed-familia' ) {
      return {
        id: queryId,
        name: '',
        hook: '',
        img: 'images/L-Programa3.png',
        tags: []
      };
    }
    if ( queryId === 'fixed-entrenador') {
      return {
        id: queryId,
        name: '',
        hook: '',
        img: 'images/L-Programa2.png',
        tags: []
      };
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
        img: productMatch.img,
        tags: productMatch.badge ? [productMatch.badge] : []
      };
    }
    return null;
  }

  private pickDefaultProduct(data: UserDashboardData): LandingComponent['featuredProduct'] | null {
    const pom = data.productOfMonth;
    if (pom) {
      return {
        id: pom.id,
        name: pom.name,
        hook: pom.hook || pom.badge || '',
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
      img: item.banner || item.feed || item.story,
      tags: []
    };
  }
}
