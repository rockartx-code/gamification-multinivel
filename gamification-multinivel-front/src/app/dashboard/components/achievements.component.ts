import { NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { AchievementsService } from '../../services/achievements.service';

@Component({
  selector: 'app-achievements',
  imports: [NgOptimizedImage],
  template: `
    <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Logros recientes
        </p>
        <h2 class="text-xl font-semibold text-slate-900">Tus insignias</h2>
      </div>
      <div class="mt-5 space-y-4">
        @for (achievement of achievements(); track achievement.id) {
          <article class="flex items-start gap-4 rounded-xl border border-slate-100 p-4">
            @if (achievement.badgeUrl) {
              <img
                class="h-12 w-12 rounded-full border border-slate-200 bg-white object-cover"
                [ngSrc]="achievement.badgeUrl"
                [alt]="'Insignia ' + achievement.title"
                width="48"
                height="48"
              />
            }
            <div>
              <h3 class="text-sm font-semibold text-slate-900">
                {{ achievement.title }}
              </h3>
              <p class="mt-1 text-sm text-slate-600">
                {{ achievement.description }}
              </p>
              @if (achievement.unlockedAt) {
                <p class="mt-2 text-xs text-slate-500">
                  Desbloqueado: {{ achievement.unlockedAt }}
                </p>
              }
            </div>
          </article>
        }
      </div>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AchievementsComponent {
  private readonly achievementsService = inject(AchievementsService);

  protected readonly achievements = toSignal(
    this.achievementsService.getAchievements(),
    { initialValue: [] }
  );
}
