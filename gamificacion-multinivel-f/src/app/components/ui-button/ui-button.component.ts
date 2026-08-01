import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Component, ElementRef, EventEmitter, Input, OnInit, Output } from '@angular/core';

@Component({
  selector: 'ui-button',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './ui-button.component.html',
  styleUrls: ['./ui-button.component.css']
})
export class UiButtonComponent implements OnInit {
  private static readonly PRIMARY_HINT_PATTERN =
    /\b(?:bg-gradient-to-r|(?:from|to|via)-(?:gold|primary|amber)|btn-primary)\b/;
  private static readonly SECONDARY_HINT_PATTERN =
    /\b(?:from-olive|to-secondary|btn-secondary)\b/;
  private static readonly LEGACY_CLASS_PATTERN =
    /\b(?:bg-gradient-to-r|(?:from|to|via)-[\w-]+|bg-[^\s"]+|border(?:-[^\s"]+)?|shadow(?:-[^\s"]+)?|shadow-\[[^\]]+\]|(?:[a-z]+:)*(?:hover|active):scale-[^\s"]+|transition-transform|hover-bg-[^\s"]+|(?:[a-z]+:)*p[xy]-[^\s"]+|btn-primary|btn-secondary|btn-ghost|btn-linkish)\b/g;

  @Input('class') hostClass = '';
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() variant: 'primary' | 'secondary' | 'ghost' | 'linkish' | 'danger' = 'ghost';
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

  /**
   * El `aria-label` puesto en `<ui-button aria-label="...">` cae en el HOST (este elemento), no
   * en el `<button>` nativo interno (que solo tiene un ícono `aria-hidden`) — su nombre accesible
   * quedaba vacío para lectores de pantalla / `getByRole('button', {name})`. Se lee el atributo
   * del host y se reexpone en el `<button>` real sin tocar el atributo del host (varias pruebas
   * lo ubican por `ui-button[aria-label="..."]`).
   */
  innerAriaLabel: string | null = null;
  /** Mismo problema/solución que innerAriaLabel, pero para `aria-describedby` (p. ej. el hint
   * de confirmación de una acción destructiva como "Cancelar orden"). */
  innerAriaDescribedby: string | null = null;

  constructor(private readonly elementRef: ElementRef<HTMLElement>) {}

  ngOnInit(): void {
    this.innerAriaLabel = this.elementRef.nativeElement.getAttribute('aria-label');
    this.innerAriaDescribedby = this.elementRef.nativeElement.getAttribute('aria-describedby');
  }

  get classes(): string {
    const base = 'btn inline-flex items-center justify-center gap-2';
    const variants = {
      primary: 'btn-primary',
      secondary: 'btn-secondary',
      ghost: 'btn-ghost',
      linkish: 'btn-linkish',
      danger: 'btn-ghost-danger'
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

  private resolveVariant(): 'primary' | 'secondary' | 'ghost' | 'linkish' | 'danger' {
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
