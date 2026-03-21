import { Injectable } from '@angular/core';

import { SaveAdminNotificationPayload } from '../models/admin.model';
import { PortalNotification } from '../models/portal-notification.model';
import { NotificationService, UiNotificationState } from './notification.service';

export type AdminNotificationForm = {
  id: string;
  title: string;
  description: string;
  linkUrl: string;
  linkText: string;
  startAt: string;
  endAt: string;
  active: boolean;
};

@Injectable({ providedIn: 'root' })
export class AdminNotificationFormService {
  constructor(private readonly notifier: NotificationService) {}

  createNotice(): UiNotificationState {
    return this.notifier.createState();
  }

  createDefaultForm(now = new Date()): AdminNotificationForm {
    const end = new Date(now.getTime() + 1000 * 60 * 60 * 24 * 7);
    return {
      id: '',
      title: '',
      description: '',
      linkUrl: '',
      linkText: 'Ver',
      startAt: this.toDateTimeLocalInput(now.toISOString()),
      endAt: this.toDateTimeLocalInput(end.toISOString()),
      active: true
    };
  }

  createEditForm(notification: PortalNotification): AdminNotificationForm {
    return {
      id: notification.id,
      title: notification.title,
      description: notification.description,
      linkUrl: notification.linkUrl || '',
      linkText: notification.linkText || 'Ver',
      startAt: this.toDateTimeLocalInput(notification.startAt),
      endAt: this.toDateTimeLocalInput(notification.endAt),
      active: notification.active !== false
    };
  }

  updateField(
    form: AdminNotificationForm,
    field: 'title' | 'description' | 'linkUrl' | 'linkText' | 'startAt' | 'endAt',
    value: string
  ): AdminNotificationForm {
    return {
      ...form,
      [field]: value
    };
  }

  descriptionLength(form: AdminNotificationForm): number {
    return form.description.length;
  }

  isValid(form: AdminNotificationForm): boolean {
    return Boolean(
      form.title.trim() &&
        form.description.trim() &&
        form.startAt &&
        form.endAt &&
        this.descriptionLength(form) <= 300 &&
        new Date(form.endAt).getTime() >= new Date(form.startAt).getTime()
    );
  }

  buildPayload(form: AdminNotificationForm): SaveAdminNotificationPayload {
    const linkUrl = form.linkUrl.trim();
    return {
      id: form.id || undefined,
      title: form.title.trim(),
      description: form.description.trim(),
      linkUrl: linkUrl || undefined,
      linkText: linkUrl ? form.linkText.trim() || 'Ver' : undefined,
      startAt: this.fromDateTimeLocalInput(form.startAt),
      endAt: this.fromDateTimeLocalInput(form.endAt),
      active: form.active
    };
  }

  announceEditing(state: UiNotificationState, notification: PortalNotification): void {
    this.notifier.show(state, `Editando notificacion: ${notification.title}.`);
  }

  announceSaveSuccess(state: UiNotificationState, formId: string, title: string): void {
    this.notifier.show(state, formId ? `Notificacion actualizada: ${title}.` : `Notificacion creada: ${title}.`, 'success');
  }

  announceSaveError(state: UiNotificationState): void {
    this.notifier.show(state, 'No se pudo guardar la notificacion.', 'error');
  }

  private toDateTimeLocalInput(value?: string): string {
    if (!value) {
      return '';
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return '';
    }
    const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
  }

  private fromDateTimeLocalInput(value: string): string {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? '' : parsed.toISOString();
  }
}
