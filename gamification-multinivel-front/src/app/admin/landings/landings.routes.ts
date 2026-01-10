import { Routes } from '@angular/router';

import { LandingsEditorPage } from './landings-editor.page';
import { LandingsListPage } from './landings-list.page';

export const landingsRoutes: Routes = [
  {
    path: '',
    component: LandingsListPage,
  },
  {
    path: 'new',
    component: LandingsEditorPage,
  },
];
