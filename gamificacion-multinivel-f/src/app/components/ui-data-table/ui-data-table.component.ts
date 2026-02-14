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
  @Input() mobileDividerClass = 'divide-white/10';
  @Input() desktopDividerClass = 'divide-white/5';

  @ContentChild('mobileRow') mobileRowTpl?: TemplateRef<{ $implicit: T }>;
  @ContentChild('desktopHeader') desktopHeaderTpl?: TemplateRef<unknown>;
  @ContentChild('desktopRow') desktopRowTpl?: TemplateRef<{ $implicit: T }>;
}
