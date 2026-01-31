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
  ProductAssetUpload,
  ProductOfMonthResponse,
  SaveAdminProductPayload
} from '../models/admin.model';
import { CreateAccountPayload, CreateAccountResponse } from '../models/auth.model';
import { CartData } from '../models/cart.model';
import { UserDashboardData } from '../models/user-dashboard.model';
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

  getUserDashboardData(): Observable<UserDashboardData> {
    return this.http.get<UserDashboardData>(`${this.baseUrl}/user-dashboard`);
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    return this.http
      .post<{ order: AdminOrder }>(`${this.baseUrl}/orders`, payload)
      .pipe(map((response) => response.order));
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

  updateOrderStatus(orderId: string, status: AdminOrder['status']): Observable<AdminOrder> {
    return this.http
      .patch<{ order: AdminOrder }>(`${this.baseUrl}/orders/${orderId}`, { status })
      .pipe(map((response) => response.order));
  }
}
