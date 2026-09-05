import { UserPrivileges } from './privileges.model';

export interface AdminEmployee {
  id: number;
  name: string;
  email: string;
  phone?: string;
  canAccessAdmin: boolean;
  privileges: UserPrivileges;
  active: boolean;
  createdAt?: string;
  tempPassword?: string;
  /** Puesto que pinta la insignia del back office: "Caja", "Almacén", "Coach" (paquete E). */
  jobTitle?: string;
  // paquete D · bodega por defecto del empleado
  defaultStockId?: string;
}

export interface CreateEmployeePayload {
  name: string;
  email: string;
  phone?: string;
  /** Puesto real de la persona; no cambia su rol ni sus privilegios (paquete E). */
  jobTitle?: string;
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
}

export interface UpdateEmployeePrivilegesPayload {
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
}
