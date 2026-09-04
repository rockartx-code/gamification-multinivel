import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { Observable, of, throwError } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { PlanSocioService } from '../../services/plan-socio.service';
import { UserProfileComponent } from './user-profile.component';

/**
 * Guarda 11 del informe 27 (§4) · el **estrechamiento 1** del §3.
 *
 * `1f759d7` ocultó el bloque de CLABE del perfil en "modo cliente". El modo
 * arranca en `invitado` y solo se corrige cuando responde `GET /customers/modo`:
 * si esa llamada falla o tarda, la socia no puede ver ni capturar su CLABE —
 * justo la pantalla donde el informe 25 dice que Fabiola lo intentó cinco veces.
 *
 *  1. Con el modo **sin resolver** (y con la llamada del modo fallando), el
 *     perfil pinta su bloque de CLABE.
 *  2. En toda la aplicación hay **un solo** formulario de captura de CLABE.
 *     Había dos (uno pedía banco y el otro no, y no se enteraban uno del otro);
 *     la propuesta 1 los unificó en `ui-clabe-form` y esta prueba impide que
 *     vuelva a aparecer un tercero.
 */

const RAIZ_APP = 'src/app';
const PLANTILLA_UNICA = 'src/app/components/ui-clabe-form/ui-clabe-form.component.html';

/** Todas las plantillas de la aplicación, en orden. */
function plantillas(dir: string = RAIZ_APP): string[] {
  const encontradas: string[] = [];
  for (const entrada of readdirSync(dir, { withFileTypes: true })) {
    const ruta = join(dir, entrada.name);
    if (entrada.isDirectory()) {
      encontradas.push(...plantillas(ruta));
    } else if (entrada.name.endsWith('.html')) {
      encontradas.push(ruta);
    }
  }
  return encontradas.sort();
}

/**
 * Campos de captura (`<input>` o `<ui-form-field>`) que piden una CLABE.
 * Se mira la etiqueta completa, que puede ocupar varias líneas.
 */
function camposDeClabe(html: string): string[] {
  const etiquetas = html.match(/<(?:input|ui-form-field)\b[\s\S]*?>/g) ?? [];
  return etiquetas.filter((etiqueta) => /clabe/i.test(etiqueta));
}

describe('Guarda 11 · la CLABE del perfil', () => {
  it('el bloque de CLABE se pinta aunque el modo de la cuenta no se resuelva', async () => {
    const planSocio = {
      modoActual: 'invitado' as const,
      // `GET /customers/modo` que nunca responde bien: el perfil no puede
      // esconder la CLABE por no saber si la cuenta es de cliente o de socia.
      modo: (): Observable<never> => throwError(() => new Error('sin respuesta'))
    };
    const api = {
      getCustomer: () =>
        of({ id: 7, name: 'Fabiola Ruiz', email: 'fabiola@example.com', clabeInterbancaria: '' }),
      getBusinessConfig: () => of({ customerDocumentTypes: [] })
    };
    const auth = { currentUser: { userId: '7', name: 'Fabiola Ruiz' } };

    await TestBed.configureTestingModule({
      imports: [UserProfileComponent],
      providers: [
        provideRouter([]),
        { provide: PlanSocioService, useValue: planSocio },
        { provide: ApiService, useValue: api },
        { provide: AuthService, useValue: auth }
      ]
    }).compileComponents();

    const fixture = TestBed.createComponent(UserProfileComponent);
    fixture.detectChanges();

    expect(fixture.componentInstance.isClientMode).toBe(false);
    expect(fixture.nativeElement.querySelector('ui-clabe-form')).toBeTruthy();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('CLABE');
  });

  it('en toda la aplicación hay un solo formulario de CLABE', () => {
    const conCampo = plantillas()
      .map((ruta) => ({ ruta, campos: camposDeClabe(readFileSync(ruta, 'utf8')) }))
      .filter((p) => p.campos.length > 0);

    expect(conCampo.map((p) => p.ruta)).toEqual([PLANTILLA_UNICA]);
    expect(conCampo[0]?.campos.length).toBe(1);
  });
});
