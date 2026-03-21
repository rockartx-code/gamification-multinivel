import { Injectable } from '@angular/core';

import { DashboardGoal } from '../models/user-dashboard.model';
import { BrowserStorageService } from './browser/browser-storage.service';
import { BrowserTimerService } from './browser/browser-timer.service';

type AchievedGoalsStorage = {
  month: string;
  goals: string[];
};

export type UserDashboardAchievedGoalsState = {
  achievedGoals: DashboardGoal[];
  newGoalKeys: Set<string>;
  newGoalOrder: Map<string, number>;
  achievedGoalsPage: number;
  isGoalsModalOpen: boolean;
  isGoalsHighlight: boolean;
  shouldAnimateHighlight: boolean;
};

export type UserDashboardGoalBarState = {
  isGoalFilling: boolean;
  visualActiveWidth: number;
  visualCartWidth: number;
};

@Injectable({ providedIn: 'root' })
export class UserDashboardAchievedGoalsService {
  private readonly achievedGoalsStorageKey = 'dashboard-achieved-goals';

  constructor(
    private readonly storage: BrowserStorageService,
    private readonly timer: BrowserTimerService
  ) {}

  resolveState(goals: DashboardGoal[], isGuest: boolean): UserDashboardAchievedGoalsState {
    if (isGuest) {
      return {
        achievedGoals: [],
        newGoalKeys: new Set<string>(),
        newGoalOrder: new Map<string, number>(),
        achievedGoalsPage: 0,
        isGoalsModalOpen: false,
        isGoalsHighlight: false,
        shouldAnimateHighlight: false
      };
    }

    const completed = (goals ?? []).filter((goal) => Boolean(goal?.achieved) && !goal?.locked);
    const monthKey = this.getCurrentMonthKey();
    const stored = this.readStorage();
    const storedMonth = stored?.month ?? '';
    const storedKeys = storedMonth === monthKey ? stored?.goals ?? [] : [];

    if (storedMonth && storedMonth !== monthKey) {
      this.clearStorage();
    }

    const completedKeys = completed.map((goal) => goal.key).filter((key) => Boolean(key));
    const newKeys = completedKeys.filter((key) => !storedKeys.includes(key));
    const newGoalKeys = new Set(newKeys);
    const newGoals = completed.filter((goal) => newGoalKeys.has(goal.key));
    const oldGoals = completed.filter((goal) => !newGoalKeys.has(goal.key));
    const achievedGoals = [...newGoals, ...oldGoals];
    const newGoalOrder = new Map(
      achievedGoals
        .filter((goal) => newGoalKeys.has(goal.key))
        .map((goal, index) => [goal.key, index])
    );

    if (newKeys.length > 0) {
      const merged = Array.from(new Set([...storedKeys, ...newKeys]));
      this.saveStorage(monthKey, merged);
    }

    return {
      achievedGoals,
      newGoalKeys,
      newGoalOrder,
      achievedGoalsPage: 0,
      isGoalsModalOpen: newKeys.length > 0,
      isGoalsHighlight: false,
      shouldAnimateHighlight: newKeys.length > 0
    };
  }

  newGoalDelay(goal: DashboardGoal, newGoalKeys: Set<string>, newGoalOrder: Map<string, number>, isHighlighting: boolean): string {
    if (!newGoalKeys.has(goal.key) || !isHighlighting) {
      return '0ms';
    }
    const order = newGoalOrder.get(goal.key) ?? 0;
    return `${order * 180}ms`;
  }

  scheduleHighlight(previousTimeoutId: number | undefined, applyHighlight: (value: boolean) => void): number | undefined {
    this.timer.clearTimeout(previousTimeoutId);
    applyHighlight(false);
    return this.timer.setTimeout(() => applyHighlight(true), 80);
  }

  animateGoalBar(
    goal: DashboardGoal,
    previousTimeoutId: number | undefined,
    goalBasePercent: (goal: DashboardGoal) => number,
    goalCartPercent: (goal: DashboardGoal) => number,
    applyState: (state: UserDashboardGoalBarState) => void
  ): number | undefined {
    const targetActive = goalBasePercent(goal);
    const targetCart = goalCartPercent(goal);
    applyState({
      isGoalFilling: false,
      visualActiveWidth: 0,
      visualCartWidth: 0
    });
    this.timer.clearTimeout(previousTimeoutId);
    this.timer.requestAnimationFrame(() => {
      applyState({
        isGoalFilling: true,
        visualActiveWidth: 0,
        visualCartWidth: 0
      });
      this.timer.requestAnimationFrame(() => {
        applyState({
          isGoalFilling: true,
          visualActiveWidth: targetActive,
          visualCartWidth: targetCart
        });
      });
    });
    return this.timer.setTimeout(() => {
      applyState({
        isGoalFilling: false,
        visualActiveWidth: targetActive,
        visualCartWidth: targetCart
      });
    }, 1100);
  }

  private getCurrentMonthKey(): string {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    return `${now.getFullYear()}-${month}`;
  }

  private readStorage(): AchievedGoalsStorage | null {
    const parsed = this.storage.getJson<{ month?: string; goals?: string[] }>(this.achievedGoalsStorageKey);
    if (!parsed?.month || !Array.isArray(parsed.goals)) {
      return null;
    }
    return {
      month: parsed.month,
      goals: parsed.goals.filter((key) => typeof key === 'string')
    };
  }

  private saveStorage(month: string, goals: string[]): void {
    this.storage.setJson(this.achievedGoalsStorageKey, { month, goals });
  }

  private clearStorage(): void {
    this.storage.removeItem(this.achievedGoalsStorageKey);
  }
}
