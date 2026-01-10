import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

const TONE_CLASSES: Record<StatusTone, string> = {
  success: 'border-green-200 bg-green-50 text-green-900',
  warning: 'border-yellow-200 bg-yellow-50 text-yellow-900',
  danger: 'border-red-200 bg-red-50 text-red-900',
};

@Component({
  selector: 'app-coach-message',
  template: `
    <div
      class="rounded-lg border p-4"
      role="status"
      aria-live="polite"
      [class]="toneClasses()"
    >
      <p class="text-sm font-semibold">{{ title() }}</p>
      <p class="mt-1 text-sm text-slate-700">{{ message() }}</p>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CoachMessageComponent {
  title = input<string>('Mensaje del coach');
  message = input<string>('Sigue avanzando, estás más cerca de tu meta.');
  tone = input<StatusTone>('success');

  protected readonly toneClasses = computed(() => TONE_CLASSES[this.tone()]);
}
