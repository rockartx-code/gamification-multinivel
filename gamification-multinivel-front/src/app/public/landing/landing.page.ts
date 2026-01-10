import { NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { CTAButtonComponent } from '../../core/components/cta-button.component';
import { SessionService } from '../../core/session.service';
import { LandingService } from '../../services/landing.service';

@Component({
  selector: 'app-landing-page',
  template: `
    <section class="min-h-screen bg-slate-950 text-slate-100">
      <div class="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-12 lg:grid lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:gap-12">
        @if (landing(); as landingContent) {
          <div class="space-y-6">
            <span class="inline-flex items-center gap-2 rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-indigo-200">
              Multinivel inteligente
            </span>
            <div class="space-y-4">
              <h1 class="text-3xl font-semibold leading-tight text-white sm:text-4xl">
                {{ landingContent.heroTitle }}
              </h1>
              <p class="text-base text-slate-200 sm:text-lg">
                {{ landingContent.heroSubtitle }}
              </p>
            </div>
            <div class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <img
                class="h-auto w-full rounded-xl"
                [ngSrc]="landingContent.heroImageUrl"
                [attr.alt]="landingContent.heroImageAlt"
                width="640"
                height="480"
                priority
              />
            </div>
            <ul class="space-y-3 text-sm text-slate-200">
              @for (highlight of landingContent.highlights; track highlight) {
                <li class="flex items-start gap-3">
                  <span class="mt-1 inline-flex h-2 w-2 flex-shrink-0 rounded-full bg-indigo-400"></span>
                  <span>{{ highlight }}</span>
                </li>
              }
            </ul>
          </div>
          <div class="rounded-3xl border border-slate-800 bg-white p-6 text-slate-900 shadow-xl sm:p-8">
            <div class="space-y-2">
              <h2 class="text-xl font-semibold text-slate-900">Registra tu acceso</h2>
              <p class="text-sm text-slate-600">
                Completa tu información y activa el seguimiento de tu red.
              </p>
            </div>
            <form class="mt-6 space-y-4" [formGroup]="registrationForm" (ngSubmit)="submitForm()">
              <div class="space-y-2">
                <label class="text-sm font-medium text-slate-700" for="full-name">Nombre completo</label>
                <input
                  id="full-name"
                  class="w-full rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-900 outline-none transition focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-200"
                  type="text"
                  formControlName="fullName"
                  autocomplete="name"
                  [attr.aria-invalid]="showFullNameError()"
                  [attr.aria-describedby]="showFullNameError() ? 'full-name-error' : null"
                  required
                />
                @if (showFullNameError()) {
                  <p id="full-name-error" class="text-xs text-red-600" role="alert">
                    Ingresa tu nombre completo.
                  </p>
                }
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-slate-700" for="email">Correo electrónico</label>
                <input
                  id="email"
                  class="w-full rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-900 outline-none transition focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-200"
                  type="email"
                  formControlName="email"
                  autocomplete="email"
                  [attr.aria-invalid]="showEmailError()"
                  [attr.aria-describedby]="showEmailError() ? 'email-error' : null"
                  required
                />
                @if (showEmailError()) {
                  <p id="email-error" class="text-xs text-red-600" role="alert">
                    Comparte un correo válido para continuar.
                  </p>
                }
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-slate-700" for="phone">Teléfono de contacto</label>
                <input
                  id="phone"
                  class="w-full rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-900 outline-none transition focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-200"
                  type="tel"
                  formControlName="phone"
                  autocomplete="tel"
                />
              </div>
              <div class="rounded-2xl bg-slate-50 px-4 py-3 text-xs text-slate-600">
                Al enviar aceptas que tu registro sea validado por el equipo comercial.
              </div>
              <app-cta-button
                [label]="landingContent.ctaLabel"
                [type]="'submit'"
                [fullWidth]="true"
              />
            </form>
          </div>
        } @else {
          <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-sm text-slate-300">
            Cargando experiencia...
          </div>
        }
      </div>
    </section>
  `,
  imports: [CTAButtonComponent, NgOptimizedImage, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingPage {
  private readonly landingService = inject(LandingService);
  private readonly route = inject(ActivatedRoute);
  private readonly formBuilder = inject(FormBuilder);
  private readonly sessionService = inject(SessionService);

  protected readonly landing = toSignal(this.landingService.getLanding(), {
    initialValue: null,
  });
  private readonly paramMap = toSignal(this.route.paramMap, {
    initialValue: this.route.snapshot.paramMap,
  });
  private readonly referrerUserId = computed(
    () => this.paramMap()?.get('refCode') ?? '',
  );
  private readonly landingSlug = computed(
    () => this.paramMap()?.get('landingSlug') ?? '',
  );
  protected readonly registrationForm = this.formBuilder.nonNullable.group({
    fullName: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    phone: [''],
  });
  private readonly attemptedSubmit = signal(false);

  constructor() {
    effect(() => {
      const referrerUserId = this.referrerUserId();
      const landingSlug = this.landingSlug();
      if (referrerUserId && landingSlug) {
        this.sessionService.saveLandingContext(referrerUserId, landingSlug);
      }
    });
  }

  submitForm(): void {
    this.attemptedSubmit.set(true);
    this.registrationForm.markAllAsTouched();
  }

  protected showFullNameError(): boolean {
    const control = this.registrationForm.controls.fullName;
    return (control.invalid && control.touched) || (control.invalid && this.attemptedSubmit());
  }

  protected showEmailError(): boolean {
    const control = this.registrationForm.controls.email;
    return (control.invalid && control.touched) || (control.invalid && this.attemptedSubmit());
  }
}
