import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import { ApiService } from './api.service';

export type UserRole = 'admin' | 'cliente';

export interface AuthUser {
  userId?: string;
  name: string;
  role: UserRole;
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

  loginAs(role: UserRole): AuthUser {
    const user: AuthUser =
      role === 'admin'
        ? {
            userId: 'admin-001',
            name: 'Admin Rivera',
            role: 'admin'
          }
        : {
            userId: 'client-001',
            name: 'Valeria Torres',
            role: 'cliente',
            discountPercent: 15,
            discountActive: true,
            level: 'Oro'
          };

    this.setUser(user);
    return user;
  }

  logout(): void {
    this.userSubject.next(null);
    localStorage.removeItem(this.storageKey);
  }

  private setUser(user: AuthUser): void {
    this.userSubject.next(user);
    localStorage.setItem(this.storageKey, JSON.stringify(user));
  }

  private loadUser(): AuthUser | null {
    const raw = localStorage.getItem(this.storageKey);
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw) as AuthUser;
    } catch {
      localStorage.removeItem(this.storageKey);
      return null;
    }
  }
}
