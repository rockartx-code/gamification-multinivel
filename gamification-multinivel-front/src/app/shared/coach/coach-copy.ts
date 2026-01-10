import { AuthCoachMessage } from '../../domain/models';

type StatusTone = 'success' | 'warning' | 'danger';

export type CoachLocale = 'es';
export type AuthCoachState = 'default' | 'registrationSuccess';
export type DashboardCoachState = 'overview';
export type StoreCoachState = 'catalog' | 'cart' | 'quote' | 'checkout';

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
  store: Record<
    StoreCoachState,
    {
      title: string;
      message: string;
    }
  >;
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
    registrationSuccess: {
      title: 'Coach: Registro confirmado',
      messages: [
        {
          id: 'coach-register-1',
          title: 'Coach: Tu cuenta ya está en marcha',
          body: 'Revisa tu correo para activar el acceso y confirmar tu información.',
        },
        {
          id: 'coach-register-2',
          title: 'Coach: Prepara tu siguiente paso',
          body: 'Mientras validamos tu registro, reúne los datos de tu equipo para acelerar tu arranque.',
        },
        {
          id: 'coach-register-3',
          title: 'Coach: Mantén la conexión',
          body: 'Comparte el enlace de onboarding con tu red para sumar más puntos desde el inicio.',
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
  store: {
    catalog: {
      title: 'Coach: Prioriza lo que rota rápido',
      message:
        'Elige productos con alta demanda para asegurar recompras y mantener tu volumen mensual.',
    },
    cart: {
      title: 'Coach: Ajusta antes de enviar',
      message:
        'Verifica cantidades y bonos aplicados para proteger tu margen y entregar una oferta clara.',
    },
    quote: {
      title: 'Coach: Cierra con valor',
      message:
        'Incluye beneficios y próximos pasos para que tu cliente tome acción hoy mismo.',
    },
    checkout: {
      title: 'Coach: Confirma y celebra',
      message:
        'Asegura el envío y comunica el seguimiento para fortalecer la confianza del cliente.',
    },
  },
};

const COACH_COPY_BY_LOCALE: Record<CoachLocale, CoachCopy> = {
  es: ES_COACH_COPY,
};

export const DEFAULT_COACH_LOCALE: CoachLocale = 'es';

export const getCoachCopy = (locale: CoachLocale = DEFAULT_COACH_LOCALE): CoachCopy =>
  COACH_COPY_BY_LOCALE[locale];
