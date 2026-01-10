import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

type ButtonType = 'button' | 'submit' | 'reset';

const TONE_CLASSES: Record<StatusTone, string> = {
  success:
    'bg-green-600 text-white hover:bg-green-700 focus-visible:ring-green-600',
  warning:
    'bg-yellow-500 text-slate-900 hover:bg-yellow-600 focus-visible:ring-yellow-500',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-600',
};

@Component({
  selector: 'app-cta-button',
  template: `
    <button
      class="inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
      [class]="toneClasses()"
      [attr.type]="type()"
      [disabled]="disabled()"
    >
      {{ label() }}
    </button>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CTAButtonComponent {
  label = input<string>('Continuar');
  type = input<ButtonType>('button');
  disabled = input<boolean>(false);
  tone = input<StatusTone>('success');

  protected readonly toneClasses = computed(() => TONE_CLASSES[this.tone()]);
}
