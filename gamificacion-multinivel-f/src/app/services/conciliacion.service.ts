import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { ConciliacionCorrida, ConciliacionPayload, ConciliacionResultado } from '../models/suscripcion.model';
import { RealApiService } from './real-api.service';

/**
 * Conciliación de pagos con MercadoPago (paquete H): revisa los pedidos
 * pendientes de pago de las últimas horas y acredita los que la pasarela
 * reporta aprobados. Privilegio `order_mark_paid`.
 */
@Injectable({ providedIn: 'root' })
export class ConciliacionService {
  private readonly baseUrl = `${environment.apiBaseUrl}/orders/conciliacion`;

  constructor(private readonly http: HttpClient, private readonly realApi: RealApiService) {}

  conciliar(payload: ConciliacionPayload = {}): Observable<ConciliacionResultado> {
    return this.http.post<ConciliacionResultado>(this.baseUrl, payload, { headers: this.realApi.actorHeaders() });
  }

  ultimaCorrida(): Observable<ConciliacionCorrida | null> {
    return this.http
      .get<{ run: ConciliacionCorrida | null }>(`${this.baseUrl}/ultima`, { headers: this.realApi.actorHeaders() })
      .pipe(map((r) => r.run ?? null));
  }
}
