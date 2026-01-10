import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-auth-page',
  template: `
    <section>
      <h1>Autenticación</h1>
      <p>Zona pública para iniciar sesión o registrarse.</p>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthPage {}
