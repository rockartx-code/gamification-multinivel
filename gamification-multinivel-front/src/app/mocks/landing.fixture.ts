import { Landing } from '../domain/models';

export const landingFixture: Landing = {
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
};
