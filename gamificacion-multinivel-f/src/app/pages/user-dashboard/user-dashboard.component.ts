import { CommonModule } from '@angular/common';
import { AfterViewInit, ChangeDetectorRef, Component, OnDestroy, OnInit, signal } from '@angular/core';
import { Subscription } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import {
  DashboardGoal,
  DashboardProduct,
  FeaturedItem,
  NetworkMember,
  UserDashboardData
} from '../../models/user-dashboard.model';
import { CartItem } from '../../models/cart.model';
import { AdminOrder } from '../../models/admin.model';
import { AuthService, AuthUser } from '../../services/auth.service';
import { ApiService } from '../../services/api.service';
import { CartControlService } from '../../services/cart-control.service';
import { GoalControlService } from '../../services/goal-control.service';
import { UserDashboardControlService } from '../../services/user-dashboard-control.service';

@Component({
  selector: 'app-user-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './user-dashboard.component.html',
  styleUrl: './user-dashboard.component.css'
})
export class UserDashboardComponent implements OnInit, OnDestroy, AfterViewInit {
  constructor(
    private readonly authService: AuthService,
    private readonly dashboardControl: UserDashboardControlService,
    private readonly cartControl: CartControlService,
    private readonly goalControl: GoalControlService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef,
    private readonly api: ApiService
  ) {}

  readonly countdownLabel = signal('');
  activeFeaturedId = '';
  socialFormat: 'story' | 'feed' | 'banner' = 'story';
  socialChannel: 'whatsapp' | 'instagram' | 'facebook' = 'whatsapp';
  featuredPage = 0;
  readonly featuredPageSize = 4;
  secondaryGoalsVisible = false;
  toastMessage = 'Actualizado.';
  isToastVisible = false;
  captionText = '';
  hasCopiedLink = false;
  hasCopiedCopy = false;
  hasCopiedAsset = false;
  lastAutoCaption = true;
  lastClipboardError = '';
  guestRegisterForm = {
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  };
  isGuestRegisterSubmitting = false;
  guestRegisterFeedback = '';
  guestRegisterFeedbackType: 'error' | 'success' | '' = '';
  isLoading = false;
  activeGoal: any | null = null;
  secondaryGoals: any[] = [];
  isDevMode = false;
  showGuestRegisterModal = false;
  orders: AdminOrder[] = [];
  isOrdersLoading = false;
  isCommissionModalOpen = false;
  isCommissionSubmitting = false;
  isCommissionUploading = false;
  isUserDetailsOpen = false;
  isMobileNavOpen = false;
  isGoalsHighlight = false;
  achievedGoalsPage = 0;
  readonly achievedGoalsPageSize = 3;
  private readonly achievedGoalsStorageKey = 'dashboard-achieved-goals';
  private newAchievedGoalKeys = new Set<string>();
  private newAchievedGoalOrder = new Map<string, number>();
  private goalsAnimTimeout?: number;
  visualActiveWidth = 0;
  visualCartWidth = 0;
  isGoalFilling = false;
  private goalFillTimeout?: number;
  private lastActiveGoalKey = '';
  private lastActiveGoalBase = -1;
  private lastActiveGoalCart = -1;
  commissionClabe = '';
  commissionUploadName = '';
  showCommissionLedger = false;
  showBlockedTooltip = false;
  clabeDraft = '';
  clabePending = '';
  isClabeConfirmOpen = false;
  isClabeSaving = false;
  isGoalsModalOpen = false;
  isProductDetailsOpen = false;
  selectedProduct: DashboardProduct | null = null;
  achievedGoals: DashboardGoal[] = [];
  private goalToastState: 'near' | 'done' | '' = '';

  private countdownInterval?: number;
  private toastTimeout?: number;
  private goalsSub?: Subscription;


  

  get currentUser(): AuthUser | null {
    return this.authService.currentUser;
  }

  get isClient(): boolean {
    return this.currentUser?.role === 'cliente';
  }

  private get dashboardUser(): UserDashboardData['user'] | null {
    return this.dashboardControl.data?.user ?? null;
  }

  get userLevel(): string {
    return this.dashboardUser?.level || this.currentUser?.level || '';
  }

  private get discountPercentValue(): number {
    const raw = this.dashboardUser?.discountPercent ?? this.currentUser?.discountPercent;
    const value = typeof raw === 'string' ? Number(raw) : Number(raw ?? 0);
    return Number.isFinite(value) ? value : 0;
  }

  private get discountActiveValue(): boolean {
    const raw = this.dashboardUser?.discountActive;
    if (typeof raw === 'boolean') {
      return raw;
    }
    return Boolean(this.currentUser?.discountActive);
  }

  get isGuest(): boolean {
    if (this.dashboardControl.data?.isGuest != null) {
      return this.dashboardControl.data.isGuest;
    }
    return !this.currentUser;
  }

  get goals(): DashboardGoal[] {
    return this.goalControl.goals;
  }

  get products(): DashboardProduct[] {
    return this.dashboardControl.products;
  }

  get featured(): FeaturedItem[] {
    return this.dashboardControl.featured;
  }

  get featuredCarousel(): FeaturedItem[] {
    const fixed: FeaturedItem[] = [
      {
        id: 'fixed-familia',
        label: 'Familia',
        hook: 'Programa familiar',
        story: 'images/L-Programa3.png',
        feed: 'images/L-Programa3.png',
        banner: 'images/L-Programa3.png'
      },
      {
        id: 'fixed-entrenador',
        label: 'Entrenador',
        hook: 'Programa entrenador',
        story: 'images/L-Programa2.png',
        feed: 'images/L-Programa2.png',
        banner: 'images/L-Programa2.png'
      }
    ];

    const featuredIds = new Set(this.featured.map((item) => item.id));
    const productItems: FeaturedItem[] = this.products
      .filter((product) => !featuredIds.has(product.id))
      .map((product) => ({
        id: product.id,
        label: product.name,
        hook: product.badge || 'Producto destacado',
        story: product.img || '',
        feed: product.img || '',
        banner: product.img || ''
      }));

    return [...fixed, ...this.featured, ...productItems];
  }

  get pagedFeatured(): FeaturedItem[] {
    const start = this.featuredPage * this.featuredPageSize;
    return this.featuredCarousel.slice(start, start + this.featuredPageSize);
  }

