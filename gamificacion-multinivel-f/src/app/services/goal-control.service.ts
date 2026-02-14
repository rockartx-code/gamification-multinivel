import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, combineLatest, distinctUntilChanged, map } from 'rxjs';

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
    combineLatest([this.dashboardControl.data$, this.cartControl.data$])
      .pipe(
        map(([data]) => {
          if (!data?.goals?.length) {
            return [] as DashboardGoal[];
          }
          const cartTotal = this.cartControl.subtotal;
          return data.goals.map((goal) => {
            const isConsumptionGoal =
              goal.key === 'active' ||
              goal.key === 'discount' ||
              goal.key.startsWith('discount_');
            if (isConsumptionGoal && !goal.isCountGoal) {
              return { ...goal, cart: cartTotal };
            }
            return goal;
          });
        }),
        distinctUntilChanged((prev, next) => this.sameGoals(prev, next))
      )
      .subscribe((goals) => {
        this.goalsSubject.next(goals);
      });
  }

  load(): Observable<UserDashboardData> {
    return this.dashboardControl.load();
  }

  get goals(): DashboardGoal[] {
    return this.goalsSubject.value;
  }

  private sameGoals(prev: DashboardGoal[], next: DashboardGoal[]): boolean {
    if (prev.length !== next.length) {
      return false;
    }
    for (let i = 0; i < prev.length; i += 1) {
      const a = prev[i];
      const b = next[i];
      if (
        a.key !== b.key ||
        a.base !== b.base ||
        a.cart !== b.cart ||
        a.target !== b.target ||
        Boolean(a.achieved) !== Boolean(b.achieved) ||
        Boolean(a.locked) !== Boolean(b.locked)
      ) {
        return false;
      }
    }
    return true;
  }
}
