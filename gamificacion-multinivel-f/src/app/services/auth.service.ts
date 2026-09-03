import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, map, tap } from 'rxjs';

import {
  CreateAccountCustomer,
  PasswordRecoveryRequestResponse,
  ResendEmailConfirmationResponse,
  ResetPasswordPayload,
  ResetPasswordResponse
} from '../models/auth.model';
import { RespuestaOk, SesionAbierta } from '../models/checkout.model';
import { AdminViewId, AppPrivilege, normalizePrivileges, SCREEN_PRIVILEGE_BY_VIEW, UserPrivileges } from '../models/privileges.model';
import { ApiService } from './api.service';
import { CheckoutService } from './checkout.service';

export type UserRole = 'admin' | 'cliente' | 'employee';

export interface AuthUser {
  userId?: string;
  name: string;
  role: UserRole;
  token?: string;
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
  isSuperUser?: boolean;
  discountPercent?: number;
  discountActive?: boolean;
  level?: string;
  // paquete C · sesión persistente
  /** true → 30 días en localStorage; false → 24 h en sessionStorage (se cierra con el navegador). */
  rememberMe?: boolean;
  expiresAt?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly storageKey = 'auth-user';
  private readonly userSubject = new BehaviorSubject<AuthUser | null>(this.loadUser());

  readonly user$ = this.userSubject.asObservable();

  constructor(
    private readonly api: ApiService,
    private readonly checkout: CheckoutService
  ) {}

  get currentUser(): AuthUser | null {
    return this.userSubject.value;
  }

  get isLoggedIn(): boolean {
    return this.userSubject.value !== null;
  }

  get hasSession(): boolean {
    return this.hasValidSession(this.userSubject.value);
  }

  /**
   * Inicia sesión. Con "Recordarme" (por omisión) la sesión dura 30 días y vive en
   * localStorage; sin marcarlo dura 24 horas y vive en sessionStorage, así que se
   * cierra al cerrar el navegador (computadoras compartidas).
   */
  login(username: string, password: string, rememberMe = true): Observable<AuthUser> {
    return this.checkout.iniciarSesion(username, password, rememberMe).pipe(
      map((sesion) => this.usuarioDesdeSesion(sesion, rememberMe)),
      tap((user) => this.setUser(user))
    );
  }

  /** Enlace de acceso por correo: pide el enlace (nunca revela si el correo existe). */
  requestLoginLink(email: string, rememberMe = true): Observable<RespuestaOk> {
    return this.checkout.pedirEnlaceAcceso(email, rememberMe);
  }

  /** Canjea el enlace `/#/login?enlace=TOKEN` y abre la sesión. */
  loginWithLink(token: string, rememberMe = true): Observable<AuthUser> {
    return this.checkout.canjearEnlaceAcceso(token, rememberMe).pipe(
      map((sesion) => this.usuarioDesdeSesion(sesion, rememberMe)),
      tap((user) => this.setUser(user))
    );
  }

  requestPasswordRecovery(email: string): Observable<PasswordRecoveryRequestResponse> {
    return this.api.requestPasswordRecovery({ email });
  }

  resendEmailConfirmation(email: string): Observable<ResendEmailConfirmationResponse> {
    return this.api.resendEmailConfirmation({ email });
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
    this.borrarAlmacenado();
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

  private usuarioDesdeSesion(sesion: SesionAbierta, rememberMe: boolean): AuthUser {
    if (!sesion?.token) {
      throw new Error('La respuesta de acceso no incluyó la sesión.');
    }
    const user = sesion.user;
    return {
      ...user,
      userId: user?.userId != null ? String(user.userId) : undefined,
      name: user?.name || '',
      role: user?.role || 'cliente',
      token: sesion.token,
      rememberMe: sesion.rememberMe ?? rememberMe,
      expiresAt: sesion.expiresAt
    };
  }

  private setUser(user: AuthUser): void {
    const normalized: AuthUser = {
      ...user,
      token: typeof user.token === 'string' && user.token.trim().length > 0 ? user.token.trim() : undefined,
      canAccessAdmin: Boolean(user.canAccessAdmin),
      privileges: normalizePrivileges(user.privileges),
      rememberMe: user.rememberMe !== false
    };
    this.userSubject.next(normalized);
    this.guardar(normalized);
  }

  /** Persiste la sesión donde toca y limpia el otro almacén para no dejar dos copias. */
  private guardar(user: AuthUser): void {
    const serializado = JSON.stringify(user);
    try {
      if (user.rememberMe === false) {
        sessionStorage.setItem(this.storageKey, serializado);
        localStorage.removeItem(this.storageKey);
      } else {
        localStorage.setItem(this.storageKey, serializado);
        sessionStorage.removeItem(this.storageKey);
      }
    } catch {
      // Almacenamiento bloqueado (modo privado): la sesión vive solo en memoria.
    }
  }

  private borrarAlmacenado(): void {
    try {
      localStorage.removeItem(this.storageKey);
      sessionStorage.removeItem(this.storageKey);
    } catch {
      // nada que limpiar
    }
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
    return !this.hasAdminPanelAccess(user);
  }

  hasAdminAndUserAccess(user: AuthUser | null | undefined = this.currentUser): boolean {
    return this.hasAdminPanelAccess(user) && this.hasUserDashboardAccess(user);
  }

  defaultRoute(user: AuthUser | null | undefined = this.currentUser): string {
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
    // La sesión corta (sin "Recordarme") manda sobre la larga si conviven.
    let raw: string | null = null;
    try {
      raw = sessionStorage.getItem(this.storageKey) ?? localStorage.getItem(this.storageKey);
    } catch {
      raw = null;
    }
    if (!raw) {
      return null;
    }

    try {
      const parsed = JSON.parse(raw) as AuthUser;
      if (this.sesionVencida(parsed)) {
        this.borrarAlmacenado();
        return null;
      }
      return {
        ...parsed,
        canAccessAdmin: Boolean(parsed.canAccessAdmin),
        privileges: normalizePrivileges(parsed.privileges)
      };
    } catch {
      this.borrarAlmacenado();
      return null;
    }
  }

  /** `expiresAt` es informativo (el TTL de la sesión manda en el servidor), pero evita mostrar un panel muerto. */
  private sesionVencida(user: AuthUser): boolean {
    if (!user?.expiresAt) {
      return false;
    }
    const vence = Date.parse(user.expiresAt);
    return Number.isFinite(vence) && vence <= Date.now();
  }

  private hasValidSession(user: AuthUser | null | undefined): boolean {
    return typeof user?.token === 'string' && user.token.trim().length > 0;
  }
}
