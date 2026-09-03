/** Paquete F · coach-seguimiento (propuestas 15 y 19). */

export type SeguimientoSituacion = 'bienvenida' | 'fria' | 'clabe_pendiente' | 'pedido_tardio' | 'activa';
export type SeguimientoAlcance = 'mine' | 'all';
export type CanalContacto = 'whatsapp' | 'email' | 'call';
export type PreferenciaContacto = 'whatsapp' | 'email' | 'none';

export interface SeguimientoUltimoPedido {
  id: string;
  createdAt: string | null;
  total: number;
  status: string;
  productName: string;
}

export interface SeguimientoMarcadores {
  nombre: string;
  coach: string;
  producto: string;
  monto: string;
  folio: string;
}

export interface SeguimientoFila {
  /** Vacío cuando es un comprador invitado sin ficha. */
  customerId: string;
  isGuest: boolean;
  email: string;
  name: string;
  mode: string;
  phone: string;
  /** `https://wa.me/52XXXXXXXXXX`; vacío si el teléfono no cuadra a 10 dígitos. */
  whatsappUrl: string;
  sponsorName: string;
  executiveId: string;
  executiveName: string;
  origin: string;
  contactPreference: string;
  lastOrder: SeguimientoUltimoPedido | null;
  registeredAt: string | null;
  daysSinceRegistration: number | null;
  daysSinceLastPurchase: number | null;
  daysSinceLastContact: number | null;
  lastContactAt: string | null;
  situation: SeguimientoSituacion;
  situationLabel: string;
  urgent: boolean;
  priority: number;
  templateKey: string;
  placeholders: SeguimientoMarcadores;
  /** Solo invitados: cuántos pedidos hizo con ese correo. */
  orderCount?: number;
}

export interface SeguimientoEjecutiva {
  id: string;
  name: string;
  active: boolean;
}

export interface SeguimientoHoyRespuesta {
  date: string;
  scope: SeguimientoAlcance;
  executiveId: string;
  coachName: string;
  rows: SeguimientoFila[];
  total: number;
  excluded: { doNotContact: number; otherExecutive: number };
  executives: SeguimientoEjecutiva[];
  thresholds: { coldDays: number; welcomeDays: number; lateOrderDays: number };
}

export interface SeguimientoPlantilla {
  title: string;
  text: string;
}

export interface SeguimientoPlantillasRespuesta {
  templates: Record<string, SeguimientoPlantilla>;
  placeholders: string[];
}

export interface ContactoPayload {
  channel: CanalContacto;
  templateKey?: string;
  message: string;
  /** Obligatorio cuando el id es `invitado`. */
  guestEmail?: string;
}

export interface NotaContacto {
  text: string;
  by: string;
  at: string;
  channel: CanalContacto;
  templateKey: string;
}

export interface ContactoRespuesta {
  note: NotaContacto;
  whatsappUrl: string;
  customerId?: string;
  customerName?: string;
  guestEmail?: string;
  lastContactAt: string;
}

export interface FichaSeguimientoPayload {
  contactPreference?: PreferenciaContacto;
  executiveId?: string;
}

export interface FichaInvitadoRespuesta {
  customer: Record<string, unknown> & { customerId?: number | string; name?: string; email?: string };
  linkedOrders: string[];
}
