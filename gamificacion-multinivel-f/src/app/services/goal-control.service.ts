import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, combineLatest } from 'rxjs';

import { DashboardGoal, UserDashboardData } from '../models/user-dashboard.model';
import { CartControlService } from './cart-control.service';
import { UserDashboardControlService } from './user-dashboard-control.service';

@Injectable({
  providedIn: 'root'
})
export class GoalControlService {
  private readonly goalsSubject = new BehaviorSubject<DashboardGoal[]>([]);
  readonly goals$ = this.goalsSubject.asObservable();

  constructor(
    private readonly dashboardControl: UserDashboardControlService,
    private readonly cartControl: CartControlService
  ) {
    combineLatest([this.dashboardControl.data$, this.cartControl.data$]).subscribe(([data]) => {
      if (!data?.goals?.length) {
        this.goalsSubject.next([]);
        return;
      }
      const cartTotal = this.cartControl.subtotal;
      const goals = data.goals.map((goal) => {
        const isConsumptionGoal =
          goal.key === 'active' ||
          goal.key === 'discount' ||
          goal.key.startsWith('discount_');
        if (isConsumptionGoal && !goal.isCountGoal) {
          return { ...goal, cart: cartTotal };
        }
        return goal;
      });
      this.goalsSubject.next(goals);
    });
  }

  load(): Observable<UserDashboardData> {
    return this.dashboardControl.load();
  }

  get goals(): DashboardGoal[] {
    return this.goalsSubject.value;
  }
}
