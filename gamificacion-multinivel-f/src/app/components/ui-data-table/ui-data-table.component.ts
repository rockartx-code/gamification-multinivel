import { CommonModule } from '@angular/common';
import { Component, ContentChild, Input, TemplateRef } from '@angular/core';

@Component({
  selector: 'ui-data-table',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-data-table.component.html'
})
export class UiDataTableComponent<T = unknown> {
  @Input() rows: T[] = [];
  // Divisores visibles en tema claro (antes divide-white/10: invisibles)
  @Input() mobileDividerClass = 'divide-olive-20';
  @Input() desktopDividerClass = 'divide-olive-20';

  @ContentChild('mobileRow') mobileRowTpl?: TemplateRef<{ $implicit: T }>;
  @ContentChild('desktopHeader') desktopHeaderTpl?: TemplateRef<unknown>;
  @ContentChild('desktopRow') desktopRowTpl?: TemplateRef<{ $implicit: T }>;
}
