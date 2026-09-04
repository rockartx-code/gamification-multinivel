import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

/**
 * La pantalla que se quiso abrir y no está entre las de esta persona.
 *
 * §3.5: «se DICE en pantalla cuál se quiso abrir, en vez de quitarla en
 * silencio». El aviso viajaba solo en `?sinAcceso=` y solo lo leía
 * `AdminComponent` al arrancar: navegando dentro del panel el componente se
 * reutiliza y no se pintaba nada, y quien rebota a Despacho o a Seguimiento
 * —que son componentes aparte— no lo veía nunca. Aquí lo anota la guarda y lo
 * lee cualquier pantalla que monte `ui-aviso-sin-acceso`.
 */
@Injectable({ providedIn: 'root' })
export class AccesoPantallaService {
  private readonly sujeto = new BehaviorSubject<string>('');
  private saltosPorDelante = 0;

  /** Título de la última pantalla negada; cadena vacía cuando no hay aviso. */
  get pantallaSinAcceso$(): Observable<string> {
    return this.sujeto.asObservable();
  }

  /** La guarda rebotó: el aviso sobrevive al salto que ella misma provoca. */
  anotar(titulo: string): void {
    this.saltosPorDelante = 1;
    this.sujeto.next(String(titulo ?? '').trim());
  }

  /**
   * Navegación permitida. La primera es la del propio rebote (la que pinta el
   * aviso); a partir de la siguiente, el aviso se retira solo, para que no
   * acompañe a la persona por todo el panel.
   */
  navegacionPermitida(): void {
    if (this.saltosPorDelante > 0) {
      this.saltosPorDelante -= 1;
      return;
    }
    this.limpiar();
  }

  limpiar(): void {
    this.saltosPorDelante = 0;
    this.sujeto.next('');
  }
}
