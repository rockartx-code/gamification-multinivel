import { NextAction } from '../domain/models';

export const nextActionsFixture: NextAction[] = [
  {
    id: 'action-001',
    label: 'Contactar a 3 prospectos nuevos',
    description: 'Envía mensajes personalizados para iniciar conversaciones.',
    rewardPoints: 150,
    completed: false,
  },
  {
    id: 'action-002',
    label: 'Completar módulo de entrenamiento',
    description: 'Finaliza el módulo de cierre de ventas en la academia.',
    rewardPoints: 250,
    completed: true,
  },
];
