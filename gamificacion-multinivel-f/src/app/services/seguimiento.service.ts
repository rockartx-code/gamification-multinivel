import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  ContactoPayload,
  ContactoRespuesta,
  FichaInvitadoRespuesta,
  FichaSeguimientoPayload,
  SeguimientoAlcance,
  SeguimientoHoyRespuesta,
  SeguimientoPlantillasRespuesta,
  SeguimientoSituacion
} from '../models/seguimiento.model';
import { RealApiService } from './real-api.service';

/** Paquete F · coach-seguimiento: rutas `/customers/seguimiento/*` y `/customers/{id}/contacto`. */
@Injectable({
  providedIn: 'root'
})
export class SeguimientoService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient, private readonly api: RealApiService) {}

  hoy(params: { scope?: SeguimientoAlcance; situation?: SeguimientoSituacion | ''; limit?: number } = {}): Observable<SeguimientoHoyRespuesta> {
    const q = new URLSearchParams();
    q.set('scope', params.scope ?? 'mine');
    if (params.situation) q.set('situation', params.situation);
    if (params.limit) q.set('limit', String(params.limit));
    return this.http.get<SeguimientoHoyRespuesta>(`${this.baseUrl}/customers/seguimiento/hoy?${q.toString()}`, {
      headers: this.api.actorHeaders()
    });
  }

  plantillas(): Observable<SeguimientoPlantillasRespuesta> {
    return this.http.get<SeguimientoPlantillasRespuesta>(`${this.baseUrl}/customers/seguimiento/plantillas`, {
      headers: this.api.actorHeaders()
    });
  }

  /** `customerId` vacío o `invitado` anota el contacto de un comprador sin ficha (requiere `guestEmail`). */
  contacto(customerId: string, payload: ContactoPayload): Observable<ContactoRespuesta> {
    const id = customerId && customerId.trim() ? customerId.trim() : 'invitado';
    return this.http.post<ContactoRespuesta>(`${this.baseUrl}/customers/${encodeURIComponent(id)}/contacto`, payload, {
      headers: this.api.actorHeaders()
    });
  }

  crearFichaInvitado(email: string): Observable<FichaInvitadoRespuesta> {
    return this.http.post<FichaInvitadoRespuesta>(`${this.baseUrl}/customers/seguimiento/ficha-invitado`, { email }, {
      headers: this.api.actorHeaders()
    });
  }

  actualizarFicha(customerId: string, payload: FichaSeguimientoPayload): Observable<{ customer: Record<string, unknown> }> {
    return this.http.patch<{ customer: Record<string, unknown> }>(`${this.baseUrl}/customers/${encodeURIComponent(customerId)}`, payload, {
      headers: this.api.actorHeaders()
    });
  }
}
