import { ChangeDetectionStrategy, Component, input } from '@angular/core';

type StatusTone = 'success' | 'warning' | 'danger';

type ButtonType = 'button' | 'submit' | 'reset';

@Component({
  selector: 'app-cta-button',
  template: `
    <button
      class="app-button text-sm"
      [class.app-button--full]="fullWidth()"
      [class.app-button--success]="tone() === 'success'"
      [class.app-button--warning]="tone() === 'warning'"
      [class.app-button--danger]="tone() === 'danger'"
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
  fullWidth = input<boolean>(false);

}
