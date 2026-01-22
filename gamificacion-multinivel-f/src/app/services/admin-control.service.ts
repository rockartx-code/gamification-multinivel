import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import {
  AdminCustomer,
  AdminData,
  AdminOrder,
  AdminProduct,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  ProductAssetUpload,
  SaveAdminProductPayload
} from '../models/admin.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class AdminControlService {
  private readonly dataSubject = new BehaviorSubject<AdminData | null>(null);
  readonly data$ = this.dataSubject.asObservable();

  constructor(private readonly api: ApiService) {}

  load(): Observable<AdminData> {
    return this.api.getAdminData().pipe(
      tap((data) => {
        const normalized: AdminData = {
          ...data,
          orders: data.orders ?? [],
          customers: data.customers ?? [],
          products: data.products ?? [],
          warnings: data.warnings ?? [],
          assetSlots: data.assetSlots ?? []
        };
        this.dataSubject.next(structuredClone(normalized));
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
    return this.data?.products?.length ?? 0;
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

  updateOrderStatus(orderId: string, status: AdminOrder['status']): Observable<AdminOrder> {
    return this.api.updateOrderStatus(orderId, status).pipe(
      tap((order) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const nextStatus = order.status ?? status;
        const updatedOrders = current.orders.map((entry) =>
          entry.id === orderId ? { ...entry, status: nextStatus } : entry
        );
        this.dataSubject.next({ ...current, orders: updatedOrders });
      })
    );
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

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    return this.api.saveProduct(payload).pipe(
      tap((product) => {
        const current = this.dataSubject.value;
        if (!current) {
          return;
        }
        const existingIndex = current.products.findIndex((entry) => entry.id === payload.id);
        const updatedProducts =
          existingIndex >= 0
            ? current.products.map((entry, index) => (index === existingIndex ? product : entry))
            : [product, ...current.products];
        this.dataSubject.next({ ...current, products: updatedProducts });
      })
    );
  }

  selectCustomer(customerId: number): AdminCustomer | null {
    return this.customers.find((customer) => customer.id === customerId) ?? null;
  }
}
