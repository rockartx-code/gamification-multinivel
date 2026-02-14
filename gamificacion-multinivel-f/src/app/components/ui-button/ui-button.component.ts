import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'ui-button',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './ui-button.component.html',
  styleUrls: ['./ui-button.component.css']
})
export class UiButtonComponent {
  private static readonly PRIMARY_HINT_PATTERN =
    /\b(?:bg-gradient-to-r|(?:from|to|via)-(?:gold|primary|amber)|btn-primary)\b/;
  private static readonly SECONDARY_HINT_PATTERN =
    /\b(?:from-olive|to-secondary|btn-secondary)\b/;
  private static readonly LEGACY_CLASS_PATTERN =
    /\b(?:bg-gradient-to-r|(?:from|to|via)-[\w-]+|bg-[^\s"]+|border(?:-[^\s"]+)?|shadow(?:-[^\s"]+)?|shadow-\[[^\]]+\]|(?:[a-z]+:)*(?:hover|active):scale-[^\s"]+|transition-transform|hover-bg-[^\s"]+|(?:[a-z]+:)*p[xy]-[^\s"]+|btn-primary|btn-secondary|btn-ghost|btn-linkish)\b/g;

  @Input('class') hostClass = '';
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() variant: 'primary' | 'secondary' | 'ghost' | 'linkish' = 'ghost';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() disabled = false;
  @Input() fullWidth = false;
  @Input() iconClass = '';
  @Input() extraClass = '';
  @Input() routerLink: string | unknown[] | null = null;
    @Input() stacked = false;
    @Input() title = '';
    @Input() subtitle = '';
    

  @Output() pressed = new EventEmitter<MouseEvent>();

  get classes(): string {
    const base = 'btn inline-flex items-center justify-center gap-2';
    const variants = {
      primary: 'btn-primary',
      secondary: 'btn-secondary',
      ghost: 'btn-ghost',
      linkish: 'btn-linkish'
    };
    const resolvedVariant = this.resolveVariant();
    const sizes = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm',
      lg: 'h-12 px-6 text-sm'
    };
    const cleanedHostClass = this.sanitizeClasses(this.hostClass);
    const cleanedExtraClass = this.sanitizeClasses(this.extraClass);

    return [
      base,
      variants[resolvedVariant],
      sizes[this.size],
      this.fullWidth ? 'w-full' : '',
      this.disabled ? 'btn-disabled' : '',
      cleanedHostClass,
      cleanedExtraClass
    ]
      .filter(Boolean)
      .join(' ');
  }

  private resolveVariant(): 'primary' | 'secondary' | 'ghost' | 'linkish' {
    if (this.variant !== 'ghost') {
      return this.variant;
    }

    const source = `${this.hostClass} ${this.extraClass}`;
    if (UiButtonComponent.SECONDARY_HINT_PATTERN.test(source)) {
      return 'secondary';
    }
    if (UiButtonComponent.PRIMARY_HINT_PATTERN.test(source)) {
      return 'primary';
    }

    return 'ghost';
  }

  private sanitizeClasses(raw: string): string {
    if (!raw) {
      return '';
    }

    return raw
      .replace(UiButtonComponent.LEGACY_CLASS_PATTERN, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  onClick(event: MouseEvent): void {
    if (this.disabled) {
      event.preventDefault();
      return;
    }
    this.pressed.emit(event);
  }
}
