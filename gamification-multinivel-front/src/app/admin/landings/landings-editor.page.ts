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
    <main class="space-y-6 bg-slate-50 px-4 py-6 md:px-8">
      <header class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p class="text-sm font-semibold uppercase text-slate-500">Admin / Landings</p>
          <h1 class="text-2xl font-semibold text-slate-900">Editor de landing</h1>
          <p class="text-sm text-slate-600">
            Completa los campos principales y revisa la vista previa en vivo (mock).
          </p>
        </div>
        <a class="text-sm font-semibold text-slate-600" routerLink="/admin/landings">Volver</a>
      </header>

      <section class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <form class="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" [formGroup]="form">
          @if (saveState() === 'success') {
            <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800" role="status">
              Landing guardada correctamente.
            </div>
          }
          @if (saveState() === 'error') {
            <div class="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
              Revisa los campos obligatorios antes de guardar.
            </div>
          }
          @if (previewState() === 'success') {
            <div class="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800" role="status">
              Previsualización actualizada (mock).
            </div>
          }
          @if (previewState() === 'error') {
            <div class="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
              Completa los campos obligatorios antes de previsualizar.
            </div>
          }
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700" for="h1">H1</label>
            <input
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              id="h1"
              name="h1"
              type="text"
              formControlName="h1"
              placeholder="Título principal de la landing"
            />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700" for="text">Texto</label>
            <textarea
              class="min-h-[120px] w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              id="text"
              name="text"
              formControlName="text"
              placeholder="Resumen que acompaña al H1"
            ></textarea>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700" for="imageUrl">Imagen</label>
            <input
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              id="imageUrl"
              name="imageUrl"
              type="url"
              formControlName="imageUrl"
              placeholder="https://..."
            />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700" for="ctaLabel">CTA</label>
            <input
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              id="ctaLabel"
              name="ctaLabel"
              type="text"
              formControlName="ctaLabel"
              placeholder="Texto del botón"
            />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700" for="slug">Slug</label>
            <input
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              id="slug"
              name="slug"
              type="text"
              formControlName="slug"
              placeholder="landing-promocion"
            />
            <p class="text-xs text-slate-500">
              URL final: /landing/{{ preview().slug }}
            </p>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700" for="status">Estado</label>
            <select
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
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
              class="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
              [class.opacity-70]="isSaving()"
              [class.pointer-events-none]="isSaving()"
              type="button"
              (click)="handleSave()"
            >
              {{ isSaving() ? 'Guardando...' : 'Guardar' }}
            </button>
            <button
              class="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700"
              [class.opacity-70]="isPreviewing()"
              [class.pointer-events-none]="isPreviewing()"
              type="button"
              (click)="handlePreview()"
            >
              {{ isPreviewing() ? 'Actualizando...' : 'Previsualizar' }}
            </button>
          </div>
        </form>

        <aside class="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-900">Preview en vivo</h2>
            <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">Mock</span>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div class="space-y-4">
              <div class="space-y-2">
                <p class="text-xs font-semibold uppercase text-slate-500">Hero</p>
                <h3 class="text-xl font-semibold text-slate-900">{{ preview().h1 }}</h3>
                <p class="text-sm text-slate-600">{{ preview().text }}</p>
              </div>
              @if (preview().imageUrl) {
                <img
                  alt="Vista previa de la imagen principal"
                  class="h-auto w-full rounded-lg object-cover"
                  height="360"
                  width="640"
                  [ngSrc]="preview().imageUrl"
                />
              } @else {
                <div class="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-slate-200">
                  <p class="text-sm text-slate-500">Añade una imagen para verla aquí.</p>
                </div>
              }
              <button
                class="inline-flex items-center justify-center rounded-lg border border-sky-200 bg-white px-4 py-2 text-sm font-semibold text-sky-700"
                type="button"
              >
                {{ preview().ctaLabel }}
              </button>
            </div>
          </div>
        </aside>
      </section>
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
