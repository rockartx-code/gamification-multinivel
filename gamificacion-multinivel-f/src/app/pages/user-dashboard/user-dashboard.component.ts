import { CommonModule } from '@angular/common';
import { AfterViewInit, ChangeDetectorRef, Component, OnDestroy, OnInit, signal } from '@angular/core';
import { Subscription } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import {
  DashboardGoal,
  DashboardCampaign,
  DashboardProduct,
  FeaturedItem,
  NetworkMember,
  SponsorContact,
  UserDashboardData
} from '../../models/user-dashboard.model';
import { PortalNotification } from '../../models/portal-notification.model';
import { CartItem } from '../../models/cart.model';
import { AdminOrder } from '../../models/admin.model';
import { AuthService, AuthUser } from '../../services/auth.service';
import { ApiService } from '../../services/api.service';
import { CartControlService } from '../../services/cart-control.service';
import { GoalControlService } from '../../services/goal-control.service';
import { UserDashboardControlService } from '../../services/user-dashboard-control.service';
import { UiButtonComponent } from '../../components/ui-button/ui-button.component';
import { UiFormFieldComponent } from '../../components/ui-form-field/ui-form-field.component';
import { UiModalComponent } from '../../components/ui-modal/ui-modal.component';
import { UiTableComponent } from '../../components/ui-table/ui-table.component';
import { UiKpiCardComponent } from '../../components/ui-kpi-card/ui-kpi-card.component';
import { UiHeaderComponent } from '../../components/ui-header/ui-header.component';
import { UiFooterComponent } from '../../components/ui-footer/ui-footer.component';
import { SidebarLink, UiSidebarNavComponent } from '../../components/ui-sidebar-nav/ui-sidebar-nav.component';
import { UiProductCardComponent } from '../../components/ui-product-card/ui-product-card.component';
import { UiStatusBadgeComponent } from '../../components/ui-status-badge/ui-status-badge.component';
import { UiGoalProgressComponent } from '../../components/ui-goal-progress/ui-goal-progress.component';
import { UiDataTableComponent } from '../../components/ui-data-table/ui-data-table.component';
import { UiNetworkGraphComponent } from '../../components/ui-networkgraph/ui-networkgraph.component';
import { BrowserClipboardService } from '../../services/browser/browser-clipboard.service';
import { BrowserDomService } from '../../services/browser/browser-dom.service';
import { BrowserLocationService } from '../../services/browser/browser-location.service';
import { BrowserStorageService } from '../../services/browser/browser-storage.service';
import { BrowserTimerService } from '../../services/browser/browser-timer.service';
import { NotificationService, UiNotificationState } from '../../services/notification.service';
import {
  UserDashboardAchievedGoalsService,
  UserDashboardGoalBarState
} from '../../services/user-dashboard-achieved-goals.service';
import { UserDashboardNotificationsService } from '../../services/user-dashboard-notifications.service';
import {
  UserDashboardGraphLayout,
  UserDashboardNetworkGraphService
} from '../../services/user-dashboard-network-graph.service';
import { UserDashboardReferralService } from '../../services/user-dashboard-referral.service';
import {
  UserDashboardShareService,
  UserDashboardSocialChannel,
  UserDashboardSocialFormat
} from '../../services/user-dashboard-share.service';

