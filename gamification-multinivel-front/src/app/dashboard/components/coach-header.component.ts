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
    <section class="app-card app-card--bright sticky top-4 z-20 p-6">
      @if (profile(); as profile) {
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-4">
            @if (profile.avatarUrl) {
              <img
                class="h-14 w-14 rounded-full border border-slate-700/60 object-cover"
                [ngSrc]="profile.avatarUrl"
                [alt]="'Avatar de ' + profile.displayName"
                width="56"
                height="56"
              />
            } @else {
              <div
                class="flex h-14 w-14 items-center justify-center rounded-full border border-slate-700/60 bg-slate-900/80 text-sm font-semibold text-slate-200"
                aria-hidden="true"
              >
                {{ initials() }}
              </div>
            }
            <div>
              <p class="app-eyebrow">
                Coach personal
              </p>
              <h1 class="text-2xl font-semibold text-white">
                Hola, {{ profile.displayName }}
              </h1>
              <p class="mt-1 text-sm text-slate-300">
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
              class="app-button app-button--full text-sm"
              [attr.href]="actionHref()"
            >
              {{ actionLabel() }}
            </a>
          </div>
        </div>
      } @else {
        <p class="text-sm text-slate-300">Cargando tu resumen...</p>
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
