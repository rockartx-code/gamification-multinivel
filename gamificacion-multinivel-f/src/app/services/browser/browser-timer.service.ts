import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class BrowserTimerService {
  setTimeout(callback: () => void, delay = 0): number | undefined {
    if (typeof window === 'undefined') {
      return undefined;
    }
    return window.setTimeout(callback, delay);
  }

  clearTimeout(timeoutId?: number): void {
    if (typeof window === 'undefined' || timeoutId == null) {
      return;
    }
    window.clearTimeout(timeoutId);
  }

  setInterval(callback: () => void, delay: number): number | undefined {
    if (typeof window === 'undefined') {
      return undefined;
    }
    return window.setInterval(callback, delay);
  }

  clearInterval(intervalId?: number): void {
    if (typeof window === 'undefined' || intervalId == null) {
      return;
    }
    window.clearInterval(intervalId);
  }

  requestAnimationFrame(callback: FrameRequestCallback): number | undefined {
    if (typeof requestAnimationFrame !== 'function') {
      return this.setTimeout(() => callback(Date.now()), 16);
    }
    return requestAnimationFrame(callback);
  }
}
