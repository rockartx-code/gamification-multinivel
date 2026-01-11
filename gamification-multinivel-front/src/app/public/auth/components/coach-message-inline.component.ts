import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { AuthCoachMessage } from '../../../domain/models';

@Component({
  selector: 'app-coach-message-inline',
  template: `
    <article class="app-card app-card--soft coach-message" aria-live="polite">
      <h3 class="coach-message__title">{{ message().title }}</h3>
      <p class="coach-message__body">{{ message().body }}</p>
    </article>
  `,
  styles: [
    `
      .coach-message {
        padding: 12px 14px;
      }

      .coach-message__title {
        margin: 0 0 6px;
        font-size: 14px;
        color: var(--ritual-text-strong);
      }

      .coach-message__body {
        margin: 0;
        font-size: 13px;
        color: var(--ritual-text-soft);
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CoachMessageInlineComponent {
  readonly message = input.required<AuthCoachMessage>();
}
