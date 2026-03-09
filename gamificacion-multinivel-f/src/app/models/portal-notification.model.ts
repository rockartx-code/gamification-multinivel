export type PortalNotificationStatus = 'active' | 'scheduled' | 'expired' | 'inactive';

export interface PortalNotification {
  id: string;
  title: string;
  description: string;
  linkUrl?: string;
  linkText?: string;
  startAt?: string;
  endAt?: string;
  active: boolean;
  status?: PortalNotificationStatus;
  isRead?: boolean;
  readAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface SavePortalNotificationPayload {
  id?: string;
  title: string;
  description: string;
  linkUrl?: string;
  linkText?: string;
  startAt: string;
  endAt: string;
  active: boolean;
}

export interface NotificationReadResponse {
  ok: boolean;
  notificationId: string;
  customerId?: number | string;
  readAt?: string;
}
