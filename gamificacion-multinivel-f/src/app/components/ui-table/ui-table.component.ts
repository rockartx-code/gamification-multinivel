import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'ui-table',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-table.component.html'
})
export class UiTableComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() iconClass = '';
}
