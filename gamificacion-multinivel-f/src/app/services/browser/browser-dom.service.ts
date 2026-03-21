import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class BrowserDomService {
  getElementById<T extends HTMLElement = HTMLElement>(id: string): T | null {
    if (typeof document === 'undefined' || !id) {
      return null;
    }
    return document.getElementById(id) as T | null;
  }

  querySelector<T extends Element = Element>(selector: string): T | null {
    if (typeof document === 'undefined' || !selector) {
      return null;
    }
    return document.querySelector<T>(selector);
  }

  scrollIntoView(target: Element | null | undefined, options?: ScrollIntoViewOptions): void {
    target?.scrollIntoView(options);
  }

  focus(target: HTMLElement | null | undefined): void {
    target?.focus();
  }
}
