import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, catchError, map, shareReplay, tap, throwError } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  ActivacionModoSocioRespuesta,
  AhorroSocio,
  ModoCuenta,
  ModoCuentaRespuesta,
  PlanSocio,
  calcularAhorroConTramos
} from '../models/plan-socio.model';
import { AuthService } from './auth.service';
import { RealApiService } from './real-api.service';

export type ModoVisible = ModoCuenta | 'invitado';

/**
 * Plan publicado y modo de la cuenta (paquete B).
 *
 * `plan$` cachea `GET /catalog/plan`; `modoActual` es lo que sabemos de la
 * sesión (lo dice el login, lo confirma el panel y lo cambia la activación).
 */
@Injectable({
  providedIn: 'root'
})
export class PlanSocioService {
  private readonly baseUrl = environment.apiBaseUrl;
  private planRequest?: Observable<PlanSocio>;
  private readonly modoSubject = new BehaviorSubject<ModoVisible>('invitado');

  readonly modo$ = this.modoSubject.asObservable();

  constructor(
    private readonly http: HttpClient,
    private readonly realApi: RealApiService,
    private readonly authService: AuthService
  ) {
    this.authService.user$.subscribe((user) => {
      if (!user || !this.authService.hasSession) {
        this.modoSubject.next('invitado');
        return;
      }
      // Las sesiones abiertas antes de esta ronda no traen `mode`: se asume
      // socio (no se promete un ahorro que no exista) hasta que el panel lo confirme.
      this.modoSubject.next(user.mode === 'cliente' ? 'cliente' : 'socio');
    });
  }

  get modoActual(): ModoVisible {
    return this.modoSubject.value;
  }

  /** Lo llama el panel al cargar (`GET /customers/dashboard` trae `mode`). */
  fijarModo(modo: ModoVisible | null | undefined): void {
    if (modo === 'cliente' || modo === 'socio' || modo === 'invitado') {
      if (modo !== this.modoSubject.value) {
        this.modoSubject.next(modo);
      }
    }
  }

  get plan$(): Observable<PlanSocio> {
    if (!this.planRequest) {
      this.planRequest = this.http.get<{ plan: PlanSocio }>(`${this.baseUrl}/catalog/plan`).pipe(
        map((respuesta) => respuesta.plan),
        catchError((error) => {
          // Sin caché de un error: el siguiente que pregunte vuelve a intentar.
          this.planRequest = undefined;
          return throwError(() => error);
        }),
        shareReplay(1)
      );
    }
    return this.planRequest;
  }

  modo(): Observable<ModoCuentaRespuesta> {
    return this.http
      .get<ModoCuentaRespuesta>(`${this.baseUrl}/customers/modo`, { headers: this.realApi.actorHeaders() })
      .pipe(tap((respuesta) => this.fijarModo(respuesta.mode)));
  }

  /**
   * Sin `customerId` activa la propia cuenta. Un admin con `customer_add`
   * puede pasar `customerId` y `mode` (también para regresar a cliente).
   */
  activarModoSocio(opciones: { customerId?: string | number; mode?: ModoCuenta; acceptedPlanVersion?: string } = {}): Observable<ActivacionModoSocioRespuesta> {
    const cuerpo: Record<string, unknown> = {};
    if (opciones.customerId != null) {
      cuerpo['customerId'] = String(opciones.customerId);
    }
    if (opciones.mode) {
      cuerpo['mode'] = opciones.mode;
    }
    if (opciones.acceptedPlanVersion) {
      cuerpo['acceptedPlanVersion'] = opciones.acceptedPlanVersion;
    }
    return this.http
      .post<ActivacionModoSocioRespuesta>(`${this.baseUrl}/customers/modo-socio`, cuerpo, { headers: this.realApi.actorHeaders() })
      .pipe(
        tap((respuesta) => {
          if (opciones.customerId == null) {
            this.fijarModo(respuesta.mode);
          }
        })
      );
  }

  /** Cálculo local con la tabla real del plan (misma regla que el pedido). */
  ahorroComoSocio(gross: number, monthNet: number): Observable<AhorroSocio> {
    return this.plan$.pipe(map((plan) => calcularAhorroConTramos(plan.descuento.tramos, gross, monthNet)));
  }

  /** Cálculo en el servidor (público); con sesión propia considera el neto del mes. */
  cotizarAhorro(items: Array<{ price: number; quantity: number }>, customerId?: string | number): Observable<AhorroSocio> {
    const cuerpo: Record<string, unknown> = { items };
    if (customerId != null) {
      cuerpo['customerId'] = String(customerId);
    }
    return this.http.post<AhorroSocio>(`${this.baseUrl}/customers/ahorro-socio`, cuerpo, { headers: this.realApi.actorHeaders() });
  }
}
