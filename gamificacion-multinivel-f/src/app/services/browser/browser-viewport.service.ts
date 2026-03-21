import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class BrowserViewportService {
  matches(query: string): boolean {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function' || !query) {
      return false;
    }
    return window.matchMedia(query).matches;
  }
}
