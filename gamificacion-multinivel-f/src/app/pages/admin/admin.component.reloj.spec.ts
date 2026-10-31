import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { AdminCustomer } from '../../models/admin.model';
import { PagoPeriodos } from '../../models/pagos.model';
import { AdminControlService } from '../../services/admin-control.service';
import { AuthService } from '../../services/auth.service';
import { PagosService } from '../../services/pagos.service';
import { AdminComponent } from './admin.component';

/**
 * Guarda 13 del informe 27 (§4) · «dos pantallas con dos relojes distintos».
 *
 * Alma estuvo media hora creyendo que marzo había cerrado en ceros: el
 * navegador iba en 2026-09 y el mundo simulado en 2027-04. Todo lo que el back
 * office diga sobre "cuándo" —el mes contable y los días que lleva una clienta
 * sin comprar— sale del reloj del servidor (`serverNow`), nunca de `Date.now()`.
 *
 * El componente se crea sin pintar la plantilla (no se llama a
 * `detectChanges`): aquí se mide de dónde salen las fechas, no cómo se ven.
 */

const AHORA_SERVIDOR = '2027-04-10T12:00:00Z';

const PERIODOS: PagoPeriodos = {
  serverNow: AHORA_SERVIDOR,
  mesContableVigente: '2027-04',
  defaultMonth: '2027-03',
  payoutDay: 10,
  periodos: [
    {
      monthKey: '2027-03',
      label: 'marzo 2027',
      beneficiarias: 3,
      confirmado: 1200,
      porConfirmar: 0,
      bloqueado: 0,
      estado: 'IN_PROGRESS'
    }
  ]
};

function clienta(lastPurchaseAt: string): AdminCustomer {
  return { id: 1, name: 'Claudia', email: 'c@example.com', lastPurchaseAt } as AdminCustomer;
}

describe('Guarda 13 · el back office lee la hora del servidor', () => {
  let fixture: ComponentFixture<AdminComponent>;
  let componente: AdminComponent;
  let datos: BehaviorSubject<Record<string, unknown> | null>;
  let pagos: { getPeriodos: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    // El navegador, seis meses y medio atrasado respecto del servidor.
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-09-25T12:00:00Z'));

    datos = new BehaviorSubject<Record<string, unknown> | null>(null);
    pagos = { getPeriodos: vi.fn(() => of(PERIODOS)) };

    await TestBed.configureTestingModule({
      imports: [AdminComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        { provide: PagosService, useValue: pagos },
        {
          provide: AdminControlService,
          useValue: { data$: datos.asObservable(), load: () => of(null) }
        },
        {
          provide: AuthService,
          useValue: {
            currentUser: { userId: '1', name: 'Alma' },
            user$: of({ userId: '1', name: 'Alma' }),
            hasPrivilege: () => true,
            hasSession: true
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AdminComponent);
    componente = fixture.componentInstance;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('el mes contable es el que manda el servidor, no el del navegador', () => {
    // Lo que hace la vista de Clientes al abrirse (WP-A · 17).
    (componente as unknown as { cargarPeriodosDelServidor(): void }).cargarPeriodosDelServidor();

    expect(pagos.getPeriodos).toHaveBeenCalledTimes(1);
    expect(componente.serverNow).toBe(AHORA_SERVIDOR);
    expect(componente.commissionsMonthKey).toBe('2027-03');
    expect(componente.commissionsMonthLabel).toContain('2027');
    // Septiembre de 2026 es el mes del navegador: no debe aparecer por ningún lado.
    expect(componente.commissionsMonthKey).not.toBe('2026-08');
    expect(componente.activeReportMonth).toBe('2027-04');
  });

  it('"días desde la última compra" se cuenta con el reloj del servidor', () => {
    datos.next({ serverNow: AHORA_SERVIDOR, warnings: [], customers: [] });

    // Compró hace nueve días **en el mundo del servidor**; con el reloj del
    // navegador (2026-09-25) la resta daría negativa y se pintaría "0 días",
    // que fue lo que hizo creer a Alma que nadie compraba.
    expect(componente.daysSinceLastPurchase(clienta('2027-04-01T12:00:00Z'))).toBe(9);

    // Y una compra vieja de verdad sigue contando como fría (30+ días).
    expect(componente.daysSinceLastPurchase(clienta('2027-01-10T12:00:00Z'))).toBe(90);
    expect(componente.isColdCustomer(clienta('2027-01-10T12:00:00Z'))).toBe(true);
    expect(componente.isColdCustomer(clienta('2027-04-01T12:00:00Z'))).toBe(false);
  });
});
