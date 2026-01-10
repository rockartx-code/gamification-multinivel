import { Achievement } from '../domain/models';

export const achievementsFixture: Achievement[] = [
  {
    id: 'achievement-001',
    title: 'Embajador estrella',
    description: 'Alcanzaste 10 referidos activos en un mes.',
    badgeUrl: '/assets/badges/estrella.png',
    unlockedAt: '2025-03-08T10:30:00Z',
  },
  {
    id: 'achievement-002',
    title: 'Consistencia total',
    description: 'Registraste ventas durante 4 semanas consecutivas.',
    badgeUrl: '/assets/badges/consistencia.png',
    unlockedAt: '2025-03-15T15:45:00Z',
  },
];
