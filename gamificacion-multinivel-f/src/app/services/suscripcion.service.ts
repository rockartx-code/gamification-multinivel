import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  Suscripcion,
  SuscripcionCambios,
  SuscripcionPayload,
  SuscripcionRespuesta
} from '../models/suscripcion.model';
import { RealApiService } from './real-api.service';

/**
 * Suscripción mensual del socio (paquete H). Habla directo con
 * `/orders/suscripciones`; las cabeceras de sesión vienen de RealApiService.
 */
@Injectable({ providedIn: 'root' })
export class SuscripcionService {
  private readonly baseUrl = `${environment.apiBaseUrl}/orders/suscripciones`;

  constructor(private readonly http: HttpClient, private readonly realApi: RealApiService) {}

  listar(customerId?: string | number): Observable<Suscripcion[]> {
    const qs = customerId != null && String(customerId).trim() ? `?customerId=${encodeURIComponent(String(customerId))}` : '';
    return this.http
      .get<{ subscriptions: Suscripcion[] }>(`${this.baseUrl}${qs}`, { headers: this.realApi.actorHeaders() })
      .pipe(map((r) => r.subscriptions ?? []));
  }

  crear(payload: SuscripcionPayload): Observable<Suscripcion> {
    return this.http
      .post<SuscripcionRespuesta>(this.baseUrl, payload, { headers: this.realApi.actorHeaders() })
      .pipe(map((r) => r.subscription));
  }

  editar(subscriptionId: string, cambios: SuscripcionCambios): Observable<Suscripcion> {
    return this.http
      .patch<SuscripcionRespuesta>(`${this.baseUrl}/${encodeURIComponent(subscriptionId)}`, cambios, { headers: this.realApi.actorHeaders() })
      .pipe(map((r) => r.subscription));
  }

  pausar(subscriptionId: string, pausedUntil?: string): Observable<Suscripcion> {
    return this.editar(subscriptionId, pausedUntil ? { status: 'paused', pausedUntil } : { status: 'paused' });
  }

  reanudar(subscriptionId: string): Observable<Suscripcion> {
    return this.editar(subscriptionId, { status: 'active' });
  }

  cancelar(subscriptionId: string, reason?: string): Observable<Suscripcion> {
    return this.http
      .delete<SuscripcionRespuesta>(`${this.baseUrl}/${encodeURIComponent(subscriptionId)}`, {
        headers: this.realApi.actorHeaders(),
        body: reason ? { reason } : {}
      })
      .pipe(map((r) => r.subscription));
  }
}
