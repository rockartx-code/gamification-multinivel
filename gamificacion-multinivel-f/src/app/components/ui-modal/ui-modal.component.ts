import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnDestroy,
  Output,
  ViewChild
} from '@angular/core';

/** Selector de elementos potencialmente enfocables dentro del diálogo. */
const FOCUSABLE_SELECTOR = [
  'a[href]',
  'area[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'iframe',
  'audio[controls]',
  'video[controls]',
  '[contenteditable]:not([contenteditable="false"])',
  '[tabindex]:not([tabindex="-1"])'
].join(', ');

@Component({
  selector: 'ui-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-modal.component.html'
})
export class UiModalComponent implements OnDestroy {
  @Input() maxWidthClass = 'max-w-lg';
  @Input() contentClass = 'p-6';
  @Input() containerClass = 'fixed inset-0 z-50 flex items-center justify-center modal-backdrop px-4';
  @Input() panelClass = 'modal-card w-full max-h-[90vh] overflow-hidden';
  @Input() closeOnBackdrop = true;
  /** Etiqueta accesible del diálogo (cuando el contenido no tiene encabezado propio). */
  @Input() ariaLabel = '';

  @Output() closed = new EventEmitter<void>();

  private open = false;
  /** Elemento que tenía el foco antes de abrir el diálogo, para devolvérselo al cerrar. */
  private previouslyFocused: HTMLElement | null = null;
  /** Panel del diálogo; solo existe en el DOM mientras está abierto (*ngIf). */
  private panel: HTMLElement | null = null;

  @Input()
  set isOpen(value: boolean) {
    const next = !!value;
    if (next === this.open) {
      return;
    }
    this.open = next;
    if (next) {
      // Se abre: recordamos quién tenía el foco antes de que el panel entre al DOM.
      this.previouslyFocused = this.getActiveElement();
    } else {
      // Se cierra: el panel desaparece del DOM y devolvemos el foco.
      this.panel = null;
      this.restoreFocus();
    }
  }
  get isOpen(): boolean {
    return this.open;
  }

  /**
   * El setter se dispara cuando *ngIf crea (o destruye) el panel, así que es el
   * momento exacto para llevar el foco dentro del diálogo recién abierto.
   */
  @ViewChild('panel')
  set panelRef(ref: ElementRef<HTMLElement> | undefined) {
    this.panel = ref?.nativeElement ?? null;
    if (this.panel && this.open) {
      this.focusFirstElement();
    }
  }

  close(): void {
    this.closed.emit();
  }

  onBackdropClick(): void {
    if (this.closeOnBackdrop) {
      this.close();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open && this.closeOnBackdrop) {
      this.close();
    }
  }

  /** Atrapa el Tab dentro del panel: del último enfocable vuelve al primero y al revés con Shift+Tab. */
  onPanelKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Tab' || !this.panel) {
      return;
    }

    const focusables = this.getFocusableElements();
    if (focusables.length === 0) {
      // Sin elementos enfocables el foco se queda en el propio panel.
      event.preventDefault();
      this.panel.focus();
      return;
    }

    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = this.getActiveElement();

    if (event.shiftKey && (active === first || active === this.panel || !this.panel.contains(active))) {
      event.preventDefault();
      last.focus();
      return;
    }

    if (!event.shiftKey && (active === last || !this.panel.contains(active))) {
      event.preventDefault();
      first.focus();
    }
  }

  ngOnDestroy(): void {
    // Si el componente muere con el diálogo abierto, el foco no debe quedarse huérfano.
    this.panel = null;
    if (this.open) {
      this.open = false;
      this.restoreFocus();
    }
    this.previouslyFocused = null;
  }

  /** Mueve el foco al primer enfocable del panel, o al panel mismo (tabindex="-1") si no hay ninguno. */
  private focusFirstElement(): void {
    if (!this.panel) {
      return;
    }
    const focusables = this.getFocusableElements();
    (focusables[0] ?? this.panel).focus();
  }

  /** Devuelve el foco al elemento que lo tenía antes de abrir, si sigue en el documento. */
  private restoreFocus(): void {
    const target = this.previouslyFocused;
    this.previouslyFocused = null;
    if (target && typeof target.focus === 'function' && target.isConnected) {
      target.focus();
    }
  }

  private getFocusableElements(): HTMLElement[] {
    if (!this.panel) {
      return [];
    }
    const nodes = Array.from(this.panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
    // Descartamos lo deshabilitado u oculto (sin medir layout: jsdom/SSR no lo calculan).
    return nodes.filter((node) => !node.hasAttribute('disabled') && this.isVisible(node));
  }

  private isVisible(node: HTMLElement): boolean {
    if (node.hasAttribute('hidden') || node.getAttribute('aria-hidden') === 'true' || node.closest('[hidden]')) {
      return false;
    }
    if (typeof window === 'undefined' || typeof window.getComputedStyle !== 'function') {
      return true;
    }
    const style = window.getComputedStyle(node);
    return style.display !== 'none' && style.visibility !== 'hidden';
  }

  /** Acceso al foco actual seguro en SSR/pruebas (puede no existir `document`). */
  private getActiveElement(): HTMLElement | null {
    if (typeof document === 'undefined') {
      return null;
    }
    const active = document.activeElement;
    return active instanceof HTMLElement ? active : null;
  }
}
