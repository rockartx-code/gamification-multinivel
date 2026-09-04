import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { UiBadgeComponent } from '../../../components/ui-badge/ui-badge.component';
import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { UiDataTableComponent } from '../../../components/ui-data-table/ui-data-table.component';
import { UiFormFieldComponent } from '../../../components/ui-form-field/ui-form-field.component';
import { UiHeaderComponent } from '../../../components/ui-header/ui-header.component';
import { UiModalComponent } from '../../../components/ui-modal/ui-modal.component';
import { UiStatusBadgeComponent } from '../../../components/ui-status-badge/ui-status-badge.component';
import {
  CanalContacto,
  PreferenciaContacto,
  SeguimientoAlcance,
  SeguimientoEjecutiva,
  SeguimientoFila,
  SeguimientoHoyRespuesta,
  SeguimientoPlantilla,
  SeguimientoSituacion
} from '../../../models/seguimiento.model';
import { AuthService } from '../../../services/auth.service';
import { SeguimientoService } from '../../../services/seguimiento.service';

type Tono = 'active' | 'inactive' | 'pending' | 'delivered' | 'danger';

const ETIQUETAS_ORIGEN: Record<string, string> = {
  '': 'Sin registrar',
  organico: 'Búsqueda orgánica',
  referido: 'Referido por un socio',
  red_social: 'Red social de un socio',
  anuncio_google: 'Anuncio en Google',
  anuncio_facebook: 'Anuncio en Facebook',
  anuncio_instagram: 'Anuncio en Instagram',
  anuncio_youtube: 'Anuncio en YouTube',
  tienda_fisica: 'Tienda física',
  invitado: 'Compró como invitado'
};

const ETIQUETAS_PREFERENCIA: Record<string, string> = {
  '': 'Sin registrar',
  whatsapp: 'WhatsApp',
  email: 'Correo',
  none: 'Prefiere que no le escriban'
};

const ETIQUETAS_CANAL: Record<CanalContacto, string> = {
  whatsapp: 'WhatsApp',
  email: 'Correo',
  call: 'Llamada'
};

/**
 * Seguimiento de hoy (paquete F): la lista que la coach abre al empezar el turno.
 *
 * Ivonne cruzaba Clientes, Pedidos y Estadísticas y abría ficha por ficha para
 * saber a quién escribirle y quién es su patrocinadora; después redactaba el
 * mismo WhatsApp y anotaba la nota a mano. Aquí todo está en la misma fila,
 * "Escribir" prellena el mensaje y al abrir WhatsApp la nota queda sola.
 */
