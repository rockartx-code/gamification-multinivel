import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AvisoBloqueadasRespuesta,
  DeshacerPagoRespuesta,
  LotePagoPayload,
  LotePagoRespuesta,
  PagoPeriodos,
  PagosMes,
  PedirClabeRespuesta
} from '../models/pagos.model';
import { RealApiService } from './real-api.service';

/**
 * Paquete A · pagos-comisiones. Servicio propio del paquete (doc 23 §0.5):
 * habla con `/commissions/pagos/*` sin tocar api.service ni mock-api.
 */
@Injectable({ providedIn: 'root' })
export class PagosService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(
    private readonly http: HttpClient,
    private readonly realApi: RealApiService
  ) {}

  /** Beneficiarias del mes con monto confirmado, CLABE enmascarada y estado. */
  getPagosMes(monthKey: string): Observable<PagosMes> {
    return this.http.get<PagosMes>(`${this.baseUrl}/commissions/pagos?month=${encodeURIComponent(monthKey)}`, {
      headers: this.realApi.actorHeaders()
    });
  }

  /**
   * Paquete A · ronda 26 · propuesta 17: los meses contables con datos, el mes
   * por omisión y la hora del servidor. Renata recargaba y marzo de 2027
   * desaparecía del selector porque se armaba con el reloj del navegador.
   */
  getPeriodos(): Observable<PagoPeriodos> {
    return this.http.get<PagoPeriodos>(`${this.baseUrl}/commissions/periodos`, {
      headers: this.realApi.actorHeaders()
    });
  }

  /** Anexo de las que todavía no se pueden depositar, con su motivo (35). */
  descargarPendientesCsv(monthKey: string): Observable<string> {
    return this.http.get(`${this.baseUrl}/commissions/pagos/pendientes.csv?month=${encodeURIComponent(monthKey)}`, {
      headers: this.realApi.actorHeaders(),
      responseType: 'text'
    });
  }

  /** Archivo de dispersión bancaria (CSV con las comisiones listas para depositar). */
  descargarDispersionCsv(monthKey: string): Observable<string> {
    return this.http.get(`${this.baseUrl}/commissions/pagos/dispersion.csv?month=${encodeURIComponent(monthKey)}`, {
      headers: this.realApi.actorHeaders(),
      responseType: 'text'
    });
  }

  /** Un comprobante para N beneficiarias; el backend salta con código las que no cumplen. */
  registrarLote(payload: LotePagoPayload): Observable<LotePagoRespuesta> {
    return this.http.post<LotePagoRespuesta>(`${this.baseUrl}/commissions/pagos/lote`, payload, {
      headers: this.realApi.actorHeaders()
    });
  }

  /** Deshacer un pago registrado por error (ruta existente; por fila, nunca por lote). */
  deshacerPago(customerId: string, monthKey: string, reason: string): Observable<DeshacerPagoRespuesta> {
    return this.http.post<DeshacerPagoRespuesta>(
      `${this.baseUrl}/commissions/admin/receipt/revert`,
      { customerId, monthKey, reason },
      { headers: this.realApi.actorHeaders() }
    );
  }

  /** Reenvía a la socia el recordatorio de registrar su CLABE (correo + aviso en el panel). */
  pedirClabe(customerId: string, monthKey: string): Observable<PedirClabeRespuesta> {
    return this.http.post<PedirClabeRespuesta>(
      `${this.baseUrl}/commissions/pagos/pedir-clabe`,
      { customerId, monthKey },
      { headers: this.realApi.actorHeaders() }
    );
  }

  /** Tarea programable de avisos de bloqueadas (útil para probarla a mano). */
  avisarBloqueadas(opciones: { force?: boolean; dryRun?: boolean } = {}): Observable<AvisoBloqueadasRespuesta> {
    return this.http.post<AvisoBloqueadasRespuesta>(`${this.baseUrl}/commissions/avisos/bloqueadas`, opciones, {
      headers: this.realApi.actorHeaders()
    });
  }
}
