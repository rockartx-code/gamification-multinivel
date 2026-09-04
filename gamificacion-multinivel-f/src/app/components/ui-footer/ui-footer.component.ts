import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';

import { ContactoPublico, enlaceWhatsapp } from '../../models/ayuda.model';
import { AyudaService } from '../../services/ayuda.service';

/**
 * Paquete D · propuesta 8 — el pie de página que Julio no encontró.
 *
 * "El pie de página dice, completo: «© 2026 finding U». Ni un enlace. Ni ayuda,
 * ni contacto, ni devoluciones, ni un teléfono." Para hallar el teléfono de la
 * tienda a la que ya le había pagado $1,209 tuvo que crear una cuenta y
 * verificar su correo.
 *
 * Ahora lleva correo, WhatsApp, horario y los enlaces de ayuda, contacto,
 * devoluciones, sucursales y facturación; el año se calcula (estaba quemado en
 * 2026) y los datos salen de `GET /catalog/ayuda`, sin sesión.
 */
@Component({
  selector: 'ui-footer',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './ui-footer.component.html'
})
export class UiFooterComponent implements OnInit {
  @Input() logoMode: 'default' | 'compact' = 'default';
  @Input() containerClass = 'mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-6 py-10 md:flex-row md:items-start';

  contacto: ContactoPublico = { email: '', whatsapp: '', horario: '', direccion: '' };
  readonly anio = new Date().getFullYear();

  constructor(private readonly ayudaService: AyudaService) {}

  ngOnInit(): void {
    this.ayudaService.ayuda().subscribe((ayuda) => {
      this.contacto = ayuda.contacto;
    });
  }

  get logoClass(): string {
    return this.logoMode === 'compact' ? 'h-10 w-auto sm:h-12 md:h-14' : 'h-15 w-40';
  }

  get whatsappUrl(): string {
    return enlaceWhatsapp(this.contacto.whatsapp, 'Hola, tengo una duda sobre mi pedido.');
  }

  get correoUrl(): string {
    return this.contacto.email ? `mailto:${this.contacto.email}` : '';
  }
}
