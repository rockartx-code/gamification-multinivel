import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-landing-page',
  template: `
    <section>
      <h1>Landing</h1>
      <p>Bienvenido a la experiencia pública.</p>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingPage {}
