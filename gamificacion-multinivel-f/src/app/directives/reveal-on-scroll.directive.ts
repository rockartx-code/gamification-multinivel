import { Directive, ElementRef, Input, NgZone, OnDestroy, OnInit, Renderer2 } from '@angular/core';

/**
 * Hace aparecer el elemento con un desplazamiento suave cuando entra al
 * viewport. Usa las clases .reveal / .is-visible de styles.css y respeta
 * prefers-reduced-motion (definido también en CSS).
 *
 *   <div revealOnScroll [revealDelay]="120">…</div>
 */
@Directive({
  selector: '[revealOnScroll]',
  standalone: true
})
export class RevealOnScrollDirective implements OnInit, OnDestroy {
  /** Retraso en ms antes de iniciar la transición (para escalonar tarjetas). */
  @Input() revealDelay = 0;

  private observer: IntersectionObserver | null = null;

  constructor(
    private readonly el: ElementRef<HTMLElement>,
    private readonly renderer: Renderer2,
    private readonly zone: NgZone
  ) {}

  ngOnInit(): void {
    const element = this.el.nativeElement;

    if (typeof IntersectionObserver === 'undefined') {
      return;
    }

    this.renderer.addClass(element, 'reveal');
    if (this.revealDelay > 0) {
      this.renderer.setStyle(element, '--reveal-delay', `${this.revealDelay}ms`, 2 /* DashCase */);
    }

    this.zone.runOutsideAngular(() => {
      this.observer = new IntersectionObserver(
        entries => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              this.renderer.addClass(entry.target, 'is-visible');
              this.observer?.unobserve(entry.target);
            }
          }
        },
        { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
      );
      this.observer.observe(element);
    });
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    this.observer = null;
  }
}
