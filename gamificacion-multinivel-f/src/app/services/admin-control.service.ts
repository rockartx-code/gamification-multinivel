import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, tap } from 'rxjs';

import {
  AdminCustomer,
  AdminData,
  AdminOrder,
  AdminProduct,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  ProductAssetUpload
} from '../models/admin.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class AdminControlService {
  private readonly dataSubject = new BehaviorSubject<AdminData | null>(null);

  constructor(private readonly api: ApiService) {}

  load(): Observable<AdminData> {
    return this.api.getAdminData().pipe(
      tap((data) => {
        this.dataSubject.next(structuredClone(data));
      })
    );
  }

  get data(): AdminData | null {
    return this.dataSubject.value;
  }

  get orders(): AdminOrder[] {
    return this.data?.orders ?? [];
  }

  get customers(): AdminCustomer[] {
    return this.data?.customers ?? [];
  }

  get productsCount(): number {
    return this.data?.products.length ?? 0;
  }

  get customersCount(): number {
    return this.customers.length;
  }

  get pendingCount(): number {
    return this.orders.filter((order) => order.status === 'pending').length;
  }

  get paidCount(): number {
    return this.orders.filter((order) => order.status === 'paid').length;
  }

  get shipCount(): number {
    return this.orders.filter((order) => order.status === 'paid').length;
  }

  get commissionsTotal(): number {
    return this.customers.reduce((acc, customer) => acc + customer.commissions, 0);
  }

  formatMoney(value: number): string {
    return `$${value.toFixed(0)}`;
  }

  getFilteredOrders(status: AdminOrder['status']): AdminOrder[] {
    return this.orders.filter((order) => order.status === status);
  }

  advanceOrder(orderId: string): void {
    const current = this.dataSubject.value;
    if (!current) {
      return;
    }
    const updatedOrders = current.orders.map((order): AdminOrder => {
      if (order.id !== orderId) {
        return order;
      }
      const nextStatus: AdminOrder['status'] =
        order.status === 'pending' ? 'paid' : order.status === 'paid' ? 'delivered' : order.status;
      return { ...order, status: nextStatus };
    });
    this.dataSubject.next({ ...current, orders: updatedOrders });
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    return this.api.createOrder(payload).pipe(
      tap((order) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        this.dataSubject.next({ ...current, orders: [order, ...current.orders] });
      })
    );
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.api.createStructureCustomer(payload).pipe(
      tap((customer) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        this.dataSubject.next({ ...current, customers: [customer, ...current.customers] });
      })
    );
  }

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    return this.api.createProductAsset(payload);
  }

  saveProduct(payload: { id: number | null; name: string; price: number; active: boolean }): Observable<AdminProduct> {
    const current = this.dataSubject.value;
    const nextId =
      current?.products.reduce((max, product) => Math.max(max, product.id), 0) ?? 0;
    const product: AdminProduct = {
      id: payload.id ?? nextId + 1,
      name: payload.name,
      price: payload.price,
      active: payload.active
    };
    if (current) {
      const existingIndex = current.products.findIndex((entry) => entry.id === payload.id);
      const updatedProducts =
        existingIndex >= 0
          ? current.products.map((entry, index) => (index === existingIndex ? product : entry))
          : [product, ...current.products];
      this.dataSubject.next({ ...current, products: updatedProducts });
    }
    return of(product);
  }

  selectCustomer(customerId: number): AdminCustomer | null {
    return this.customers.find((customer) => customer.id === customerId) ?? null;
  }
}
