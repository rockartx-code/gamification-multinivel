import { Injectable } from '@angular/core';

import { NetworkMember } from '../models/user-dashboard.model';

export type UserDashboardGraphNode = {
  id: string;
  level: string;
  x: number;
  y: number;
  label: string;
  name: string;
  status?: NetworkMember['status'];
  leaderId?: string;
  meta?: Record<string, unknown>;
};

export type UserDashboardGraphLayout = {
  nodes: UserDashboardGraphNode[];
  links: Array<{ x1: number; y1: number; x2: number; y2: number }>;
};

export type UserDashboardGraphSnapshot = {
  layout: UserDashboardGraphLayout;
  size: { width: number; height: number };
};

@Injectable({ providedIn: 'root' })
export class UserDashboardNetworkGraphService {
  buildSnapshot(members: NetworkMember[], rootName: string): UserDashboardGraphSnapshot {
    const l1Members = members.filter((member) => member.level === 'L1');
    const l2Members = members.filter((member) => member.level === 'L2');
    const l3Members = members.filter((member) => member.level === 'L3');
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

    const root: UserDashboardGraphNode = {
      id: 'root',
      level: 'root',
      x: rootX,
      y: rootY,
      label: this.nodeLabel(rootName),
      name: rootName,
      meta: { spend: 0 }
    };

    const l1Nodes = l1Members.map((member, index) => ({
      id: member.id ? `l1-${member.id}` : `l1-${index}`,
      level: 'L1',
      x: l1Positions[index]?.x ?? l1X,
      y: l1Positions[index]?.y ?? rootY,
      label: this.nodeLabel(member.name),
      name: member.name || 'Miembro',
      status: member.status,
      meta: { spend: member.spend ?? 0 }
    }));

    const l1ByMemberId = new Map<string, UserDashboardGraphNode>();
    l1Members.forEach((member, index) => {
      const memberId = member.id ? String(member.id) : `idx-${index}`;
      const node = l1Nodes[index];
      if (node) {
        l1ByMemberId.set(memberId, node);
      }
    });

    const l2Nodes = l2Members.map((member, index) => ({
      id: member.id ? `l2-${member.id}` : `l2-${index}`,
      level: 'L2',
      x: l2Positions[index]?.x ?? l2X,
      y: l2Positions[index]?.y ?? rootY,
      label: this.nodeLabel(member.name),
      name: member.name || 'Miembro',
      status: member.status,
      leaderId: member.leaderId ? String(member.leaderId) : undefined,
      meta: { spend: member.spend ?? 0 }
    }));

    const l2ByMemberId = new Map<string, UserDashboardGraphNode>();
    l2Members.forEach((member, index) => {
      const memberId = member.id ? String(member.id) : `idx-${index}`;
      const node = l2Nodes[index];
      if (node) {
        l2ByMemberId.set(memberId, node);
      }
    });

    const l3Nodes = l3Members.map((member, index) => ({
      id: member.id ? `l3-${member.id}` : `l3-${index}`,
      level: 'L3',
      x: l3Positions[index]?.x ?? l3X,
      y: l3Positions[index]?.y ?? rootY,
      label: this.nodeLabel(member.name),
      name: member.name || 'Miembro',
      status: member.status,
      leaderId: member.leaderId ? String(member.leaderId) : undefined,
      meta: { spend: member.spend ?? 0 }
    }));

    const links: UserDashboardGraphLayout['links'] = [];
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

    return {
      layout: { nodes: [root, ...l1Nodes, ...l2Nodes, ...l3Nodes], links },
      size: { width: metrics.width, height: metrics.height }
    };
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

  private buildColumnPositions(count: number, x: number, top: number, spacing: number): { x: number; y: number }[] {
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
}
