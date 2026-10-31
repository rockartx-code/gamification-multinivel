import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { readFileSync } from 'node:fs';
import { Observable, of } from 'rxjs';

import { UiClabeFormComponent } from '../../components/ui-clabe-form/ui-clabe-form.component';
import { ApiService } from '../../services/api.service';

/**
 * Guarda 10 del informe 27 (§4) · **el caso que motivó toda la auditoría**.
 *
 * Paulina y Fabiola escribieron su CLABE diez veces entre las dos y marzo cerró
 * con $0.00 depositados. El informe 25 lo contó como "guardar CLABE no guarda";
 * la auditoría (§2) demostró que sí guardaba, pero en **dos pasos**: el segundo
 * era un modal de confirmación que ninguna de las dos pulsó, mientras el rótulo
 * de arriba seguía diciendo "No registrada". Nunca hubo un `POST`, ni siquiera
 * un `OPTIONS`, desde el navegador de una socia.
 *
 * Estas tres pruebas son el candado de la corrección (propuesta 1 del informe
 * 25, ya implementada en `ui-clabe-form`, el formulario que monta el panel del
 * socio):
 *
 *  1. Guardar llama al API **en un solo paso**: un clic, una llamada, sin
 *     diálogo intermedio.
 *  2. El estado se pinta **en el propio campo** ("termina en 6789"), no en un
 *     aviso al fondo de una página kilométrica.
 *  3. Una CLABE de 17 dígitos da mensaje en línea y **no** llama al API.
 */

interface ApiFalso {
  saveCustomerClabe: ReturnType<typeof vi.fn>;
}

/** El formulario que el panel del socio monta para la CLABE (`<ui-clabe-form>`). */
const PLANTILLA_PANEL = 'src/app/pages/user-dashboard/user-dashboard.component.html';

function leer(ruta: string): string {
  return readFileSync(ruta, 'utf8');
}

describe('Guarda 10 · la CLABE del panel del socio se guarda de un tirón', () => {
  let api: ApiFalso;
  let fixture: ComponentFixture<UiClabeFormComponent>;

  beforeEach(async () => {
    api = {
      saveCustomerClabe: vi.fn(
        (): Observable<{ clabeLast4: string }> => of({ clabeLast4: '6789' })
      )
    };

    await TestBed.configureTestingModule({
      imports: [UiClabeFormComponent],
      providers: [provideRouter([]), { provide: ApiService, useValue: api }]
    }).compileComponents();

    fixture = TestBed.createComponent(UiClabeFormComponent);
    fixture.componentInstance.customerId = 42;
    fixture.componentInstance.modo = 'propio';
    fixture.detectChanges();
  });

  /** Teclea en el campo de la CLABE como lo hace una persona. */
  function escribir(valor: string): void {
    const campo = fixture.nativeElement.querySelector(
      'ui-form-field[name="clabe"] input'
    ) as HTMLInputElement;
    expect(campo).toBeTruthy();
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  /** Pulsa el botón de guardar (el único cuyo texto empieza por "Guardar"). */
  function pulsarGuardar(): void {
    const botones = Array.from(
      fixture.nativeElement.querySelectorAll('button')
    ) as HTMLButtonElement[];
    const guardar = botones.find((b) => /^Guardar/.test((b.textContent ?? '').trim()));
    expect(guardar).toBeTruthy();
    guardar!.click();
    fixture.detectChanges();
  }

  function textoVisible(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  it('guarda en un solo paso: un clic escribe en el servidor, sin diálogo de confirmación', () => {
    escribir('012180001234566789');

    // Antes del clic no se ha llamado a nadie: el campo no dispara solo.
    expect(api.saveCustomerClabe).not.toHaveBeenCalled();

    pulsarGuardar();

    // Un clic, una llamada. Nada de "Confirmar" en un segundo paso.
    expect(api.saveCustomerClabe).toHaveBeenCalledTimes(1);
    expect(api.saveCustomerClabe).toHaveBeenCalledWith(
      expect.objectContaining({ customerId: 42, clabe: '012180001234566789' })
    );

    // Y no hay ningún modal de por medio (era el paso que nadie pulsaba).
    expect(fixture.nativeElement.querySelector('ui-modal')).toBeNull();

    // El panel del socio monta este formulario, no uno propio con su modal.
    expect(leer(PLANTILLA_PANEL)).toContain('<ui-clabe-form');
  });

  it('el estado se lee en el propio campo: "termina en 6789"', () => {
    escribir('012180001234566789');
    pulsarGuardar();

    // Lo que la socia lee junto al campo, sin bajar al final de la página.
    expect(textoVisible()).toContain('termina en 6789');
    // Y el rótulo de arriba deja de mentir.
    expect(textoVisible()).not.toContain('Todavía no registras tu CLABE');
    expect(fixture.componentInstance.estado).toBe('guardada');
  });

  it('con 17 dígitos avisa en línea y no llama al servidor', () => {
    escribir('01218000123456678');
    pulsarGuardar();

    expect(api.saveCustomerClabe).not.toHaveBeenCalled();
    expect(fixture.componentInstance.estado).toBe('error');
    const texto = textoVisible();
    expect(texto).toContain('18 dígitos');
    expect(texto).toContain('17');
  });
});
