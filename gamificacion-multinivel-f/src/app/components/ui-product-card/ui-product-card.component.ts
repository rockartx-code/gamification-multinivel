import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { UiButtonComponent } from '../ui-button/ui-button.component';
import { UiFormFieldComponent } from '../ui-form-field/ui-form-field.component';

export type ProductVariantCard = {
  id: string;
  name: string;
  price?: number;
  active?: boolean;
};

export type ProductCardModel = {
  id: string;
  name: string;
  badge?: string;
  description?: string;
  img: string;
  price: number;
  variants?: ProductVariantCard[];
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
  @Input() selectedVariantId = '';

  @Output() qtyChange = new EventEmitter<number>();
  @Output() viewDetails = new EventEmitter<void>();
  @Output() add = new EventEmitter<void>();
  @Output() variantSelected = new EventEmitter<string>();

  get hasDiscount(): boolean {
    return !!this.originalPriceLabel && this.originalPriceLabel !== this.discountedPriceLabel;
  }

  get activeVariants(): ProductVariantCard[] {
    return (this.product.variants ?? []).filter((v) => v.active !== false);
  }

  selectVariant(variantId: string): void {
    this.variantSelected.emit(variantId);
  }
}
