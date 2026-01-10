import { NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { CoachMessageComponent } from '../../core/components/coach-message.component';
import { UserProfileService } from '../../services/user-profile.service';
import { getCoachCopy } from '../../shared/coach/coach-copy';

@Component({
  selector: 'app-coach-header',
  imports: [NgOptimizedImage, CoachMessageComponent],
  template: `
    <section class="rounded-2xl bg-white p-6 shadow-sm">
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
          <div class="min-w-[220px]">
            <app-coach-message
              [title]="coachHeaderMessage.title"
              [message]="coachHeaderMessage.message"
              [tone]="coachHeaderMessage.tone"
            />
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

  protected readonly profile = toSignal(this.userProfileService.getUserProfile(), {
    initialValue: null,
  });

  protected readonly coachHeaderMessage = this.coachCopy.dashboard.header.overview;

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
