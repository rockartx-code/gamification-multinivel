import { ChangeDetectionStrategy, Component, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

@Component({
  selector: 'app-coach-message',
  template: `
    <div
      class="app-message"
      role="status"
      aria-live="polite"
      [class.app-message--success]="tone() === 'success'"
      [class.app-message--warning]="tone() === 'warning'"
      [class.app-message--danger]="tone() === 'danger'"
    >
      <p class="text-sm font-semibold">{{ title() }}</p>
      <p class="mt-1 text-sm text-slate-300">{{ message() }}</p>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CoachMessageComponent {
  title = input<string>('Mensaje del coach');
  message = input<string>('Sigue avanzando, estás más cerca de tu meta.');
  tone = input<StatusTone>('success');
}
