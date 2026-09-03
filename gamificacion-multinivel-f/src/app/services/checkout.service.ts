import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  DatosFiscales,
  EnvioInfo,
  FacturaEmitida,
  FacturaEmitidaPayload,
  FacturaSolicitada,
  RespuestaOk,
  SesionAbierta,
  SucursalesRecoger,
  SugerenciaActivacion,
  SugerenciaActivacionItem
} from '../models/checkout.model';
import { RealApiService } from './real-api.service';

/**
 * Paquete C · checkout-y-sesion. Un servicio por paquete (docs/arquitectura/23 §0.5):
 * habla con `/orders/checkout/*`, `/orders/{id}/factura*`, `/auth/login` y `/auth/enlace-acceso*`.
 */
@Injectable({ providedIn: 'root' })
export class CheckoutService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(
    private readonly http: HttpClient,
    private readonly realApi: RealApiService
  ) {}

  /** Tarifa base, umbral de envío gratis y faltante, medidos como diga la configuración. */
  envioInfo(subtotal: number): Observable<EnvioInfo> {
    const params = new HttpParams().set('subtotal', String(Math.max(0, Math.round(subtotal * 100) / 100)));
    return this.http.get<EnvioInfo>(`${this.baseUrl}/orders/checkout/envio-info`, { params });
  }

  /** Producto más barato que cierra los VP de activación que faltan con el carrito actual. */
  sugerenciaActivacion(payload: {
    customerId: string | number;
    items: SugerenciaActivacionItem[];
    couponCode?: string;
  }): Observable<SugerenciaActivacion> {
    return this.http.post<SugerenciaActivacion>(`${this.baseUrl}/orders/checkout/sugerencia-activacion`, payload, {
      headers: this.realApi.actorHeaders()
    });
  }

  /** Sucursales donde se puede recoger en la ciudad/estado del cliente y con existencia del carrito. */
  sucursalesRecoger(payload: {
    city?: string;
    state?: string;
    postalCode?: string;
    items: Array<{ productId: string | number; quantity: number }>;
  }): Observable<SucursalesRecoger> {
    return this.http.post<SucursalesRecoger>(`${this.baseUrl}/orders/checkout/sucursales-recoger`, payload);
  }

  solicitarFactura(orderId: string, datos: DatosFiscales): Observable<FacturaSolicitada> {
    return this.http.post<FacturaSolicitada>(
      `${this.baseUrl}/orders/${encodeURIComponent(orderId)}/factura`,
      datos,
      { headers: this.realApi.actorHeaders() }
    );
  }

  marcarFacturaEmitida(orderId: string, payload: FacturaEmitidaPayload): Observable<FacturaEmitida> {
    return this.http.post<FacturaEmitida>(
      `${this.baseUrl}/orders/${encodeURIComponent(orderId)}/factura/emitida`,
      payload,
      { headers: this.realApi.actorHeaders() }
    );
  }

  /** Ciudad y estado de un almacén (formulario de Stocks). */
  actualizarUbicacionSucursal(stockId: string, ubicacion: { city: string; state: string }): Observable<{ stock: Record<string, unknown> }> {
    return this.http.patch<{ stock: Record<string, unknown> }>(
      `${this.baseUrl}/inventory/stocks/${encodeURIComponent(stockId)}`,
      ubicacion,
      { headers: this.realApi.actorHeaders() }
    );
  }

  // ── Sesión ──────────────────────────────────────────────────────────

  iniciarSesion(username: string, password: string, rememberMe: boolean): Observable<SesionAbierta> {
    return this.http.post<SesionAbierta>(`${this.baseUrl}/auth/login`, { username, password, rememberMe });
  }

  pedirEnlaceAcceso(email: string, rememberMe: boolean): Observable<RespuestaOk> {
    return this.http.post<RespuestaOk>(`${this.baseUrl}/auth/enlace-acceso`, { email, rememberMe });
  }

  canjearEnlaceAcceso(token: string, rememberMe: boolean): Observable<SesionAbierta> {
    return this.http.post<SesionAbierta>(`${this.baseUrl}/auth/enlace-acceso/canjear`, { token, rememberMe });
  }
}
