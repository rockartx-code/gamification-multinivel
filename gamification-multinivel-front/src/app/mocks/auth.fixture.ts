import { AuthContext } from '../domain/models';

export const authFixture: AuthContext = {
  title: 'Bienvenido al panel multinivel',
  subtitle: 'Inicia sesión o crea tu cuenta para seguir avanzando en tu ruta de logros.',
  helperText: 'Tus datos están protegidos y solo se usan para personalizar tu experiencia.',
  primaryActionLabel: 'Ingresar',
  secondaryActionLabel: 'Crear cuenta',
  coachMessages: [
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
};
