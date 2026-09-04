import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiChoiceCardComponent } from '../../../components/ui-choice-card/ui-choice-card.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { UiModalComponent } from '../../../components/ui-modal/ui-modal.component';
import { ArqueoCaja, CorteCaja, MovimientoCaja, RetiroCaja } from '../../../models/caja.model';
import { CajaService } from '../../../services/caja.service';

type PasoCorte = 1 | 2 | 3 | 4;
type PasoRetiro = 1 | 2 | 3;
type DestinoEfectivo = 'fondo' | 'retiro';

/**
 * Corte de caja con arqueo y retiro guiado (paquete E, propuesta 16).
 *
 * Nadia: "la pantalla sólo registra el número"; Paco: "¿debo guardarme los
 * $440 de cambio en mi bolsillo?". Aquí el corte compara lo que debería haber
 * en el cajón con lo que la cajera contó, pide motivo si no cuadra y deja
 * escrito a dónde va el efectivo. Todo lo que se confirma sale de la
 * respuesta del servidor, nunca del formulario.
 */
@Component({
  selector: 'app-admin-arqueo',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent, UiFormFieldComponent, UiModalComponent, UiChoiceCardComponent],
  templateUrl: './admin-arqueo.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AdminArqueoComponent implements OnChanges {
  /** Sucursal ligada a la caja; null cuando el usuario no tiene ninguna. */
  @Input() stockId: string | null = null;
  @Input() stockName = '';
  @Input() operatorName = '';
  /** Tiene el privilegio `pos_register_sale`. */
  @Input() canOperate = false;
  /** El padre lo incrementa tras cada venta, abono o anulación para recargar el arqueo. */
  @Input() refreshToken = 0;

  /** Se emite tras cerrar un corte o registrar un retiro, con lo que el servidor devolvió. */
  @Output() cajaCambio = new EventEmitter<{ corte?: CorteCaja; retiro?: RetiroCaja }>();

  arqueo: ArqueoCaja | null = null;
  cargando = false;
  errorCarga = '';
  movimientosAbiertos = false;

  // --- Abrir turno (propuesta 5): el fondo lo declara quien tiene el dinero ---
  fondoAperturaTexto = '';
  guardandoApertura = false;
  errorApertura = '';
  aperturaGuardada = '';

  // --- Código de autorización (propuesta 6): tres estados, al salir del paso 3 ---
  estadoCodigo: 'sin_validar' | 'validando' | 'correcto' | 'incorrecto' = 'sin_validar';
  motivoCodigo = '';

  // --- Corte con arqueo ---
  corteAbierto = false;
  pasoCorte: PasoCorte = 1;
  contadoTexto = '';
  contarPorDenominacion = false;
  conteo: Record<string, string> = {};
  motivoDiferencia = '';
  destino: DestinoEfectivo = 'fondo';
  fondoTexto = '';
  receptor = '';
  codigoCorte = '';
  errorCorte = '';
  guardandoCorte = false;

  // --- Comprobante ---
  comprobante: CorteCaja | null = null;
  comprobanteAbierto = false;
  correoDestino = '';
  enviandoCorreo = false;
  correoEnviadoA = '';
  errorCorreo = '';

  // --- Retiro guiado ---
  retiroAbierto = false;
  pasoRetiro: PasoRetiro = 1;
  retiroMontoTexto = '';
  retiroMotivo = '';
  retiroReceptor = '';
  retiroCodigo = '';
  errorRetiro = '';
  guardandoRetiro = false;
  retiroConfirmado: { folio: string; monto: number; receptor: string; restante: number } | null = null;

  constructor(private readonly caja: CajaService, private readonly cdr: ChangeDetectorRef) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['stockId'] || changes['refreshToken']) {
      this.cargarArqueo();
    }
  }

  // ------------------------------------------------------------------ carga

  cargarArqueo(): void {
    if (!this.stockId) {
      this.arqueo = null;
      return;
    }
    this.cargando = true;
    this.errorCarga = '';
    this.caja
      .obtenerArqueo(this.stockId)
      .pipe(finalize(() => { this.cargando = false; this.requestViewUpdate(); }))
      .subscribe({
        next: ({ arqueo }) => { this.arqueo = arqueo; this.requestViewUpdate(); },
        error: (err: unknown) => { this.errorCarga = this.mensajeDeError(err, 'No se pudo leer el estado de la caja.'); this.requestViewUpdate(); }
      });
  }

  /** La caja nunca cortó ni declaró fondo: se pide, no se enseña un $0.00. */
  get necesitaApertura(): boolean {
    return Boolean(this.arqueo?.needsOpening);
  }

  /** De dónde sale el fondo inicial, en una línea. */
  get textoFondoInicial(): string {
    const a = this.arqueo;
    if (!a) return '';
    if (a.openingSource === 'apertura') {
      const quien = (a.openingDeclaredBy || '').trim();
      return `Fondo declarado al abrir el turno${quien ? ' por ' + quien : ''}`;
    }
    if (a.openingSource === 'corte_anterior') {
      return 'Fondo que dejó el corte anterior';
    }
    return 'Esta caja nunca ha cerrado un corte: captura el fondo con el que arrancas';
  }

  get fondoAperturaNumero(): number {
    return this.redondear(this.aNumero(this.fondoAperturaTexto));
  }

  /** Por qué no se puede guardar el fondo todavía. Vacío si se puede. */
  motivoAperturaDeshabilitada(): string {
    if (!this.canOperate) return 'No tienes el permiso "Ventas en caja": pídeselo a tu gerente.';
    if (!this.stockId) return 'Sin sucursal vinculada: pide a la gerente que te ligue a una en Almacenes.';
    if (this.guardandoApertura) return 'Guardando el fondo…';
    if (String(this.fondoAperturaTexto).trim() === '') return 'Escribe con cuánto arrancas (puede ser $0).';
    if (this.fondoAperturaNumero < 0) return 'El fondo no puede ser negativo.';
    return '';
  }

  /** Guarda el fondo declarado: el arqueo del día arranca de ahí. */
  guardarApertura(): void {
    if (this.motivoAperturaDeshabilitada() || !this.stockId) {
      this.errorApertura = this.motivoAperturaDeshabilitada();
      this.requestViewUpdate();
      return;
    }
    this.guardandoApertura = true;
    this.errorApertura = '';
    this.aperturaGuardada = '';
    this.caja
      .abrirTurno({ stockId: this.stockId, openingCash: this.fondoAperturaNumero })
      .pipe(finalize(() => { this.guardandoApertura = false; this.requestViewUpdate(); }))
      .subscribe({
        next: ({ opening, arqueo }) => {
          this.arqueo = arqueo;
          this.fondoAperturaTexto = '';
          this.aperturaGuardada = `Turno abierto con ${this.dinero(opening.openingCash)} de fondo. `
            + 'Queda escrito en los movimientos y en el comprobante del corte.';
          this.requestViewUpdate();
        },
        error: (err: unknown) => {
          this.errorApertura = this.mensajeDeError(err, 'No se pudo guardar el fondo con el que arrancas.');
          this.requestViewUpdate();
        }
      });
  }

  get efectivoEsperado(): number {
    return this.redondear(this.arqueo?.expectedCash ?? 0);
  }

  get denominaciones(): number[] {
    const lista = this.arqueo?.config?.denominations ?? [];
    return lista.length ? lista : [1000, 500, 200, 100, 50, 20, 10, 5, 2, 1];
  }

  get hayAlgoQueCortar(): boolean {
    return Boolean(this.arqueo && (this.arqueo.salesCount > 0 || this.arqueo.withdrawalCount > 0));
  }

  /** Por qué el botón está deshabilitado, en una línea. Vacío si está habilitado. */
  motivoDeshabilitado(accion: 'corte' | 'retiro'): string {
    if (!this.canOperate) {
      return 'No tienes el permiso "Ventas en caja": pídeselo a tu gerente.';
    }
    if (!this.stockId) {
      return 'Sin sucursal vinculada: pide a la gerente que te ligue a una en Almacenes.';
    }
    if (this.cargando && !this.arqueo) {
      return 'Leyendo el estado de la caja…';
    }
    if (this.errorCarga) {
      return this.errorCarga;
    }
    if (accion === 'corte') {
      if (this.guardandoCorte) return 'Guardando el corte…';
      if (!this.hayAlgoQueCortar) return 'No hay ventas ni retiros desde el último corte: no hay nada que cortar todavía.';
    }
    if (accion === 'retiro') {
      if (this.guardandoRetiro) return 'Registrando el retiro…';
      if (this.efectivoEsperado <= 0) return 'No hay efectivo en caja para retirar.';
    }
    return '';
  }

  // ------------------------------------------------------------------ corte

  abrirCorte(): void {
    if (this.motivoDeshabilitado('corte')) return;
    this.pasoCorte = 1;
    this.contadoTexto = '';
    this.contarPorDenominacion = false;
    this.conteo = {};
    this.motivoDiferencia = '';
    this.destino = 'fondo';
    this.fondoTexto = '';
    this.receptor = '';
    this.codigoCorte = '';
    this.errorCorte = '';
    this.estadoCodigo = 'sin_validar';
    this.motivoCodigo = '';
    this.corteAbierto = true;
    this.cargarArqueo();
  }

  cerrarCorteModal(): void {
    if (this.guardandoCorte) return;
    this.corteAbierto = false;
    this.requestViewUpdate();
  }

  get contadoNumero(): number {
    if (this.contarPorDenominacion) {
      return this.redondear(
        this.denominaciones.reduce((suma, d) => suma + d * (Number(this.conteo[String(d)]) || 0), 0)
      );
    }
    return this.redondear(this.aNumero(this.contadoTexto));
  }

  get contadoCapturado(): boolean {
    return this.contarPorDenominacion
      ? Object.values(this.conteo).some((v) => Number(v) > 0)
      : String(this.contadoTexto).trim() !== '';
  }

  get diferencia(): number {
    return this.redondear(this.contadoNumero - this.efectivoEsperado);
  }

  get requiereMotivo(): boolean {
    return this.diferencia !== 0 && (this.arqueo?.config?.requireDifferenceReason ?? true);
  }

  /** ¿La gerencia configuró un código de autorización? (propuesta 6). */
  get codigoConfigurado(): boolean {
    return this.arqueo?.config?.authCodeConfigured !== false;
  }

  /** El texto honesto cuando no hay ningún código configurado. */
  get textoSinCodigo(): string {
    return 'Todavía no hay un código de autorización configurado: nadie puede autorizar un retiro. '
      + 'Deja todo como fondo y avisa a tu gerente.';
  }

  actualizarConteo(denominacion: number, valor: string): void {
    this.conteo = { ...this.conteo, [String(denominacion)]: valor };
  }

  alternarDenominaciones(activar: boolean): void {
    this.contarPorDenominacion = activar;
    this.requestViewUpdate();
  }

  get fondoNumero(): number {
    if (this.destino === 'fondo') return this.contadoNumero;
    return this.redondear(this.aNumero(this.fondoTexto));
  }

  get retiroDelCorte(): number {
    return this.redondear(Math.max(0, this.contadoNumero - this.fondoNumero));
  }

  elegirDestino(destino: DestinoEfectivo): void {
    this.destino = destino;
    this.estadoCodigo = 'sin_validar';
    this.motivoCodigo = '';
    if (destino === 'fondo') {
      this.fondoTexto = '';
      this.receptor = '';
      this.codigoCorte = '';
    } else if (!this.fondoTexto) {
      // "Retirar una parte" proponía llevarse todo, fondo de cambio incluido.
      const fondo = this.redondear(this.arqueo?.openingCash ?? 0);
      this.fondoTexto = fondo > 0 ? String(fondo) : '0';
    }
    this.errorCorte = '';
    this.requestViewUpdate();
  }

  /** Validación de cada paso, en palabras; vacío si se puede avanzar. */
  bloqueoPaso(paso: PasoCorte): string {
    if (paso === 1) {
      return this.arqueo ? '' : 'Espera a que cargue el efectivo esperado.';
    }
    if (paso === 2) {
      if (!this.contadoCapturado) return 'Escribe cuánto efectivo contaste (puede ser $0).';
      if (this.contadoNumero < 0) return 'El efectivo contado no puede ser negativo.';
      if (this.requiereMotivo && !this.motivoDiferencia.trim()) {
        return `Hay una diferencia de ${this.dinero(this.diferencia)}: escribe el motivo para poder continuar.`;
      }
      return '';
    }
    if (paso === 3) {
      if (this.destino === 'retiro') {
        // Tres estados, y el primero es el de este mundo: no hay código configurado.
        if (!this.codigoConfigurado) return this.textoSinCodigo;
        if (this.fondoNumero < 0 || this.fondoNumero > this.contadoNumero) {
          return `El fondo debe estar entre $0 y ${this.dinero(this.contadoNumero)} (lo contado).`;
        }
        if (this.retiroDelCorte <= 0) return 'Si no se retira nada, elige "Dejar todo como fondo".';
        if (!this.receptor.trim()) return 'Escribe quién recibe el efectivo retirado.';
        if (!this.codigoCorte.trim()) return 'Escribe el código de autorización de la gerente para el retiro.';
        if (this.estadoCodigo === 'validando') return 'Comprobando el código de autorización…';
        if (this.estadoCodigo === 'incorrecto') return this.motivoCodigo;
      }
      return '';
    }
    return '';
  }

  avanzarCorte(): void {
    const bloqueo = this.bloqueoPaso(this.pasoCorte);
    if (bloqueo) {
      this.errorCorte = bloqueo;
      this.requestViewUpdate();
      return;
    }
    this.errorCorte = '';
    // El código se comprueba aquí, al salir del paso 3, y no en "Cerrar el
    // corte": Mireya se llevó el 403 con el dinero contado y el turno acabado.
    if (this.pasoCorte === 3 && this.destino === 'retiro' && this.estadoCodigo !== 'correcto') {
      this.comprobarCodigo(this.codigoCorte.trim(), () => this.pasarAlPaso(4));
      return;
    }
    if (this.pasoCorte < 4) {
      this.pasoCorte = (this.pasoCorte + 1) as PasoCorte;
    }
    this.requestViewUpdate();
  }

  private pasarAlPaso(paso: PasoCorte): void {
    this.pasoCorte = paso;
    this.requestViewUpdate();
  }

  /**
   * Comprueba el código contra el servidor y traduce sus tres respuestas:
   * no hay código configurado, código incorrecto o correcto.
   */
  private comprobarCodigo(codigo: string, siEsCorrecto: () => void): void {
    this.estadoCodigo = 'validando';
    this.motivoCodigo = '';
    this.requestViewUpdate();
    this.caja.validarCodigo(codigo).subscribe({
      next: () => {
        this.estadoCodigo = 'correcto';
        this.motivoCodigo = '';
        siEsCorrecto();
      },
      error: (err: unknown) => {
        const e = err as { status?: number } | null;
        if (e?.status === 409 && this.arqueo?.config) {
          // Nadie ha configurado un código: se dice eso, no "incorrecto".
          this.arqueo = { ...this.arqueo, config: { ...this.arqueo.config, authCodeConfigured: false } };
          this.estadoCodigo = 'sin_validar';
          this.motivoCodigo = '';
          this.errorCorte = this.textoSinCodigo;
          this.errorRetiro = this.textoSinCodigo;
        } else {
          this.estadoCodigo = 'incorrecto';
          this.motivoCodigo = this.mensajeDeError(err, 'Código de autorización incorrecto: pídeselo a tu gerente.');
          this.errorCorte = this.motivoCodigo;
          this.errorRetiro = this.motivoCodigo;
        }
        this.requestViewUpdate();
      }
    });
  }

  alCambiarCodigoCorte(valor: string): void {
    this.codigoCorte = valor;
    this.estadoCodigo = 'sin_validar';
    this.motivoCodigo = '';
    this.errorCorte = '';
  }

  retrocederCorte(): void {
    this.errorCorte = '';
    if (this.pasoCorte > 1) {
      this.pasoCorte = (this.pasoCorte - 1) as PasoCorte;
    }
    this.requestViewUpdate();
  }

  get textoEfectoCorte(): string {
    const a = this.arqueo;
    if (!a) return '';
    const ventas = `${a.salesCount} venta${a.salesCount === 1 ? '' : 's'}`;
    const total = this.dinero(this.redondear(a.cashSales + a.cashSettlements + a.cashFromMixed + a.nonCashTotal));
    const partes = [`Se cerrará el corte con ${ventas} por ${total}.`, `Fondo para mañana: ${this.dinero(this.fondoNumero)}.`];
    if (this.retiroDelCorte > 0) {
      partes.push(`Retiro: ${this.dinero(this.retiroDelCorte)} a nombre de ${this.receptor.trim()}.`);
    } else {
      partes.push('No se retira efectivo.');
    }
    if (this.diferencia !== 0) {
      partes.push(`La diferencia de ${this.dinero(this.diferencia)} queda registrada con motivo: "${this.motivoDiferencia.trim()}".`);
    } else {
      partes.push('El efectivo contado coincide con el esperado.');
    }
    return partes.join(' ');
  }

  confirmarCorte(): void {
    if (!this.stockId || this.guardandoCorte) return;
    for (const paso of [2, 3] as PasoCorte[]) {
      const bloqueo = this.bloqueoPaso(paso);
      if (bloqueo) {
        this.pasoCorte = paso;
        this.errorCorte = bloqueo;
        this.requestViewUpdate();
        return;
      }
    }
    const denominations: Record<string, number> = {};
    if (this.contarPorDenominacion) {
      for (const d of this.denominaciones) {
        const n = Number(this.conteo[String(d)]) || 0;
        if (n > 0) denominations[String(d)] = n;
      }
    }
    this.guardandoCorte = true;
    this.errorCorte = '';
    this.caja
      .cerrarCorte({
        stockId: this.stockId,
        cashCounted: this.contadoNumero,
        denominations: this.contarPorDenominacion ? denominations : undefined,
        differenceReason: this.motivoDiferencia.trim() || undefined,
        cashToKeep: this.fondoNumero,
        withdrawalAmount: this.retiroDelCorte,
        withdrawalReceiver: this.retiroDelCorte > 0 ? this.receptor.trim() : undefined,
        authCode: this.retiroDelCorte > 0 ? this.codigoCorte.trim() : undefined
      })
      .pipe(finalize(() => { this.guardandoCorte = false; this.requestViewUpdate(); }))
      .subscribe({
        next: ({ cut }) => {
          this.comprobante = cut;
          this.correoDestino = '';
          this.correoEnviadoA = '';
          this.errorCorreo = '';
          this.corteAbierto = false;
          this.comprobanteAbierto = true;
          this.cajaCambio.emit({ corte: cut });
          this.cargarArqueo();
        },
        error: (err: unknown) => {
          this.errorCorte = this.mensajeDeError(err, 'No se pudo cerrar el corte. Revisa los datos e inténtalo de nuevo.');
          this.requestViewUpdate();
        }
      });
  }

  // ------------------------------------------------------------ comprobante

  cerrarComprobante(): void {
    this.comprobanteAbierto = false;
    this.requestViewUpdate();
  }

  get correoConfigurado(): boolean {
    return Boolean(this.arqueo?.config?.notifyEmailConfigured);
  }

  enviarComprobante(): void {
    if (!this.comprobante || this.enviandoCorreo) return;
    const correo = this.correoDestino.trim();
    if (!this.correoConfigurado && !correo) {
      this.errorCorreo = 'No hay un correo de gerente configurado: escribe uno para enviar el comprobante.';
      this.requestViewUpdate();
      return;
    }
    this.enviandoCorreo = true;
    this.errorCorreo = '';
    this.caja
      .enviarCorte(this.comprobante.cashCutId, correo || undefined)
      .pipe(finalize(() => { this.enviandoCorreo = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (r) => { this.correoEnviadoA = r.to; this.requestViewUpdate(); },
        error: (err: unknown) => { this.errorCorreo = this.mensajeDeError(err, 'No se pudo enviar el comprobante.'); this.requestViewUpdate(); }
      });
  }

  imprimirComprobante(): void {
    const c = this.comprobante;
    if (!c) return;
    const filas: Array<[string, string]> = [
      ['Fondo inicial', this.dinero(c.openingCash ?? 0)],
      ['Ventas en efectivo', this.dinero(c.cashSales ?? 0)],
      ['Abonos en efectivo', this.dinero(c.cashSettlements ?? 0)],
      ['Parte en efectivo de pagos mixtos', this.dinero(c.cashFromMixed ?? 0)],
      ['Retiros del turno', `- ${this.dinero(c.totalWithdrawals ?? 0)}`],
      ['Efectivo esperado', this.dinero(c.cashExpected ?? 0)],
      ['Efectivo contado', this.dinero(c.cashCounted ?? 0)],
      ['Diferencia', this.dinero(c.difference ?? 0)],
      ['Se deja como fondo', this.dinero(c.cashToKeep ?? 0)],
      ['Se retira', this.dinero(c.withdrawnAmount ?? 0)],
      ['Tarjeta y transferencia (no entran a caja)', this.dinero(c.nonCashTotal ?? 0)]
    ];
    const esc = (t: string) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const html = `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Corte ${esc(c.cashCutId)}</title>
<style>body{font-family:Arial,sans-serif;padding:24px;color:#222}h1{font-size:20px;margin:0 0 4px}p{margin:4px 0;font-size:13px}
table{border-collapse:collapse;width:100%;margin-top:12px}td{padding:6px 8px;border-bottom:1px solid #ddd;font-size:13px}td:last-child{text-align:right;font-weight:bold}</style></head>
<body><h1>Comprobante del corte ${esc(c.cashCutId)}</h1>
<p>Sucursal: ${esc(this.stockName || c.stockId)} · Operador: ${esc(this.operatorName || String(c.attendantUserId ?? ''))}</p>
<p>Periodo: ${esc(this.fecha(c.startedAt))} a ${esc(this.fecha(c.endedAt ?? c.createdAt))} · ${c.salesCount} venta(s)</p>
<table>${filas.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</table>
${c.differenceReason ? `<p>Motivo de la diferencia: ${esc(c.differenceReason)}</p>` : ''}
${c.withdrawalReceiver ? `<p>El retiro lo recibe: ${esc(c.withdrawalReceiver)}</p>` : ''}
<p style="margin-top:24px">Firma de quien entrega: ______________________ &nbsp;&nbsp; Firma de quien recibe: ______________________</p>
</body></html>`;
    const ventana = window.open('', '_blank', 'width=720,height=900');
    if (!ventana) {
      this.errorCorreo = 'El navegador bloqueó la ventana de impresión: permite las ventanas emergentes e inténtalo de nuevo.';
      this.requestViewUpdate();
      return;
    }
    ventana.document.write(html);
    ventana.document.close();
    ventana.focus();
    ventana.print();
  }

  // ----------------------------------------------------------------- retiro

  abrirRetiro(): void {
    if (this.motivoDeshabilitado('retiro')) return;
    this.pasoRetiro = 1;
    this.retiroMontoTexto = '';
    this.retiroMotivo = '';
    this.retiroReceptor = '';
    this.retiroCodigo = '';
    this.errorRetiro = '';
    this.estadoCodigo = 'sin_validar';
    this.motivoCodigo = '';
    this.retiroConfirmado = null;
    this.retiroAbierto = true;
    this.cargarArqueo();
  }

  cerrarRetiroModal(): void {
    if (this.guardandoRetiro) return;
    this.retiroAbierto = false;
    this.requestViewUpdate();
  }

  get retiroMontoNumero(): number {
    return this.redondear(this.aNumero(this.retiroMontoTexto));
  }

  bloqueoPasoRetiro(paso: PasoRetiro): string {
    if (paso === 1) {
      if (!String(this.retiroMontoTexto).trim() || this.retiroMontoNumero <= 0) return 'Escribe cuánto vas a retirar (mayor a $0).';
      if (this.retiroMontoNumero > this.efectivoEsperado) {
        return `Solo hay ${this.dinero(this.efectivoEsperado)} en caja: no puedes retirar ${this.dinero(this.retiroMontoNumero)}.`;
      }
      return '';
    }
    if (paso === 2) {
      if (!this.retiroMotivo.trim()) return 'Escribe para qué es el retiro (por ejemplo: paquetería, proveedor, depósito).';
      if (!this.retiroReceptor.trim()) return 'Escribe quién recibe el efectivo.';
      return '';
    }
    if (!this.codigoConfigurado) return this.textoSinCodigo;
    if (!this.retiroCodigo.trim()) return 'Escribe el código de autorización de la gerente.';
    if (this.estadoCodigo === 'validando') return 'Comprobando el código de autorización…';
    if (this.estadoCodigo === 'incorrecto') return this.motivoCodigo;
    return '';
  }

  alCambiarCodigoRetiro(valor: string): void {
    this.retiroCodigo = valor;
    this.estadoCodigo = 'sin_validar';
    this.motivoCodigo = '';
    this.errorRetiro = '';
  }

  avanzarRetiro(): void {
    const bloqueo = this.bloqueoPasoRetiro(this.pasoRetiro);
    if (bloqueo) {
      this.errorRetiro = bloqueo;
      this.requestViewUpdate();
      return;
    }
    this.errorRetiro = '';
    if (this.pasoRetiro < 3) {
      this.pasoRetiro = (this.pasoRetiro + 1) as PasoRetiro;
    }
    this.requestViewUpdate();
  }

  retrocederRetiro(): void {
    this.errorRetiro = '';
    if (this.pasoRetiro > 1) {
      this.pasoRetiro = (this.pasoRetiro - 1) as PasoRetiro;
    }
    this.requestViewUpdate();
  }

  confirmarRetiro(): void {
    if (!this.stockId || this.guardandoRetiro) return;
    for (const paso of [1, 2, 3] as PasoRetiro[]) {
      const bloqueo = this.bloqueoPasoRetiro(paso);
      if (bloqueo) {
        this.pasoRetiro = paso;
        this.errorRetiro = bloqueo;
        this.requestViewUpdate();
        return;
      }
    }
    this.guardandoRetiro = true;
    this.errorRetiro = '';
    this.caja
      .retirar({
        stockId: this.stockId,
        amount: this.retiroMontoNumero,
        reason: this.retiroMotivo.trim(),
        receiver: this.retiroReceptor.trim(),
        authCode: this.retiroCodigo.trim()
      })
      .pipe(finalize(() => { this.guardandoRetiro = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (r) => {
          this.retiroConfirmado = {
            folio: r.withdrawal.withdrawalId,
            monto: Number(r.withdrawal.amount ?? 0),
            receptor: r.withdrawal.receiver || '',
            restante: Number(r.remainingCash ?? r.control?.currentTotal ?? 0)
          };
          this.cajaCambio.emit({ retiro: r.withdrawal });
          this.cargarArqueo();
        },
        error: (err: unknown) => {
          this.errorRetiro = this.mensajeDeError(err, 'No se pudo registrar el retiro.');
          this.requestViewUpdate();
        }
      });
  }

  // ---------------------------------------------------------------- helpers

  etiquetaMovimiento(m: MovimientoCaja): string {
    return m.customerName && m.type !== 'opening' ? `${m.label} · ${m.customerName}` : m.label;
  }

  dinero(valor: number | null | undefined): string {
    const n = Number(valor ?? 0);
    const signo = n < 0 ? '-' : '';
    return `${signo}$${Math.abs(n).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  fecha(valor: string | null | undefined): string {
    if (!valor) return '-';
    const d = new Date(valor);
    return Number.isNaN(d.getTime()) ? String(valor) : d.toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
  }

  private aNumero(texto: string | number): number {
    const n = Number(String(texto ?? '').replace(/[^0-9.-]/g, ''));
    return Number.isFinite(n) ? n : 0;
  }

  private redondear(valor: number): number {
    return Math.round((Number(valor) + Number.EPSILON) * 100) / 100;
  }

  private mensajeDeError(err: unknown, porOmision: string): string {
    const e = err as { error?: { message?: string }; message?: string } | null;
    return e?.error?.message || e?.message || porOmision;
  }

  private requestViewUpdate(): void {
    this.cdr.markForCheck();
  }
}
