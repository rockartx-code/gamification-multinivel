import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import {
  DashboardGoal,
  DashboardProduct,
  FeaturedItem,
  NetworkMember
} from '../../models/user-dashboard.model';
import { AuthService, AuthUser } from '../../services/auth.service';
import { UserDashboardControlService } from '../../services/user-dashboard-control.service';

@Component({
  selector: 'app-user-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './user-dashboard.component.html',
  styleUrl: './user-dashboard.component.css'
})
export class UserDashboardComponent implements OnInit, OnDestroy {
  constructor(
    private readonly authService: AuthService,
    private readonly dashboardControl: UserDashboardControlService,
    private readonly router: Router
  ) {}

  readonly countdownLabel = signal('');
  activeFeaturedId = 'colageno';
  socialFormat: 'story' | 'feed' | 'banner' = 'story';
  goalsCollapsed = false;
  toastMessage = 'Actualizado.';
  isToastVisible = false;
  captionText = '';

  private countdownInterval?: number;
  private toastTimeout?: number;

  get currentUser(): AuthUser | null {
    return this.authService.currentUser;
  }

  get isClient(): boolean {
    return this.currentUser?.role === 'cliente';
  }

  get goals(): DashboardGoal[] {
    return this.dashboardControl.goals;
  }

  get products(): DashboardProduct[] {
    return this.dashboardControl.products;
  }

  get featured(): FeaturedItem[] {
    return this.dashboardControl.featured;
  }

  get networkMembers(): NetworkMember[] {
    return this.dashboardControl.networkMembers;
  }

  get heroQty(): number {
    return this.dashboardControl.heroQuantity;
  }

  get buyAgainProducts(): DashboardProduct[] {
    return this.products.filter((product) => this.dashboardControl.buyAgainIds.has(product.id));
  }

  get otherProducts(): DashboardProduct[] {
    return this.products.filter((product) => !this.dashboardControl.buyAgainIds.has(product.id));
  }

  get productsCount(): string {
    return `${this.products.length} productos`;
  }

  get activeFeatured(): FeaturedItem {
    return this.featured.find((item) => item.id === this.activeFeaturedId) ?? this.featured[0];
  }

  get referralLink(): string {
    const userCode = this.dashboardControl.data?.settings.userCode ?? '';
    return `https://tu-dominio.com/r/${userCode}?p=${this.activeFeatured.id}`;
  }

  get networkProgress(): number {
    return this.networkMembers.reduce((acc, member) => acc + member.spend, 0);
  }

  get networkPercent(): number {
    const goal = this.dashboardControl.data?.settings.networkGoal ?? 0;
    if (goal === 0) {
      return 0;
    }
    return Math.min(100, (this.networkProgress / goal) * 100);
  }

  get levelOneCount(): number {
    return this.networkMembers.filter((member) => member.level === 'L1').length;
  }

  get levelTwoCount(): number {
    return this.networkMembers.filter((member) => member.level === 'L2').length;
  }

  get activeCount(): number {
    return this.networkMembers.filter((member) => member.status === 'Activa').length;
  }

  get cartTotal(): number {
    return this.dashboardControl.cartTotal;
  }

  get socialFormatLabel(): string {
    if (this.socialFormat === 'feed') {
      return 'Feed (1:1)';
    }
    if (this.socialFormat === 'banner') {
      return 'Banner (16:9)';
    }
    return 'Story (9:16)';
  }

  get socialAspectRatio(): string {
    if (this.socialFormat === 'feed') {
      return '1/1';
    }
    if (this.socialFormat === 'banner') {
      return '16/9';
    }
    return '9/16';
  }

  get activeSocialAsset(): string {
    if (this.socialFormat === 'feed') {
      return this.activeFeatured.feed;
    }
    if (this.socialFormat === 'banner') {
      return this.activeFeatured.banner;
    }
    return this.activeFeatured.story;
  }

