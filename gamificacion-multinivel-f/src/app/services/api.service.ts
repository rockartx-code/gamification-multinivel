import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AdminCustomer,
  AdminData,
  AdminOrder,
  CreateAdminOrderPayload,
  CreateProductAssetPayload,
  CreateStructureCustomerPayload,
  ProductAssetUpload
} from '../models/admin.model';
import { CartData } from '../models/cart.model';
import { UserDashboardData } from '../models/user-dashboard.model';
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

  getAdminData(): Observable<AdminData> {
    return this.resolveApi().getAdminData();
  }

  getCartData(): Observable<CartData> {
    return this.resolveApi().getCartData();
  }

  getUserDashboardData(): Observable<UserDashboardData> {
    return this.resolveApi().getUserDashboardData();
  }

  createOrder(payload: CreateAdminOrderPayload): Observable<AdminOrder> {
    return this.resolveApi().createOrder(payload);
  }

  createStructureCustomer(payload: CreateStructureCustomerPayload): Observable<AdminCustomer> {
    return this.resolveApi().createStructureCustomer(payload);
  }

  createProductAsset(payload: CreateProductAssetPayload): Observable<ProductAssetUpload> {
    return this.resolveApi().createProductAsset(payload);
  }

  private resolveApi(): MockApiService | RealApiService {
    return environment.useMockApi ? this.mockApi : this.realApi;
  }
}
