/**
 * Paquete D · ronda 26 — lo que publica `GET /catalog/ayuda`, sin sesión.
 *
 * Julio compró como invitado, le llegó el bote estrellado y para encontrar el
 * teléfono de la tienda a la que ya le había pagado $1,209 tuvo que crear una
 * cuenta y verificar su correo. Aurora probó cuatro rutas sin saber a qué hora
 * abre la sucursal donde va a recoger.
 *
 * El texto de la política de devolución **no se escribe aquí**: llega armado
 * del servidor (`ayuda_handlers.texto_politica`) para que la página, el
 * asistente y los dos correos digan exactamente lo mismo.
 */

export interface ContactoPublico {
  email: string;
  whatsapp: string;
  horario: string;
  direccion: string;
  avisoPrivacidadUrl?: string;
}

export interface SucursalPublica {
  id: string;
  name: string;
  location: string;
  city: string;
  state: string;
}

/** Uno de los seis puntos del proceso de devolución. */
export interface PasoPolitica {
  clave: 'que' | 'plazo' | 'evidencia' | 'envio' | 'direccion' | 'reembolso' | string;
  titulo: string;
  texto: string;
}

export interface MotivoDevolucion {
  key: string;
  label: string;
  limiteHoras: number;
  plazoTexto: string;
  responsableEnvio: 'empresa' | 'cliente';
  responsableTexto: string;
  evidencia: 'completa' | 'paquete_cerrado' | string;
  evidenciaTexto: string;
}

export interface PoliticaDevolucion {
  motivos: MotivoDevolucion[];
  pasos: PasoPolitica[];
  direccionDevolucion: string;
  inspeccionDiasHabiles: string;
  refundMethod: string;
  refundBusinessDays: string;
}

export interface AyudaPublica {
  contacto: ContactoPublico;
  sucursales: SucursalPublica[];
  devoluciones: PoliticaDevolucion;
}

/**
 * Propuesta 24 · lo que `GET /orders/{id}` dice del botón "Devolver / Llegó
 * dañado": si se puede pulsar y, si no, por qué. El motivo y el plazo los
 * calcula el servidor con la misma regla con la que valida la solicitud.
 */
export interface EstadoDevolucionPedido {
  puedeSolicitar: boolean;
  motivo: string;
  horasRestantes: number | null;
  plazoTexto: string;
  motivos: MotivoDevolucion[];
}

/** Enlace de WhatsApp a partir del número publicado ("+52 33 1234 5678"). */
export function enlaceWhatsapp(numero: string | undefined | null, mensaje = ''): string {
  const digitos = String(numero ?? '').replace(/[^\d]/g, '');
  if (!digitos) {
    return '';
  }
  const texto = mensaje ? `?text=${encodeURIComponent(mensaje)}` : '';
  return `https://wa.me/${digitos}${texto}`;
}