  get canPrevFeatured(): boolean {
    return this.featuredPage > 0;
  }

  get canNextFeatured(): boolean {
    return (this.featuredPage + 1) * this.featuredPageSize < this.featuredCarousel.length;
  }

  get networkMembers(): NetworkMember[] {
    return this.dashboardControl.networkMembers;
  }

  get commissionSummary(): UserDashboardData['commissions'] {
    return this.dashboardControl.data?.commissions ?? null;
  }

  get hasCommissionPending(): boolean {
    return Boolean(this.commissionSummary?.hasPending);
  }

  get heroQty(): number {
    const heroId = this.productOfMonth?.id;
    if (!heroId) {
      return 0;
    }
    return this.cartControl.getQty(heroId);
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

  get productOfMonth(): UserDashboardData['productOfMonth'] {
    return this.dashboardControl.data?.productOfMonth ?? null;
  }

  get heroProductPrice(): number {
    return this.productOfMonth?.price ?? 0;
  }

  get heroImage(): string {
    return this.productOfMonth?.img || 'images/Colageno-Clean.png';
  }

  get heroTags(): string[] {
    return this.productOfMonth?.tags?.length
      ? this.productOfMonth.tags
      : ['10g por porci?n', 'Vitamina C + AH', 'Alta absorci?n'];
  }

  get heroGoalHint(): string {
    if (!this.activeGoal?.title) {
      return '';
    }
    return `Este producto te acerca a: ${this.activeGoal.title}`;
  }

  get cutoffRemainingSeconds(): number {
    const settings = this.dashboardControl.data?.settings;
    if (!settings) {
      return 0;
    }
    const next = this.getNextCutoffDate(settings);
    return Math.max(0, Math.floor((next.getTime() - Date.now()) / 1000));
  }

  get cutoffTotalSeconds(): number {
    const settings = this.dashboardControl.data?.settings;
    if (!settings) {
      return 1;
    }
    const next = this.getNextCutoffDate(settings);
    const prev = new Date(next);
    prev.setMonth(prev.getMonth() - 1);
    const total = Math.max(1, Math.floor((next.getTime() - prev.getTime()) / 1000));
    return total;
  }

  private readonly emptyFeatured: FeaturedItem = {
    id: '',
    label: '',
    hook: '',
    story: '',
    feed: '',
    banner: ''
  };

  get activeFeatured(): FeaturedItem {
    return (
      this.featuredCarousel.find((item) => item.id === this.activeFeaturedId) ??
      this.featuredCarousel[0] ??
      this.emptyFeatured
    );
  }

  get referralLink(): string {
    if (this.isGuest) {
      return '';
    }
    const userCode = this.dashboardControl.data?.settings.userCode ?? '';
    if (!userCode) {
      return '';
    }
    const productId = this.activeFeatured.id ?? '';
    const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
    const query = productId ? `?p=${productId}` : '';
    return `${baseUrl}/#/${userCode}${query}`;
  }

  get networkProgress(): number {
    return this.networkMembers.reduce((acc, member) => acc + member.spend, 0);
  }

  get networkGoal(): number {
    return this.dashboardControl.data?.settings.networkGoal ?? 0;
  }

  get networkPercent(): number {
    if (this.networkGoal === 0) {
      return 0;
    }
    return Math.min(100, (this.networkProgress / this.networkGoal) * 100);
  }

  get remainingNetworkGoal(): number {
    return Math.max(0, this.networkGoal - this.networkProgress);
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
    return this.cartControl.subtotal;
  }

  get cartDiscount(): number {
    if (!this.hasDiscount) {
      return 0;
    }
    return Math.round(this.cartTotal * (this.discountPercentValue / 100));
  }

  get cartDiscountPercent(): number {
    return this.hasDiscount ? Math.round(this.discountPercentValue) : 0;
  }

  get cartDiscountLabel(): string {
    if (this.cartDiscount <= 0 || this.cartDiscountPercent <= 0) {
      return 'Sin descuento';
    }
    return `Dto ${this.cartDiscountPercent}%`;
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
      return this.activeFeatured.feed || '';
    }
    if (this.socialFormat === 'banner') {
      return this.activeFeatured.banner || '';
    }
    return this.activeFeatured.story || '';
  }

  discountBadgeText(): string {
    if (!this.discountActiveValue) {
      return 'Inactivo';
    }
    const pct = this.discountPercentValue;
    if (!pct) {
      return 'Sin descuento';
    }
    if (pct >= 50) {
      return `Dto ${pct}% • Nivel 3`;
    }
    if (pct >= 40) {
      return `Dto ${pct}% • Nivel 2`;
    }
    if (pct >= 30) {
      return `Dto ${pct}% • Nivel 1`;
    }
    return `Dto ${pct}%`;
  }

  get hasDiscount(): boolean {
    return this.discountActiveValue && this.discountPercentValue > 0;
  }

  get discountPercent(): number {
    return this.hasDiscount ? this.discountPercentValue : 0;
  }

  get discountPercentMobile(): string {
    if (!this.hasDiscount) {
      return '';
    }
    return `${Math.round(this.discountPercentValue)}%`;
  }

  discountAppliedLabel(): string {
    return this.hasDiscount ? `Dto ${this.discountPercentValue}%` : 'Sin descuento';
  }

  discountedPrice(value: number): number {
    if (!this.hasDiscount) {
      return value;
    }
    const pct = this.discountPercentValue / 100;
    return Math.max(0, Math.round(value * (1 - pct)));
  }

  discountBadgeIcon(): string {
    if (!this.discountActiveValue) {
      return 'fa-lock';
    }
    return 'fa-tags';
  }

  discountBadgeClass(): string {
    if (!this.discountActiveValue) {
      return 'border-white/10 bg-white/5 text-zinc-300';
    }
    const pct = this.discountPercentValue;
    if (pct >= 50) {
      return 'border-yellow-400/30 bg-yellow-400/10 text-yellow-200';
    }
    if (pct >= 40) {
      return 'border-zinc-300/30 bg-zinc-400/10 text-zinc-200';
    }
    if (pct >= 30) {
      return 'border-amber-700/40 bg-gradient-to-br from-amber-600/20 via-amber-700/20 to-stone-900/30 text-amber-200';
    }
    return 'border-blue-400/30 bg-blue-500/10 text-blue-200';
  }

