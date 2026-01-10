import { Goal } from '../domain/models';

export const goalsFixture: Goal[] = [
  {
    id: 'goal-001',
    title: 'Vender 10 productos premium',
    targetAmount: 10,
    currentAmount: 6,
    remainingMessage: 'Te faltan 4 ventas para completar la meta.',
    dueDate: '2025-04-15',
  },
  {
    id: 'goal-002',
    title: 'Alcanzar $5.000 en ingresos',
    targetAmount: 5000,
    currentAmount: 3200,
    remainingMessage: 'Aún necesitas $1.800 para llegar al objetivo.',
  },
];
