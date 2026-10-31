import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { AyudaPublica, enlaceWhatsapp } from '../../models/ayuda.model';
import { AyudaService } from '../../services/ayuda.service';

/** Las cuatro rutas que rebotaban a la tienda; son la misma pantalla. */
export type SeccionAyuda = 'ayuda' | 'contacto' | 'sucursales' | 'facturacion';

/**
 * Paquete D · propuesta 8 — la puerta de salida de quien ya pagó.
 *
 * `#/ayuda`, `#/contacto`, `#/sucursales` y `#/facturacion` son la misma
 * pantalla con secciones ancladas; `#/devoluciones` es propia porque es la más
 * larga y la que más se enlaza desde los correos.
 *
 * "Comprarles me costó cinco minutos. Reclamarles no lo logré en veinte."
 * (Julio, docs/qa/25 §3.11). Aquí está el teléfono, el correo, el horario, las
 * sucursales con su dirección y qué hacer para pedir una factura, sin cuenta y
 * sin verificar ningún correo.
 *
 * También es el destino de la ruta comodín: una URL mal escrita cae aquí con
 * el aviso de que esa página no existe, en vez de dejar el contenedor vacío.
 */
@Component({
  selector: 'app-ayuda',
  standalone: true,
  imports: [CommonModule, RouterLink, UiButtonComponent, UiHeaderComponent, UiFooterComponent],
  templateUrl: './ayuda.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AyudaComponent implements OnInit {
  ayuda: AyudaPublica = AyudaService.vacia;
  cargando = true;

  /** Sección a la que se entra: la ruta la fija con `data.seccion`. */
  seccion: SeccionAyuda = 'ayuda';
  /** Cierto cuando se llegó por una URL que no existe (ruta comodín). */
  rutaDesconocida = false;

  constructor(
    private readonly ayudaService: AyudaService,
    private readonly route: ActivatedRoute,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const datos = this.route.snapshot.data as { seccion?: SeccionAyuda; noEncontrada?: boolean };
    this.seccion = datos.seccion ?? 'ayuda';
    this.rutaDesconocida = Boolean(datos.noEncontrada);

    this.ayudaService.ayuda().subscribe((ayuda) => {
      this.ayuda = ayuda;
      this.cargando = false;
      this.cdr.markForCheck();
    });
  }

  get whatsappUrl(): string {
    return enlaceWhatsapp(this.ayuda.contacto.whatsapp, 'Hola, necesito ayuda con mi pedido.');
  }

  get correoUrl(): string {
    return this.ayuda.contacto.email ? `mailto:${this.ayuda.contacto.email}` : '';
  }

  get tituloDeLaSeccion(): string {
    switch (this.seccion) {
      case 'contacto':
        return 'Contáctanos';
      case 'sucursales':
        return 'Nuestras sucursales';
      case 'facturacion':
        return 'Facturación';
      default:
        return 'Centro de ayuda';
    }
  }
}
