import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  BodegaResumen,
  CierreResponse,
  DespachoEnviarPayload,
  DespachoEnviarResponse,
  DespachoPendientesResponse,
  EnvioResumenTurno,
  PreferenciasDespacho,
  RastreoResponse,
  ResumenTurno,
  SurtidoResponse
} from '../models/despacho.model';
import { RealApiService } from './real-api.service';

/**
 * Paquete D · almacén, despacho y paquetería.
 * Servicio propio (docs/arquitectura/23 §0.5): HttpClient + `environment.apiBaseUrl`
 * con las cabeceras de actor de `RealApiService`.
 */
@Injectable({ providedIn: 'root' })
export class DespachoService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient, private readonly realApi: RealApiService) {}

  private get headers() {
    return this.realApi.actorHeaders();
  }

  /** Almacenes disponibles (nombre y ubicación) para el selector de bodega. */
  bodegas(): Observable<BodegaResumen[]> {
    return this.http
      .get<{ stocks: Array<{ stockId?: string; id?: string; name?: string; location?: string }> }>(`${this.baseUrl}/inventory/stocks`, { headers: this.headers })
      .pipe(
        map((res) =>
          (res.stocks ?? []).map((stock) => ({
            id: String(stock.stockId ?? stock.id ?? ''),
            name: String(stock.name ?? stock.stockId ?? ''),
            location: stock.location ? String(stock.location) : undefined
          }))
        )
      );
  }

  pendientes(stockId?: string): Observable<DespachoPendientesResponse> {
    const params = stockId ? new HttpParams().set('stockId', stockId) : undefined;
    return this.http.get<DespachoPendientesResponse>(`${this.baseUrl}/inventory/despacho/pendientes`, { headers: this.headers, params });
  }

  surtido(stockId: string, orderIds: string[]): Observable<SurtidoResponse> {
    return this.http.post<SurtidoResponse>(`${this.baseUrl}/inventory/despacho/surtido`, { stockId, orderIds }, { headers: this.headers });
  }

  enviar(payload: DespachoEnviarPayload): Observable<DespachoEnviarResponse> {
    return this.http.post<DespachoEnviarResponse>(`${this.baseUrl}/inventory/despacho/enviar`, payload, { headers: this.headers });
  }

  preferencias(): Observable<PreferenciasDespacho> {
    return this.http.get<PreferenciasDespacho>(`${this.baseUrl}/inventory/despacho/preferencias`, { headers: this.headers });
  }

  guardarPreferencias(defaultStockId: string): Observable<PreferenciasDespacho> {
    return this.http.put<PreferenciasDespacho>(`${this.baseUrl}/inventory/despacho/preferencias`, { defaultStockId }, { headers: this.headers });
  }

  rastrear(body: { orderIds?: string[]; dryRun?: boolean } = {}): Observable<RastreoResponse> {
    return this.http.post<RastreoResponse>(`${this.baseUrl}/inventory/envios/rastrear`, body, { headers: this.headers });
  }

  cerrar(body: { dryRun?: boolean } = {}): Observable<CierreResponse> {
    return this.http.post<CierreResponse>(`${this.baseUrl}/inventory/envios/cerrar`, body, { headers: this.headers });
  }

  resumenTurno(userId?: string, date?: string): Observable<ResumenTurno> {
    let params = new HttpParams();
    if (userId) {
      params = params.set('userId', userId);
    }
    if (date) {
      params = params.set('date', date);
    }
    return this.http.get<ResumenTurno>(`${this.baseUrl}/inventory/turno/resumen`, { headers: this.headers, params });
  }

  /**
   * Paquete F · ronda 26 (propuesta 28): mínimo de piezas por producto. Toño no
   * tenía forma de saber que Guadalajara se quedó en una pieza hasta que un
   * cliente pagara y no hubiera.
   */
  minimosDeStock(): Observable<{ minStockDefault: number; minimos: Record<string, number> }> {
    return this.http.get<{ minStockDefault: number; minimos: Record<string, number> }>(
      `${this.baseUrl}/inventory/stocks/minimos`, { headers: this.headers });
  }

  guardarMinimosDeStock(minimos: Record<string, number>): Observable<{ ok: boolean; minimos: Record<string, number> }> {
    return this.http.put<{ ok: boolean; minimos: Record<string, number> }>(
      `${this.baseUrl}/inventory/stocks/minimos`, { minimos }, { headers: this.headers });
  }

  /**
   * Paquete F · ronda 26 (propuesta 30): entregar el turno por correo, como ya
   * se entrega el corte de caja. Toño se lo mandaba a Renata por WhatsApp.
   */
  enviarResumenTurno(body: { userId?: string; date?: string; email?: string; reenviar?: boolean }): Observable<EnvioResumenTurno> {
    return this.http.post<EnvioResumenTurno>(`${this.baseUrl}/inventory/turno/resumen/enviar`, body, { headers: this.headers });
  }
}
