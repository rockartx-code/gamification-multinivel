import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnDestroy,
  Output,
  ViewChild
} from '@angular/core';

export type UiNetworkGraphNode = {
  id: string;
  x: number;
  y: number;
  label: string;
  name?: string;
  level?: 'root' | 'L1' | 'L2' | 'L3' | string;
  status?: string;
  role?: string;
  meta?: Record<string, any>;
};

export type UiNetworkGraphLink = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

type RenderLink = UiNetworkGraphLink & {
  parentId?: string;
  childId?: string;
};

type TooltipState = {
  node: UiNetworkGraphNode;
  leftPct: number;
  topPct: number;
};

type SvgPoint = {
  x: number;
  y: number;
};

type NodePlateBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type TreeData = {
  roots: string[];
  parentById: Map<string, string | null>;
  childrenByParent: Map<string, string[]>;
};

type PortraitLayout = {
  nodes: UiNetworkGraphNode[];
  links: RenderLink[];
  width: number;
  height: number;
};

@Component({
  selector: 'ui-networkgraph',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ui-networkgraph.component.html',
  styleUrl: './ui-networkgraph.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UiNetworkGraphComponent implements AfterViewInit, OnDestroy {
  @ViewChild('graphHost') graphHost?: ElementRef<HTMLElement>;
  @ViewChild('svgEl') svgEl?: ElementRef<SVGSVGElement>;

  @Input({ required: true }) nodes: UiNetworkGraphNode[] = [];
  @Input({ required: true }) links: UiNetworkGraphLink[] = [];
  @Input() viewBoxWidth?: number;
  @Input() viewBoxHeight?: number;
  @Input() heightPx?: number | null;
  @Input() linkStyle: 'curved' | 'straight' = 'curved';
  @Input() labelMode: 'initials' | 'short' | 'full' = 'short';
  @Input() interactive = true;
  @Input() selectedNodeId: string | null = null;
  @Input() showLegend = false;
  @Input() emptyStateText = 'Sin datos para mostrar';
  @Input() spendMax?: number | null;
  @Input() showSpend = true;
  @Input() showStatusDot = true;
  @Input() portraitTree: boolean | 'auto' = 'auto';
  @Input() portraitBreakpoint = 860;

  @Output() readonly nodeClick = new EventEmitter<UiNetworkGraphNode>();
  @Output() readonly nodeHover = new EventEmitter<UiNetworkGraphNode | null>();

  hoveredNodeId: string | null = null;
  tooltip: TooltipState | null = null;
  zoomedNodeId: string | null = null;
  private hoverAnchor: SvgPoint | null = null;
  private isViewportAnimating = false;
  private pendingHoverClear = false;

  private viewportWidth = typeof window !== 'undefined' ? window.innerWidth : 1024;
  private viewportIsPortrait = typeof window !== 'undefined'
    ? window.matchMedia('(orientation: portrait)').matches
    : false;

  private containerWidth = 0;
  private containerHeight = 0;
  private resizeObserver?: ResizeObserver;
  private svgScaleMeet = 1;

  private portraitLayoutCache: {
    nodesRef: UiNetworkGraphNode[];
    linksRef: UiNetworkGraphLink[];
    width: number;
    height: number;
    layout: PortraitLayout;
  } | null = null;

  ngAfterViewInit(): void {
    if (typeof ResizeObserver === 'undefined' || !this.graphHost?.nativeElement) {
      return;
    }
    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === this.graphHost?.nativeElement) {
          this.containerWidth = entry.contentRect.width;
          this.containerHeight = entry.contentRect.height;
          this.portraitLayoutCache = null;
        }
      }
      this.updateSvgMeetScale();
    });
    this.resizeObserver.observe(this.graphHost.nativeElement);
    if (this.svgEl?.nativeElement) {
      this.resizeObserver.observe(this.svgEl.nativeElement);
    }
    this.updateSvgMeetScale();
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
  }

  @HostListener('window:resize')
  onViewportResize(): void {
    if (typeof window === 'undefined') {
      return;
    }
    this.viewportWidth = window.innerWidth;
    this.viewportIsPortrait = window.matchMedia('(orientation: portrait)').matches;
    this.portraitLayoutCache = null;
    this.updateSvgMeetScale();
  }

  get isPortrait(): boolean {
    return this.isPortraitTreeActive;
  }

  get preserveAspect(): string {
    return this.isPortrait ? 'xMinYMin meet' : 'xMidYMid meet';
  }

  get viewportTransform(): string {
    const nodeId = this.zoomedNodeId ?? this.hoveredNodeId;
    if (!nodeId) {
      return '';
    }
    const target = this.renderNodes.find((node) => node.id === nodeId);
    if (!target) {
      return '';
    }
    const scale = this.zoomedNodeId ? this.zoomScale : this.hoverZoomScale;
    if (!this.zoomedNodeId) {
      const anchor = this.hoverAnchor ?? { x: this.computedViewBoxWidth / 2, y: this.computedViewBoxHeight / 2 };
      const tx = anchor.x - target.x * scale;
      const ty = anchor.y - target.y * scale;
      return `translate(${tx} ${ty}) scale(${scale})`;
    }
    const tx = this.computedViewBoxWidth / 2 - target.x * scale;
    const ty = this.computedViewBoxHeight / 2 - target.y * scale;
    return `translate(${tx} ${ty}) scale(${scale})`;
  }

  get zoomScale(): number {
    if (!this.zoomedNodeId) {
      return 1;
    }
    return this.isPortrait ? 1.28 : 1.36;
  }

  get hoverZoomScale(): number {
    const clickScale = this.isPortrait ? 1.28 : 1.36;
    return 1 + (clickScale - 1) * 0.5;
  }

  get computedViewBoxWidth(): number {
    if (!this.isPortrait) {
      if (this.viewBoxWidth && this.viewBoxWidth > 0) {
        return this.viewBoxWidth;
      }
      return this.estimateGraphSize().width;
    }
    return this.getPortraitLayout().width;
  }

  get computedViewBoxHeight(): number {
    if (!this.isPortrait) {
      if (this.viewBoxHeight && this.viewBoxHeight > 0) {
        return this.viewBoxHeight;
      }
      return this.estimateGraphSize().height;
    }
    return this.getPortraitLayout().height;
  }

  get computedHeightPx(): number {
    if (this.isPortrait) {
      return this.computedViewBoxHeight;
    }
    if (this.heightPx != null && this.heightPx > 0) {
      return this.heightPx;
    }
    if (this.viewBoxHeight && this.viewBoxHeight > 0) {
      return this.viewBoxHeight;
    }
    return this.estimateGraphSize().height;
  }

  get hasData(): boolean {
    return this.nodes.length > 0;
  }

  get activeNodeId(): string | null {
    return this.hoveredNodeId ?? this.selectedNodeId;
  }

  get renderNodes(): UiNetworkGraphNode[] {
    return this.isPortrait ? this.getPortraitLayout().nodes : this.nodes;
  }

  get renderLinks(): RenderLink[] {
    return this.isPortrait ? this.getPortraitLayout().links : this.links;
  }

  get resolvedSpendMax(): number {
    if (this.spendMax != null && this.spendMax > 0) {
      return this.spendMax;
    }
    const derivedMax = this.nodes.reduce((max, node) => Math.max(max, this.spendValue(node)), 0);
    return Math.max(derivedMax, 1);
  }

  get ariaLabel(): string {
    const total = this.nodes.length;
    const links = this.links.length;
    return `Grafo de red con ${total} nodos y ${links} enlaces`;
  }

  curvePath(link: UiNetworkGraphLink, offset = 0): string {
    const midX = (link.x1 + link.x2) / 2;
    const midY = (link.y1 + link.y2) / 2 + offset;
    return `M ${link.x1} ${link.y1} Q ${midX} ${midY}, ${link.x2} ${link.y2}`;
  }

  portraitLinkPath(link: UiNetworkGraphLink): string {
    const startX = link.x1 + 10;
    const endX = link.x2 - 10;
    if (endX <= startX) {
      return this.curvePath(link, 0);
    }
    const elbowX = startX + Math.max(12, (endX - startX) * 0.45);
    return `M ${startX} ${link.y1} H ${elbowX} V ${link.y2} H ${endX}`;
  }

  nodeRadius(node: UiNetworkGraphNode): number {
    const baseRadius = this.baseNodeRadius(node);
    if (this.hoveredNodeId === node.id && this.nodeRole(node) !== 'root') {
      return Math.max(baseRadius, this.baseNodeRadius({ ...node, level: 'root', role: 'root' }));
    }
    return baseRadius;
  }

  private baseNodeRadius(node: UiNetworkGraphNode): number {
    const customRadius = Number(node.meta?.['radius']);
    if (Number.isFinite(customRadius) && customRadius > 0) {
      return customRadius;
    }

    const role = this.nodeRole(node);
    if (role === 'root') {
      return 25;
    }
    if (role === 'L1') {
      return 17;
    }
    if (role === 'L2') {
      return 14;
    }
    return 12;
  }

  nodeFill(node: UiNetworkGraphNode): string {
    if (this.isInactive(node.status)) {
      return 'rgba(var(--rgb-text), 0.24)';
    }

    const role = this.nodeRole(node);
    if (role === 'root') {
      return 'var(--ng-root)';
    }
    if (role === 'L1') {
      return 'var(--ng-l1)';
    }
    if (role === 'L2') {
      return 'var(--ng-l2)';
    }
    return 'var(--ng-l3)';
  }

  nodeStroke(node: UiNetworkGraphNode): string {
    if (this.isInactive(node.status)) {
      return 'rgba(var(--rgb-text), 0.28)';
    }
    if (this.nodeRole(node) === 'root') {
      return 'rgba(var(--rgb-primary), 0.62)';
    }
    return 'rgba(var(--rgb-surface-1), 0.95)';
  }

  ringRadius(node: UiNetworkGraphNode): number {
    return this.nodeRadius(node) + 7;
  }

  ringCircumference(node: UiNetworkGraphNode): number {
    return 2 * Math.PI * this.ringRadius(node);
  }

  ringDashoffset(node: UiNetworkGraphNode): number {
    const circumference = this.ringCircumference(node);
    const ratio = this.spendRatio(node);
    return circumference * (1 - ratio);
  }

  ringTransform(node: UiNetworkGraphNode): string {
    return `rotate(-90 ${node.x} ${node.y})`;
  }

  spendValue(node: UiNetworkGraphNode): number {
    const raw = Number(node.meta?.['spend'] ?? 0);
    return Number.isFinite(raw) && raw > 0 ? raw : 0;
  }

  spendRatio(node: UiNetworkGraphNode): number {
    const max = this.resolvedSpendMax;
    if (max <= 0) {
      return 0;
    }
    return this.clamp(this.spendValue(node) / max, 0, 1);
  }

  compactMoney(value: number): string {
    const amount = Number.isFinite(value) ? Math.max(0, value) : 0;
    if (amount < 1000) {
      return `$${Math.round(amount)}`;
    }
    if (amount < 1_000_000) {
      return `$${Math.floor(amount / 1000)}K`;
    }
    const m = Math.floor(amount / 100_000) / 10;
    return `$${this.trimZeros(m.toFixed(1))}M`;
  }

  nodeBadge(node: UiNetworkGraphNode): string {
    const source = (node.name || node.label || '').trim();
    if (!source) {
      return 'ID';
    }
    const words = source.split(/\s+/).filter(Boolean);
    if (words.length >= 2) {
      return `${words[0][0] ?? ''}${words[1][0] ?? ''}`.toUpperCase();
    }
    return source.slice(0, 2).toUpperCase();
  }

  nodeDisplayName(node: UiNetworkGraphNode): string {
    return (node.name || node.label || 'Sin nombre').trim();
  }

  nodeAlwaysLabel(node: UiNetworkGraphNode): string {
    const value = `${this.compactNodeName(node)} | ${this.compactMoney(this.spendValue(node))}`;
    return value.length > 28 ? `${value.slice(0, 27)}...` : value;
  }

  nodeAriaLabel(node: UiNetworkGraphNode): string {
    const title = this.nodeDisplayName(node);
    const role = node.role || node.level || 'Sin nivel';
    const status = node.status || (this.isInactive(node.status) ? 'Inactiva' : 'Activa');
    const spend = this.compactMoney(this.spendValue(node));
    return `${title}, nivel ${role}, estado ${status}, consumo ${spend}`;
  }

  nodePlateBox(node: UiNetworkGraphNode): NodePlateBox {
    const width = this.nodeRole(node) === 'root' ? 170 : 150;
    const height = 64;
    const radius = this.nodeRadius(node);
    const air = 18 + this.clamp((this.invSvgScale - 1) * 14, 0, 20);
    const minX = 4;
    const minY = 4;
    const maxX = this.computedViewBoxWidth - width - 4;
    const maxY = this.computedViewBoxHeight - height - 4;

    const below = {
      x: this.clamp(node.x - width / 2, minX, maxX),
      y: this.clamp(node.y + radius + air, minY, maxY),
      width,
      height
    };
    if (!this.boxOverlapsNode(below, node.x, node.y, radius)) {
      return below;
    }

    const above = {
      x: this.clamp(node.x - width / 2, minX, maxX),
      y: this.clamp(node.y - radius - height - air, minY, maxY),
      width,
      height
    };
    if (!this.boxOverlapsNode(above, node.x, node.y, radius)) {
      return above;
    }

    const right = {
      x: this.clamp(node.x + radius + air, minX, maxX),
      y: this.clamp(node.y - height / 2, minY, maxY),
      width,
      height
    };
    if (!this.boxOverlapsNode(right, node.x, node.y, radius)) {
      return right;
    }

    const left = {
      x: this.clamp(node.x - radius - air - width, minX, maxX),
      y: this.clamp(node.y - height / 2, minY, maxY),
      width,
      height
    };
    return left;
  }

  get invSvgScale(): number {
    const s = this.svgScaleMeetSafe;
    return this.clamp(1 / s, 0.7, 1.8);
  }

  get plateInverseCssScale(): string {
    return `scale(${this.invSvgScale})`;
  }

  compactNodeName(node: UiNetworkGraphNode): string {
    const fullName = this.nodeDisplayName(node);
    const parts = fullName.split(/\s+/).filter(Boolean);
    if (!parts.length) {
      return 'Sin n';
    }
    if (parts.length === 1) {
      return parts[0].slice(0, 5);
    }
    const first = parts[0].slice(0, 5);
    const restInitials = parts
      .slice(1)
      .map((part) => `${part[0]?.toUpperCase() ?? ''}.`)
      .join(' ');
    return restInitials ? `${first} ${restInitials}` : first;
  }

  shouldShowPlate(node: UiNetworkGraphNode): boolean {
    return this.hoveredNodeId === node.id || this.selectedNodeId === node.id || this.zoomedNodeId === node.id;
  }

  isNodeConnected(node: UiNetworkGraphNode): boolean {
    const current = this.activeNodeId;
    if (!current) {
      return false;
    }
    return node.id === current || this.renderLinks.some((link) => this.isLinkConnected(link, current) && this.linkTouchesNode(link, node));
  }

  isLinkConnected(link: UiNetworkGraphLink, nodeId: string | null): boolean {
    if (!nodeId) {
      return false;
    }
    const activeNode = this.renderNodes.find((node) => node.id === nodeId);
    if (!activeNode) {
      return false;
    }
    return this.isSamePoint(activeNode.x, activeNode.y, link.x1, link.y1) || this.isSamePoint(activeNode.x, activeNode.y, link.x2, link.y2);
  }

  onNodeMouseEnter(event: MouseEvent, node: UiNetworkGraphNode): void {
    if (!this.interactive) {
      return;
    }
    this.pendingHoverClear = false;
    this.hoveredNodeId = node.id;
    this.hoverAnchor = this.clientToSvgPoint(event.clientX, event.clientY);
    this.tooltip = {
      node,
      leftPct: this.toPct(node.x, this.computedViewBoxWidth),
      topPct: this.toPct(node.y, this.computedViewBoxHeight)
    };
    this.nodeHover.emit(node);
  }

  onNodeMouseMove(event: MouseEvent): void {
    if (!this.interactive || !this.hoveredNodeId || this.zoomedNodeId) {
      return;
    }
    this.hoverAnchor = this.clientToSvgPoint(event.clientX, event.clientY);
  }

  onNodeMouseLeave(node: UiNetworkGraphNode): void {
    if (!this.interactive || this.hoveredNodeId !== node.id) {
      return;
    }
    if (this.isViewportAnimating && !this.zoomedNodeId) {
      this.pendingHoverClear = true;
      return;
    }
    this.clearHoverState();
  }

  onViewportTransitionStart(): void {
    this.isViewportAnimating = true;
  }

  onViewportTransitionEnd(): void {
    this.isViewportAnimating = false;
    if (this.pendingHoverClear && !this.zoomedNodeId) {
      this.clearHoverState();
    }
    this.pendingHoverClear = false;
  }

  private clearHoverState(): void {
    this.hoveredNodeId = null;
    this.hoverAnchor = null;
    this.tooltip = null;
    this.nodeHover.emit(null);
  }

  onNodeFocus(node: UiNetworkGraphNode): void {
    if (!this.interactive) {
      return;
    }
    this.hoveredNodeId = node.id;
    this.tooltip = {
      node,
      leftPct: this.toPct(node.x, this.computedViewBoxWidth),
      topPct: this.toPct(node.y, this.computedViewBoxHeight)
    };
    this.nodeHover.emit(node);
  }

  onNodeBlur(node: UiNetworkGraphNode): void {
    if (!this.interactive || this.hoveredNodeId !== node.id) {
      return;
    }
    this.hoveredNodeId = null;
    this.tooltip = null;
    this.nodeHover.emit(null);
  }

  onNodeClick(event: MouseEvent, node: UiNetworkGraphNode): void {
    if (!this.interactive) {
      return;
    }
    event.stopPropagation();
    
  (event.currentTarget as HTMLElement)?.blur?.();
    this.zoomedNodeId = this.zoomedNodeId === node.id ? null : node.id;
    this.nodeClick.emit(node);
  }

  onNodeKeydown(event: KeyboardEvent, node: UiNetworkGraphNode): void {
    if (!this.interactive) {
      return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      this.zoomedNodeId = this.zoomedNodeId === node.id ? null : node.id;
      this.nodeClick.emit(node);
    }
  }

  closeNodePlate(event: MouseEvent): void {
    event.stopPropagation();
    this.zoomedNodeId = null;
  }

  onCanvasClick(): void {
    if (!this.zoomedNodeId) {
      return;
    }
    this.zoomedNodeId = null;
  }

  trackNode(_: number, node: UiNetworkGraphNode): string {
    return node.id;
  }

  trackLink(index: number): number {
    return index;
  }

  nodeRole(node: UiNetworkGraphNode): string {
    const value = (node.level || node.role || '').toUpperCase();
    if (value === 'ROOT') {
      return 'root';
    }
    if (value === 'L1' || value === 'L2' || value === 'L3') {
      return value;
    }
    return 'L3';
  }

  isInactive(status?: string): boolean {
    if (!status) {
      return false;
    }
    return status.trim().toLowerCase().includes('inactiv');
  }

  buildTree(nodes: UiNetworkGraphNode[], links: UiNetworkGraphLink[]): TreeData {
    const nodeById = new Map(nodes.map((node) => [node.id, node]));
    const parentById = new Map<string, string | null>();
    const childrenSets = new Map<string, Set<string>>();

    for (const node of nodes) {
      parentById.set(node.id, null);
      childrenSets.set(node.id, new Set<string>());
    }

    for (const node of nodes) {
      const parentIdRaw = node.meta?.['parentId'];
      const parentId = typeof parentIdRaw === 'string' ? parentIdRaw : String(parentIdRaw ?? '');
      if (parentId && nodeById.has(parentId) && parentId !== node.id) {
        parentById.set(node.id, parentId);
        childrenSets.get(parentId)?.add(node.id);
      }
    }

    for (const link of links) {
      const parentId = this.findNodeIdByPoint(nodes, link.x1, link.y1);
      const childId = this.findNodeIdByPoint(nodes, link.x2, link.y2);
      if (!parentId || !childId || parentId === childId) {
        continue;
      }
      if (parentById.get(childId)) {
        continue;
      }
      parentById.set(childId, parentId);
      childrenSets.get(parentId)?.add(childId);
    }

    const rootsByRole = nodes
      .filter((node) => this.nodeRole(node) === 'root')
      .map((node) => node.id);
    const rootsByParent = nodes
      .filter((node) => !parentById.get(node.id))
      .map((node) => node.id);

    const roots = rootsByRole.length
      ? rootsByRole
      : rootsByParent.length
        ? rootsByParent
        : nodes[0]
          ? [nodes[0].id]
          : [];

    const childrenByParent = new Map<string, string[]>();
    for (const [id, children] of childrenSets.entries()) {
      const ordered = [...children].sort((a, b) => {
        const na = nodeById.get(a);
        const nb = nodeById.get(b);
        return (na?.x ?? 0) - (nb?.x ?? 0);
      });
      childrenByParent.set(id, ordered);
    }

    return { roots, parentById, childrenByParent };
  }

  computeDepths(roots: string[], childrenByParent: Map<string, string[]>): Map<string, number> {
    const depths = new Map<string, number>();
    const queue: Array<{ id: string; depth: number }> = roots.map((id) => ({ id, depth: 0 }));

    while (queue.length) {
      const current = queue.shift();
      if (!current || depths.has(current.id)) {
        continue;
      }
      depths.set(current.id, current.depth);
      const children = childrenByParent.get(current.id) ?? [];
      for (const child of children) {
        queue.push({ id: child, depth: current.depth + 1 });
      }
    }

    return depths;
  }

  computeSubtreeSizes(roots: string[], childrenByParent: Map<string, string[]>): Map<string, number> {
    const subtreeSizes = new Map<string, number>();
    const visit = (id: string, stack = new Set<string>()): number => {
      if (subtreeSizes.has(id)) {
        return subtreeSizes.get(id) ?? 1;
      }
      if (stack.has(id)) {
        return 1;
      }
      stack.add(id);
      const children = childrenByParent.get(id) ?? [];
      if (!children.length) {
        subtreeSizes.set(id, 1);
        stack.delete(id);
        return 1;
      }
      let sum = 0;
      for (const child of children) {
        sum += visit(child, stack);
      }
      const size = Math.max(1, sum);
      subtreeSizes.set(id, size);
      stack.delete(id);
      return size;
    };

    for (const rootId of roots) {
      visit(rootId);
    }

    return subtreeSizes;
  }

  assignPositions(
    roots: string[],
    childrenByParent: Map<string, string[]>,
    subtreeSizes: Map<string, number>,
    depths: Map<string, number>
  ): Map<string, { x: number; y: number }> {
    const positions = new Map<string, { x: number; y: number }>();
    const topPadding = 42;
    const leftPadding = 34;
    const depthIndent = 92;
    const rowGap = 86;
    const rootGapRows = 1;
    const visited = new Set<string>();
    let rowIndex = 0;

    const placeDfs = (id: string): void => {
      if (visited.has(id)) {
        return;
      }
      visited.add(id);
      const depth = depths.get(id) ?? 0;
      positions.set(id, {
        x: leftPadding + depth * depthIndent,
        y: topPadding + rowIndex * rowGap
      });
      rowIndex += 1;

      const children = childrenByParent.get(id) ?? [];
      const orderedChildren = [...children].sort((a, b) => (subtreeSizes.get(b) ?? 1) - (subtreeSizes.get(a) ?? 1));
      for (const childId of orderedChildren) {
        placeDfs(childId);
      }
    };

    for (const rootId of roots) {
      placeDfs(rootId);
      rowIndex += rootGapRows;
    }

    return positions;
  }

  private getPortraitLayout(): PortraitLayout {
    const cache = this.portraitLayoutCache;
    if (
      cache &&
      cache.nodesRef === this.nodes &&
      cache.linksRef === this.links &&
      cache.width === this.containerWidth &&
      cache.height === this.containerHeight
    ) {
      return cache.layout;
    }

    const tree = this.buildTree(this.nodes, this.links);
    const depths = this.computeDepths(tree.roots, tree.childrenByParent);
    for (const node of this.nodes) {
      if (!depths.has(node.id)) {
        depths.set(node.id, 0);
      }
    }
    const subtreeSizes = this.computeSubtreeSizes(tree.roots, tree.childrenByParent);
    const positions = this.assignPositions(tree.roots, tree.childrenByParent, subtreeSizes, depths);

    const positionedNodes = this.nodes.map((node) => {
      const point = positions.get(node.id) ?? { x: node.x, y: node.y };
      return { ...node, x: point.x, y: point.y };
    });

    const nodeById = new Map(positionedNodes.map((node) => [node.id, node]));
    const renderedLinks: RenderLink[] = [];
    for (const [childId, parentId] of tree.parentById.entries()) {
      if (!parentId) {
        continue;
      }
      const parent = nodeById.get(parentId);
      const child = nodeById.get(childId);
      if (!parent || !child) {
        continue;
      }
      renderedLinks.push({
        x1: parent.x,
        y1: parent.y,
        x2: child.x,
        y2: child.y,
        parentId,
        childId
      });
    }

    const bounds = this.computePortraitBounds(positionedNodes, depths);
    const shiftedNodes = positionedNodes.map((node) => ({
      ...node,
      x: node.x + bounds.shiftX,
      y: node.y + bounds.shiftY
    }));
    const shiftedLinks = renderedLinks.map((link) => ({
      ...link,
      x1: link.x1 + bounds.shiftX,
      y1: link.y1 + bounds.shiftY,
      x2: link.x2 + bounds.shiftX,
      y2: link.y2 + bounds.shiftY
    }));

    const layout: PortraitLayout = {
      nodes: shiftedNodes,
      links: shiftedLinks,
      width: bounds.viewWidth,
      height: bounds.viewHeight
    };

    this.portraitLayoutCache = {
      nodesRef: this.nodes,
      linksRef: this.links,
      width: this.containerWidth,
      height: this.containerHeight,
      layout
    };

    return layout;
  }

  private computePortraitBounds(nodes: UiNetworkGraphNode[], depths: Map<string, number>): {
    shiftX: number;
    shiftY: number;
    viewWidth: number;
    viewHeight: number;
  } {
    if (!nodes.length) {
      return { shiftX: 0, shiftY: 0, viewWidth: 360, viewHeight: 520 };
    }

    let minX = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;

    for (const node of nodes) {
      const radius = this.nodeRadius(node);
      const labelHalf = this.estimatedLabelHalfWidth(node);
      minX = Math.min(minX, node.x - Math.max(radius + 12, labelHalf));
      maxX = Math.max(maxX, node.x + Math.max(radius + 12, labelHalf));
      minY = Math.min(minY, node.y - radius - 16);
      maxY = Math.max(maxY, node.y + radius + 26);
    }

    const leftPad = 24;
    const topPad = 24;
    const rightPad = 24;
    const bottomPad = 28;

    const shiftX = minX < leftPad ? leftPad - minX : 0;
    const shiftY = minY < topPad ? topPad - minY : 0;

    const maxDepth = Math.max(...depths.values(), 0);
    const minHeightByDepth = 48 + (maxDepth + 1) * 88 + 64;
    const viewWidth = Math.max(
      320,
      Math.round(maxX - minX + leftPad + rightPad)
    );
    const viewHeight = Math.max(
      minHeightByDepth,
      Math.round(maxY - minY + topPad + bottomPad)
    );

    return { shiftX, shiftY, viewWidth, viewHeight };
  }

  private estimatedLabelHalfWidth(node: UiNetworkGraphNode): number {
    const text = this.nodeAlwaysLabel(node);
    return Math.max(42, Math.min(112, text.length * 3.4));
  }

  private estimateGraphSize(): { width: number; height: number } {
    if (!this.nodes.length) {
      return { width: 700, height: 250 };
    }

    const xs = this.nodes.map((node) => node.x);
    const ys = this.nodes.map((node) => node.y + this.nodeRadius(node) + 64);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const width = Math.max(360, Math.ceil(maxX - minX + 180));
    const height = Math.max(240, Math.ceil(maxY - minY + 60));
    return { width, height };
  }

  private get isPortraitTreeActive(): boolean {
    if (this.portraitTree === true) {
      return true;
    }
    if (this.portraitTree === false) {
      return false;
    }

    const containerPortrait = this.containerWidth > 0 && this.containerHeight > 0
      ? this.containerHeight >= this.containerWidth
      : false;

    return containerPortrait || this.viewportIsPortrait || this.viewportWidth <= this.portraitBreakpoint;
  }

  private get svgScaleMeetSafe(): number {
    return Number.isFinite(this.svgScaleMeet) && this.svgScaleMeet > 0 ? this.svgScaleMeet : 1;
  }

  private updateSvgMeetScale(): void {
    const svg = this.svgEl?.nativeElement;
    if (!svg) {
      this.svgScaleMeet = 1;
      return;
    }
    const vbW = this.computedViewBoxWidth;
    const vbH = this.computedViewBoxHeight;
    if (vbW <= 0 || vbH <= 0) {
      this.svgScaleMeet = 1;
      return;
    }
    const sx = svg.clientWidth / vbW;
    const sy = svg.clientHeight / vbH;
    const s = Math.min(sx, sy);
    this.svgScaleMeet = Number.isFinite(s) && s > 0 ? s : 1;
  }

  private clientToSvgPoint(clientX: number, clientY: number): SvgPoint {
    const svg = this.svgEl?.nativeElement;
    if (!svg) {
      return { x: this.computedViewBoxWidth / 2, y: this.computedViewBoxHeight / 2 };
    }

    const rect = svg.getBoundingClientRect();
    const vbW = this.computedViewBoxWidth;
    const vbH = this.computedViewBoxHeight;
    const s = this.svgScaleMeetSafe;
    const renderW = vbW * s;
    const renderH = vbH * s;
    const offsetX = this.preserveAspect.includes('xMid') ? (rect.width - renderW) / 2 : 0;
    const offsetY = this.preserveAspect.includes('YMid') ? (rect.height - renderH) / 2 : 0;
    const x = (clientX - rect.left - offsetX) / s;
    const y = (clientY - rect.top - offsetY) / s;
    return {
      x: this.clamp(x, 0, vbW),
      y: this.clamp(y, 0, vbH)
    };
  }


  private findNodeIdByPoint(nodes: UiNetworkGraphNode[], x: number, y: number): string | null {
    const exact = nodes.find((node) => this.isSamePoint(node.x, node.y, x, y));
    if (exact) {
      return exact.id;
    }

    let bestId: string | null = null;
    let bestDistance = Number.POSITIVE_INFINITY;
    for (const node of nodes) {
      const dx = node.x - x;
      const dy = node.y - y;
      const dist = Math.hypot(dx, dy);
      if (dist < bestDistance) {
        bestDistance = dist;
        bestId = node.id;
      }
    }

    return bestDistance <= 3 ? bestId : null;
  }

  private linkTouchesNode(link: UiNetworkGraphLink, node: UiNetworkGraphNode): boolean {
    return this.isSamePoint(node.x, node.y, link.x1, link.y1) || this.isSamePoint(node.x, node.y, link.x2, link.y2);
  }

  private isSamePoint(x1: number, y1: number, x2: number, y2: number): boolean {
    return Math.abs(x1 - x2) < 0.01 && Math.abs(y1 - y2) < 0.01;
  }

  private toPct(value: number, total: number): number {
    if (!total) {
      return 50;
    }
    const raw = (value / total) * 100;
    return Math.max(3, Math.min(97, raw));
  }

  private trimZeros(value: string): string {
    return value.replace(/\.0$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
  }

  private clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
  }

  private boxOverlapsNode(
    box: NodePlateBox,
    nodeX: number,
    nodeY: number,
    nodeRadius: number
  ): boolean {
    const padding = 8;
    const left = box.x - padding;
    const right = box.x + box.width + padding;
    const top = box.y - padding;
    const bottom = box.y + box.height + padding;
    const overlapsRect = nodeX >= left && nodeX <= right && nodeY >= top && nodeY <= bottom;
    if (overlapsRect) {
      return true;
    }

    const closestX = this.clamp(nodeX, box.x, box.x + box.width);
    const closestY = this.clamp(nodeY, box.y, box.y + box.height);
    const dx = nodeX - closestX;
    const dy = nodeY - closestY;
    return Math.hypot(dx, dy) <= nodeRadius + padding;
  }
}
