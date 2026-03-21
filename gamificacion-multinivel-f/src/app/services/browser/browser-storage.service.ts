import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class BrowserStorageService {
  getItem(key: string): string | null {
    try {
      return this.storage?.getItem(key) ?? null;
    } catch {
      return null;
    }
  }

  setItem(key: string, value: string): void {
    try {
      this.storage?.setItem(key, value);
    } catch {
      // ignore storage errors
    }
  }

  removeItem(key: string): void {
    try {
      this.storage?.removeItem(key);
    } catch {
      // ignore storage errors
    }
  }

  getJson<T>(key: string): T | null {
    const raw = this.getItem(key);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  }

  setJson(key: string, value: unknown): void {
    this.setItem(key, JSON.stringify(value));
  }

  private get storage(): Storage | null {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    return localStorage;
  }
}
