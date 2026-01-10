import { AuthContext } from '../domain/models';
import { getCoachCopy } from '../shared/coach/coach-copy';

const coachCopy = getCoachCopy();

export const authFixture: AuthContext = {
  title: 'Bienvenido al panel multinivel',
  subtitle: 'Inicia sesión o crea tu cuenta para seguir avanzando en tu ruta de logros.',
  helperText: 'Tus datos están protegidos y solo se usan para personalizar tu experiencia.',
  primaryActionLabel: 'Ingresar',
  secondaryActionLabel: 'Crear cuenta',
  coachMessages: coachCopy.auth.default.messages,
};