@Component({
  selector: 'app-user-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, UiButtonComponent, UiFormFieldComponent, UiModalComponent, UiTableComponent, UiKpiCardComponent, UiHeaderComponent, UiFooterComponent, UiSidebarNavComponent, UiProductCardComponent, UiStatusBadgeComponent, UiGoalProgressComponent, UiDataTableComponent, UiNetworkGraphComponent],
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
    private readonly api: ApiService,
    private readonly cdr: ChangeDetectorRef,
    private readonly clipboard: BrowserClipboardService,
    private readonly dom: BrowserDomService,
    private readonly storage: BrowserStorageService,
    private readonly location: BrowserLocationService,
    private readonly timer: BrowserTimerService,
    private readonly notifications: NotificationService,
    private readonly achievedGoalsCoordinator: UserDashboardAchievedGoalsService,
    private readonly referralContent: UserDashboardReferralService,
    private readonly notificationFlow: UserDashboardNotificationsService,
    private readonly networkGraph: UserDashboardNetworkGraphService,
    private readonly shareContent: UserDashboardShareService
  ) {}

  readonly countdownLabel = signal('');
  activeFeaturedId = '';
  socialFormat: UserDashboardSocialFormat = 'story';
  socialChannel: UserDashboardSocialChannel = 'whatsapp';
  featuredPage = 0;
  readonly featuredPageSize = 4;
  secondaryGoalsVisible = false;
  private readonly toast: UiNotificationState = { message: '', tone: 'info', visible: false };
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
  isNotificationModalOpen = false;
  isNotificationsCenterOpen = false;
  isUserDetailsOpen = false;
  isMobileNavOpen = false;
  isGoalsHighlight = false;
  achievedGoalsPage = 0;
  readonly achievedGoalsPageSize = 3;
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
  showOrdersHelp = false;
  clabeDraft = '';
  clabePending = '';
  isClabeConfirmOpen = false;
  isClabeSaving = false;
  isGoalsModalOpen = false;
  isProductDetailsOpen = false;
  selectedProduct: DashboardProduct | null = null;
  activeNotification: PortalNotification | null = null;
  achievedGoals: DashboardGoal[] = [];
  private goalToastState: 'near' | 'done' | '' = '';

  private countdownInterval?: number;
  private toastTimeout?: number;
  private goalsSub?: Subscription;
  private notificationModalTimeout?: number;
  private dashboardNavLinksCache: SidebarLink[] = [];
  private dashboardNavLinksKey = '';
  private featuredCarouselCache: FeaturedItem[] = [];
  private featuredCarouselProductsRef: DashboardProduct[] | null = null;
  private featuredCarouselFeaturedRef: FeaturedItem[] | null = null;
  private featuredCarouselCampaignsRef: DashboardCampaign[] | null = null;
  private graphLayoutCache: UserDashboardGraphLayout = { nodes: [], links: [] };
  private graphSizeCache = { width: 860, height: 260 };
  private graphMembersRef: NetworkMember[] | null = null;
  private graphRootNameCache = '';
  private notificationQueue: PortalNotification[] = [];

  get toastMessage(): string {
    return this.toast.message || 'Actualizado.';
  }

  get isToastVisible(): boolean {
    return this.toast.visible;
  }


  

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

  get canOpenAdminPanel(): boolean {
    return this.authService.hasAdminAndUserAccess(this.currentUser);
  }

  get dashboardNavLinks(): SidebarLink[] {
    const adminAccess = this.canOpenAdminPanel ? 'admin' : 'no-admin';
    const key = `${this.isGuest ? 'guest' : 'user'}|${this.commissionSummary ? 'with-commissions' : 'no-commissions'}|${adminAccess}`;
    if (key === this.dashboardNavLinksKey) {
      return this.dashboardNavLinksCache;
    }

    const links: SidebarLink[] = [{ id: 'merchant', icon: 'fa-store', label: 'Tienda' }];
    if (!this.isGuest) {
      links.push(
        { id: 'red', icon: 'fa-users', label: 'Red' },
        { id: 'links', icon: 'fa-link', label: 'Links' },
        { id: 'ordenes', icon: 'fa-receipt', label: 'Ordenes' }
      );
      if (this.commissionSummary) {
        links.push({ id: 'comisiones', icon: 'fa-wallet', label: 'Comisiones' });
      }
      if (this.canOpenAdminPanel) {
        links.push({ id: 'admin-panel', icon: 'fa-shield-halved', label: 'Administracion' });
      }
    }

    this.dashboardNavLinksKey = key;
    this.dashboardNavLinksCache = links;
    return this.dashboardNavLinksCache;
  }

  handleDashboardNavSelect(sectionId: string): void {
    if (sectionId === 'admin-panel') {
      void this.router.navigate(['/admin']);
      this.closeMobileNav();
      return;
    }
    this.scrollToSection(sectionId);
    this.closeMobileNav();
  }

  openAdminPanel(): void {
    this.isUserDetailsOpen = false;
    this.closeMobileNav();
    void this.router.navigate(['/admin']);
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

  get campaigns(): DashboardCampaign[] {
    return this.dashboardControl.campaigns;
  }

  get featuredCarousel(): FeaturedItem[] {
    const featured = this.featured;
    const products = this.products;
    const campaigns = this.campaigns;
    if (
      this.featuredCarouselFeaturedRef === featured &&
      this.featuredCarouselProductsRef === products &&
      this.featuredCarouselCampaignsRef === campaigns
    ) {
      return this.featuredCarouselCache;
    }

    this.featuredCarouselFeaturedRef = featured;
    this.featuredCarouselProductsRef = products;
    this.featuredCarouselCampaignsRef = campaigns;
    this.featuredCarouselCache = this.shareContent.buildFeaturedCarousel(featured, products, campaigns);
    return this.featuredCarouselCache;
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

  get currentNotifications(): PortalNotification[] {
    return this.dashboardControl.notifications;
  }

  get hasCurrentNotifications(): boolean {
    return this.currentNotifications.length > 0;
  }

  get unreadNotificationsCount(): number {
    return this.currentNotifications.filter((notification) => !notification.isRead).length;
  }

  get sponsor(): SponsorContact | null {
    return this.dashboardControl.data?.sponsor ?? null;
  }

  get sponsorEmailHref(): string {
    return this.referralContent.getSponsorEmailHref(this.sponsor);
  }

  get sponsorWhatsappHref(): string {
    return this.referralContent.getSponsorWhatsappHref(this.sponsor);
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

  get hasBuyAgainProducts(): boolean {
    return this.buyAgainProducts.length > 0;
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
    return this.referralContent.buildReferralLink({
      isGuest: this.isGuest,
      userCode: this.dashboardControl.data?.settings.userCode,
      activeFeaturedId: this.activeFeatured.id,
      origin: this.location.origin
    });
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
    return this.shareContent.getSocialFormatLabel(this.socialFormat);
  }

  get socialAspectRatio(): string {
    return this.shareContent.getSocialAspectRatio(this.socialFormat);
  }

  get activeSocialAsset(): string {
    return this.shareContent.getActiveSocialAsset(this.socialFormat, this.activeFeatured);
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
      return 'badge badge-inactive';
    }
    const pct = this.discountPercentValue;
    if (pct >= 50) {
      return 'badge badge-pending';
    }
    return 'badge badge-active';
  }

  medalBadgeClass(): string {
    const level = (this.userLevel || '').toLowerCase();
    if (level.includes('oro') || level.includes('gold')) {
      return 'badge badge-pending';
    }
    if (level.includes('plata') || level.includes('silver')) {
      return 'badge badge-active';
    }
    return 'badge badge-inactive';
  }

  toggleUserDetails(): void {
    this.isUserDetailsOpen = !this.isUserDetailsOpen;
  }

  closeNotificationModal(): void {
    const modalState = this.notificationFlow.closeModal(this.notificationQueue);
    this.isNotificationModalOpen = modalState.isNotificationModalOpen;
    this.activeNotification = modalState.activeNotification;
    this.isNotificationsCenterOpen = modalState.isNotificationsCenterOpen;
    this.timer.clearTimeout(this.notificationModalTimeout);
    if (modalState.shouldOpenNext) {
      this.notificationModalTimeout = this.timer.setTimeout(() => this.openNextNotification(), 0);
    }
  }

  openNotificationsCenter(): void {
    if (!this.hasCurrentNotifications) {
      return;
    }
    this.isNotificationsCenterOpen = true;
  }

  closeNotificationsCenter(): void {
    this.isNotificationsCenterOpen = false;
  }

  openNotification(notification: PortalNotification): void {
    const modalState = this.notificationFlow.openNotification(notification);
    this.isNotificationsCenterOpen = modalState.isNotificationsCenterOpen;
    this.activeNotification = modalState.activeNotification;
    this.isNotificationModalOpen = modalState.isNotificationModalOpen;
    if (modalState.shouldMarkAsRead && notification) {
      this.markNotificationAsRead(notification);
    }
  }

  openNotificationLink(url?: string): void {
    if (!url) {
      return;
    }
    this.location.open(url, '_blank', 'noopener');
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
      case 'focus':
        return 'kpi-good';
      case 'urgent':
        return 'kpi-warn';
      case 'critical':
      default:
        return 'kpi-warn';
    }
  }


  get graphLayout(): UserDashboardGraphLayout {
    const members = this.networkMembers;
    const rootName = this.currentUser?.name || 'Tu';
    if (this.graphMembersRef === members && this.graphRootNameCache === rootName) {
      return this.graphLayoutCache;
    }

    const graphSnapshot = this.networkGraph.buildSnapshot(members, rootName);

    this.graphMembersRef = members;
    this.graphRootNameCache = rootName;
    this.graphLayoutCache = graphSnapshot.layout;
    this.graphSizeCache = graphSnapshot.size;
    return this.graphLayoutCache;
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
    this.graphLayout;
    return this.graphSizeCache;
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
        this.cdr.markForCheck();
      }
    });
    this.goalControl
      .load()
      .pipe(
        finalize(() => {
          this.isLoading = false;
          this.updateCountdown();
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (data) => {
          this.processGoals(data?.goals ?? []);
          this.loadAchievedGoals(data?.goals ?? []);
          this.prepareNotifications(data?.notifications ?? []);
          if (!this.activeFeaturedId) {
            const nextFeaturedId = this.featuredCarousel[0]?.id ?? data?.featured?.[0]?.id ?? this.featured[0]?.id ?? '';
            if (nextFeaturedId) {
              this.setFeatured(nextFeaturedId);
            }
          }
          this.featuredPage = 0;
          this.loadOrders();
          this.cdr.markForCheck();
        },
        error: () => {
          this.showToast('No se pudo cargar el dashboard.');
          this.cdr.markForCheck();
        }
      });
    this.countdownInterval = this.timer.setInterval(() => this.updateCountdown(), 1000);
  }

  ngAfterViewInit(): void {
    if (!this.activeGoal?.key) {
      return;
    }
    this.timer.setTimeout(() => {
      const node = this.dom.getElementById(`goal-${this.activeGoal.key}`);
      this.dom.scrollIntoView(node, { behavior: 'smooth', block: 'center' });
    }, 0);
  }

  ngOnDestroy(): void {
    if (this.countdownInterval) {
      this.timer.clearInterval(this.countdownInterval);
    }
    if (this.toastTimeout) {
      this.timer.clearTimeout(this.toastTimeout);
    }
    if (this.goalsAnimTimeout) {
      this.timer.clearTimeout(this.goalsAnimTimeout);
    }
    if (this.goalFillTimeout) {
      this.timer.clearTimeout(this.goalFillTimeout);
    }
    if (this.notificationModalTimeout) {
      this.timer.clearTimeout(this.notificationModalTimeout);
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
    this.storage.setJson('cart-items', items);
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
      referralToken: this.storage.getItem('leaderId') || undefined
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
          this.location.reload();
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

  setSocialFormat(format: UserDashboardSocialFormat): void {
    this.socialFormat = format;
  }

  // Color del icono del usuario: gris inactivo, azul activo.
  levelIconClass(): string {
    if (!this.isClient || !this.discountActiveValue) {
      return 'icon-status-inactive';
    }
    return 'icon-status-active';
  }

  // Borde / anillo principal: estado + nivel.
  discountRingClass(): string {
    if (!this.isClient || !this.discountActiveValue) {
      return 'ring ring-status-inactive level-5';
    }
    return `ring ring-status-active ${this.discountLevelClass()}`;
  }

  discountBadgeMiniClass(): string {
    if (!this.isClient || !this.discountActiveValue) {
      return 'badge badge-compact status-inactive';
    }
    return `badge badge-compact status-active ${this.discountLevelClass()}`;
  }

  private discountPercentNumber(): number {
    const raw = (this.discountPercent ?? '').toString().trim();
    const n = Number(raw.replace('%', ''));
    return Number.isFinite(n) ? n : 0;
  }

  private discountLevelNumber(): number {
    const pct = this.discountPercentNumber();
    if (pct >= 50) {
      return 1;
    }
    if (pct >= 40) {
      return 2;
    }
    if (pct >= 30) {
      return 3;
    }
    if (pct >= 20) {
      return 4;
    }
    return 5;
  }

  discountLevelClass(): string {
    return `level-${this.discountLevelNumber()}`;
  }

  commissionLedgerStatusClass(status?: string): string {
    const normalized = String(status || '').toLowerCase();
    if (normalized.includes('paid') || normalized.includes('pagad') || normalized.includes('entregad')) {
      return 'badge badge-compact level-1 status-active';
    }
    if (normalized.includes('confirm')) {
      return 'badge badge-compact level-2 status-active';
    }
    if (normalized.includes('pending') || normalized.includes('pendient')) {
      return 'badge badge-compact level-3';
    }
    if (normalized.includes('block') || normalized.includes('bloque')) {
      return 'badge badge-compact level-5 status-inactive';
    }
    return 'badge badge-compact level-4';
  }

  commissionPrevStatusClass(status?: string): string {
    if (status === 'paid') {
      return 'badge badge-compact level-1 status-active';
    }
    if (status === 'pending') {
      return 'badge badge-compact level-3';
    }
    return 'badge badge-compact level-5 status-inactive';
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

  setChannel(channel: UserDashboardSocialChannel): void {
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

  generateTemplate(channel: UserDashboardSocialChannel = this.socialChannel): void {
    this.captionText = this.shareContent.buildChannelTemplate({
      channel,
      activeFeatured: this.activeFeatured,
      referralLink: this.referralLink,
      products: this.products
    });
    this.showToast('Template generado.');
    this.lastAutoCaption = true;
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
    this.location.open(this.referralLink, '_blank', 'noopener');
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

  toggleOrdersHelp(): void {
    this.showOrdersHelp = !this.showOrdersHelp;
  }

  openCommissionReceipt(url?: string): void {
    if (!url) {
      this.showToast('No hay comprobante disponible.');
      return;
    }
    this.location.open(url, '_blank', 'noopener');
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
    return this.achievedGoalsCoordinator.newGoalDelay(
      goal,
      this.newAchievedGoalKeys,
      this.newAchievedGoalOrder,
      this.isGoalsHighlight
    );
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
          this.dashboardControl.load().subscribe();
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
          this.dashboardControl.load().subscribe();
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
    const node = this.dom.getElementById(goalId);
    if (!node) {
      return;
    }
    this.dom.scrollIntoView(node, { behavior: 'smooth', block: 'center' });
    node.classList.add('ring-2', 'ring-yellow-400/60');
    this.timer.setTimeout(() => node.classList.remove('ring-2', 'ring-yellow-400/60'), 1200);
  }

  scrollToSection(sectionId: string): void {
    const node = this.dom.getElementById(sectionId);
    if (!node) {
      return;
    }
    this.dom.scrollIntoView(node, { behavior: 'smooth', block: 'start' });
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
    const state = this.achievedGoalsCoordinator.resolveState(goals, this.isGuest);
    this.achievedGoals = state.achievedGoals;
    this.newAchievedGoalKeys = state.newGoalKeys;
    this.newAchievedGoalOrder = state.newGoalOrder;
    this.achievedGoalsPage = state.achievedGoalsPage;
    this.isGoalsModalOpen = state.isGoalsModalOpen;
    this.isGoalsHighlight = state.isGoalsHighlight;
    if (state.shouldAnimateHighlight) {
      this.triggerGoalsAnimation();
    }
  }

  private triggerGoalsAnimation(): void {
    this.goalsAnimTimeout = this.achievedGoalsCoordinator.scheduleHighlight(this.goalsAnimTimeout, (value) => {
      this.isGoalsHighlight = value;
    });
  }

  private animateGoalBar(goal: DashboardGoal): void {
    this.goalFillTimeout = this.achievedGoalsCoordinator.animateGoalBar(
      goal,
      this.goalFillTimeout,
      (currentGoal) => this.goalBasePercent(currentGoal),
      (currentGoal) => this.goalCartPercent(currentGoal),
      (state: UserDashboardGoalBarState) => {
        this.isGoalFilling = state.isGoalFilling;
        this.visualActiveWidth = state.visualActiveWidth;
        this.visualCartWidth = state.visualCartWidth;
      }
    );
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

  private prepareNotifications(notifications: PortalNotification[]): void {
    this.notificationQueue = this.notificationFlow.prepareQueue(notifications, this.isGuest);
    if (!this.isNotificationModalOpen && this.notificationQueue.length) {
      this.openNextNotification();
      return;
    }
    if (!this.notificationQueue.length) {
      this.activeNotification = null;
      this.isNotificationModalOpen = false;
    }
  }

  private openNextNotification(): void {
    const queueState = this.notificationFlow.takeNext(this.notificationQueue);
    this.notificationQueue = queueState.queue;
    if (!queueState.activeNotification) {
      this.activeNotification = null;
      this.isNotificationModalOpen = queueState.isNotificationModalOpen;
      return;
    }
    this.openNotification(queueState.activeNotification);
  }

  private markNotificationAsRead(notification: PortalNotification): void {
    if (!notification?.id || !this.currentUser?.userId) {
      return;
    }
    this.dashboardControl.markNotificationRead(notification.id).subscribe({
      error: () => {
        this.showToast('No se pudo registrar la lectura del aviso.');
      }
    });
  }

  private buildAutoCaption(): string {
    return this.shareContent.buildAutoCaption({
      channel: this.socialChannel,
      activeFeatured: this.activeFeatured,
      referralLink: this.referralLink,
      products: this.products
    });
  }

  private copyImageToClipboard(url: string, toastMessage: string): void {
    if (!url) {
      this.showToast('No hay imagen disponible.');
      return;
    }
    if (typeof ClipboardItem === 'undefined' || !this.clipboard.canWrite) {
      this.copyToClipboard(url, 'No se pudo copiar la imagen. Copie la ruta.');
      return;
    }
    fetch(url)
      .then((response) => response.blob())
      .then((blob) => {
        const item = new ClipboardItem({ [blob.type || 'image/png']: blob });
        return this.clipboard.write([item]);
      })
      .then(() => this.showToast(toastMessage))
      .catch((error) => {
        this.lastClipboardError = this.formatClipboardError(error);
        console.log('Clipboard image error:', this.lastClipboardError);
        this.showToast('No se pudo copiar la imagen.');
      });
  }

  private showToast(message: string): void {
    this.toastTimeout = this.notifications.showFor(this.toast, message, 2200, this.toastTimeout);
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
    if (!this.clipboard.canWriteText) {
      this.showToast('No se pudo copiar.');
      return;
    }
    this.clipboard
      .writeText(text)
      .then(() => this.showToast(toastMessage))
      .catch((error) => {
        this.lastClipboardError = this.formatClipboardError(error);
        console.log('Clipboard text error:', this.lastClipboardError);
        this.showToast('No se pudo copiar.');
      });
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



