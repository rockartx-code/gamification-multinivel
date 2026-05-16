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

  @Input() variantQtys: Record<string, number> = {};
  @Output() variantQtyChange = new EventEmitter<{ variantId: string; qty: number }>();
  @Output() qtyChange = new EventEmitter<number>();
  @Output() viewDetails = new EventEmitter<void>();
  @Output() add = new EventEmitter<void>();

  private readonly checkedVariantIds = new Set<string>();
  private defaultApplied = false;

  get hasDiscount(): boolean {
    return !!this.originalPriceLabel && this.originalPriceLabel !== this.discountedPriceLabel;
  }

  get activeVariants(): ProductVariantCard[] {
    return (this.product.variants ?? []).filter((v) => v.active !== false);
  }

  private applyDefault(): void {
    if (this.defaultApplied) {
      return;
    }
    this.defaultApplied = true;
    const first = this.activeVariants[0];
    if (first) {
      this.checkedVariantIds.add(first.id);
    }
  }

  isVariantChecked(variantId: string): boolean {
    this.applyDefault();
    return this.checkedVariantIds.has(variantId) || (this.variantQtys[variantId] ?? 0) > 0;
  }

  toggleVariant(variantId: string): void {
    this.applyDefault();
    if (this.checkedVariantIds.has(variantId)) {
      this.checkedVariantIds.delete(variantId);
      if ((this.variantQtys[variantId] ?? 0) > 0) {
        this.variantQtyChange.emit({ variantId, qty: 0 });
      }
    } else {
      this.checkedVariantIds.add(variantId);
    }
  }

  getVariantQty(variantId: string): number {
    return this.variantQtys[variantId] ?? 0;
  }

  changeVariantQty(variantId: string, delta: number): void {
    const current = this.getVariantQty(variantId);
    const next = Math.max(0, current + delta);
    this.variantQtyChange.emit({ variantId, qty: next });
  }
}
