import { ChangeDetectionStrategy, Component, computed, inject, signal, WritableSignal } from '@angular/core';
import { NgOptimizedImage } from '@angular/common';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

type LandingFormValue = {
  h1: string;
  text: string;
  imageUrl: string;
  ctaLabel: string;
  slug: string;
  status: 'Borrador' | 'Publicado';
};

type UiRequestState = 'idle' | 'loading' | 'success' | 'error';

@Component({
  selector: 'app-landings-editor-page',
  imports: [NgOptimizedImage, ReactiveFormsModule, RouterLink],
  template: `
    <main class="app-page">
      <div class="app-shell space-y-6">
        <header class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p class="app-eyebrow">Admin / Landings</p>
            <h1 class="text-2xl font-semibold text-white">Editor de landing</h1>
            <p class="text-sm text-slate-300">
              Completa los campos principales y revisa la vista previa en vivo (mock).
            </p>
          </div>
          <a class="app-link text-sm" routerLink="/admin/landings">Volver</a>
        </header>

        <section class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <form class="app-card app-card--soft space-y-4 p-6" [formGroup]="form">
          @if (saveState() === 'success') {
            <div class="app-message app-message--success text-sm text-emerald-100" role="status">
              Landing guardada correctamente.
            </div>
          }
          @if (saveState() === 'error') {
            <div class="app-message app-message--danger text-sm text-rose-100" role="alert">
              Revisa los campos obligatorios antes de guardar.
            </div>
          }
          @if (previewState() === 'success') {
            <div class="app-message app-message--success text-sm text-slate-100" role="status">
              Previsualización actualizada (mock).
            </div>
          }
          @if (previewState() === 'error') {
            <div class="app-message app-message--danger text-sm text-rose-100" role="alert">
              Completa los campos obligatorios antes de previsualizar.
            </div>
          }
          <div class="space-y-2">
            <label class="app-label" for="h1">H1</label>
            <input
              class="app-input"
              id="h1"
              name="h1"
              type="text"
              formControlName="h1"
              placeholder="Título principal de la landing"
            />
          </div>

          <div class="space-y-2">
            <label class="app-label" for="text">Texto</label>
            <textarea
              class="app-input min-h-[120px]"
              id="text"
              name="text"
              formControlName="text"
              placeholder="Resumen que acompaña al H1"
            ></textarea>
          </div>

          <div class="space-y-2">
            <label class="app-label" for="imageUrl">Imagen</label>
            <input
              class="app-input"
              id="imageUrl"
              name="imageUrl"
              type="url"
              formControlName="imageUrl"
              placeholder="https://..."
            />
          </div>

          <div class="space-y-2">
            <label class="app-label" for="ctaLabel">CTA</label>
            <input
              class="app-input"
              id="ctaLabel"
              name="ctaLabel"
              type="text"
              formControlName="ctaLabel"
              placeholder="Texto del botón"
            />
          </div>

          <div class="space-y-2">
            <label class="app-label" for="slug">Slug</label>
            <input
              class="app-input"
              id="slug"
              name="slug"
              type="text"
              formControlName="slug"
              placeholder="landing-promocion"
            />
            <p class="app-hint">
              URL final: /landing/{{ preview().slug }}
            </p>
          </div>

          <div class="space-y-2">
            <label class="app-label" for="status">Estado</label>
            <select
              class="app-input"
              id="status"
              name="status"
              formControlName="status"
            >
              @for (option of statuses(); track option) {
                <option [value]="option">{{ option }}</option>
              }
            </select>
          </div>

          <div class="flex flex-wrap gap-3 pt-2">
            <button
              class="app-button text-sm"
              [class.opacity-70]="isSaving()"
              [class.pointer-events-none]="isSaving()"
              type="button"
              (click)="handleSave()"
            >
              {{ isSaving() ? 'Guardando...' : 'Guardar' }}
            </button>
            <button
              class="app-button app-button--ghost text-sm"
              [class.opacity-70]="isPreviewing()"
              [class.pointer-events-none]="isPreviewing()"
              type="button"
              (click)="handlePreview()"
            >
              {{ isPreviewing() ? 'Actualizando...' : 'Previsualizar' }}
            </button>
          </div>
        </form>

        <aside class="app-card app-card--soft space-y-4 p-6">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-white">Preview en vivo</h2>
            <span class="app-badge app-badge--warning">Mock</span>
          </div>

          <div class="app-card app-card--soft p-4">
            <div class="space-y-4">
              <div class="space-y-2">
                <p class="app-eyebrow">Hero</p>
                <h3 class="text-xl font-semibold text-white">{{ preview().h1 }}</h3>
                <p class="text-sm text-slate-300">{{ preview().text }}</p>
              </div>
              @if (preview().imageUrl) {
                <img
                  alt="Vista previa de la imagen principal"
                  class="h-auto w-full rounded-lg object-cover shadow-lg"
                  height="360"
                  width="640"
                  [ngSrc]="preview().imageUrl"
                />
              } @else {
                <div class="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-slate-700/60">
                  <p class="text-sm text-slate-400">Añade una imagen para verla aquí.</p>
                </div>
              }
              <button
                class="app-button app-button--ghost text-sm"
                type="button"
              >
                {{ preview().ctaLabel }}
              </button>
            </div>
          </div>
        </aside>
      </section>
      </div>
    </main>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingsEditorPage {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly saveState = signal<UiRequestState>('idle');
  readonly previewState = signal<UiRequestState>('idle');

  readonly form = this.fb.group({
    h1: this.fb.control('Impulsa tu red con retos y recompensas', Validators.required),
    text: this.fb.control(
      'Motiva a tu equipo con objetivos claros, métricas en tiempo real y misiones guiadas.',
      Validators.required,
    ),
    imageUrl: this.fb.control('https://images.unsplash.com/photo-1521737604893-d14cc237f11d', Validators.required),
    ctaLabel: this.fb.control('Empieza ahora', Validators.required),
    slug: this.fb.control('impulsa-tu-red', Validators.required),
    status: this.fb.control<LandingFormValue['status']>('Borrador', Validators.required),
  });

  readonly statuses = signal<LandingFormValue['status'][]>(['Borrador', 'Publicado']);
  readonly isSaving = computed(() => this.saveState() === 'loading');
  readonly isPreviewing = computed(() => this.previewState() === 'loading');

  private readonly formValue = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });

  readonly preview = computed(() => {
    const value = this.formValue();

    return {
      h1: value.h1 || 'Título de la landing',
      text: value.text || 'Describe el objetivo principal de esta landing.',
      imageUrl: value.imageUrl || '',
      ctaLabel: value.ctaLabel || 'Llamado a la acción',
      slug: value.slug || 'nueva-landing',
      status: value.status,
    };
  });

  handleSave(): void {
    this.previewState.set('idle');
    this.triggerMockRequest(this.saveState);
  }

  handlePreview(): void {
    this.saveState.set('idle');
    this.triggerMockRequest(this.previewState);
  }

  private triggerMockRequest(state: WritableSignal<UiRequestState>): void {
    if (this.form.invalid) {
      state.set('error');
      this.clearStateLater(state, 'error');
      return;
    }

    state.set('loading');
    setTimeout(() => {
      state.set('success');
      this.clearStateLater(state, 'success');
    }, 800);
  }

  private clearStateLater(state: WritableSignal<UiRequestState>, expected: UiRequestState): void {
    setTimeout(() => {
      if (state() === expected) {
        state.set('idle');
      }
    }, 2400);
  }
}
