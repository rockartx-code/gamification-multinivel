import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import {
  CreateAccountCustomer,
  PasswordRecoveryRequestResponse,
  ResetPasswordPayload,
  ResetPasswordResponse
} from '../models/auth.model';
import { AdminViewId, AppPrivilege, normalizePrivileges, SCREEN_PRIVILEGE_BY_VIEW, UserPrivileges } from '../models/privileges.model';
import { ApiService } from './api.service';

export type UserRole = 'admin' | 'cliente';

export interface AuthUser {
  userId?: string;
  name: string;
  role: UserRole;
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
  isSuperUser?: boolean;
  discountPercent?: number;
  discountActive?: boolean;
  level?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly storageKey = 'auth-user';
  private readonly userSubject = new BehaviorSubject<AuthUser | null>(this.loadUser());

  readonly user$ = this.userSubject.asObservable();

  constructor(private readonly api: ApiService) {}

  get currentUser(): AuthUser | null {
    return this.userSubject.value;
  }

  get isLoggedIn(): boolean {
    return this.userSubject.value !== null;
  }

  login(username: string, password: string): Observable<AuthUser> {
    return this.api.login(username, password).pipe(tap((user) => this.setUser(user)));
  }

  requestPasswordRecovery(email: string): Observable<PasswordRecoveryRequestResponse> {
    return this.api.requestPasswordRecovery({ email });
  }

  resetPassword(payload: ResetPasswordPayload): Observable<ResetPasswordResponse> {
    return this.api.resetPassword(payload);
  }

  loginAs(role: UserRole): AuthUser {
    const user: AuthUser =
      role === 'admin'
        ? {
            userId: 'admin-001',
            name: 'Admin Rivera',
            role: 'admin',
            canAccessAdmin: true,
            isSuperUser: true
          }
        : {
            userId: 'client-001',
            name: 'Valeria Torres',
            role: 'cliente',
            canAccessAdmin: false,
            discountPercent: 15,
            discountActive: true
          };

    this.setUser(user);
    return user;
  }

  logout(): void {
    this.userSubject.next(null);
    localStorage.removeItem(this.storageKey);
  }

  setUserFromCreateAccount(customer: CreateAccountCustomer): void {
    const user: AuthUser = {
      userId: customer?.id != null ? String(customer.id) : undefined,
      name: customer?.name || '',
      role: 'cliente',
      discountPercent: customer?.discountRate ? Math.round(customer.discountRate * 100) : 0,
      discountActive: Boolean(customer?.activeBuyer || (customer?.discountRate ?? 0) > 0),
      level: customer?.level
    };
    this.setUser(user);
  }

  private setUser(user: AuthUser): void {
    const normalized: AuthUser = {
      ...user,
      canAccessAdmin: Boolean(user.canAccessAdmin),
      privileges: normalizePrivileges(user.privileges)
    };
    this.userSubject.next(normalized);
    localStorage.setItem(this.storageKey, JSON.stringify(normalized));
  }

  isSuperUser(user: AuthUser | null | undefined = this.currentUser): boolean {
    if (!user) {
      return false;
    }
    if (user.isSuperUser) {
      return true;
    }
    return user.userId === 'admin-001' || user.name.trim().toLowerCase() === 'admin';
  }

  hasAdminPanelAccess(user: AuthUser | null | undefined = this.currentUser): boolean {
    if (!user) {
      return false;
    }
    if (this.isSuperUser(user)) {
      return true;
    }
    return Boolean(user.canAccessAdmin || user.role === 'admin');
  }

  hasUserDashboardAccess(user: AuthUser | null | undefined = this.currentUser): boolean {
    if (!user) {
      return false;
    }
    return !this.isSuperUser(user);
  }

  hasAdminAndUserAccess(user: AuthUser | null | undefined = this.currentUser): boolean {
    return this.hasAdminPanelAccess(user) && this.hasUserDashboardAccess(user);
  }

  defaultRoute(user: AuthUser | null | undefined = this.currentUser): string {
    if (this.hasUserDashboardAccess(user)) {
      return '/dashboard';
    }
    if (this.hasAdminPanelAccess(user)) {
      return '/admin';
    }
    return '/dashboard';
  }

  hasPrivilege(privilege: AppPrivilege, user: AuthUser | null | undefined = this.currentUser): boolean {
    if (!user) {
      return false;
    }
    if (this.isSuperUser(user)) {
      return true;
    }
    return user.privileges?.[privilege] === true;
  }

  canAccessAdminView(view: AdminViewId, user: AuthUser | null | undefined = this.currentUser): boolean {
    if (!this.hasAdminPanelAccess(user)) {
      return false;
    }
    return this.hasPrivilege(SCREEN_PRIVILEGE_BY_VIEW[view], user);
  }

  private loadUser(): AuthUser | null {
    const raw = localStorage.getItem(this.storageKey);
    if (!raw) {
      return null;
    }

    try {
      const parsed = JSON.parse(raw) as AuthUser;
      return {
        ...parsed,
        canAccessAdmin: Boolean(parsed.canAccessAdmin),
        privileges: normalizePrivileges(parsed.privileges)
      };
    } catch {
      localStorage.removeItem(this.storageKey);
      return null;
    }
  }
}
