import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { AuthContext, AuthSession, UserRole } from '../domain/models';
import { authAccounts } from '../mocks/auth-session.fixture';
import { authFixture } from '../mocks/auth.fixture';

const AUTH_SESSION_KEY = 'auth-session';
const SESSION_TTL_MS = 1000 * 60 * 60 * 8;

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiClient = inject(ApiClient);
  private readonly platformId = inject(PLATFORM_ID);

  getAuthContext(): Observable<AuthContext> {
    return this.apiClient.get(authFixture);
  }

  login(email: string, password: string): Observable<AuthSession> {
    const account = authAccounts.find((entry) => entry.email === email && entry.password === password);
    if (!account) {
      return throwError(() => new Error('Credenciales inválidas.'));
    }

    const session: AuthSession = {
      email: account.email,
      role: account.role,
      token: `mock-${account.role}-${Date.now()}`,
      expiresAt: Date.now() + SESSION_TTL_MS,
    };

    this.persistSession(session);
    return this.apiClient.get(session);
  }

  getSession(): AuthSession | null {
    if (!isPlatformBrowser(this.platformId)) {
      return null;
    }

    const storedSession = window.localStorage.getItem(AUTH_SESSION_KEY);
    if (!storedSession) {
      return null;
    }

    try {
      const session = JSON.parse(storedSession) as AuthSession;
      if (!this.isSessionValid(session)) {
        this.clearSession();
        return null;
      }
      return session;
    } catch {
      this.clearSession();
      return null;
    }
  }

  validateSession(): boolean {
    return this.getSession() !== null;
  }

  clearSession(): void {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    window.localStorage.removeItem(AUTH_SESSION_KEY);
  }

  private persistSession(session: AuthSession): void {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    window.localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
  }

  private isSessionValid(session: AuthSession): boolean {
    if (!session || typeof session !== 'object') {
      return false;
    }

    const role = session.role;
    const isRoleValid: role is UserRole = role === 'admin' || role === 'user' || role === 'public';
    if (!isRoleValid) {
      return false;
    }

    return typeof session.token === 'string' && typeof session.email === 'string' && session.expiresAt > Date.now();
  }
}
