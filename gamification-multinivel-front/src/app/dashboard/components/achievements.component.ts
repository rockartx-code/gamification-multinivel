import { NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { AchievementsService } from '../../services/achievements.service';

@Component({
  selector: 'app-achievements',
  imports: [NgOptimizedImage],
  template: `
    <section class="app-card app-card--soft p-6">
      <div>
        <p class="app-eyebrow">
          Logros recientes
        </p>
        <h2 class="text-xl font-semibold text-white">Tus insignias</h2>
      </div>
      <div class="mt-5 space-y-4">
        @for (achievement of achievements(); track achievement.id) {
          <article class="app-card app-card--soft flex items-start gap-4 p-4">
            @if (achievement.badgeUrl) {
              <img
                class="h-12 w-12 rounded-full border border-slate-700/60 bg-slate-900/80 object-cover"
                [ngSrc]="achievement.badgeUrl"
                [alt]="'Insignia ' + achievement.title"
                width="48"
                height="48"
              />
            }
            <div>
              <h3 class="text-sm font-semibold text-white">
                {{ achievement.title }}
              </h3>
              <p class="mt-1 text-sm text-slate-300">
                {{ achievement.description }}
              </p>
              @if (achievement.unlockedAt) {
                <p class="mt-2 text-xs text-slate-400">
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
