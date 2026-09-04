import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';

import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { AyudaPublica, enlaceWhatsapp } from '../../models/ayuda.model';
import { AyudaService } from '../../services/ayuda.service';

/**
 * Paquete D · propuesta 39 — la política de devolución, publicada.
 *
 * La decisión del dueño: paga el envío de regreso quien devuelve, salvo
 * producto dañado o error nuestro, donde lo pagamos nosotros. Julio preguntó
 * las cuatro cosas por WhatsApp —plazo, evidencia, quién paga y a dónde se
 * manda— porque no estaban escritas en ninguna pantalla, y esta página existe
 * para que se sepan **antes** de comprar.
 *
 * Ni un texto se escribe en esta pantalla: los seis puntos llegan armados de
 * `GET /catalog/ayuda`, la misma fuente que lee el asistente de devolución y
 * los dos correos. Si el negocio cambia el plazo en la configuración, cambia
 * aquí en la misma frase.
 */
@Component({
  selector: 'app-devoluciones',
  standalone: true,
  imports: [CommonModule, RouterLink, UiButtonComponent, UiHeaderComponent, UiFooterComponent],
  templateUrl: './devoluciones.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DevolucionesComponent implements OnInit {
  ayuda: AyudaPublica = AyudaService.vacia;
  cargando = true;

  constructor(
    private readonly ayudaService: AyudaService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.ayudaService.ayuda().subscribe((ayuda) => {
      this.ayuda = ayuda;
      this.cargando = false;
      this.cdr.markForCheck();
    });
  }

  get whatsappUrl(): string {
    return enlaceWhatsapp(this.ayuda.contacto.whatsapp, 'Hola, quiero devolver algo de mi pedido.');
  }

  get correoUrl(): string {
    return this.ayuda.contacto.email ? `mailto:${this.ayuda.contacto.email}` : '';
  }

  /** Icono de cada paso, para que los seis se distingan de un vistazo. */
  icono(clave: string): string {
    switch (clave) {
      case 'que':
        return 'fa-solid fa-box-open';
      case 'plazo':
        return 'fa-regular fa-clock';
      case 'evidencia':
        return 'fa-solid fa-camera';
      case 'envio':
        return 'fa-solid fa-truck';
      case 'direccion':
        return 'fa-solid fa-location-dot';
      case 'reembolso':
        return 'fa-solid fa-money-bill-transfer';
      default:
        return 'fa-solid fa-circle-info';
    }
  }
}
