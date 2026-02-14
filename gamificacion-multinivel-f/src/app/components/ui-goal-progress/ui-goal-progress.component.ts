import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'ui-goal-progress',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-goal-progress.component.html'
})
export class UiGoalProgressComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() currentValue = 0;
  @Input() cartValue = 0;
  @Input() targetValue = 0;

  get basePercent(): number {
    if (this.targetValue <= 0) {
      return 0;
    }
    return this.clamp((this.currentValue / this.targetValue) * 100);
  }

  get cartPercent(): number {
    if (this.targetValue <= 0) {
      return 0;
    }
    const raw = (this.cartValue / this.targetValue) * 100;
    return this.clamp(raw, 0, 100 - this.basePercent);
  }

  private clamp(value: number, min = 0, max = 100): number {
    return Math.max(min, Math.min(max, Number.isFinite(value) ? value : 0));
  }
}