  ngOnInit(): void {
    this.dashboardControl.load().subscribe(() => {
      if (!this.activeFeaturedId) {
        this.activeFeaturedId = this.featured[0]?.id ?? '';
      }
      this.updateCountdown();
    });
    this.countdownInterval = window.setInterval(() => this.updateCountdown(), 1000);
  }

  ngOnDestroy(): void {
    if (this.countdownInterval) {
      window.clearInterval(this.countdownInterval);
    }
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  formatMoney(value: number): string {
    return this.dashboardControl.formatMoney(value);
  }

  goalBasePercent(goal: DashboardGoal): number {
    return this.dashboardControl.goalBasePercent(goal);
  }

  goalCartPercent(goal: DashboardGoal): number {
    return this.dashboardControl.goalCartPercent(goal);
  }

  goalProgressLabel(goal: DashboardGoal): string {
    return this.dashboardControl.goalProgressLabel(goal);
  }

  statusBadgeClass(status: NetworkMember['status']): string {
    return this.dashboardControl.statusBadgeClass(status);
  }

  toggleGoals(): void {
    this.goalsCollapsed = !this.goalsCollapsed;
  }

  setFeatured(id: string): void {
    this.activeFeaturedId = id;
  }

  setSocialFormat(format: 'story' | 'feed' | 'banner'): void {
    this.socialFormat = format;
  }

  copyLink(): void {
    this.copyToClipboard(this.referralLink, 'Link copiado.');
  }

  copyAssetPath(): void {
    this.copyToClipboard(this.activeSocialAsset, 'Ruta copiada.');
  }

  generateTemplate(): void {
    const template = `✨ ${this.activeFeatured.label}\n${this.activeFeatured.hook}\n\nConsíguelo aquí 👉 ${this.referralLink}`;
    this.captionText = template;
    this.showToast('Template generado.');
  }

  copyCaption(): void {
    const text = this.captionText.trim();
    if (!text) {
      this.showToast('Escribe un copy primero.');
      return;
    }
    this.copyToClipboard(text, 'Copy copiado.');
  }

  updateCart(productId: string, qty: number): void {
    this.dashboardControl.updateCart(productId, qty);
    if (this.cartTotal > 0) {
      this.showToast(`En carrito: ${this.formatMoney(this.cartTotal)} (pendiente de pago)`);
    }
  }

  addQuick(productId: string, addQty: number): void {
    this.dashboardControl.addQuick(productId, addQty);
  }

  setHeroQty(value: number): void {
    this.dashboardControl.setHeroQty(value);
  }

  addHeroToCart(): void {
    this.dashboardControl.addHeroToCart();
  }

  getCartQty(productId: string): number {
    return this.dashboardControl.getCartQty(productId);
  }

  showCartToast(): void {
    this.showToast(`Carrito: ${this.formatMoney(this.cartTotal)}`);
  }

  scrollToGoal(goalId: string): void {
    const node = document.getElementById(goalId);
    if (!node) {
      return;
    }
    node.scrollIntoView({ behavior: 'smooth', block: 'center' });
    node.classList.add('ring-2', 'ring-yellow-400/60');
    window.setTimeout(() => node.classList.remove('ring-2', 'ring-yellow-400/60'), 1200);
  }

  scrollToSection(sectionId: string): void {
    const node = document.getElementById(sectionId);
    if (!node) {
      return;
    }
    node.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  notifyAction(message: string): void {
    this.showToast(message);
  }

  simulateInvite(): void {
    this.showToast('Invitación enviada (mock).');
  }

  private updateCountdown(): void {
    this.countdownLabel.set(this.dashboardControl.getCountdownLabel());
  }

  private showToast(message: string): void {
    this.toastMessage = message;
    this.isToastVisible = true;
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
    this.toastTimeout = window.setTimeout(() => {
      this.isToastVisible = false;
    }, 2200);
  }

  private copyToClipboard(text: string, toastMessage: string): void {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(() => this.showToast(toastMessage))
        .catch(() => this.showToast('No se pudo copiar.'));
      return;
    }
    this.showToast('No se pudo copiar.');
  }
}
