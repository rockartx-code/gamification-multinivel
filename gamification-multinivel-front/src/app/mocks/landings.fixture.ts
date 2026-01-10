import { Landing } from '../domain/models';

export const landingsFixture: Landing[] = [
  {
    heroTitle: 'Impulsa tu red con retos y recompensas',
    heroSubtitle: 'Motiva a tu equipo con objetivos claros, métricas en tiempo real y misiones guiadas.',
    heroImageUrl: '/landing-hero.svg',
    heroImageAlt: 'Equipo colaborando frente a un panel con métricas y misiones.',
    ctaLabel: 'Empieza ahora',
    ctaUrl: '/registro',
    highlights: [
      'Paneles de progreso personalizados',
      'Misiones semanales con recompensas',
      'Ranking actualizado en tiempo real',
    ],
  },
  {
    heroTitle: 'Convierte visitas en líderes activos',
    heroSubtitle: 'Guía a los nuevos socios con un recorrido claro y seguimiento automático.',
    heroImageUrl: '/landing-onboarding.svg',
    heroImageAlt: 'Nueva líder revisando su progreso en un panel.',
    ctaLabel: 'Iniciar recorrido',
    ctaUrl: '/onboarding',
    highlights: [
      'Checklist de activación comercial',
      'Mensajes personalizados por nivel',
      'Alertas para el coach responsable',
    ],
  },
  {
    heroTitle: 'Planifica tu próxima campaña',
    heroSubtitle: 'Organiza lanzamientos con metas claras y recordatorios automáticos.',
    heroImageUrl: '/landing-campaign.svg',
    heroImageAlt: 'Equipo planificando campañas con métricas de rendimiento.',
    ctaLabel: 'Ver calendario',
    ctaUrl: '/campanas',
    highlights: [
      'Calendario compartido por líderes',
      'Resumen de conversiones clave',
      'Reportes semanales automáticos',
    ],
  },
];
