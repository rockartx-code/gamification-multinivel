import { Injectable } from '@angular/core';

import { PortalNotification } from '../models/portal-notification.model';

export type UserDashboardNotificationModalState = {
  activeNotification: PortalNotification | null;
  isNotificationModalOpen: boolean;
  isNotificationsCenterOpen: boolean;
  shouldMarkAsRead: boolean;
};

export type UserDashboardNotificationQueueState = {
  queue: PortalNotification[];
  activeNotification: PortalNotification | null;
  isNotificationModalOpen: boolean;
};

@Injectable({ providedIn: 'root' })
export class UserDashboardNotificationsService {
  prepareQueue(notifications: PortalNotification[], isGuest: boolean): PortalNotification[] {
    if (isGuest || !notifications.length) {
      return [];
    }
    return notifications.filter((notification) => !notification.isRead);
  }

  openNotification(notification: PortalNotification | null): UserDashboardNotificationModalState {
    if (!notification) {
      return {
        activeNotification: null,
        isNotificationModalOpen: false,
        isNotificationsCenterOpen: false,
        shouldMarkAsRead: false
      };
    }

    return {
      activeNotification: notification,
      isNotificationModalOpen: true,
      isNotificationsCenterOpen: false,
      shouldMarkAsRead: !notification.isRead
    };
  }

  closeModal(queue: PortalNotification[]): { shouldOpenNext: boolean } & UserDashboardNotificationModalState {
    return {
      activeNotification: null,
      isNotificationModalOpen: false,
      isNotificationsCenterOpen: false,
      shouldMarkAsRead: false,
      shouldOpenNext: queue.length > 0
    };
  }

  takeNext(queue: PortalNotification[]): UserDashboardNotificationQueueState {
    const nextQueue = [...queue];
    const next = nextQueue.shift() ?? null;
    return {
      queue: nextQueue,
      activeNotification: next,
      isNotificationModalOpen: Boolean(next)
    };
  }
}
