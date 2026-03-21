import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class BrowserClipboardService {
  get canWrite(): boolean {
    return typeof navigator !== 'undefined' && typeof navigator.clipboard?.write === 'function';
  }

  get canWriteText(): boolean {
    return typeof navigator !== 'undefined' && typeof navigator.clipboard?.writeText === 'function';
  }

  write(items: ClipboardItem[]): Promise<void> {
    if (!this.canWrite) {
      return Promise.reject(new Error('Clipboard API unavailable.'));
    }
    return navigator.clipboard.write(items);
  }

  writeText(text: string): Promise<void> {
    if (!this.canWriteText) {
      return Promise.reject(new Error('Clipboard text API unavailable.'));
    }
    return navigator.clipboard.writeText(text);
  }
}
