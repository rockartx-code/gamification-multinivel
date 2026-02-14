import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'ui-footer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-footer.component.html'
})
export class UiFooterComponent {
  @Input() logoMode: 'default' | 'compact' = 'default';
  @Input() containerClass = 'mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-6 py-10 md:flex-row md:items-center';

  get logoClass(): string {
    return this.logoMode === 'compact' ? 'h-10 w-auto sm:h-12 md:h-14' : 'h-15 w-40';
  }
}
