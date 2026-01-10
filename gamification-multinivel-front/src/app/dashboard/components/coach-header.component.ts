import { NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { CoachMessageComponent } from '../../core/components/coach-message.component';
import { UserProfileService } from '../../services/user-profile.service';
import { getCoachCopy } from '../../shared/coach/coach-copy';

type StatusTone = 'success' | 'warning' | 'danger';

@Component({
  selector: 'app-coach-header',
  imports: [NgOptimizedImage, CoachMessageComponent],
  template: `
    <section class="sticky top-4 z-20 rounded-2xl bg-white p-6 shadow-sm">
      @if (profile(); as profile) {
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-4">
            @if (profile.avatarUrl) {
              <img
                class="h-14 w-14 rounded-full border border-slate-200 object-cover"
                [ngSrc]="profile.avatarUrl"
                [alt]="'Avatar de ' + profile.displayName"
                width="56"
                height="56"
              />
            } @else {
              <div
                class="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600"
                aria-hidden="true"
              >
                {{ initials() }}
              </div>
            }
            <div>
              <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Coach personal
              </p>
              <h1 class="text-2xl font-semibold text-slate-900">
                Hola, {{ profile.displayName }}
              </h1>
              <p class="mt-1 text-sm text-slate-600">
                Nivel {{ profile.level }} · {{ profile.totalPoints }} puntos · Puesto
                #{{ profile.rank }}
              </p>
            </div>
          </div>
          <div class="min-w-[220px] space-y-3">
            <app-coach-message
              [title]="messageTitle()"
              [message]="messageBody()"
              [tone]="messageTone()"
            />
            <a
              class="inline-flex w-full items-center justify-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              [attr.href]="actionHref()"
            >
              {{ actionLabel() }}
            </a>
          </div>
        </div>
      } @else {
        <p class="text-sm text-slate-500">Cargando tu resumen...</p>
      }
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CoachHeaderComponent {
  private readonly userProfileService = inject(UserProfileService);
  private readonly coachCopy = getCoachCopy();

  readonly messageTitle = input(this.coachCopy.dashboard.header.overview.title);
  readonly messageBody = input(this.coachCopy.dashboard.header.overview.message);
  readonly messageTone = input<StatusTone>(this.coachCopy.dashboard.header.overview.tone);
  readonly actionLabel = input('Ir a la siguiente acción');
  readonly actionHref = input('#next-action');

  protected readonly profile = toSignal(this.userProfileService.getUserProfile(), {
    initialValue: null,
  });

  protected readonly initials = computed(() => {
    const name = this.profile()?.displayName ?? 'Usuario';
    return name
      .split(' ')
      .map((segment) => segment[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  });
}
