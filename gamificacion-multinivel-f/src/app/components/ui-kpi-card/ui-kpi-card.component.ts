import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'ui-kpi-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-kpi-card.component.html'
})
export class UiKpiCardComponent {
  @Input() label = '';
  @Input() value: string | number = '';
  @Input() iconClass = '';
}
