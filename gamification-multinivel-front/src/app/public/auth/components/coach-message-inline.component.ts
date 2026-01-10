import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { AuthCoachMessage } from '../../../domain/models';

@Component({
  selector: 'app-coach-message-inline',
  template: `
    <article class="coach-message" aria-live="polite">
      <h3 class="coach-message__title">{{ message().title }}</h3>
      <p class="coach-message__body">{{ message().body }}</p>
    </article>
  `,
  styles: [
    `
      .coach-message {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 12px 14px;
        background: #ffffff;
      }

      .coach-message__title {
        margin: 0 0 6px;
        font-size: 14px;
        color: #111827;
      }

      .coach-message__body {
        margin: 0;
        font-size: 13px;
        color: #4b5563;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CoachMessageInlineComponent {
  readonly message = input.required<AuthCoachMessage>();
}
