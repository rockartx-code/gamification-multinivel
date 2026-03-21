import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class BrowserLocationService {
  get origin(): string {
    return this.location?.origin ?? '';
  }

  get hash(): string {
    return this.location?.hash ?? '';
  }

  assign(url: string): void {
    if (!url) {
      return;
    }
    this.location?.assign(url);
  }

  open(url: string, target = '_blank', features = 'noopener'): Window | null {
    if (typeof window === 'undefined' || !url) {
      return null;
    }
    return window.open(url, target, features);
  }

  reload(): void {
    this.location?.reload();
  }

  private get location(): Location | null {
    if (typeof window === 'undefined') {
      return null;
    }
    return window.location;
  }
}
