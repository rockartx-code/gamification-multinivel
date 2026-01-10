import { Mission } from '../domain/models';

export const missionsFixture: Mission[] = [
  {
    id: 'mission-001',
    title: 'Semana de activaciones',
    description: 'Completa 5 activaciones con tu equipo.',
    progressPercent: 60,
    rewardPoints: 500,
    status: 'active',
  },
  {
    id: 'mission-002',
    title: 'Entrenamiento líder',
    description: 'Guía a un nuevo integrante durante su primera venta.',
    progressPercent: 100,
    rewardPoints: 750,
    status: 'completed',
  },
];
