import { AuthCoachMessage } from '../../domain/models';

type StatusTone = 'success' | 'warning' | 'danger';

export type CoachLocale = 'es';
export type AuthCoachState = 'default';
export type DashboardCoachState = 'overview';

export interface CoachCopy {
  auth: Record<AuthCoachState, { title: string; messages: AuthCoachMessage[] }>;
  dashboard: {
    header: Record<
      DashboardCoachState,
      {
        title: string;
        message: string;
        tone: StatusTone;
      }
    >;
  };
}

const ES_COACH_COPY: CoachCopy = {
  auth: {
    default: {
      title: 'Guía del coach',
      messages: [
        {
          id: 'coach-1',
          title: 'Coach: Enfócate en el primer paso',
          body: 'Completa tu acceso para desbloquear la misión inicial y sumar tus primeros puntos.',
        },
        {
          id: 'coach-2',
          title: 'Coach: Mantén tu ritmo',
          body: 'Una vez dentro, revisa tu objetivo semanal para avanzar sin distracciones.',
        },
        {
          id: 'coach-3',
          title: 'Coach: Aprovecha tu red',
          body: 'Conecta con tu equipo para recibir apoyo y recomendaciones personalizadas.',
        },
      ],
    },
  },
  dashboard: {
    header: {
      overview: {
        title: 'Tu foco hoy',
        message: 'Completa la meta activa y ejecuta la siguiente acción prioritaria.',
        tone: 'success',
      },
    },
  },
};

const COACH_COPY_BY_LOCALE: Record<CoachLocale, CoachCopy> = {
  es: ES_COACH_COPY,
};

export const DEFAULT_COACH_LOCALE: CoachLocale = 'es';

export const getCoachCopy = (locale: CoachLocale = DEFAULT_COACH_LOCALE): CoachCopy =>
  COACH_COPY_BY_LOCALE[locale];
