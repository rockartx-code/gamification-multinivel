import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-admin-page',
  imports: [RouterLink],
  template: `
    <section class="app-page">
      <div class="app-shell space-y-4">
        <h1 class="app-title">Admin</h1>
        <p class="app-subtitle">Panel reservado para administradores.</p>
        <a class="app-link" routerLink="/admin/landings">Gestionar landings</a>
      </div>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminPage {}
