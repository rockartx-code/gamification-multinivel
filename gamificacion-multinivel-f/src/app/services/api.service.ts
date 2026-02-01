import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

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
import { MockApiService } from './mock-api.service';
import { RealApiService } from './real-api.service';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(
    private readonly mockApi: MockApiService,
    private readonly realApi: RealApiService
  ) {}

  login(username: string, password: string): Observable<AuthUser> {
    return this.resolveApi().login(username, password);
  }

  createAccount(payload: CreateAccountPayload): Observable<CreateAccountResponse> {
    return this.resolveApi().createAccount(payload);
  }

  getAdminData(): Observable<AdminData> {
    return this.resolveApi().getAdminData();
  }

  getCartData(): Observable<CartData> {
    return this.resolveApi().getCartData();
  }

  getUserDashboardData(userId?: string): Observable<UserDashboardData> {
    return this.resolveApi().getUserDashboardData(userId);
  }

  requestCommissionPayout(payload: CommissionRequestPayload): Observable<{ request: unknown; summary?: unknown }> {
    return this.resolveApi().requestCommissionPayout(payload);
  }

  uploadCommissionReceipt(payload: CommissionReceiptPayload): Observable<{ receipt: unknown; asset?: unknown }> {
    return this.resolveApi().uploadCommissionReceipt(payload);
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    return this.resolveApi().createOrder(payload);
  }

  getOrder(orderId: string): Observable<AdminOrder> {
    return this.resolveApi().getOrder(orderId);
  }

  getOrders(customerId: string): Observable<AdminOrder[]> {
    return this.resolveApi().getOrders(customerId);
  }

  getCustomer(customerId: string): Observable<CustomerProfile> {
    return this.resolveApi().getCustomer(customerId);
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.resolveApi().createStructureCustomer(payload);
  }

  createAsset(payload: CreateAssetPayload): Observable<AssetResponse> {
    return this.resolveApi().createAsset(payload);
  }

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    return this.resolveApi().createProductAsset(payload);
  }

  setProductOfMonth(productId: number): Observable<ProductOfMonthResponse> {
    return this.resolveApi().setProductOfMonth(productId);
  }

  saveProduct(payload: SaveAdminProductPayload): Observable<AdminProduct> {
    return this.resolveApi().saveProduct(payload);
  }

  updateOrderStatus(orderId: string, payload: UpdateOrderStatusPayload): Observable<AdminOrder> {
    return this.resolveApi().updateOrderStatus(orderId, payload);
  }

  private resolveApi(): MockApiService | RealApiService {
    return environment.useMockApi ? this.mockApi : this.realApi;
  }
}
