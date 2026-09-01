import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { FeatureBadgeComponent } from '../../components/feature-badge/feature-badge.component';
import { UiBadgeComponent } from '../../components/ui-badge/ui-badge.component';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiGoalProgressComponent } from '../../components/ui-goal-progress/ui-goal-progress.component';
import { UiKpiCardComponent } from '../../components/ui-kpi-card/ui-kpi-card.component';
import { UiModalComponent } from '../../components/ui-modal/ui-modal.component';
import { UiOrderTimelineComponent } from '../../components/ui-order-timeline/ui-order-timeline.component';
import { UiProductCardComponent, ProductCardModel } from '../../components/ui-product-card/ui-product-card.component';
import { UiSidebarNavComponent } from '../../components/ui-sidebar-nav/ui-sidebar-nav.component';
import { UiStatusBadgeComponent } from '../../components/ui-status-badge/ui-status-badge.component';

/**
 * Galería interna de componentes (styleguide vivo).
 * Renderiza cada componente en todos sus estados para validación visual
 * y de regresión. No está enlazada desde la navegación: /#/galeria.
 */
@Component({
  selector: 'app-galeria',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    FeatureBadgeComponent,
    UiBadgeComponent,
    UiButtonComponent,
    UiFormFieldComponent,
    UiGoalProgressComponent,
    UiKpiCardComponent,
    UiModalComponent,
    UiOrderTimelineComponent,
    UiProductCardComponent,
    UiSidebarNavComponent,
    UiStatusBadgeComponent
  ],
  templateUrl: './galeria.component.html'
})
export class GaleriaComponent {
  demoModalOpen = false;
  demoText = '';
  demoPassword = '';
  demoVariantQtys: Record<string, number> = { v2: 2 };

  readonly orderStatuses = [
    'pending', 'paid', 'shipped', 'delivered', 'cancelled',
    'refunded', 'en_devolucion', 'devuelto_validado', 'devolucion_rechazada'
  ];

  readonly networkStatuses = ['Activa', 'En progreso', 'Inactiva'];

  readonly productoSinVariantes: ProductCardModel = {
    id: 'demo-1',
    name: 'CREATINA',
    badge: 'Fuerza',
    description: 'Potencia rendimiento y fuerza en entrenamientos diarios.',
    img: 'images/Colageno-Clean.png',
    price: 27,
    vpPoints: 12
  };

  readonly productoConVariantes: ProductCardModel = {
    id: 'demo-2',
    name: 'COLÁGENO',
    badge: 'Regeneración',
    description: 'Soporte articular, elasticidad y recuperación.',
    img: 'images/Colageno-Clean.png',
    price: 35,
    vpPoints: 15,
    variants: [
      { id: 'v1', name: 'Natural', active: true },
      { id: 'v2', name: 'Sabor Coco', price: 38, active: true },
      { id: 'v3', name: 'Sabor Vainilla', price: 38, active: true }
    ]
  };

  readonly navDemo = [
    { id: 'h1', icon: '', label: 'Grupo de proceso', heading: true },
    { id: 'a', icon: 'fa-receipt', label: 'Elemento activo' },
    { id: 'b', icon: 'fa-users', label: 'Elemento normal' }
  ];

  onVariantQty(event: { variantId: string; qty: number }): void {
    this.demoVariantQtys = { ...this.demoVariantQtys, [event.variantId]: event.qty };
  }
}
