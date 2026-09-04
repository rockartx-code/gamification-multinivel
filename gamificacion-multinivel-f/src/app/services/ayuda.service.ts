import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, catchError, of, shareReplay } from 'rxjs';

import { environment } from '../../environments/environment';
import { AyudaPublica } from '../models/ayuda.model';

/**
 * Paquete D · ronda 26 — contacto, sucursales y política de devolución.
 *
 * Una sola llamada (`GET /catalog/ayuda`, pública) que alimenta el pie de
 * página de todas las pantallas, `#/ayuda` y `#/devoluciones`. Se cachea con
 * `shareReplay(1)`: el pie está en trece pantallas y no puede costar trece
 * peticiones.
 *
 * Si la petición falla, `ayuda$` devuelve un respaldo vacío en vez de romper:
 * un pie de página sin teléfono es malo, pero una pantalla en blanco por el
 * pie de página es peor.
 */
@Injectable({ providedIn: 'root' })
export class AyudaService {
  private readonly baseUrl = environment.apiBaseUrl;
  private peticion?: Observable<AyudaPublica>;

  constructor(private readonly http: HttpClient) {}

  static readonly vacia: AyudaPublica = {
    contacto: { email: '', whatsapp: '', horario: '', direccion: '' },
    sucursales: [],
    devoluciones: {
      motivos: [],
      pasos: [],
      direccionDevolucion: '',
      inspeccionDiasHabiles: '',
      refundMethod: '',
      refundBusinessDays: ''
    }
  };

  ayuda(): Observable<AyudaPublica> {
    if (!this.peticion) {
      this.peticion = this.http.get<AyudaPublica>(`${this.baseUrl}/catalog/ayuda`).pipe(
        catchError(() => of(AyudaService.vacia)),
        shareReplay(1)
      );
    }
    return this.peticion;
  }
}