  medalBadgeClass(): string {
    const level = (this.userLevel || '').toLowerCase();
    if (level.includes('oro') || level.includes('gold')) {
      return 'border-yellow-400/30 bg-yellow-400/10 text-yellow-200';
    }
    if (level.includes('plata') || level.includes('silver')) {
      return 'border-zinc-300/30 bg-zinc-400/10 text-zinc-200';
    }
    if (level.includes('bronce') || level.includes('bronze')) {
      return 'border-amber-400/30 bg-amber-400/10 text-amber-200';
    }
    return 'border-purple-400/30 bg-purple-400/10 text-purple-200';
  }

  toggleUserDetails(): void {
    this.isUserDetailsOpen = !this.isUserDetailsOpen;
  }

  getCountdownState(): 'calm' | 'focus' | 'urgent' | 'critical' {
    const total = this.cutoffTotalSeconds;
    const remaining = this.cutoffRemainingSeconds;
    const pct = total > 0 ? remaining / total : 0;
    if (pct > 0.6) {
      return 'calm';
    }
    if (pct > 0.3) {
      return 'focus';
    }
    if (pct > 0.1) {
      return 'urgent';
    }
    return 'critical';
  }

  getCountdownLabel(): string {
    const state = this.getCountdownState();
    switch (state) {
      case 'calm':
        return 'Tienes buen margen';
      case 'focus':
        return 'Momento de acelerar';
      case 'urgent':
        return 'Ultimo empujon';
      case 'critical':
      default:
        return 'Ahora o pierdes el mes';
    }
  }

  getCountdownColor(): string {
    const state = this.getCountdownState();
    switch (state) {
      case 'calm':
        return 'text-emerald-300';
      case 'focus':
        return 'text-blue-300';
      case 'urgent':
        return 'text-yellow-300';
      case 'critical':
      default:
        return 'text-red-400 animate-pulse';
    }
  }


  get graphLayout(): {
    nodes: Array<{
      id: string;
      level: string;
      x: number;
      y: number;
      label: string;
      name: string;
      status?: NetworkMember['status'];
      leaderId?: string;
    }>;
    links: Array<{ x1: number; y1: number; x2: number; y2: number }>;
  } {
    const l1Members = this.networkMembers.filter((member) => member.level === 'L1');
    const l2Members = this.networkMembers.filter((member) => member.level === 'L2');
    const l3Members = this.networkMembers.filter((member) => member.level === 'L3');
    const metrics = this.getGraphMetrics(l1Members.length, l2Members.length, l3Members.length);
    const rootX = 120;
    const l1X = 320;
    const l2X = 540;
    const l3X = 760;

    const l1Positions = this.buildColumnPositions(l1Members.length, l1X, metrics.top, metrics.spacing);
    const l2Positions = this.buildColumnPositions(l2Members.length, l2X, metrics.top, metrics.spacing);
    const l3Positions = this.buildColumnPositions(l3Members.length, l3X, metrics.top, metrics.spacing);
    const rootY =
      l1Positions.length > 0
        ? (l1Positions[0].y + l1Positions[l1Positions.length - 1].y) / 2
        : l2Positions.length > 0
          ? (l2Positions[0].y + l2Positions[l2Positions.length - 1].y) / 2
          : l3Positions.length > 0
            ? (l3Positions[0].y + l3Positions[l3Positions.length - 1].y) / 2
            : metrics.height / 2;

    const rootName = this.currentUser?.name || 'Tu';
    const root = {
      id: 'root',
      level: 'root',
      x: rootX,
      y: rootY,
      label: this.nodeLabel(rootName),
      name: rootName
    };

    const l1Nodes = l1Members.map((member, idx) => ({
      id: member.id ? `l1-${member.id}` : `l1-${idx}`,
      level: 'L1',
      x: l1Positions[idx]?.x ?? l1X,
      y: l1Positions[idx]?.y ?? rootY,
      label: this.nodeLabel(member.name),
      name: member.name || 'Miembro',
      status: member.status
    }));

    const l1ByMemberId = new Map<string, (typeof l1Nodes)[number]>();
    l1Members.forEach((member, idx) => {
      const memberId = member.id ? String(member.id) : `idx-${idx}`;
      l1ByMemberId.set(memberId, l1Nodes[idx]);
    });

    const l2Nodes = l2Members.map((member, idx) => {
      const memberId = member.id ? `l2-${member.id}` : `l2-${idx}`;
      return {
        id: memberId,
        level: 'L2',
        x: l2Positions[idx]?.x ?? l2X,
        y: l2Positions[idx]?.y ?? rootY,
        label: this.nodeLabel(member.name),
        name: member.name || 'Miembro',
        status: member.status,
        leaderId: member.leaderId ? String(member.leaderId) : undefined
      };
    });

    const l2ByMemberId = new Map<string, (typeof l2Nodes)[number]>();
    l2Members.forEach((member, idx) => {
      const memberId = member.id ? String(member.id) : `idx-${idx}`;
      l2ByMemberId.set(memberId, l2Nodes[idx]);
    });

    const l3Nodes = l3Members.map((member, idx) => {
      const memberId = member.id ? `l3-${member.id}` : `l3-${idx}`;
      return {
        id: memberId,
        level: 'L3',
        x: l3Positions[idx]?.x ?? l3X,
        y: l3Positions[idx]?.y ?? rootY,
        label: this.nodeLabel(member.name),
        name: member.name || 'Miembro',
        status: member.status,
        leaderId: member.leaderId ? String(member.leaderId) : undefined
      };
    });

    const links: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];
    for (const node of l1Nodes) {
      links.push({ x1: root.x, y1: root.y, x2: node.x, y2: node.y });
    }
    for (const node of l2Nodes) {
      const parentId = node.leaderId ?? '';
      const parent = l1ByMemberId.get(parentId) ?? (l1Nodes.length ? l1Nodes[0] : root);
      links.push({ x1: parent.x, y1: parent.y, x2: node.x, y2: node.y });
    }
    for (const node of l3Nodes) {
      const parentId = node.leaderId ?? '';
      const parent = l2ByMemberId.get(parentId) ?? (l2Nodes.length ? l2Nodes[0] : root);
      links.push({ x1: parent.x, y1: parent.y, x2: node.x, y2: node.y });
    }

