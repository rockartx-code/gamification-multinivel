import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { AdminData } from '../models/admin.model';
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
    return this.http.post<AuthUser>(`${this.baseUrl}/auth/login`, {
      username,
      password
    });
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
}
