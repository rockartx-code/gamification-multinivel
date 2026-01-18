import { inject, Injectable, InjectionToken } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { UserDashboardData } from '../models/user-dashboard.model';

export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: () => ''
});

export interface UserProfilePayload {
  userId?: string;
  name?: string;
  email?: string;
  role?: string;
  userCode: string;
}

export interface UserProfileResponse {
  profile: Record<string, unknown>;
}

export interface DashboardResponse {
  items: Record<string, unknown>[];
}

export interface AssetRequest {
  filename: string;
  contentType?: string;
  ownerType?: string;
  ownerId?: string;
}

export interface AssetResponse {
  asset: Record<string, unknown>;
  uploadUrl?: string;
  downloadUrl?: string;
}

@Injectable({
  providedIn: 'root'
})
export class GamificationApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  createUserProfile(payload: UserProfilePayload): Observable<UserProfileResponse> {
    return this.http.post<UserProfileResponse>(this.buildUrl('/users'), payload);
  }

  getUserProfile(userId: string): Observable<UserProfileResponse> {
    return this.http.get<UserProfileResponse>(this.buildUrl(`/users/${userId}`));
  }

  updateDashboard(userId: string, payload: UserDashboardData): Observable<{ message: string } & DashboardResponse> {
    return this.http.put<{ message: string } & DashboardResponse>(
      this.buildUrl(`/dashboards/${userId}`),
      payload
    );
  }

  getDashboard(userId: string): Observable<DashboardResponse> {
    return this.http.get<DashboardResponse>(this.buildUrl(`/dashboards/${userId}`));
  }

  getNetwork(userId: string, filters?: { level?: string; status?: string }): Observable<DashboardResponse> {
    let params = new HttpParams();
    if (filters?.level) {
      params = params.set('level', filters.level);
    }
    if (filters?.status) {
      params = params.set('status', filters.status);
    }
    return this.http.get<DashboardResponse>(this.buildUrl(`/network/${userId}`), { params });
  }

  createAsset(payload: AssetRequest): Observable<AssetResponse> {
    return this.http.post<AssetResponse>(this.buildUrl('/assets'), payload);
  }

  getAsset(assetId: string): Observable<AssetResponse> {
    return this.http.get<AssetResponse>(this.buildUrl(`/assets/${assetId}`));
  }

  private buildUrl(path: string): string {
    if (!this.baseUrl) {
      return path;
    }
    return `${this.baseUrl.replace(/\/$/, '')}${path}`;
  }
}
