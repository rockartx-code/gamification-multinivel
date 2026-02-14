import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'ui-button',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './ui-button.component.html'
})
export class UiButtonComponent {
  @Input('class') hostClass = '';
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() variant: 'primary' | 'olive' | 'ghost' | 'linkish' = 'ghost';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() disabled = false;
  @Input() fullWidth = false;
  @Input() iconClass = '';
  @Input() extraClass = '';
  @Input() routerLink: string | unknown[] | null = null;

  @Output() pressed = new EventEmitter<MouseEvent>();

  get classes(): string {
    const base = 'inline-flex items-center justify-center gap-2 rounded-full transition';
    const variants = {
      primary: 'btn-primary',
      olive: 'btn-olive',
      ghost: 'btn-ghost',
      linkish: 'btn-linkish'
    };
    const sizes = {
      sm: 'px-3 py-1.5 text-xs font-semibold',
      md: 'px-4 py-2 text-sm font-semibold',
      lg: 'px-6 py-3 text-sm font-semibold'
    };

    return [
      base,
      variants[this.variant],
      sizes[this.size],
      this.fullWidth ? 'w-full' : '',
      this.disabled ? 'btn-disabled' : 'hover:scale-[1.02]',
      this.hostClass,
      this.extraClass
    ]
      .filter(Boolean)
      .join(' ');
  }

  onClick(event: MouseEvent): void {
    if (this.disabled) {
      event.preventDefault();
      return;
    }
    this.pressed.emit(event);
  }
}
