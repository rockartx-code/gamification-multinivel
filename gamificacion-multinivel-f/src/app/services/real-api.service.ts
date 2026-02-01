import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AdminCustomer,
  AdminData,
  AdminOrder,
  AdminProduct,
  AssetResponse,
  CreateAssetPayload,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  CustomerProfile,
  UpdateOrderStatusPayload,
  ProductAssetUpload,
  ProductOfMonthResponse,
  SaveAdminProductPayload
} from '../models/admin.model';
import { CreateAccountPayload, CreateAccountResponse } from '../models/auth.model';
import { CartData } from '../models/cart.model';
import { CommissionReceiptPayload, CommissionRequestPayload, UserDashboardData } from '../models/user-dashboard.model';
import type { AuthUser } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class RealApiService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient) {}

  login(username: string, password: string): Observable<AuthUser> {
    return this.http
      .post<{ user?: AuthUser; message?: string; Error?: string }>(`${this.baseUrl}/login`, {
        username,
        password
      })
      .pipe(
        map((response) => {
          if (response.user) {
            return response.user;
          }
          throw new Error(response.message ?? 'No se pudo iniciar sesion.');
        })
      );
  }

  createAccount(payload: CreateAccountPayload): Observable<CreateAccountResponse> {
    return this.http
      .post<{ customer?: CreateAccountResponse['customer']; message?: string; Error?: string }>(
        `${this.baseUrl}/crearcuenta`,
        payload
      )
      .pipe(
        map((response) => {
          if (response.customer) {
            return { customer: response.customer };
          }
          throw new Error(response.message ?? 'No se pudo crear la cuenta.');
        })
      );
  }

  getAdminData(): Observable<AdminData> {
    return this.http.get<AdminData>(`${this.baseUrl}/admin/dashboard`);
  }

  getCartData(): Observable<CartData> {
    return this.http.get<CartData>(`${this.baseUrl}/cart`);
  }

  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    const query = userId ? `?userId=${encodeURIComponent(userId)}` : '';
    return this.http.get<UserDashboardData>(`${this.baseUrl}/user-dashboard${query}`);
  }

  requestCommissionPayout(payload: CommissionRequestPayload): Observable<{ request: unknown; summary?: unknown }> {
    return this.http.post<{ request: unknown; summary?: unknown }>(`${this.baseUrl}/commissions/request`, payload);
  }

  uploadCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.http.post<{ receipt: unknown; asset?: unknown }>(`${this.baseUrl}/commissions/receipt`, payload);
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    return this.http
      .post<{ order: AdminOrder }>(`${this.baseUrl}/orders`, payload)
      .pipe(map((response) => response.order));
  }

  getOrder(orderId: string): Observable<AdminOrder> {
    return this.http
      .get<{ order: AdminOrder }>(`${this.baseUrl}/orders/${orderId}`)
      .pipe(map((response) => response.order));
  }

  getOrders(customerId: string): Observable<AdminOrder[]> {
    return this.http
      .get<{ orders: AdminOrder[] }>(`${this.baseUrl}/orders?customerId=${encodeURIComponent(customerId)}`)
      .pipe(map((response) => response.orders));
  }

  getCustomer(customerId: string): Observable<CustomerProfile> {
    return this.http
      .get<{ customer: Record<string, unknown> }>(`${this.baseUrl}/customers/${encodeURIComponent(customerId)}`)
      .pipe(
        map((response) => {
          const customer = response.customer ?? {};
          return {
            id: Number(customer['customerId'] ?? customer['id'] ?? 0),
            name: String(customer['name'] ?? ''),
            email: String(customer['email'] ?? ''),
            phone: customer['phone'] ? String(customer['phone']) : undefined,
            address: customer['address'] ? String(customer['address']) : undefined,
            city: customer['city'] ? String(customer['city']) : undefined,
            state: customer['state'] ? String(customer['state']) : undefined,
            postalCode: customer['postalCode'] ? String(customer['postalCode']) : undefined
          };
        })
      );
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.http
      .post<{ customer: AdminCustomer }>(`${this.baseUrl}/customers`, payload)
      .pipe(map((response) => response.customer));
  }

  createAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    return this.http.post<AssetResponse>(`${this.baseUrl}/assets`, payload);
  }

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    return this.http.post<ProductAssetUpload>(`${this.baseUrl}/products/assets`, payload);
  }

  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse> {
    return this.http.post<ProductOfMonthResponse>(`${this.baseUrl}/products/product-of-month`, { productId });
  }

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    return this.http
      .post<{ product: AdminProduct }>(`${this.baseUrl}/products`, payload)
      .pipe(map((response) => response.product));
  }

  updateOrderStatus(orderId: string, payload: UpdateOrderStatusPayload): Observable<AdminOrder> {
    return this.http
      .patch<{ order: AdminOrder }>(`${this.baseUrl}/orders/${orderId}`, payload)
      .pipe(map((response) => response.order));
  }
}