@Component({
  selector: 'app-admin-seguimiento',
  standalone: true,
  imports: [CommonModule, FormsModule, UiHeaderComponent, UiButtonComponent, UiFormFieldComponent, UiModalComponent, UiStatusBadgeComponent, UiBadgeComponent, UiDataTableComponent],
  templateUrl: './admin-seguimiento.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AdminSeguimientoComponent implements OnInit {
  scope: SeguimientoAlcance = 'mine';
  situation: SeguimientoSituacion | '' = '';
  search = '';

  isLoading = false;
  loadError = '';
  rows: SeguimientoFila[] = [];
  total = 0;
  excluded = { doNotContact: 0, otherExecutive: 0 };
  executives: SeguimientoEjecutiva[] = [];
  coachName = '';
  date = '';
  thresholds = { coldDays: 30, welcomeDays: 7, lateOrderDays: 5 };
  templates: Record<string, SeguimientoPlantilla> = {};

  // Modal "Escribir"
  writeRow: SeguimientoFila | null = null;
  writeTemplateKey = '';
  writeChannel: CanalContacto = 'whatsapp';
  writeMessage = '';
  isSavingContact = false;
  /** Enlace wa.me cuando el navegador bloqueó la ventana: se muestra para copiar. */
  blockedLink = '';
  linkCopied = false;

  // Modal "Ficha"
  fichaRow: SeguimientoFila | null = null;
  fichaPreference: PreferenciaContacto | '' = '';
  fichaExecutiveId = '';
  isSavingFicha = false;

  // Modal "Crear ficha" (invitados)
  guestRow: SeguimientoFila | null = null;
  isCreatingGuest = false;

  snackbar: { message: string; tone: 'success' | 'error'; visible: boolean } = { message: '', tone: 'success', visible: false };
  private snackbarTimeout: number | null = null;

  readonly situationOptions: Array<{ value: SeguimientoSituacion | ''; label: string }> = [
    { value: '', label: 'Todas las que necesitan contacto' },
    { value: 'clabe_pendiente', label: 'CLABE pendiente (tienen comisión y no hay dónde depositar)' },
    { value: 'pedido_tardio', label: 'Pedido tardío (pagado sin despachar o enviado sin entregar)' },
    { value: 'bienvenida', label: 'Bienvenida (recién registradas, sin compra)' },
    { value: 'fria', label: 'Frías (hace tiempo que no compran)' },
    { value: 'activa', label: 'Activas (compraron hace poco; solo para consultar)' }
  ];

  readonly channelOptions: Array<{ value: CanalContacto; label: string }> = [
    { value: 'whatsapp', label: 'WhatsApp (se abre con el mensaje listo)' },
    { value: 'call', label: 'Llamada (solo se anota)' },
    { value: 'email', label: 'Correo (solo se anota)' }
  ];

  readonly preferenceOptions: Array<{ value: PreferenciaContacto | ''; label: string }> = [
    { value: '', label: 'Sin registrar' },
    { value: 'whatsapp', label: 'WhatsApp' },
    { value: 'email', label: 'Correo' },
    { value: 'none', label: 'Prefiere que no le escriban seguido' }
  ];

  constructor(
    private readonly seguimiento: SeguimientoService,
    private readonly auth: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.load();
    this.seguimiento.plantillas().subscribe({
      next: (r) => {
        this.templates = r.templates ?? {};
        this.requestViewUpdate();
      },
      error: () => {
        // Sin plantillas la coach puede seguir escribiendo a mano; no se bloquea la pantalla.
      }
    });
  }

  // --- Carga y filtros -------------------------------------------------------

  load(): void {
    this.isLoading = true;
    this.loadError = '';
    this.seguimiento
      .hoy({ scope: this.scope, situation: this.situation })
      .pipe(finalize(() => { this.isLoading = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (r: SeguimientoHoyRespuesta) => {
          this.rows = r.rows ?? [];
          this.total = r.total ?? this.rows.length;
          this.excluded = r.excluded ?? { doNotContact: 0, otherExecutive: 0 };
          this.executives = r.executives ?? [];
          this.coachName = r.coachName || this.auth.currentUser?.name || '';
          this.date = r.date;
          this.thresholds = r.thresholds ?? this.thresholds;
        },
        error: (error: unknown) => {
          this.rows = [];
          this.loadError = this.errorMessage(error, 'No se pudo cargar la lista. Revisa tu conexión y vuelve a intentar.');
        }
      });
  }

  setScope(scope: SeguimientoAlcance): void {
    if (this.scope === scope) return;
    this.scope = scope;
    this.load();
  }

  setSituation(value: string): void {
    this.situation = (value || '') as SeguimientoSituacion | '';
    this.load();
  }

  onSearch(value: string): void {
    this.search = value ?? '';
    this.requestViewUpdate();
  }

  get filteredRows(): SeguimientoFila[] {
    const q = this.search.trim().toLowerCase();
    if (!q) return this.rows;
    const digitos = q.replace(/\D/g, '');
    return this.rows.filter((r) =>
      r.name.toLowerCase().includes(q) ||
      r.email.toLowerCase().includes(q) ||
      (digitos !== '' && (r.phone || '').replace(/\D/g, '').includes(digitos)) ||
      (r.sponsorName || '').toLowerCase().includes(q) ||
      (r.lastOrder?.id || '').toLowerCase().includes(q)
    );
  }

  count(situation: SeguimientoSituacion): number {
    return this.rows.filter((r) => r.situation === situation).length;
  }

  get guestCount(): number {
    return this.rows.filter((r) => r.isGuest).length;
  }

  get excludedText(): string {
    const partes: string[] = [];
    if (this.excluded.doNotContact) {
      partes.push(`${this.excluded.doNotContact} que pidieron "no contactar"`);
    }
    if (this.excluded.otherExecutive) {
      partes.push(`${this.excluded.otherExecutive} de otra ejecutiva (cámbiate a "Todas" para verlas)`);
    }
    return partes.length ? `No se muestran: ${partes.join(' y ')}.` : '';
  }

  // --- Etiquetas ---------------------------------------------------------------

  situationTone(situation: SeguimientoSituacion): Tono {
    switch (situation) {
      case 'clabe_pendiente':
      case 'pedido_tardio':
        return 'danger';
      case 'bienvenida':
        return 'active';
      case 'fria':
        return 'pending';
      default:
        return 'inactive';
    }
  }

  situationHelp(situation: SeguimientoSituacion): string {
    switch (situation) {
      case 'clabe_pendiente':
        return 'Tiene comisión confirmada y no ha registrado su CLABE: no se le puede depositar.';
      case 'pedido_tardio':
        return `Pagó y su pedido lleva ${this.thresholds.lateOrderDays}+ días sin despachar, o va enviado 7+ días sin entrega. Avísale; almacén despacha.`;
      case 'bienvenida':
        return `Se registró hace menos de ${this.thresholds.welcomeDays} días y aún no compra.`;
      case 'fria':
        return `Lleva ${this.thresholds.coldDays}+ días sin comprar (o nunca compró y ya pasó la bienvenida).`;
      default:
        // G/11: ya tiene plantilla propia, así que el texto deja de cerrar la puerta.
        return 'Compró hace poco; no necesita contacto hoy. Si le escribes, es para preguntarle cómo le fue.';
    }
  }

  originLabel(origin: string): string {
    return ETIQUETAS_ORIGEN[origin || ''] ?? origin;
  }

  preferenceLabel(value: string): string {
    return ETIQUETAS_PREFERENCIA[value || ''] ?? value;
  }

  channelLabel(value: CanalContacto): string {
    return ETIQUETAS_CANAL[value];
  }

  modeLabel(row: SeguimientoFila): string {
    if (row.isGuest) return 'Invitado (sin cuenta)';
    if (row.mode === 'cliente') return 'Cliente';
    return 'Socio/a';
  }

  daysLabel(days: number | null): string {
    if (days === null || days === undefined) return 'nunca';
    if (days === 0) return 'hoy';
    if (days === 1) return '1 día';
    return `${days} días`;
  }

  formatMoney(value: number | null | undefined): string {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number(value ?? 0));
  }

  executiveName(id: string): string {
    return this.executives.find((e) => e.id === id)?.name ?? '';
  }

  get executiveOptions(): Array<{ value: string; label: string }> {
    return [
      { value: '', label: 'Sin asignar (cartera FindingU)' },
      ...this.executives.map((e) => ({ value: e.id, label: e.active ? e.name : `${e.name} (inactiva)` }))
    ];
  }

  get templateOptions(): Array<{ value: string; label: string }> {
    return [
      { value: '', label: 'Sin plantilla (escribo yo)' },
      ...Object.entries(this.templates).map(([key, t]) => ({ value: key, label: t.title }))
    ];
  }

  writeDisabledReason(row: SeguimientoFila): string {
    return row.whatsappUrl ? '' : (row.phone ? 'El teléfono de la ficha no es un celular de 10 dígitos' : 'Sin teléfono en la ficha');
  }

  trackRow(_index: number, row: SeguimientoFila): string {
    return row.customerId || `invitado:${row.email}`;
  }

  // --- Escribir --------------------------------------------------------------

  openWrite(row: SeguimientoFila): void {
    this.writeRow = row;
    this.blockedLink = '';
    this.linkCopied = false;
    this.writeChannel = row.whatsappUrl ? 'whatsapp' : (row.contactPreference === 'email' ? 'email' : 'call');
    // G/11: mientras una situación no tenga plantilla no se propone ninguna. El
    // respaldo a 'fria' dejó a Gaby a un clic de mandarle "Hace tiempo que no te
    // vemos por la tienda" a Julio, con el pedido entregado el viernes.
    const suggested = row.templateKey && this.templates[row.templateKey] ? row.templateKey : '';
    this.writeTemplateKey = suggested;
    this.writeMessage = this.render(suggested, row);
    this.requestViewUpdate();
  }

  changeTemplate(key: string): void {
    this.writeTemplateKey = key || '';
    if (this.writeRow) {
      this.writeMessage = this.render(this.writeTemplateKey, this.writeRow);
    }
    this.requestViewUpdate();
  }

  render(templateKey: string, row: SeguimientoFila): string {
    const template = this.templates[templateKey];
    if (!template) return '';
    const valores: Record<string, string> = {
      nombre: row.placeholders?.nombre || row.name.split(' ')[0] || '',
      coach: row.placeholders?.coach || this.coachName || 'tu coach',
      producto: row.placeholders?.producto || 'tu último pedido',
      monto: row.placeholders?.monto || '',
      folio: row.placeholders?.folio || ''
    };
    return template.text.replace(/\{(nombre|coach|producto|monto|folio)\}/g, (_m, clave: string) => valores[clave] ?? '');
  }

  closeWrite(): void {
    if (this.isSavingContact) return;
    this.writeRow = null;
    this.blockedLink = '';
    this.requestViewUpdate();
  }

  get writeCanSend(): boolean {
    if (!this.writeRow || this.isSavingContact || !this.writeMessage.trim()) return false;
    if (this.writeChannel === 'whatsapp' && !this.writeRow.whatsappUrl) return false;
    return true;
  }

  get writeButtonLabel(): string {
    return this.writeChannel === 'whatsapp' ? 'Abrir WhatsApp y anotar' : 'Guardar la nota';
  }

  /**
   * Abre WhatsApp en el mismo clic (si se espera al servidor el navegador lo
   * bloquea) y registra la nota. Si aun así se bloquea, se muestra el enlace.
   */
  sendContact(): void {
    const row = this.writeRow;
    if (!row || !this.writeCanSend) return;
    const message = this.writeMessage.trim();
    let popup: Window | null = null;
    if (this.writeChannel === 'whatsapp') {
      const url = `${row.whatsappUrl}?text=${encodeURIComponent(message)}`;
      popup = window.open(url, '_blank', 'noopener,noreferrer');
      if (!popup) {
        this.blockedLink = url;
      }
    }
    this.isSavingContact = true;
    this.seguimiento
      .contacto(row.isGuest ? 'invitado' : row.customerId, {
        channel: this.writeChannel,
        templateKey: this.writeTemplateKey || undefined,
        message,
        guestEmail: row.isGuest ? row.email : undefined
      })
      .pipe(finalize(() => { this.isSavingContact = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (r) => {
          const hora = new Date(r.note.at).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
          this.patchRow(row, { daysSinceLastContact: 0, lastContactAt: r.lastContactAt });
          if (this.blockedLink) {
            this.blockedLink = r.whatsappUrl || this.blockedLink;
            this.showSnackbar(`Nota guardada a las ${hora} (${r.note.text.split(':')[0]}). El navegador no abrió WhatsApp: copia el enlace.`);
          } else {
            this.showSnackbar(`Nota guardada a las ${hora}: "${r.note.text.split(':')[0]}" para ${r.customerName || row.name}.`);
            this.writeRow = null;
          }
        },
        error: (error: unknown) => {
          this.showSnackbar(this.errorMessage(error, 'No se pudo guardar la nota. Si ya mandaste el mensaje, anótalo desde la ficha.'), 'error');
        }
      });
  }

  copyBlockedLink(): void {
    if (!this.blockedLink) return;
    const done = () => {
      this.linkCopied = true;
      this.showSnackbar('Enlace copiado. Pégalo en el navegador o en WhatsApp Web.');
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(this.blockedLink).then(done).catch(() => this.showSnackbar('No se pudo copiar; selecciona el enlace y cópialo a mano.', 'error'));
    } else {
      this.showSnackbar('Tu navegador no permite copiar automáticamente; selecciona el enlace y cópialo a mano.', 'error');
    }
  }

  // --- Ficha -----------------------------------------------------------------

  openFicha(row: SeguimientoFila): void {
    if (row.isGuest) {
      this.guestRow = row;
    } else {
      this.fichaRow = row;
      this.fichaPreference = (row.contactPreference || '') as PreferenciaContacto | '';
      this.fichaExecutiveId = row.executiveId || '';
    }
    this.requestViewUpdate();
  }

  closeFicha(): void {
    if (this.isSavingFicha) return;
    this.fichaRow = null;
    this.requestViewUpdate();
  }

  get fichaHasChanges(): boolean {
    const row = this.fichaRow;
    if (!row) return false;
    return (this.fichaPreference || '') !== (row.contactPreference || '') || (this.fichaExecutiveId || '') !== (row.executiveId || '');
  }

  saveFicha(): void {
    const row = this.fichaRow;
    if (!row || !this.fichaHasChanges || this.isSavingFicha) return;
    const payload: { contactPreference?: PreferenciaContacto; executiveId?: string } = { executiveId: this.fichaExecutiveId || '' };
    if (this.fichaPreference) {
      payload.contactPreference = this.fichaPreference;
    }
    this.isSavingFicha = true;
    this.seguimiento
      .actualizarFicha(row.customerId, payload)
      .pipe(finalize(() => { this.isSavingFicha = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (r) => {
          const saved = r.customer ?? {};
          const preference = String(saved['contactPreference'] ?? '');
          const executiveId = String(saved['executiveId'] ?? '');
          this.patchRow(row, { contactPreference: preference, executiveId, executiveName: this.executiveName(executiveId) });
          const ejecutiva = this.executiveName(executiveId) || 'sin asignar (cartera FindingU)';
          this.showSnackbar(`Ficha guardada: contacto por ${this.preferenceLabel(preference).toLowerCase()}, ejecutiva ${ejecutiva}.`);
          this.fichaRow = null;
        },
        error: (error: unknown) => this.showSnackbar(this.errorMessage(error, 'No se pudo guardar la ficha.'), 'error')
      });
  }

  closeGuest(): void {
    if (this.isCreatingGuest) return;
    this.guestRow = null;
    this.requestViewUpdate();
  }

  createGuestProfile(): void {
    const row = this.guestRow;
    if (!row || this.isCreatingGuest) return;
    this.isCreatingGuest = true;
    this.seguimiento
      .crearFichaInvitado(row.email)
      .pipe(finalize(() => { this.isCreatingGuest = false; this.requestViewUpdate(); }))
      .subscribe({
        next: (r) => {
          const nombre = String(r.customer?.['name'] ?? row.name);
          const ligados = (r.linkedOrders ?? []).length;
          this.showSnackbar(`Ficha creada para ${nombre} con ${ligados} pedido${ligados === 1 ? '' : 's'} ligado${ligados === 1 ? '' : 's'}. Ya aparece como cliente.`);
          this.guestRow = null;
          this.load();
        },
        error: (error: unknown) => this.showSnackbar(this.errorMessage(error, 'No se pudo crear la ficha.'), 'error')
      });
  }

  // --- Utilidades ------------------------------------------------------------

  private patchRow(row: SeguimientoFila, cambios: Partial<SeguimientoFila>): void {
    const key = this.trackRow(0, row);
    this.rows = this.rows.map((r) => (this.trackRow(0, r) === key ? { ...r, ...cambios } : r));
    if (this.writeRow && this.trackRow(0, this.writeRow) === key) this.writeRow = { ...this.writeRow, ...cambios };
    if (this.fichaRow && this.trackRow(0, this.fichaRow) === key) this.fichaRow = { ...this.fichaRow, ...cambios };
  }

  showSnackbar(message: string, tone: 'success' | 'error' = 'success'): void {
    if (this.snackbarTimeout) {
      window.clearTimeout(this.snackbarTimeout);
    }
    this.snackbar = { message, tone, visible: true };
    this.requestViewUpdate();
    this.snackbarTimeout = window.setTimeout(() => {
      this.snackbar = { ...this.snackbar, visible: false };
      this.requestViewUpdate();
    }, 6000);
  }

  private errorMessage(error: unknown, fallback: string): string {
    if (!error || typeof error !== 'object') return fallback;
    const candidate = error as { error?: { message?: string }; message?: string; status?: number };
    if (candidate.status === 403) return 'Tu usuario no tiene el permiso de Clientes; pídeselo a la gerente.';
    const fromApi = candidate.error?.message;
    return typeof fromApi === 'string' && fromApi.trim() ? fromApi.trim() : fallback;
  }

  private requestViewUpdate(): void {
    this.cdr.markForCheck();
  }
}
