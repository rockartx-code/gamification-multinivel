import { NetworkMember } from '../domain/models';

export const networkMembersFixture: NetworkMember[] = [
  {
    id: 'member-001',
    name: 'Luis Mendoza',
    level: 2,
    joinedAt: '2024-11-02',
    active: true,
  },
  {
    id: 'member-002',
    name: 'Sofía Herrera',
    level: 3,
    joinedAt: '2025-01-18',
    active: false,
  },
];
