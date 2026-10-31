import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  DevolucionDetalle,
  DevolucionSolicitudPayload,
  DevolucionSolicitudResponse
} from '../models/devoluciones.model';
import { RealApiService } from './real-api.service';

/**
 * Paquete G · devoluciones. Servicio propio del paquete (docs/arquitectura/23 §0.5):
 * usa `HttpClient` directo con las cabeceras de sesión de `RealApiService.actorHeaders()`.
 */
@Injectable({ providedIn: 'root' })
export class DevolucionesService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(
    private readonly http: HttpClient,
    private readonly realApi: RealApiService
  ) {}

  /** Registra la solicitud: qué líneas, motivo, evidencia según el motivo y envío de regreso. */
  solicitar(orderId: string, payload: DevolucionSolicitudPayload): Observable<DevolucionSolicitudResponse> {
    return this.http.post<DevolucionSolicitudResponse>(
      `${this.baseUrl}/orders/${encodeURIComponent(orderId)}/return`,
      payload,
      { headers: this.realApi.actorHeaders() }
    );
  }

  /** Estado de la solicitud del pedido (pendiente / validada / rechazada / reembolsada). */
  detalle(orderId: string): Observable<DevolucionDetalle> {
    return this.http
      .get<{ request: DevolucionDetalle }>(
        `${this.baseUrl}/orders/${encodeURIComponent(orderId)}/devolucion`,
        { headers: this.realApi.actorHeaders() }
      )
      .pipe(map((res) => res.request));
  }
}
