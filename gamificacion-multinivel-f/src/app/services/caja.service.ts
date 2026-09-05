import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AbonoCajaRespuesta,
  AnulacionCajaRespuesta,
  AperturaTurnoPayload,
  AperturaTurnoRespuesta,
  ArqueoCaja,
  CerrarCortePayload,
  CorteCaja,
  RetiroCajaPayload,
  RetiroCajaRespuesta,
  VentaCajaPayload,
  VentaCajaRespuesta
} from '../models/caja.model';
import { RealApiService } from './real-api.service';

/**
 * Caja y arqueo (paquete E). Habla con `/inventory/pos/*` y devuelve lo que el
 * servidor guardó, para que cada confirmación muestre folio y montos reales.
 */
@Injectable({ providedIn: 'root' })
export class CajaService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient, private readonly realApi: RealApiService) {}

  obtenerArqueo(stockId: string): Observable<{ arqueo: ArqueoCaja }> {
    return this.http.get<{ arqueo: ArqueoCaja }>(
      `${this.baseUrl}/inventory/pos/arqueo?stockId=${encodeURIComponent(stockId)}`,
      { headers: this.realApi.actorHeaders() }
    );
  }

  /**
   * Abrir turno declarando el fondo con el que arranca la caja (propuesta 5).
   * Mireya llegó con $500 y la pantalla le dijo "Fondo inicial $0.00".
   */
  abrirTurno(payload: AperturaTurnoPayload): Observable<AperturaTurnoRespuesta> {
    return this.http.post<AperturaTurnoRespuesta>(
      `${this.baseUrl}/inventory/pos/turno/abrir`,
      payload,
      { headers: this.realApi.actorHeaders() }
    );
  }

  /** Valida el código de autorización antes de pedirle a la cajera que avance (propuesta 6). */
  validarCodigo(code: string): Observable<{ ok: boolean; configured: boolean }> {
    return this.http.post<{ ok: boolean; configured: boolean }>(
      `${this.baseUrl}/inventory/pos/validate-auth`,
      { code },
      { headers: this.realApi.actorHeaders() }
    );
  }

  cerrarCorte(payload: CerrarCortePayload): Observable<{ cut: CorteCaja; control: { currentTotal: number; salesCount: number } }> {
    return this.http.post<{ cut: CorteCaja; control: { currentTotal: number; salesCount: number } }>(
      `${this.baseUrl}/inventory/pos/cash-cut`,
      payload,
      { headers: this.realApi.actorHeaders() }
    );
  }

  obtenerCorte(cashCutId: string): Observable<{ cut: CorteCaja }> {
    return this.http.get<{ cut: CorteCaja }>(
      `${this.baseUrl}/inventory/pos/cash-cuts/${encodeURIComponent(cashCutId)}`,
      { headers: this.realApi.actorHeaders() }
    );
  }

  enviarCorte(cashCutId: string, email?: string): Observable<{ sent: boolean; to: string; sentAt: string }> {
    return this.http.post<{ sent: boolean; to: string; sentAt: string }>(
      `${this.baseUrl}/inventory/pos/cash-cuts/${encodeURIComponent(cashCutId)}/enviar`,
      email ? { email } : {},
      { headers: this.realApi.actorHeaders() }
    );
  }

  retirar(payload: RetiroCajaPayload): Observable<RetiroCajaRespuesta> {
    return this.http.post<RetiroCajaRespuesta>(
      `${this.baseUrl}/inventory/pos/withdrawal`,
      payload,
      { headers: this.realApi.actorHeaders() }
    );
  }

  registrarVenta(payload: VentaCajaPayload): Observable<VentaCajaRespuesta> {
    return this.http.post<VentaCajaRespuesta>(
      `${this.baseUrl}/inventory/pos/sales`,
      payload,
      { headers: this.realApi.actorHeaders() }
    );
  }

  abonar(saleId: string, payload: { amount: number; paymentMethod: 'cash' | 'card' | 'transfer' }): Observable<AbonoCajaRespuesta> {
    return this.http.post<AbonoCajaRespuesta>(
      `${this.baseUrl}/inventory/pos/sales/${encodeURIComponent(saleId)}/payments`,
      payload,
      { headers: this.realApi.actorHeaders() }
    );
  }

  anular(saleId: string, reason: string): Observable<AnulacionCajaRespuesta> {
    return this.http.post<AnulacionCajaRespuesta>(
      `${this.baseUrl}/inventory/pos/sales/${encodeURIComponent(saleId)}/void`,
      { reason },
      { headers: this.realApi.actorHeaders() }
    );
  }
}
