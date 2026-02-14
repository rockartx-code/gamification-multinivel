import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { UiButtonComponent } from '../ui-button/ui-button.component';
import { UiFormFieldComponent } from '../ui-form-field/ui-form-field.component';

export type ProductCardModel = {
  id: string;
  name: string;
  badge?: string;
  img: string;
  price: number;
};

@Component({
  selector: 'ui-product-card',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiFormFieldComponent],
  templateUrl: './ui-product-card.component.html'
})
export class UiProductCardComponent {
  @Input({ required: true }) product!: ProductCardModel;
  @Input() discountedPriceLabel = '';
  @Input() originalPriceLabel = '';
  @Input() discountLabel = '';
  @Input() qty = 0;
  @Input() mode: 'detailed' | 'compact' = 'detailed';

  @Output() qtyChange = new EventEmitter<number>();
  @Output() viewDetails = new EventEmitter<void>();
  @Output() add = new EventEmitter<void>();

  get hasDiscount(): boolean {
    return !!this.originalPriceLabel && this.originalPriceLabel !== this.discountedPriceLabel;
  }
}