    return { nodes: [root, ...l1Nodes, ...l2Nodes, ...l3Nodes], links };
  }

  nodeFill(level: string, status?: NetworkMember['status']): string {
    if (status === 'Inactiva') {
      return 'rgba(148,163,184,.75)';
    }
    if (level === 'root') {
      return 'rgba(59,130,246,.92)';
    }
    if (level === 'L1') {
      return 'rgba(245,185,66,.92)';
    }
    return 'rgba(139,92,246,.92)';
  }

  nodeRadius(level: string): number {
    if (level === 'root') {
      return 28;
    }
    if (level === 'L1') {
      return 18;
    }
    return 14;
  }

  get graphSize(): { width: number; height: number } {
    const l1Count = this.networkMembers.filter((member) => member.level === 'L1').length;
    const l2Count = this.networkMembers.filter((member) => member.level === 'L2').length;
    const l3Count = this.networkMembers.filter((member) => member.level === 'L3').length;
    const metrics = this.getGraphMetrics(l1Count, l2Count, l3Count);
    return { width: metrics.width, height: metrics.height };
  }

  private getGraphMetrics(
    l1Count: number,
    l2Count: number,
    l3Count: number
  ): { width: number; height: number; top: number; spacing: number } {
    const maxCount = Math.max(l1Count, l2Count, l3Count, 1);
    const top = 40;
    const spacing = 64;
    const height = Math.max(260, top * 2 + spacing * (maxCount - 1));
    return { width: 860, height, top, spacing };
  }

  private buildColumnPositions(
    count: number,
    x: number,
    top: number,
    spacing: number
  ): { x: number; y: number }[] {
    if (count <= 0) {
      return [];
    }
    if (count === 1) {
      return [{ x, y: top }];
    }
    return Array.from({ length: count }, (_, index) => ({
      x,
      y: top + spacing * index
    }));
  }

  private nodeLabel(name?: string): string {
    const value = (name ?? '').trim();
    if (!value) {
      return 'Cliente';
    }
    const first = value.split(' ')[0] ?? value;
    return first.slice(0, 6);
  }

  curvePath(link: { x1: number; y1: number; x2: number; y2: number }, offset: number): string {
    const midX = (link.x1 + link.x2) / 2;
    const midY = (link.y1 + link.y2) / 2 + offset;
    return `M ${link.x1} ${link.y1} Q ${midX} ${midY}, ${link.x2} ${link.y2}`;
  }
  ngOnInit(): void {
    this.isLoading = true;
    this.cartControl.load().subscribe();
    this.goalsSub = this.goalControl.goals$.subscribe((goals) => {
      if (goals) {
        this.processGoals(goals);
      }
    });
    this.goalControl
      .load()
      .pipe(
        finalize(() => {
          this.isLoading = false;
          this.updateCountdown();
        })
      )
      .subscribe({
        next: (data) => {
          this.processGoals(data?.goals ?? []);
          this.loadAchievedGoals(data?.goals ?? []);
          if (!this.activeFeaturedId) {
            const nextFeaturedId = this.featuredCarousel[0]?.id ?? data?.featured?.[0]?.id ?? this.featured[0]?.id ?? '';
            if (nextFeaturedId) {
              this.setFeatured(nextFeaturedId);
            }
          }
          this.featuredPage = 0;
          this.cdr.markForCheck();
          this.loadOrders();
        },
        error: () => {
          this.showToast('No se pudo cargar el dashboard.');
        }
      });
    this.countdownInterval = window.setInterval(() => this.updateCountdown(), 1000);
  }

  ngAfterViewInit(): void {
    if (!this.activeGoal?.key) {
      return;
    }
    setTimeout(() => {
      const node = document.getElementById(`goal-${this.activeGoal.key}`);
      node?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 0);
  }

  ngOnDestroy(): void {
    if (this.countdownInterval) {
      window.clearInterval(this.countdownInterval);
    }
    if (this.toastTimeout) {
      window.clearTimeout(this.toastTimeout);
    }
    if (this.goalsAnimTimeout) {
      window.clearTimeout(this.goalsAnimTimeout);
    }
    if (this.goalFillTimeout) {
      window.clearTimeout(this.goalFillTimeout);
    }
    this.goalsSub?.unsubscribe();
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  goToCart(): void {
    const items = this.products.reduce<CartItem[]>((acc, product) => {
      const qty = this.getCartQty(product.id);
      if (!qty) {
        return acc;
      }
      acc.push({
        id: product.id,
        name: product.name,
        price: product.price,
        qty,
        note: product.badge || '',
        img: product.img || ''
      });
      return acc;
    }, []);
    localStorage.setItem('cart-items', JSON.stringify(items));
    this.router.navigate(['/carrito']);
  }

  openGuestRegisterModal(): void {
    this.showGuestRegisterModal = true;
  }

  closeGuestRegisterModal(): void {
    this.showGuestRegisterModal = false;
  }

  submitGuestRegister(): void {
    if (this.isGuestRegisterSubmitting) {
      return;
    }
    if (!this.guestRegisterForm.name || !this.guestRegisterForm.email || !this.guestRegisterForm.password) {
      this.guestRegisterFeedback = 'Completa los campos obligatorios.';
      this.guestRegisterFeedbackType = 'error';
      return;
    }
    if (this.guestRegisterForm.password !== this.guestRegisterForm.confirmPassword) {
      this.guestRegisterFeedback = 'Las contraseñas no coinciden.';
      this.guestRegisterFeedbackType = 'error';
      return;
    }

    const payload = {
      name: this.guestRegisterForm.name.trim(),
      email: this.guestRegisterForm.email.trim(),
      phone: this.guestRegisterForm.phone.trim() || undefined,
      password: this.guestRegisterForm.password,
      confirmPassword: this.guestRegisterForm.confirmPassword,
      referralToken: localStorage.getItem('leaderId') || undefined
    };

    this.isGuestRegisterSubmitting = true;
    this.api
      .createAccount(payload)
      .pipe(
        finalize(() => {
          this.isGuestRegisterSubmitting = false;
        })
      )
      .subscribe({
        next: (response) => {
          if (response?.customer) {
            this.authService.setUserFromCreateAccount(response.customer);
          }
          this.guestRegisterForm = {
            name: '',
            email: '',
            phone: '',
            password: '',
            confirmPassword: ''
          };
          this.guestRegisterFeedback = '';
          this.guestRegisterFeedbackType = '';
          this.showGuestRegisterModal = false;
          this.showToast('Cuenta creada. Bienvenido.');
          window.location.reload();
        },
        error: (error: any) => {
          const apiMessage =
            error?.error?.message || error?.error?.Error || error?.message || 'No se pudo crear la cuenta.';
          this.guestRegisterFeedback = apiMessage;
          this.guestRegisterFeedbackType = 'error';
        }
      });
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

  orderStatusClass(status?: string): string {
    const value = (status || '').toLowerCase();
    if (value === 'pending') {
      return 'border-rose-400/30 bg-rose-500/10 text-rose-200';
    }
    if (value === 'delivered') {
      return 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200';
    }
    if (value === 'shipped') {
      return 'border-blue-400/30 bg-blue-500/10 text-blue-200';
    }
    if (value === 'paid') {
      return 'border-purple-400/30 bg-purple-500/10 text-purple-200';
    }
    return 'border-white/10 bg-white/5 text-zinc-300';
  }

  orderStatusIcon(status?: string): string {
    const value = (status || '').toLowerCase();
    if (value === 'pending') {
      return 'fa-hourglass-half';
    }
    if (value === 'delivered') {
      return 'fa-circle-check';
    }
    if (value === 'shipped') {
      return 'fa-truck-fast';
    }
    if (value === 'paid') {
      return 'fa-receipt';
    }
    return 'fa-circle';
  }

  toggleSecondaryGoals(): void {
    this.secondaryGoalsVisible = !this.secondaryGoalsVisible;
  }

  toggleMobileNav(): void {
    this.isMobileNavOpen = !this.isMobileNavOpen;
  }

  closeMobileNav(): void {
    this.isMobileNavOpen = false;
  }

  setFeatured(id: string): void {
    this.activeFeaturedId = id;
    if (!this.captionText.trim() || this.lastAutoCaption) {
      this.captionText = this.buildAutoCaption();
      this.lastAutoCaption = true;
    }
  }

  setSocialFormat(format: 'story' | 'feed' | 'banner'): void {
    this.socialFormat = format;
  }

  // Color del icono del usuario: gris inactivo, azul activo.
levelIconClass(): string {
  if (!this.isClient || !this.discountActiveValue) {
    return 'text-zinc-400';
  }
  return 'text-blue-300';
}

// Borde / Anillo principal = Estado + Nivel
discountRingClass(): string {

  // Inactivo
  if (!this.isClient || !this.discountActiveValue) {
    return 'border border-white/10 opacity-60';
  }

  const p = this.discountPercentNumber();

  // 🥇 ORO 50%
  if (p >= 50) {
    return `
      ring-2 ring-yellow-400/70
      shadow-[0_0_12px_rgba(250,204,21,0.35)]
    `;
  }

  // 🥈 PLATA 40%
  if (p >= 40) {
    return `
      ring-2 ring-zinc-300/70
      shadow-[0_0_10px_rgba(212,212,216,0.25)]
    `;
  }

  // 🥉 BRONCE 30%
  if (p >= 30) {
    return `
      ring-2 ring-amber-500/70
      shadow-[0_0_10px_rgba(245,158,11,0.25)]
    `;
  }

  // 🔵 Activo sin nivel
  return `
    ring-2 ring-blue-400/50
    shadow-[0_0_8px_rgba(96,165,250,0.2)]
  `;
}


// Mini badge = Refuerzo semántico
discountBadgeMiniClass(): string {

  // Inactivo = no mostrar
  if (!this.isClient || !this.discountActiveValue) {
    return 'bg-white/5 text-zinc-400 border-white/10';
  }

  const p = this.discountPercentNumber();

  // 🥇 ORO
  if (p >= 50) {
    return `
      bg-yellow-500/15
      text-yellow-200
      border-yellow-400/40
      shadow-sm
    `;
  }

  // 🥈 PLATA
  if (p >= 40) {
    return `
      bg-zinc-400/20
      text-zinc-100
      border-zinc-300/40
    `;
  }

  // 🥉 BRONCE
  if (p >= 30) {
    return `
      bg-amber-600/20
      text-amber-300
      border-amber-500/40
    `;
  }

  // 🔵 Activo
  return `
    bg-blue-500/15
    text-blue-200
    border-blue-400/30
  `;
}


private discountPercentNumber(): number {
  // Ajusta según tu fuente real:
  // - si discountPercent = "30%" -> parse
  // - si ya es number, devuélvelo directo
  const raw = (this.discountPercent ?? '').toString().trim();
  const n = Number(raw.replace('%', ''));
  return Number.isFinite(n) ? n : 0;
}


  get hasInactiveIntermediate(): boolean {
    return this.networkMembers.some((member) => member.level === 'L1' && member.status === 'Inactiva');
  }

  nextFeaturedPage(): void {
    if (this.canNextFeatured) {
      this.featuredPage += 1;
    }
  }

  prevFeaturedPage(): void {
    if (this.canPrevFeatured) {
      this.featuredPage -= 1;
    }
  }

  private getNextCutoffDate(settings: UserDashboardData['settings']): Date {
    const now = new Date();
    let cutoff = new Date(
      now.getFullYear(),
      now.getMonth(),
      settings.cutoffDay,
      settings.cutoffHour,
      settings.cutoffMinute,
      59,
      999
    );
    if (cutoff.getTime() <= now.getTime()) {
      cutoff = new Date(
        now.getFullYear(),
        now.getMonth() + 1,
        settings.cutoffDay,
        settings.cutoffHour,
        settings.cutoffMinute,
        59,
        999
      );
    }
    return cutoff;
  }

  setChannel(channel: 'whatsapp' | 'instagram' | 'facebook'): void {
    this.socialChannel = channel;
    switch (channel) {
      case 'facebook':
        this.socialFormat = 'feed';
        break;
      case 'whatsapp':
      case 'instagram':
      default:
        this.socialFormat = 'story';
        break;
    }
    if (!this.captionText.trim() || this.lastAutoCaption) {
      this.captionText = this.buildAutoCaption();
      this.lastAutoCaption = true;
    }
  }

  copyLink(): void {
    this.hasCopiedLink = true;
    this.copyToClipboard(this.referralLink, 'Link copiado.');
  }

  copyAssetPath(): void {
    this.hasCopiedAsset = true;
    this.copyImageToClipboard(this.activeSocialAsset, 'Imagen copiada.');
  }

  copyAssetPathByUrl(url: string): void {
    if (!url) {
      this.showToast('No hay ruta disponible.');
      return;
    }
    this.hasCopiedAsset = true;
    this.copyImageToClipboard(url, 'Imagen copiada.');
  }

  generateTemplate(channel: 'whatsapp' | 'instagram' | 'facebook' = this.socialChannel): void {
    const label = this.activeFeatured.label;
    const hook = this.activeFeatured.hook;
    const productCopy = this.getActiveProductCopy(channel);
    let cta = `Pidelo aqui: ${this.referralLink}`;
    let opener = 'Te comparto esto:';
    let howTo = productCopy || 'Como lo uso: ...';

    switch (channel) {
      case 'whatsapp':
        opener = 'Te lo paso por WhatsApp:';
        howTo = productCopy || 'Resumen rapido: ...';
        cta = `Si te interesa, responde y te paso el link: ${this.referralLink}`;
        break;
      case 'instagram':
        opener = 'Tip rapido para Instagram:';
        howTo = productCopy || 'Como lo uso: ...';
        cta = `Pide el link por DM o en bio: ${this.referralLink}`;
        break;
      case 'facebook':
        opener = 'Comparte esto en Facebook:';
        howTo = productCopy || 'Mi experiencia: ...';
        cta = `Escribeme por inbox y te paso el link: ${this.referralLink}`;
        break;
      default:
        break;
    }

    const template = `${opener}\n\n${label}: ${hook}\n\n${howTo}\n\n${cta}`;
    this.captionText = template;
    this.showToast('Template generado.');
    this.lastAutoCaption = true;
  }

  private getActiveProductCopy(channel: 'whatsapp' | 'instagram' | 'facebook'): string {
    const featuredId = this.activeFeatured?.id;
    const product = featuredId ? this.products.find((item) => item.id === featuredId) : null;
    if (!product) {
      return '';
    }
    if (channel === 'facebook') {
      return (product.copyFacebook || '').trim();
    }
    if (channel === 'instagram') {
      return (product.copyInstagram || '').trim();
    }
    return (product.copyWhatsapp || '').trim();
  }

  copyCaption(): void {
    const text = this.captionText.trim();
    if (!text) {
      this.showToast('Escribe un copy primero.');
      return;
    }
    this.hasCopiedCopy = true;
    this.copyToClipboard(text, 'Copy copiado.');
  }

  copyLinkAndCopy(): void {
    const combined = `${this.referralLink}\n\n${this.captionText.trim()}`;
    this.hasCopiedLink = true;
    this.hasCopiedCopy = true;
    this.copyToClipboard(combined.trim(), 'Link y copy copiados. Pega en WhatsApp/Instagram.');
  }

  openReferralLink(): void {
    if (!this.referralLink) {
      this.showToast('No hay link disponible.');
      return;
    }
    window.open(this.referralLink, '_blank', 'noopener');
  }

  updateCart(productId: string, qty: number): void {
    const product = this.resolveProduct(productId);
    if (product) {
      this.cartControl.upsertItem(this.buildCartItem(product), qty);
    }
    this.logGoalProgress();
    if (this.cartTotal > 0) {
      this.showToast(`En carrito: ${this.formatMoney(this.cartTotal)} (pendiente de pago)`);
    }
    this.maybeShowGoalProgressToast();
  }

  addQuick(productId: string, addQty: number): void {
    const product = this.resolveProduct(productId);
    if (product) {
      this.cartControl.addItem(this.buildCartItem(product), addQty);
    }
    this.logGoalProgress();
    this.maybeShowGoalProgressToast();
  }

  setHeroQty(value: number): void {
    const productId = this.productOfMonth?.id;
    if (!productId) {
      return;
    }
    const product = this.resolveProduct(productId);
    if (product) {
      this.cartControl.upsertItem(this.buildCartItem(product), value);
    }
  }

  addHeroToCart(): void {
    const productId = this.productOfMonth?.id;
    if (!productId) {
      return;
    }
    const product = this.resolveProduct(productId);
    if (product) {
      this.cartControl.addItem(this.buildCartItem(product), 1);
    }
    this.logGoalProgress();
    this.maybeShowGoalProgressToast();
  }

  getCartQty(productId: string): number {
    return this.cartControl.getQty(productId);
  }

  showCartToast(): void {
    this.showToast(`Carrito: ${this.formatMoney(this.cartTotal)}`);
  }

  openCommissionModal(): void {
    this.commissionClabe = '';
    this.isCommissionModalOpen = true;
  }

  closeCommissionModal(): void {
    this.isCommissionModalOpen = false;
  }

  openClabeConfirm(): void {
    const clabe = this.clabeDraft.trim();
    if (!clabe) {
      this.showToast('Ingresa tu CLABE interbancaria.');
      return;
    }
    if (!/^\d{18}$/.test(clabe)) {
      this.showToast('La CLABE debe tener 18 digitos.');
      return;
    }
    this.clabePending = clabe;
    this.isClabeConfirmOpen = true;
  }

  closeClabeConfirm(): void {
    this.isClabeConfirmOpen = false;
    this.clabePending = '';
  }

  toggleCommissionLedger(): void {
    this.showCommissionLedger = !this.showCommissionLedger;
  }

  toggleBlockedTooltip(): void {
    this.showBlockedTooltip = !this.showBlockedTooltip;
  }

  openCommissionReceipt(url?: string): void {
    if (!url) {
      this.showToast('No hay comprobante disponible.');
      return;
    }
    window.open(url, '_blank', 'noopener');
  }

  formatLedgerDate(value?: string): string {
    if (!value) {
      return '-';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  closeGoalsModal(): void {
    this.isGoalsModalOpen = false;
    this.isGoalsHighlight = false;
  }

  get pagedAchievedGoals(): DashboardGoal[] {
    const start = this.achievedGoalsPage * this.achievedGoalsPageSize;
    return this.achievedGoals.slice(start, start + this.achievedGoalsPageSize);
  }

  get achievedGoalsTotalPages(): number {
    return Math.max(1, Math.ceil(this.achievedGoals.length / this.achievedGoalsPageSize));
  }

  get canPrevAchievedGoals(): boolean {
    return this.achievedGoalsPage > 0;
  }

  get canNextAchievedGoals(): boolean {
    return this.achievedGoalsPage + 1 < this.achievedGoalsTotalPages;
  }

  nextAchievedGoalsPage(): void {
    if (this.canNextAchievedGoals) {
      this.achievedGoalsPage += 1;
    }
  }

  prevAchievedGoalsPage(): void {
    if (this.canPrevAchievedGoals) {
      this.achievedGoalsPage -= 1;
    }
  }

  isNewAchievedGoal(goal: DashboardGoal): boolean {
    return this.newAchievedGoalKeys.has(goal.key);
  }

  newGoalDelay(goal: DashboardGoal): string {
    if (!this.isNewAchievedGoal(goal) || !this.isGoalsHighlight) {
      return '0ms';
    }
    const order = this.newAchievedGoalOrder.get(goal.key) ?? 0;
    return `${order * 180}ms`;
  }

  openProductDetails(product: DashboardProduct): void {
    this.selectedProduct = product;
    this.isProductDetailsOpen = true;
  }

  closeProductDetails(): void {
    this.isProductDetailsOpen = false;
    this.selectedProduct = null;
  }

  submitCommissionRequest(): void {
    if (this.isCommissionSubmitting || !this.currentUser?.userId) {
      return;
    }
    const clabe = this.commissionClabe.trim();
    if (!clabe && !this.commissionSummary?.clabeOnFile) {
      this.showToast('Ingresa tu CLABE interbancaria.');
      return;
    }
    this.isCommissionSubmitting = true;
    this.api
      .requestCommissionPayout({
        customerId: Number(this.currentUser.userId),
        clabe
      })
      .pipe(
        finalize(() => {
          this.isCommissionSubmitting = false;
        })
      )
      .subscribe({
        next: () => {
          this.showToast('Solicitud enviada. Te contactaremos por el deposito.');
          this.closeCommissionModal();
          this.dashboardControl.load().subscribe(() => this.cdr.markForCheck());
        },
        error: () => {
          this.showToast('No se pudo solicitar el pago.');
        }
      });
  }

  saveCustomerClabe(): void {
    if (this.isClabeSaving || !this.currentUser?.userId || !this.clabePending) {
      return;
    }
    this.isClabeSaving = true;
    this.api
      .saveCustomerClabe({
        customerId: Number(this.currentUser.userId),
        clabe: this.clabePending
      })
      .pipe(
        finalize(() => {
          this.isClabeSaving = false;
        })
      )
      .subscribe({
        next: () => {
          this.showToast('CLABE actualizada.');
          this.closeClabeConfirm();
          this.dashboardControl.load().subscribe(() => this.cdr.markForCheck());
        },
        error: () => {
          this.showToast('No se pudo actualizar la CLABE.');
        }
      });
  }

  onCommissionReceiptSelected(event: Event): void {
    if (!this.currentUser?.userId) {
      return;
    }
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file || this.isCommissionUploading) {
      return;
    }
    this.isCommissionUploading = true;
    this.commissionUploadName = file.name;
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? '');
      const base64 = result.includes(',') ? result.split(',')[1] : result;
      this.api
        .uploadCommissionReceipt({
          customerId: Number(this.currentUser?.userId),
          name: file.name,
          contentBase64: base64,
          contentType: file.type || 'application/octet-stream',
          monthKey: this.commissionSummary?.monthKey
        })
        .pipe(
          finalize(() => {
            this.isCommissionUploading = false;
            if (target) {
              target.value = '';
            }
          })
        )
        .subscribe({
          next: () => {
            this.showToast('Comprobante cargado.');
          },
          error: () => {
            this.showToast('No se pudo subir el comprobante.');
          }
        });
    };
    reader.onerror = () => {
      this.isCommissionUploading = false;
      this.showToast('No se pudo leer el archivo.');
    };
    reader.readAsDataURL(file);
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

  processGoals(goals: any[]): void {
    const available = (goals ?? []).filter((goal) => !goal?.achieved && !goal?.locked);
    this.activeGoal = available[0] ?? null;
    this.secondaryGoals = available.slice(1);
    this.goalToastState = '';
    if (this.activeGoal?.key) {
      const base = this.goalBasePercent(this.activeGoal);
      const cart = this.goalCartPercent(this.activeGoal);
      if (
        this.lastActiveGoalKey !== this.activeGoal.key ||
        this.lastActiveGoalBase !== base ||
        this.lastActiveGoalCart !== cart
      ) {
        this.lastActiveGoalKey = this.activeGoal.key;
        this.lastActiveGoalBase = base;
        this.lastActiveGoalCart = cart;
        this.animateGoalBar(this.activeGoal);
      }
    }
  }

  private loadAchievedGoals(goals: DashboardGoal[]): void {
    if (this.isGuest) {
      this.achievedGoals = [];
      this.isGoalsModalOpen = false;
      return;
    }
    const completed = (goals ?? []).filter((goal) => Boolean(goal?.achieved) && !goal?.locked);

    const monthKey = this.getCurrentMonthKey();
    const stored = this.readAchievedGoalsStorage();
    const storedMonth = stored?.month ?? '';
    const storedKeys = storedMonth === monthKey ? stored?.goals ?? [] : [];

    if (storedMonth && storedMonth !== monthKey) {
      this.clearAchievedGoalsStorage();
    }

    const completedKeys = completed.map((goal) => goal.key).filter((key) => Boolean(key));
    const newKeys = completedKeys.filter((key) => !storedKeys.includes(key));
    this.newAchievedGoalKeys = new Set(newKeys);
    const newGoals = completed.filter((goal) => this.newAchievedGoalKeys.has(goal.key));
    const oldGoals = completed.filter((goal) => !this.newAchievedGoalKeys.has(goal.key));
    this.achievedGoals = [...newGoals, ...oldGoals];
    this.newAchievedGoalOrder = new Map(
      this.achievedGoals
        .filter((goal) => this.newAchievedGoalKeys.has(goal.key))
        .map((goal, index) => [goal.key, index])
    );
    this.achievedGoalsPage = 0;
    this.isGoalsModalOpen = newKeys.length > 0;
    if (newKeys.length > 0) {
      this.triggerGoalsAnimation();
    } else {
      this.isGoalsHighlight = false;
    }

    if (newKeys.length > 0) {
      const merged = Array.from(new Set([...storedKeys, ...newKeys]));
      this.saveAchievedGoalsStorage(monthKey, merged);
    }
  }

  private triggerGoalsAnimation(): void {
    if (this.goalsAnimTimeout) {
      window.clearTimeout(this.goalsAnimTimeout);
    }
    this.isGoalsHighlight = false;
    this.cdr.markForCheck();
    this.goalsAnimTimeout = window.setTimeout(() => {
      this.isGoalsHighlight = true;
      this.cdr.markForCheck();
    }, 80);
  }

  private animateGoalBar(goal: DashboardGoal): void {
    const targetActive = this.goalBasePercent(goal);
    const targetCart = this.goalCartPercent(goal);
    this.isGoalFilling = false;
    this.visualActiveWidth = 0;
    this.visualCartWidth = 0;
    if (this.goalFillTimeout) {
      window.clearTimeout(this.goalFillTimeout);
    }
    this.cdr.markForCheck();
    requestAnimationFrame(() => {
      this.isGoalFilling = true;
      this.cdr.markForCheck();
      requestAnimationFrame(() => {
        this.visualActiveWidth = targetActive;
        this.visualCartWidth = targetCart;
        this.cdr.markForCheck();
        this.goalFillTimeout = window.setTimeout(() => {
          this.isGoalFilling = false;
          this.cdr.markForCheck();
        }, 1100);
      });
    });
  }

  private getCurrentMonthKey(): string {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    return `${now.getFullYear()}-${month}`;
  }

  private readAchievedGoalsStorage(): { month: string; goals: string[] } | null {
    try {
      const raw = localStorage.getItem(this.achievedGoalsStorageKey);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw) as { month?: string; goals?: string[] };
      if (!parsed?.month || !Array.isArray(parsed?.goals)) {
        return null;
      }
      return { month: parsed.month, goals: parsed.goals.filter((key) => typeof key === 'string') };
    } catch {
      return null;
    }
  }

  private saveAchievedGoalsStorage(month: string, goals: string[]): void {
    try {
      localStorage.setItem(this.achievedGoalsStorageKey, JSON.stringify({ month, goals }));
    } catch {
      // ignore storage errors
    }
  }

  private clearAchievedGoalsStorage(): void {
    try {
      localStorage.removeItem(this.achievedGoalsStorageKey);
    } catch {
      // ignore storage errors
    }
  }

  remainingForGoal(goal: any): string {
    if (!goal) {
      return '';
    }
    const target = Number(goal.target ?? 0);
    const base = Number(goal.base ?? 0);
    const remaining = Math.max(0, target - base);
    if (goal.isCountGoal) {
      return `${remaining}`;
    }
    return this.formatMoney(remaining);
  }

  private maybeShowGoalProgressToast(): void {
    if (!this.activeGoal) {
      return;
    }
    const progress = this.goalBasePercent(this.activeGoal);
    if (progress >= 100 && this.goalToastState !== 'done') {
      this.goalToastState = 'done';
      this.showToast('?? Meta alcanzada');
      return;
    }
    if (progress > 90 && this.goalToastState !== 'near') {
      this.goalToastState = 'near';
      this.showToast('?? Estás a punto de lograr tu meta');
    }
  }

  private updateCountdown(): void {
    this.countdownLabel.set(this.dashboardControl.getCountdownLabel());
  }

  private buildAutoCaption(): string {
    const label = this.activeFeatured.label || 'Producto destacado';
    const hook = this.activeFeatured.hook || 'Descubre por qué a todos les funciona.';
    const productCopy = this.getActiveProductCopy(this.socialChannel);
    const cta = `Pídelo aquí: ${this.referralLink}`;
    if (productCopy) {
      return `${productCopy}\n\n${cta}`;
    }
    return `${label}: ${hook}\n\nCómo lo uso: ...\n\n${cta}`;
  }

  private copyImageToClipboard(url: string, toastMessage: string): void {
    if (!url) {
      this.showToast('No hay imagen disponible.');
      return;
    }
    if (!('ClipboardItem' in window) || !navigator.clipboard?.write) {
      this.copyToClipboard(url, 'No se pudo copiar la imagen. Copie la ruta.');
      return;
    }
    fetch(url)
      .then((response) => response.blob())
      .then((blob) => {
        const item = new ClipboardItem({ [blob.type || 'image/png']: blob });
        return navigator.clipboard.write([item]);
      })
      .then(() => this.showToast(toastMessage))
      .catch((error) => {
        this.lastClipboardError = this.formatClipboardError(error);
        console.log('Clipboard image error:', this.lastClipboardError);
        this.showToast('No se pudo copiar la imagen.');
      });
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

  private loadOrders(): void {
    if (!this.currentUser?.userId) {
      return;
    }
    this.isOrdersLoading = true;
    this.api.getOrders(String(this.currentUser.userId)).subscribe({
      next: (orders) => {
        this.orders = orders ?? [];
        this.isOrdersLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isOrdersLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  private copyToClipboard(text: string, toastMessage: string): void {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(() => this.showToast(toastMessage))
        .catch((error) => {
          this.lastClipboardError = this.formatClipboardError(error);
          console.log('Clipboard text error:', this.lastClipboardError);
          this.showToast('No se pudo copiar.');
        });
      return;
    }
    this.showToast('No se pudo copiar.');
  }

  private formatClipboardError(error: unknown): string {
    if (error instanceof Error) {
      return `${error.name}: ${error.message}`;
    }
    try {
      return JSON.stringify(error);
    } catch {
      return String(error);
    }
  }

  private logGoalProgress(): void {
    console.log(
      'Goal progress (%):',
      (this.goals || []).map((goal) => ({
        key: goal.key,
        base: this.goalBasePercent(goal),
        cart: this.goalCartPercent(goal)
      }))
    );
    this.processGoals(this.goals);
    this.cdr.markForCheck();
  }

  private resolveProduct(productId: string): DashboardProduct | null {
    const fromList = this.products.find((product) => product.id === productId);
    if (fromList) {
      return fromList;
    }
    if (this.productOfMonth?.id === productId) {
      return {
        id: this.productOfMonth.id,
        name: this.productOfMonth.name,
        price: this.productOfMonth.price,
        badge: this.productOfMonth.badge || '',
        img: this.productOfMonth.img || ''
      };
    }
    return null;
  }

  private buildCartItem(product: DashboardProduct): CartItem {
    return {
      id: product.id,
      name: product.name,
      price: product.price,
      qty: 0,
      note: product.badge || '',
      img: product.img || ''
    };
  }
}
