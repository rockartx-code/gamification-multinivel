import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../core/api-client';
import { Order } from '../domain/models';
import { ordersFixture } from '../mocks/orders.fixture';

@Injectable({ providedIn: 'root' })
export class OrdersService {
  private readonly apiClient = inject(ApiClient);

  getOrders(): Observable<Order[]> {
    return this.apiClient.get(ordersFixture);
  }
}
