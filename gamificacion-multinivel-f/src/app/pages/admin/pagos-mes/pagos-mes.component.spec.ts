import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { readFileSync } from 'node:fs';
import { Observable, of } from 'rxjs';

import { PagoPeriodos, PagosMes } from '../../../models/pagos.model';
import { AdminControlService } from '../../../services/admin-control.service';
import { PagosService } from '../../../services/pagos.service';
import { PagosMesComponent } from './pagos-mes.component';

/**
 * Guarda 12 del informe 27 (§4) · «marzo perdido en el día de pago».
 *
 * Renata recargó la página tres veces y marzo de 2027 ya no estaba en el
 * selector: los doce meses se armaban con `new Date()` del navegador, que iba
 * en 2026. Los meses del dinero los publica el servidor
 * (`GET /commissions/periodos`, propuesta 17) y el mes elegido sigue ahí
 * después de recargar.
 */

const FUENTE = 'src/app/pages/admin/pagos-mes/pagos-mes.component.ts';

const PERIODOS: PagoPeriodos = {
  serverNow: '2027-04-10T15:00:00Z',
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
    },
    {
      monthKey: '2027-02',
      label: 'febrero 2027',
      beneficiarias: 2,
      confirmado: 800,
      porConfirmar: 0,
      bloqueado: 0,
      estado: 'PAID'
    }
  ]
};

function mesVacio(monthKey: string): PagosMes {
  return {
    monthKey,
    rows: [],
    totals: {
      listo: { count: 0, amount: 0 },
      sinClabe: { count: 0, amount: 0 },
      pagado: { count: 0, amount: 0 },
      porConfirmarFilas: { count: 0, amount: 0 },
      confirmado: 0,
      porConfirmar: 0,
      bloqueado: 0,
      reconocido: 0
    },
    baseComisionTexto: 'Sobre el subtotal sin IVA ni envío.'
  };
}

describe('Guarda 12 · el selector de meses de Pagos del mes', () => {
  let pagos: {
    getPeriodos: ReturnType<typeof vi.fn>;
    getPagosMes: ReturnType<typeof vi.fn>;
  };

  function montar(month = ''): ComponentFixture<PagosMesComponent> {
    const fixture = TestBed.createComponent(PagosMesComponent);
    fixture.componentInstance.month = month;
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(async () => {
    // El reloj del navegador, bien lejos del mundo real del servidor.
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-09-15T10:00:00Z'));

    pagos = {
      getPeriodos: vi.fn((): Observable<PagoPeriodos> => of(PERIODOS)),
      getPagosMes: vi.fn((mes: string): Observable<PagosMes> => of(mesVacio(mes)))
    };

    await TestBed.configureTestingModule({
      imports: [PagosMesComponent],
      providers: [
        provideRouter([]),
        { provide: PagosService, useValue: pagos },
        { provide: AdminControlService, useValue: { load: () => of(null) } }
      ]
    }).compileComponents();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('los meses salen del servidor, no del reloj del navegador', () => {
    const fixture = montar();
    const componente = fixture.componentInstance;

    expect(pagos.getPeriodos).toHaveBeenCalledTimes(1);
    expect(componente.monthOptions.map((o) => o.value)).toEqual(['2027-03', '2027-02']);
    // El mes que abre es el que dijo el servidor, no septiembre de 2026.
    expect(componente.monthKey).toBe('2027-03');
    expect(componente.monthKey.startsWith('2026')).toBe(false);
    expect(componente.serverNow).toBe(PERIODOS.serverNow);
    expect(pagos.getPagosMes).toHaveBeenCalledWith('2027-03');

    // Y la fuente no arma meses con el reloj del navegador (se miran las
    // instrucciones, no los comentarios que cuentan por qué ya no se hace).
    const fuente = readFileSync(FUENTE, 'utf8').replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, '');
    expect(fuente).not.toMatch(/new Date\(\s*\)/);
    expect(fuente).not.toMatch(/Date\.now\(\s*\)/);
  });

  it('la selección sobrevive a recargar la página', () => {
    const fixture = montar();
    fixture.componentInstance.onMonthChange('2027-02');
    fixture.detectChanges();
    expect(fixture.componentInstance.monthKey).toBe('2027-02');
    const elegido = fixture.componentInstance.monthKey;
    fixture.destroy();

    // La recarga: la pantalla vuelve con el mes elegido (viaja en la URL,
    // `#/admin?mes=…`) y el servidor ya ni siquiera lo lista entre los que
    // tienen dinero. Aun así sigue seleccionado y visible en el selector.
    pagos.getPeriodos.mockReturnValue(
      of({ ...PERIODOS, periodos: PERIODOS.periodos.filter((p) => p.monthKey !== elegido) })
    );
    const recargada = montar(elegido);

    expect(recargada.componentInstance.monthKey).toBe('2027-02');
    expect(recargada.componentInstance.monthOptions.map((o) => o.value)).toContain('2027-02');
    expect(pagos.getPagosMes).toHaveBeenLastCalledWith('2027-02');
  });
});
