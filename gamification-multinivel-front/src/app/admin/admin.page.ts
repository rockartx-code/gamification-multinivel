import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-admin-page',
  imports: [RouterLink],
  template: `
    <section class="space-y-4 px-4 py-6">
      <h1>Admin</h1>
      <p>Panel reservado para administradores.</p>
      <a class="inline-flex items-center gap-2 text-sm font-semibold text-sky-700" routerLink="/admin/landings">
        Gestionar landings
      </a>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminPage {}
