import { Injectable } from '@angular/core';

import { BusinessConfigNotificationTone } from '../models/business-config.model';
import { BrowserTimerService } from './browser/browser-timer.service';

export interface UiNotificationState {
  message: string;
  tone: BusinessConfigNotificationTone;
  visible: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  constructor(private readonly timer: BrowserTimerService) {}

  createState(): UiNotificationState {
    return {
      message: '',
      tone: 'info',
      visible: false
    };
  }

  show(state: UiNotificationState, message: string, tone: BusinessConfigNotificationTone = 'info'): void {
    state.message = message;
    state.tone = tone;
    state.visible = Boolean(message);
  }

  clear(state: UiNotificationState): void {
    state.message = '';
    state.visible = false;
    state.tone = 'info';
  }

  showFor(
    state: UiNotificationState,
    message: string,
    duration: number,
    timeoutId?: number,
    tone: BusinessConfigNotificationTone = 'info'
  ): number | undefined {
    this.timer.clearTimeout(timeoutId);
    this.show(state, message, tone);
    return this.timer.setTimeout(() => this.clear(state), duration);
  }
}
